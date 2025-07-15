# User Story Map Converter - 系統設計建議書 (更新版)

### **1. 專案概述**

將 Lark 多維表格的父子關係資料，轉換為互動式 User Story Map 心智圖。系統提供 Web 介面來管理不同團隊的 Lark 配置，並可將生成的心智圖匯出為多種格式。

### **2. 核心需求**

*   **資料整合**: 讀取 Lark 多維表格資料。
*   **心智圖生成**: 將結構化資料轉換為視覺化心智圖。
*   **多團隊管理**: Web 介面，用於設定多個團隊的 Lark 資料來源。
*   **縮圖與刷新**: 首頁展示各團隊心智圖縮圖，並支援手動觸發刷新。
*   **多格式匯出**: 支援 HTML (互動式)、PNG (靜態圖) 等格式。

### **3. 系統架構設計**

採用適度分層的目錄結構，保持模組化、高內聚、低耦合：

```
user_story_map_converter/
├── app.py                 # Flask 主程式
├── config.yaml           # 系統設定檔
├── requirements.txt       # 依賴管理
├── core/                 # 核心業務邏輯
│   ├── __init__.py
│   ├── lark_client.py   # Lark API 客戶端
│   ├── tree_builder.py  # 樹狀結構建構與父子關係處理
│   ├── mindmap_generator.py  # 心智圖 Markdown 生成
│   ├── task_manager.py  # 背景任務管理
│   ├── config_manager.py # YAML 設定管理
│   ├── logger.py        # 日誌配置與管理
│   └── log_formatter.py # 自定義日誌格式化器
├── models/              # 資料模型
│   ├── __init__.py
│   ├── database.py      # 資料庫操作
│   ├── team.py         # 團隊模型
│   └── task.py         # 任務模型
├── routes/              # Web 路由
│   ├── __init__.py
│   ├── main.py         # 主頁路由
│   ├── teams.py        # 團隊管理
│   └── export.py       # 匯出功能
├── static/              # 靜態檔案
│   ├── css/
│   ├── js/
│   └── images/
├── templates/           # HTML 模板
├── logs/               # 日誌檔案存放
│   ├── app.log         # 主要應用日誌
│   ├── task.log        # 背景任務專用日誌
│   ├── error.log       # 錯誤日誌集中存放
│   └── archive/        # 歷史日誌歸檔
├── temp/               # 臨時檔案與測試資料
│   ├── test_*.py       # 測試腳本
│   └── lark_data_*.json # 從 Lark 提取的原始資料
└── exports/            # 匯出檔案存放
```

**分層架構職責**:
*   **資料處理層**: `core/lark_client.py`, `core/tree_builder.py`
*   **業務邏輯層**: `core/mindmap_generator.py`, `core/task_manager.py`
*   **表現層**: `app.py`, `routes/`, `models/`
*   **支援模組**: `core/config_manager.py`, `core/logger.py`, `models/database.py`

### **4. 技術棧選擇 (已更新)**

*   **後端框架**: **Flask + SQLAlchemy**
    *   **Flask**: 作為應用的輕量化核心。
    *   **SQLAlchemy**: 簡化與 SQLite 的資料庫操作。
    *   **背景任務**: 使用 Python 原生的 `threading` 模組，並透過 `app.app_context()` 模式，確保背景執行緒能安全地與 SQLite 資料庫互動。

*   **前端框架**: **Bootstrap**
    *   採用其成熟的元件庫，快速建立風格統一、響應式且易於維護的前端介面。

*   **設定管理**: **YAML + PyYAML**
    *   使用 `config.yaml` 檔案來儲存所有設定，實現設定與程式碼的完全分離。
    *   建立 `config_manager.py` 模組，專職讀取和提供設定值，提升可維護性。

*   **資料庫**: **SQLite**
    *   輕量、免安裝、單檔案，完美符合本專案的需求。

*   **心智圖生成**: **Markmap (`markmap-cli`)**
    *   後端 Python 邏輯負責將資料轉換為 **Markdown 文字**，然後呼叫 `markmap-cli` 命令列工具，將 Markdown 渲染成互動式心智圖。

*   **匯出引擎**: **Markmap-CLI + 自定義增強**
    *   **HTML**: 直接由 Markmap 生成，產出具備完整互動性的獨立檔案，並注入自定義 CSS/JavaScript 實現 Criteria 浮動顯示功能。
    *   **PNG/PDF**: 預留 Playwright 支援（未來實作）。

### **5. 資料流設計**

```
Lark API → lark_client → tree_builder → mindmap_generator → markmap-cli → HTML 匯出
                                    ↓
                               Criteria 浮動顯示
                              JIRA 超連結整合
```

### **6. 資料管理原則**

**檔案組織規範**:
*   **temp/ 目錄**: 所有臨時檔案、測試資料、開發過程中產生的 JSON 檔案都存放在 `temp/` 目錄
    *   測試腳本: `temp/test_*.py`
    *   Lark 原始資料: `temp/lark_data_*.json`
    *   開發過程中的暫存檔案
*   **logs/ 目錄**: 系統日誌檔案專用
*   **exports/ 目錄**: 最終產品匯出檔案 (PNG, PDF, HTML 等)
*   **static/ 目錄**: Web 靜態資源 (CSS, JS, 圖片)

**資料流管理**:
*   **原始資料提取**: `tools/lark_data_extractor.py` → `temp/lark_data_*.json`
*   **中間處理結果**: 樹狀結構建構、Markdown 生成 → `temp/`
*   **最終產品**: 心智圖匯出 → `exports/`

### **7. 核心功能實作策略**

*   **心智圖生成**:
    *   Python 的核心任務是將 Lark 資料轉換為 **Markdown 格式的文字**。視覺化工作完全交由外部 `markmap-cli` 工具處理。
    *   **自定義增強**: 注入 CSS/JavaScript 實現 Criteria 浮動顯示、JIRA 超連結整合等進階功能。

*   **互動式功能**:
    *   **Criteria 浮動顯示**: 滑鼠懸浮在節點上時顯示驗收條件詳細內容。
    *   **JIRA 整合**: TCG 欄位有值時自動將 Story 編號轉換為 JIRA 超連結。
    *   **資料驗證**: 自動過濾無效或空白的 Story 編號記錄。

*   **Web 介面**:
    *   使用 **Bootstrap** 元件快速搭建管理介面，確保風格統一與響應式佈局。

*   **匯出功能**:
    *   統一使用 `markmap-cli` 作為匯出引擎，由 Flask 背景任務透過 `subprocess` 模組進行呼叫。

### **7. lark_client.py 增強實作設計**

#### **設計理念與強化目標**

基於對 `/Users/hideman/code/jira_sync_v3` 的分析，新版 `lark_client.py` 針對以下核心問題進行強化：

*   **可靠性問題**: 網路抖動或 API 瞬時錯誤導致整個資料拉取任務失敗
*   **效率問題**: 大量資料的循序分頁拉取因網路延遲累加而緩慢
*   **可維護性問題**: 模組直接依賴全域物件，單元測試困難
*   **錯誤處理問題**: 錯誤分類不清晰，難以實施適當的恢復策略

#### **核心架構改進**

新版設計採用以下增強架構：

**模組化管理器架構**:
```python
class LarkClient:
    def __init__(self, app_id: str, app_secret: str, config: Dict, logger: logging.Logger):
        self.app_id = app_id
        self.app_secret = app_secret
        self.config = config
        self.logger = logger
        
        # 初始化子管理器
        self.auth_manager = EnhancedAuthManager(app_id, app_secret, config, logger)
        self.request_manager = RequestManager(config, logger)
        self.batch_manager = BatchManager(config, logger)
        self.rate_limit_manager = RateLimitManager(config, logger)
        
        # 效能監控指標
        self.metrics = {
            'requests_total': 0,
            'requests_failed': 0,
            'auth_refreshes': 0,
            'rate_limit_hits': 0,
            'avg_response_time': 0.0
        }
```

#### **HTTP 請求與重試機制強化**

**指數退避重試機制**:
```python
class RequestManager:
    def make_request_with_retry(self, method: str, url: str, **kwargs) -> LarkResponse:
        """具備指數退避的重試機制"""
        last_exception = None
        
        # DEBUG: 記錄請求詳細資訊
        self.logger.debug(f"Lark API 請求: {method} {url}, 參數: {kwargs}")
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                response = self._make_single_request(method, url, **kwargs)
                response_time = time.time() - start_time
                
                # 更新效能指標
                self._update_metrics(response_time, response.success)
                
                if response.success:
                    self.logger.debug(f"API 請求成功: {method} {url}")
                    return response
                    
                # 處理可重試錯誤
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
        
        # CRITICAL: 所有重試都失敗
        self.logger.critical(f"API 請求完全失敗，已達最大重試次數: {last_exception}")
        return LarkResponse(
            success=False,
            error_type=LarkErrorType.NETWORK,
            error_message=f"重試{self.max_retries}次後仍失敗: {last_exception}"
        )
    
    def _calculate_delay(self, attempt: int, response: Optional[LarkResponse]) -> float:
        """計算退避延遲時間"""
        if response and response.retry_after:
            return min(response.retry_after, self.max_delay)
        
        # 指數退避 + 隨機抖動
        delay = self.base_delay * (2 ** attempt)
        import random
        jitter = random.uniform(0.1, 0.3) * delay
        return min(delay + jitter, self.max_delay)
```

**錯誤類型分類處理**:
```python
class LarkErrorType(Enum):
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    FIELD_ERROR = "field_error"
    NETWORK = "network"
    SERVER = "server"
    UNKNOWN = "unknown"

@dataclass
class LarkResponse:
    success: bool
    data: Optional[Dict] = None
    error_type: Optional[LarkErrorType] = None
    error_message: Optional[str] = None
    retry_after: Optional[int] = None

def _handle_api_error(self, response: requests.Response) -> LarkResponse:
    """增強版錯誤處理"""
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
    
    result = response.json()
    error_msg = result.get('msg', 'Unknown error')
    
    if 'FieldNameNotFound' in error_msg:
        return LarkResponse(
            success=False,
            error_type=LarkErrorType.FIELD_ERROR,
            error_message=f"欄位錯誤: {error_msg}"
        )
    
    return LarkResponse(
        success=False,
        error_type=LarkErrorType.UNKNOWN,
        error_message=f"API 錯誤: {error_msg}"
    )
```

#### **身份驗證管理強化**

**線程安全的 Token 管理**:
```python
class EnhancedAuthManager:
    def __init__(self, app_id: str, app_secret: str, config: Dict, logger: logging.Logger):
        self.app_id = app_id
        self.app_secret = app_secret
        self.config = config
        self.logger = logger
        
        # Token 管理
        self._token = None
        self._token_expire_time = None
        self._token_lock = threading.Lock()
        
        # 配置參數
        self.auth_retries = config.get('auth_retries', 3)
        self.refresh_buffer = config.get('token_refresh_buffer', 300)  # 5分鐘緩衝
        
    def get_valid_token(self) -> Optional[str]:
        """獲取有效的訪問令牌，具備自動重試"""
        with self._token_lock:
            if self._needs_refresh():
                self.logger.debug("Access Token 即將過期，開始刷新")
                success = self._refresh_token_with_retry()
                if not success:
                    self.logger.critical("無法獲取有效的 Access Token，系統將無法正常運作")
                    return None
                self.logger.info("Access Token 刷新成功")
            
            return self._token
    
    def _refresh_token_with_retry(self) -> bool:
        """帶重試的 Token 刷新"""
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
                
            # 等待後重試
            if attempt < self.auth_retries - 1:
                time.sleep(2 ** attempt)
        
        self.logger.error("Token 刷新失敗，已達最大重試次數")
        return False
```

#### **智慧型速率限制管理**

**動態速率限制控制**:
```python
class RateLimitManager:
    def __init__(self, config: Dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.rate_limit_enabled = config.get('rate_limit_enabled', True)
        self.requests_per_minute = config.get('requests_per_minute', 100)
        self.request_timestamps = []
        self.lock = threading.Lock()
        
    def wait_if_needed(self):
        """檢查並等待速率限制"""
        if not self.rate_limit_enabled:
            return
            
        with self.lock:
            now = time.time()
            # 清理超過一分鐘的記錄
            self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]
            
            if len(self.request_timestamps) >= self.requests_per_minute:
                wait_time = 60 - (now - self.request_timestamps[0])
                if wait_time > 0:
                    self.logger.warning(f"觸發 API 速率限制，將等待 {wait_time:.2f}秒")
                    time.sleep(wait_time)
            
            self.request_timestamps.append(now)
            self.logger.debug(f"目前 API 請求數: {len(self.request_timestamps)}/{self.requests_per_minute}")
```

#### **平行化分頁處理**

**並行分頁獲取**:
```python
class ParallelPaginator:
    def __init__(self, client: 'LarkClient', config: Dict):
        self.client = client
        self.config = config
        self.max_workers = config.get('pagination_workers', 5)
        self.enable_parallel = config.get('parallel_pagination', True)
        
    def fetch_all_records(self, obj_token: str, table_id: str) -> List[Dict]:
        """平行化分頁獲取所有記錄"""
        if not self.enable_parallel:
            return self._sequential_fetch(obj_token, table_id)
        
        # 首先獲取第一頁
        first_page = self._fetch_page(obj_token, table_id, page_token=None)
        if not first_page.success:
            return []
        
        all_records = first_page.data.get('items', [])
        self.client.logger.debug(f"第一頁獲取 {len(all_records)} 筆記錄")
        
        # 檢查是否有更多頁面
        if not first_page.data.get('has_more', False):
            self.client.logger.info(f"資料獲取完成，共 {len(all_records)} 筆記錄")
            return all_records
        
        # 根據 API 特性選擇並行或順序處理
        if self._can_parallelize(first_page.data):
            return self._parallel_fetch(obj_token, table_id, first_page.data)
        else:
            return self._sequential_fetch_continuation(obj_token, table_id, first_page.data)
    
    def _parallel_fetch(self, obj_token: str, table_id: str, first_page_data: Dict) -> List[Dict]:
        """並行獲取剩餘頁面"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        all_records = first_page_data.get('items', [])
        
        # 使用線程池並行處理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            page_token = first_page_data.get('page_token')
            
            # 提交並行任務
            while page_token and len(futures) < self.max_workers:
                future = executor.submit(self._fetch_page, obj_token, table_id, page_token)
                futures.append(future)
                page_token = None  # 實際需要根據 API 回應動態調整
            
            # 收集結果
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result.success:
                        items = result.data.get('items', [])
                        all_records.extend(items)
                        self.client.logger.debug(f"並行獲取 {len(items)} 筆記錄")
                except Exception as e:
                    self.client.logger.error(f"並行分頁處理異常: {e}")
        
        self.client.logger.info(f"並行分頁完成，共獲取 {len(all_records)} 筆記錄")
        return all_records
```

#### **智慧批次處理**

**動態批次大小計算**:
```python
class BatchManager:
    def __init__(self, config: Dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.max_batch_size = config.get('max_batch_size', 500)
        self.batch_retry_max = config.get('batch_retry_max', 3)
        
    def calculate_optimal_batch_size(self, records: List[Dict]) -> int:
        """根據記錄複雜度計算最佳批次大小"""
        if not records:
            return self.max_batch_size
        
        # 採樣分析
        sample_size = min(10, len(records))
        total_fields = 0
        total_content_length = 0
        
        for i in range(sample_size):
            record = records[i]
            field_count = len(record)
            content_length = len(str(record))
            
            total_fields += field_count
            total_content_length += content_length
        
        avg_fields = total_fields / sample_size
        avg_content_length = total_content_length / sample_size
        
        # 動態調整批次大小
        if avg_fields > 20 or avg_content_length > 2000:
            batch_size = min(200, self.max_batch_size)
        elif avg_fields > 10 or avg_content_length > 1000:
            batch_size = min(350, self.max_batch_size)
        else:
            batch_size = self.max_batch_size
        
        self.logger.debug(f"計算批次大小: {batch_size} (平均欄位數: {avg_fields:.1f}, 平均長度: {avg_content_length:.1f})")
        return batch_size
    
    def batch_process_with_fallback(self, operation: str, items: List[Any]) -> BatchResult:
        """增強批次處理，支援個別處理回退"""
        batch_size = self.calculate_optimal_batch_size(items)
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            try:
                # 嘗試批次操作
                self.logger.debug(f"執行批次操作 {operation}，批次大小: {len(batch)}")
                result = self._execute_batch_operation(operation, batch)
                
                if result.success:
                    self.logger.debug(f"批次操作成功: {len(batch)} 筆記錄")
                    continue
                    
                # 批次失敗，回退到個別處理
                self.logger.warning(f"批次操作失敗，回退到個別處理: {result.error_message}")
                self._fallback_to_individual_operations(operation, batch)
                
            except Exception as e:
                self.logger.error(f"批次操作異常: {e}")
                self._fallback_to_individual_operations(operation, batch)
```

#### **效能監控與指標**

**綜合效能指標**:
```python
class LarkClient:
    def get_performance_metrics(self) -> Dict[str, Any]:
        """獲取綜合效能指標"""
        return {
            **self.metrics,
            'success_rate': (self.metrics['requests_total'] - self.metrics['requests_failed']) / max(1, self.metrics['requests_total']),
            'auth_token_valid': self.auth_manager.is_token_valid(),
            'rate_limit_utilization': len(self.rate_limit_manager.request_timestamps) / self.rate_limit_manager.requests_per_minute,
            'last_error': self._get_last_error(),
            'uptime': time.time() - self.start_time
        }
    
    def _update_metrics(self, response_time: float, success: bool):
        """更新效能指標"""
        self.metrics['requests_total'] += 1
        if not success:
            self.metrics['requests_failed'] += 1
        
        # 計算平均回應時間
        current_avg = self.metrics['avg_response_time']
        total_requests = self.metrics['requests_total']
        self.metrics['avg_response_time'] = (current_avg * (total_requests - 1) + response_time) / total_requests
```

#### **日誌記錄規範**

**統一的日誌層級使用**:
*   **DEBUG**: API 請求/回應詳細內容、Token 刷新過程、速率限制狀態、樹狀結構建構過程、Threading 任務狀態
*   **INFO**: 重要操作完成 (系統啟動、Token 刷新成功、資料獲取完成、心智圖生成成功)
*   **WARNING**: 可重試錯誤 (API 請求失敗、速率限制觸發、任務執行時間過長、設定檔異常)
*   **ERROR**: 功能失敗 (認證失敗、網路異常、批次處理失敗、資料庫操作錯誤、Markmap 執行失敗)
*   **CRITICAL**: 系統級錯誤 (所有重試失敗、認證完全失敗、資料庫連接失敗、核心服務無法啟動)

**具體日誌實作模式**:
```python
# 請求處理日誌
self.logger.debug(f"Lark API 請求: {method} {url}, 參數: {kwargs}")
self.logger.debug(f"API 回應時間: {response_time:.3f}秒")
self.logger.warning(f"API 請求失敗，將在 {delay:.2f}秒後重試 (第{attempt+1}次): {error_message}")
self.logger.error(f"API 請求失敗且無法重試: {error_message}")
self.logger.critical(f"API 請求完全失敗，已達最大重試次數: {exception}")

# 認證管理日誌
self.logger.debug("Access Token 即將過期，開始刷新")
self.logger.info("Access Token 刷新成功")
self.logger.warning(f"Token 刷新失敗，將重試 (第{attempt+1}次): {error_message}")
self.logger.error(f"Token 刷新異常 (第{attempt+1}次): {exception}")
self.logger.critical("無法獲取有效的 Access Token，系統將無法正常運作")

# 速率限制日誌
self.logger.debug(f"目前 API 請求數: {current_requests}/{max_requests}")
self.logger.warning(f"觸發 API 速率限制，將等待 {wait_time:.2f}秒")

# 資料處理日誌
self.logger.debug(f"正在處理第 {page_num} 頁資料")
self.logger.info(f"全表掃描完成，共獲取 {record_count} 筆記錄")
self.logger.warning(f"發現異常記錄，已跳過: {record_id}")
self.logger.error(f"資料處理失敗: {error_details}")
```

**配置驅動的功能特性**:
```python
# config.yaml 範例
lark_client:
  timeout: 30
  max_retries: 3
  retry_base_delay: 1.0
  retry_max_delay: 60.0
  auth_retries: 3
  token_refresh_buffer: 300
  
  # 速率限制
  rate_limit_enabled: true
  requests_per_minute: 100
  
  # 批次處理
  max_batch_size: 500
  dynamic_batch_sizing: true
  batch_retry_max: 3
  
  # 並行處理
  parallel_pagination: true
  pagination_workers: 5
```

## 8. Markmap 心智圖生成技術規範

### **Markmap 基本概念**

Markmap 是結合 Markdown 和心智圖的工具，將 Markdown 內容解析並提取其內在層次結構，渲染成互動式心智圖。

**核心組件**:
- **markmap-lib**: 預處理 Markdown 為結構化資料
- **markmap-view**: 將資料渲染為互動式 SVG
- **markmap-cli**: 命令列工具，生成 HTML/PNG/SVG 等格式

### **CLI 工具使用**

**安裝**:
```bash
npm install -g markmap-cli
# 或使用 npx (免安裝)
npx markmap input.md
```

**基本語法**:
```bash
markmap [options] <input.md>

# 常用選項
--no-open           # 不自動開啟輸出檔案
--no-toolbar        # 不顯示工具列
-o, --output <file> # 指定輸出檔案名稱
--offline           # 內嵌所有資源，離線可用
-w, --watch         # 監控檔案變化（開發模式）
```

**輸出格式**:
```bash
# 生成 HTML（預設）
markmap story.md -o story.html

# 離線版本（內嵌所有資源）
markmap story.md --offline -o story_offline.html

# 注意：當前版本的 markmap-cli (0.18.12) 只支援 HTML 輸出
# PNG/SVG 生成需要額外工具或方法
```

### **Markdown 語法規範**

**層次結構**:
```markdown
# 根節點 (Level 1)
## 分支節點 (Level 2)
### 葉節點 (Level 3)
#### 子葉節點 (Level 4)
##### 深層節點 (Level 5)
###### 最深節點 (Level 6)
```

**進階語法支援**:
```markdown
### 文字樣式
- **粗體** ~~刪除線~~ *斜體* ==高亮==
- `行內程式碼`
- [x] 核取方塊
- [連結文字](https://example.com)

### 數學公式 (KaTeX)
- 公式: $x = {-b \pm \sqrt{b^2-4ac} \over 2a}$

### 程式碼區塊
```javascript
console.log('hello, JavaScript')
```

### 表格
| 產品 | 價格 |
|------|------|
| 蘋果 | 4 元 |
| 香蕉 | 2 元 |

### 圖片
![圖片描述](https://example.com/image.png)

### 有序列表
1. 項目 1
2. 項目 2
   - 子項目 2.1
   - 子項目 2.2
```

### **配置選項 (Frontmatter)**

在 Markdown 檔案開頭使用 YAML frontmatter 配置心智圖選項：

```yaml
---
title: User Story Map
markmap:
  colorFreezeLevel: 2     # 顏色凍結層級
  maxWidth: 300           # 節點最大寬度
  spacingHorizontal: 80   # 水平間距
  spacingVertical: 5      # 垂直間距
  autoFit: true          # 自動適應大小
  pan: true              # 允許拖拽
  zoom: true             # 允許縮放
  color: 
    - '#FF6B6B'          # 自定義顏色方案
    - '#4ECDC4'
    - '#45B7D1'
    - '#96CEB4'
---

# 心智圖內容從這裡開始
## 主要功能
### 登入系統
### 使用者管理
```

**重要配置說明**:
- `colorFreezeLevel`: 控制顏色層級，設為 2 表示第二層之後使用相同顏色
- `maxWidth`: 節點文字最大寬度，避免過長文字
- `fold`: 可在節點後加 `<!-- markmap: fold -->` 使其可摺疊

### **User Story Map 最佳實踐**

**推薦的 Markdown 結構**:
```markdown
---
title: User Story Map - 登入系統
markmap:
  colorFreezeLevel: 2
  maxWidth: 250
  spacingHorizontal: 100
---

# 使用者故事地圖

## Epic: 使用者驗證
### Story: 登入功能
- **AC1**: 輸入帳號密碼
- **AC2**: 驗證身份
- **AC3**: 成功登入後導向首頁

### Story: 登出功能
- **AC1**: 點擊登出按鈕
- **AC2**: 清除 Session
- **AC3**: 導向登入頁面

## Epic: 使用者管理
### Story: 個人資料
- **AC1**: 查看個人資訊
- **AC2**: 編輯個人資料
- **AC3**: 儲存變更

### Story: 密碼管理
- **AC1**: 修改密碼
- **AC2**: 忘記密碼重設
```

**資料轉換策略**:
- **Story.No** → 二級標題 (`## Story-ARD-00001`)
- **Features** → 標題文字內容
- **Criteria** → 子項目列表 (`- AC1: 具體條件`)
- **Parent-Child** → Markdown 層次結構 (`#`, `##`, `###`)
- **Extra Fields** → 額外的項目列表或註解

### **效能與限制**

**建議限制**:
- 節點數量: < 200 個（保持響應性）
- 層級深度: < 8 層（視覺清晰）
- 文字長度: 每個節點 < 100 字元（使用 maxWidth 控制）

**效能優化**:
- 使用 `colorFreezeLevel` 減少顏色計算
- 設定適當的 `maxWidth` 避免文字溢出
- 對於大型心智圖，考慮分拆為多個檔案

### **8. MindmapGenerator 核心模組**

#### **模組概述**

`core/mindmap_generator.py` 是心智圖生成的核心模組，負責將 `tree_builder` 產生的樹狀結構轉換為互動式心智圖。

**核心特性**:
- 基於 Markmap 的互動式心智圖生成
- Criteria 浮動顯示功能
- JIRA 超連結整合
- 自定義 CSS/JavaScript 注入
- 完整的錯誤處理和統計追蹤

#### **主要類別**

**MindmapGenerator 主類別**:
```python
from core.mindmap_generator import MindmapGenerator

# 初始化生成器
generator = MindmapGenerator(config=config, logger=logger)

# 生成心智圖
result = generator.generate_mindmap(tree_data, "output/mindmap")

if result.success:
    print(f"Generated files: {result.output_files}")
    print(f"Statistics: {result.metadata['stats']}")
```

**MindmapConfig 配置類別**:
```python
@dataclass
class MindmapConfig:
    color_freeze_level: int = 2
    max_width: int = 400
    spacing_horizontal: int = 150
    spacing_vertical: int = 15
    auto_fit: bool = True
    font_size: int = 14
    output_formats: List[str] = ["html"]
    jira_enabled: bool = True
```

**GenerationResult 結果類別**:
```python
@dataclass
class GenerationResult:
    success: bool
    message: str
    output_files: Dict[str, str]  # 格式 -> 檔案路徑
    metadata: Dict[str, Any]      # 統計和配置資訊
```

#### **進階功能實作**

**1. Criteria 浮動顯示**:
- 自動從 tree_builder 的 `criteria` 字段提取內容
- 注入 CSS 樣式定義浮動提示框外觀
- JavaScript 實現滑鼠懸浮事件處理
- HTML 實體解碼確保中文正確顯示

**2. JIRA 超連結整合**:
```python
# 配置 JIRA 整合
jira_config = {
    'base_url': 'https://jira.tc-gaming.co/jira',
    'issue_url_template': '{base_url}/browse/{tcg_number}',
    'link_target': '_blank',
    'link_title_template': 'Open {tcg_number} in JIRA'
}
```

**3. 資料驗證與統計**:
```python
# 生成統計資訊
stats = generator.get_generation_stats()
print(f"Nodes processed: {stats['nodes_processed']}")
print(f"Criteria nodes: {stats['criteria_nodes']}")
print(f"JIRA links: {stats['jira_links']}")
print(f"Generation time: {stats['generation_time']:.3f}s")
```

#### **Markdown 生成格式**

**樹狀結構轉換**:
```markdown
---
title: User Story Map
markmap:
  colorFreezeLevel: 2
  maxWidth: 400
  spacingHorizontal: 150
  spacingVertical: 15
  autoFit: true
  fontSize: 14
---

# **ARD**

## <span><small>Story-ARD-00001</small><br/><strong>登入畫面</strong></span>

### <span data-criteria="用戶可以輸入帳號密碼進行登入"><small><a href="https://jira.tc-gaming.co/jira/browse/TCG-109453" target="_blank" title="Open TCG-109453 in JIRA">Story-ARD-00002</a></small><br/><strong>登入畫面 - 輸入帳號密碼</strong></span>
```

**HTML 增強注入**:
```javascript
// 浮動顯示功能
function showTooltip(event, criteriaText) {
    var tooltip = createTooltip();
    tooltip.textContent = criteriaText;
    tooltip.classList.add('show');
    // 位置計算和顯示邏輯
}
```

#### **使用指引**

**基本使用**:
```python
from core.mindmap_generator import MindmapGenerator
import yaml
import logging

# 載入配置
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# 設定日誌
logger = logging.getLogger(__name__)

# 初始化生成器
generator = MindmapGenerator(config=config, logger=logger)

# 生成心智圖
result = generator.generate_mindmap(tree_data, "output/user_story_map")

if result.success:
    print("✅ 心智圖生成成功")
    for format_type, file_path in result.output_files.items():
        print(f"  - {format_type.upper()}: {file_path}")
else:
    print(f"❌ 生成失敗: {result.message}")
```

**支援的輸出格式**:
- `html`: 互動式心智圖（已實作）
- `png`: 靜態圖片（預留，未實作）
- `pdf`: PDF 格式（預留，未實作）

#### **整合 tree_builder**

**完整工作流程**:
```python
from core.tree_builder import TreeBuilder
from core.mindmap_generator import MindmapGenerator

# 1. 建構樹狀結構
builder = TreeBuilder(config=config, logger=logger)
tree_result = builder.build_tree(lark_records)

# 2. 生成心智圖
generator = MindmapGenerator(config=config, logger=logger)
mindmap_result = generator.generate_mindmap(tree_result, "output/mindmap")

# 3. 檢查結果
if mindmap_result.success:
    html_file = mindmap_result.output_files['html']
    print(f"心智圖已生成: {html_file}")
```

**錯誤處理**:
```python
try:
    result = generator.generate_mindmap(tree_data, output_path)
    if not result.success:
        logger.error(f"生成失敗: {result.message}")
        # 處理失敗情況
except Exception as e:
    logger.exception(f"生成過程發生異常: {e}")
    # 處理異常情況
```
