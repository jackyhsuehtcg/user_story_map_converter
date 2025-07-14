"""
Enhanced Lark API Client

Based on analysis of jira_sync_v3 implementation, this client provides:
- Robust HTTP request handling with retry mechanisms
- Thread-safe authentication management
- Intelligent rate limiting
- Parallel pagination support
- Comprehensive error handling
- Performance monitoring
"""

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import random

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class LarkErrorType(Enum):
    """Lark API error types for specific handling"""
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    FIELD_ERROR = "field_error"
    NETWORK = "network"
    SERVER = "server"
    UNKNOWN = "unknown"


@dataclass
class LarkResponse:
    """Enhanced response object with detailed error information"""
    success: bool
    data: Optional[Dict] = None
    error_type: Optional[LarkErrorType] = None
    error_message: Optional[str] = None
    retry_after: Optional[int] = None
    response_time: Optional[float] = None


class LarkAuthError(Exception):
    """Authentication related errors"""
    pass


class LarkRateLimitError(Exception):
    """Rate limit exceeded"""
    pass


class LarkFieldError(Exception):
    """Field-related errors"""
    pass


class EnhancedAuthManager:
    """Thread-safe authentication manager with retry logic"""
    
    def __init__(self, app_id: str, app_secret: str, config: Dict, logger):
        self.app_id = app_id
        self.app_secret = app_secret
        self.config = config
        self.logger = logger
        
        # Token management
        self._token = None
        self._token_expire_time = None
        self._token_lock = threading.Lock()
        
        # Configuration
        self.auth_url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
        self.auth_retries = config.get('auth_retries', 3)
        self.refresh_buffer = config.get('token_refresh_buffer', 300)  # 5 minutes buffer
        self.timeout = config.get('timeout', 30)
        
        # Metrics
        self.auth_refreshes = 0
        
    def get_valid_token(self) -> Optional[str]:
        """Get valid access token with automatic refresh"""
        with self._token_lock:
            if self._needs_refresh():
                self.logger.debug("Access Token 即將過期，開始刷新")
                success = self._refresh_token_with_retry()
                if not success:
                    self.logger.critical("無法獲取有效的 Access Token，系統將無法正常運作")
                    return None
                self.logger.info("Access Token 刷新成功")
                self.auth_refreshes += 1
            
            return self._token
    
    def _needs_refresh(self) -> bool:
        """Check if token needs refresh (following jira_sync_v3 pattern)"""
        return (not self._token or 
                not self._token_expire_time or 
                datetime.now() >= self._token_expire_time)
    
    def _refresh_token_with_retry(self) -> bool:
        """Refresh token with retry logic"""
        for attempt in range(self.auth_retries):
            try:
                self.logger.debug(f"嘗試刷新 Access Token (第{attempt+1}次)")
                
                response = self._request_new_token()
                if response.success:
                    self._update_token(response.data)
                    return True
                else:
                    self.logger.warning(f"Token 刷新失敗，將重試 (第{attempt+1}次): {response.error_message}")
                    
            except Exception as e:
                self.logger.error(f"Token 刷新異常 (第{attempt+1}次): {e}")
                
            # Wait before retry with exponential backoff
            if attempt < self.auth_retries - 1:
                delay = 2 ** attempt
                time.sleep(delay)
        
        self.logger.error("Token 刷新失敗，已達最大重試次數")
        return False
    
    def _request_new_token(self) -> LarkResponse:
        """Request new token from Lark API"""
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(
                self.auth_url,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    return LarkResponse(
                        success=True,
                        data=result  # Pass full result, not nested data
                    )
                else:
                    return LarkResponse(
                        success=False,
                        error_type=LarkErrorType.AUTHENTICATION,
                        error_message=result.get('msg', 'Unknown auth error')
                    )
            else:
                return LarkResponse(
                    success=False,
                    error_type=LarkErrorType.NETWORK,
                    error_message=f"HTTP {response.status_code}: {response.text}"
                )
                
        except requests.exceptions.RequestException as e:
            return LarkResponse(
                success=False,
                error_type=LarkErrorType.NETWORK,
                error_message=f"Network error: {e}"
            )
    
    def _update_token(self, token_data: Dict):
        """Update token and expiration time"""
        self._token = token_data.get('tenant_access_token')
        
        # Calculate expiration time with 5-minute buffer (following jira_sync_v3 pattern)
        expires_in = token_data.get('expire', 7200)  # Default 2 hours
        self._token_expire_time = datetime.now() + timedelta(seconds=expires_in - 300)
        
        self.logger.debug(f"Token 更新成功，過期時間: {self._token_expire_time}")
    
    def is_token_valid(self) -> bool:
        """Check if current token is valid (following jira_sync_v3 pattern)"""
        return (self._token is not None and 
                self._token_expire_time is not None and 
                datetime.now() < self._token_expire_time)


class RateLimitManager:
    """Dynamic rate limiting manager"""
    
    def __init__(self, config: Dict, logger):
        self.config = config
        self.logger = logger
        self.rate_limit_enabled = config.get('rate_limit_enabled', True)
        self.requests_per_minute = config.get('requests_per_minute', 100)
        self.request_timestamps = []
        self.lock = threading.Lock()
        
        # Metrics
        self.rate_limit_hits = 0
        
    def wait_if_needed(self):
        """Check and wait for rate limiting"""
        if not self.rate_limit_enabled:
            return
            
        with self.lock:
            now = time.time()
            # Clean up timestamps older than 1 minute
            self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]
            
            if len(self.request_timestamps) >= self.requests_per_minute:
                wait_time = 60 - (now - self.request_timestamps[0])
                if wait_time > 0:
                    self.logger.warning(f"觸發 API 速率限制，將等待 {wait_time:.2f}秒")
                    self.rate_limit_hits += 1
                    time.sleep(wait_time)
            
            self.request_timestamps.append(now)
            self.logger.debug(f"目前 API 請求數: {len(self.request_timestamps)}/{self.requests_per_minute}")


class RequestManager:
    """Enhanced HTTP request manager with retry logic"""
    
    def __init__(self, config: Dict, logger):
        self.config = config
        self.logger = logger
        
        # Configuration
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.base_delay = config.get('retry_base_delay', 1.0)
        self.max_delay = config.get('retry_max_delay', 60.0)
        
        # Setup session with connection pooling
        self.session = requests.Session()
        retry_strategy = Retry(
            total=0,  # We handle retries manually
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Metrics
        self.requests_total = 0
        self.requests_failed = 0
        self.avg_response_time = 0.0
        
    def make_request_with_retry(self, method: str, url: str, **kwargs) -> LarkResponse:
        """Make HTTP request with exponential backoff retry"""
        last_exception = None
        
        # DEBUG: Log request details
        self.logger.debug(f"Lark API 請求: {method} {url}, 參數: {kwargs}")
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                response = self._make_single_request(method, url, **kwargs)
                response_time = time.time() - start_time
                
                # Update metrics
                self._update_metrics(response_time, response.success)
                
                if response.success:
                    self.logger.debug(f"API 請求成功: {method} {url}")
                    response.response_time = response_time
                    return response
                    
                # Handle retryable errors
                if self._should_retry(response, attempt):
                    delay = self._calculate_delay(attempt, response)
                    self.logger.warning(f"API 請求失敗，將在 {delay:.2f}秒後重試 (第{attempt+1}次): {response.error_message}")
                    time.sleep(delay)
                    continue
                else:
                    self.logger.error(f"API 請求失敗且無法重試: {response.error_message}")
                    return response
                    
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt, None)
                    self.logger.error(f"網路請求異常，將在 {delay:.2f}秒後重試: {e}")
                    time.sleep(delay)
                else:
                    break
        
        # All retries failed
        self.logger.critical(f"API 請求完全失敗，已達最大重試次數: {last_exception}")
        return LarkResponse(
            success=False,
            error_type=LarkErrorType.NETWORK,
            error_message=f"重試{self.max_retries}次後仍失敗: {last_exception}"
        )
    
    def _make_single_request(self, method: str, url: str, **kwargs) -> LarkResponse:
        """Make single HTTP request"""
        try:
            response = self.session.request(
                method, 
                url, 
                timeout=self.timeout,
                **kwargs
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            return LarkResponse(
                success=False,
                error_type=LarkErrorType.NETWORK,
                error_message=f"Network error: {e}"
            )
    
    def _handle_response(self, response: requests.Response) -> LarkResponse:
        """Handle API response with proper error classification"""
        if response.status_code == 401:
            return LarkResponse(
                success=False,
                error_type=LarkErrorType.AUTHENTICATION,
                error_message="認證失敗"
            )
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            return LarkResponse(
                success=False,
                error_type=LarkErrorType.RATE_LIMIT,
                error_message="速率限制",
                retry_after=retry_after
            )
        elif response.status_code >= 500:
            return LarkResponse(
                success=False,
                error_type=LarkErrorType.SERVER,
                error_message=f"伺服器錯誤: {response.status_code}"
            )
        elif response.status_code != 200:
            return LarkResponse(
                success=False,
                error_type=LarkErrorType.UNKNOWN,
                error_message=f"HTTP {response.status_code}: {response.text}"
            )
        
        try:
            result = response.json()
            if result.get('code') == 0:
                return LarkResponse(
                    success=True,
                    data=result.get('data', {})
                )
            else:
                error_msg = result.get('msg', 'Unknown error')
                if 'FieldNameNotFound' in error_msg:
                    return LarkResponse(
                        success=False,
                        error_type=LarkErrorType.FIELD_ERROR,
                        error_message=f"欄位錯誤: {error_msg}"
                    )
                else:
                    return LarkResponse(
                        success=False,
                        error_type=LarkErrorType.UNKNOWN,
                        error_message=f"API 錯誤: {error_msg}"
                    )
                    
        except json.JSONDecodeError:
            return LarkResponse(
                success=False,
                error_type=LarkErrorType.UNKNOWN,
                error_message="Invalid JSON response"
            )
    
    def _should_retry(self, response: LarkResponse, attempt: int) -> bool:
        """Determine if request should be retried"""
        if attempt >= self.max_retries:
            return False
            
        # Retry on server errors, rate limits, and network errors
        retryable_errors = [
            LarkErrorType.SERVER,
            LarkErrorType.RATE_LIMIT,
            LarkErrorType.NETWORK
        ]
        
        return response.error_type in retryable_errors
    
    def _calculate_delay(self, attempt: int, response: Optional[LarkResponse]) -> float:
        """Calculate delay with exponential backoff and jitter"""
        if response and response.retry_after:
            return min(response.retry_after, self.max_delay)
        
        # Exponential backoff with jitter
        delay = self.base_delay * (2 ** attempt)
        jitter = random.uniform(0.1, 0.3) * delay
        return min(delay + jitter, self.max_delay)
    
    def _update_metrics(self, response_time: float, success: bool):
        """Update performance metrics"""
        self.requests_total += 1
        if not success:
            self.requests_failed += 1
        
        # Calculate rolling average response time
        if self.requests_total == 1:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (
                (self.avg_response_time * (self.requests_total - 1) + response_time) / 
                self.requests_total
            )


class LarkClient:
    """Enhanced Lark API client with comprehensive features"""
    
    def __init__(self, app_id: str, app_secret: str, config: Dict, logger):
        self.app_id = app_id
        self.app_secret = app_secret
        self.config = config
        self.logger = logger
        self.start_time = time.time()
        
        # Initialize managers
        self.auth_manager = EnhancedAuthManager(app_id, app_secret, config, logger)
        self.request_manager = RequestManager(config, logger)
        self.rate_limit_manager = RateLimitManager(config, logger)
        
        # API configuration
        self.base_url = config.get('base_url', 'https://open.larksuite.com/open-apis')
        self.max_page_size = config.get('max_page_size', 500)
        
        # Token cache for wiki_token -> obj_token mapping
        self._token_cache = {}
        
        # Performance metrics
        self.metrics = {
            'requests_total': 0,
            'requests_failed': 0,
            'auth_refreshes': 0,
            'rate_limit_hits': 0,
            'avg_response_time': 0.0
        }
        
        self.logger.info(f"Lark Client 初始化完成，配置: {self._get_config_summary()}")
    
    def _get_config_summary(self) -> Dict:
        """Get configuration summary for logging"""
        return {
            'base_url': self.base_url,
            'max_page_size': self.max_page_size,
            'timeout': self.config.get('timeout', 30),
            'max_retries': self.config.get('max_retries', 3),
            'rate_limit_enabled': self.config.get('rate_limit_enabled', True),
            'requests_per_minute': self.config.get('requests_per_minute', 100)
        }
    
    def _make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> LarkResponse:
        """Make authenticated request to Lark API"""
        # Get valid token
        token = self.auth_manager.get_valid_token()
        if not token:
            return LarkResponse(
                success=False,
                error_type=LarkErrorType.AUTHENTICATION,
                error_message="無法獲取有效的認證 Token"
            )
        
        # Apply rate limiting
        self.rate_limit_manager.wait_if_needed()
        
        # Prepare headers
        headers = kwargs.pop('headers', {})
        headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
        
        # Make request
        url = f"{self.base_url}{endpoint}"
        response = self.request_manager.make_request_with_retry(
            method, url, headers=headers, **kwargs
        )
        
        # Update metrics
        self._update_metrics(response)
        
        return response
    
    def _update_metrics(self, response: LarkResponse):
        """Update client metrics"""
        self.metrics['requests_total'] += 1
        if not response.success:
            self.metrics['requests_failed'] += 1
        
        # Update from managers
        self.metrics['auth_refreshes'] = self.auth_manager.auth_refreshes
        self.metrics['rate_limit_hits'] = self.rate_limit_manager.rate_limit_hits
        self.metrics['avg_response_time'] = self.request_manager.avg_response_time
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            **self.metrics,
            'success_rate': (
                (self.metrics['requests_total'] - self.metrics['requests_failed']) / 
                max(1, self.metrics['requests_total'])
            ),
            'auth_token_valid': self.auth_manager.is_token_valid(),
            'rate_limit_utilization': (
                len(self.rate_limit_manager.request_timestamps) / 
                self.rate_limit_manager.requests_per_minute
            ),
            'uptime': time.time() - self.start_time
        }
    
    def resolve_app_token(self, wiki_token: str) -> Optional[str]:
        """Convert wiki_token to obj_token (app_token) following jira_sync_v3 pattern"""
        # Check cache first
        if wiki_token in self._token_cache:
            self.logger.debug(f"使用快取的 obj_token: {wiki_token}")
            return self._token_cache[wiki_token]
        
        # Make request to get obj_token
        endpoint = f"/wiki/v2/spaces/get_node?token={wiki_token}"
        response = self._make_authenticated_request('GET', endpoint)
        
        if response.success:
            node_data = response.data.get('node', {})
            obj_token = node_data.get('obj_token')
            
            if obj_token:
                # Cache the result
                self._token_cache[wiki_token] = obj_token
                self.logger.info(f"成功解析 wiki_token 到 obj_token: {wiki_token} -> {obj_token}")
                return obj_token
            else:
                self.logger.error(f"API 回應中找不到 obj_token: {response.data}")
        else:
            self.logger.error(f"無法解析 wiki_token: {response.error_message}")
        
        return None

    def get_table_records(self, wiki_token: str, table_id: str, 
                         page_size: Optional[int] = None) -> List[Dict]:
        """Get all records from a table with pagination (using wiki_token)"""
        # Step 1: Resolve wiki_token to obj_token
        obj_token = self.resolve_app_token(wiki_token)
        if not obj_token:
            self.logger.error("無法解析 wiki_token 到 obj_token")
            return []
        
        # Step 2: Use obj_token to fetch table records
        return self._get_table_records_by_obj_token(obj_token, table_id, page_size)
    
    def _get_table_records_by_obj_token(self, obj_token: str, table_id: str, 
                                       page_size: Optional[int] = None) -> List[Dict]:
        """Get all records from a table using obj_token"""
        page_size = page_size or self.max_page_size
        all_records = []
        page_token = None
        
        self.logger.info(f"開始獲取表格記錄: {obj_token}/{table_id}")
        
        while True:
            # Prepare parameters
            params = {'page_size': page_size}
            if page_token:
                params['page_token'] = page_token
            
            # Make request
            endpoint = f"/bitable/v1/apps/{obj_token}/tables/{table_id}/records"
            response = self._make_authenticated_request('GET', endpoint, params=params)
            
            if not response.success:
                self.logger.error(f"獲取表格記錄失敗: {response.error_message}")
                break
            
            # Process response
            records = response.data.get('items', [])
            all_records.extend(records)
            
            self.logger.debug(f"獲取 {len(records)} 筆記錄，累計 {len(all_records)} 筆")
            
            # Check for more pages
            page_token = response.data.get('page_token')
            if not page_token or not response.data.get('has_more', False):
                break
        
        self.logger.info(f"表格記錄獲取完成，共 {len(all_records)} 筆記錄")
        return all_records
    
    def get_table_schema(self, wiki_token: str, table_id: str) -> Optional[Dict]:
        """Get table schema information (using wiki_token)"""
        # Step 1: Resolve wiki_token to obj_token
        obj_token = self.resolve_app_token(wiki_token)
        if not obj_token:
            self.logger.error("無法解析 wiki_token 到 obj_token")
            return None
        
        # Step 2: Use obj_token to fetch table schema
        endpoint = f"/bitable/v1/apps/{obj_token}/tables/{table_id}/fields"
        response = self._make_authenticated_request('GET', endpoint)
        
        if response.success:
            return response.data
        else:
            self.logger.error(f"獲取表格 Schema 失敗: {response.error_message}")
            return None
    
