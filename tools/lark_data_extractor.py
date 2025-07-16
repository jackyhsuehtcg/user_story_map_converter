#!/usr/bin/env python3
"""
Lark Data Extractor Tool

This tool extracts raw data from Lark tables including:
- Table information
- Field schemas
- Table records

Usage:
    python tools/lark_data_extractor.py <lark_table_url>

Example:
    python tools/lark_data_extractor.py "https://tcgaming.larksuite.com/base/MKdDwAgbwiVbzDkSkTHl3D8Hg0e?table=tblsGKHK8l7wxaox"
"""

import argparse
import json
import logging
import os
import re
import sys
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.lark_client import LarkClient


class LarkDataExtractor:
    """Lark data extraction tool"""
    
    def __init__(self):
        # Load configuration from config.yaml
        self.config = self._load_config()
        
        # Get Lark credentials from config
        lark_config = self.config.get('lark', {})
        self.app_id = lark_config.get('app_id')
        self.app_secret = lark_config.get('app_secret')
        
        if not self.app_id or not self.app_secret:
            raise ValueError("Lark app_id and app_secret must be configured in config.yaml")
        
        # Setup logger
        self.logger = self._setup_logger()
        
        # Configuration for Lark client (merge with config.yaml settings)
        client_config = {
            'base_url': lark_config.get('base_url', 'https://open.larksuite.com/open-apis'),
            'timeout': lark_config.get('timeout', 30),
            'max_retries': 3,
            'retry_base_delay': 1.0,
            'retry_max_delay': 60.0,
            'auth_retries': 3,
            'token_refresh_buffer': 300,
            'rate_limit_enabled': True,
            'requests_per_minute': 100,
            'max_page_size': 500
        }
        self.client_config = client_config
        
        # Initialize Lark client
        self.client = LarkClient(
            app_id=self.app_id,
            app_secret=self.app_secret,
            config=self.client_config,
            logger=self.logger
        )
    
    def _load_config(self) -> dict:
        """Load configuration from config.yaml"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError("config.yaml not found. Please make sure it exists in the project root.")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config.yaml: {e}")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for the tool"""
        logger = logging.getLogger('lark_data_extractor')
        logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
        return logger
    
    def parse_lark_url(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Parse Lark table URL to extract wiki_token and table_id
        
        Expected URL format:
        https://tcgaming.larksuite.com/base/MKdDwAgbwiVbzDkSkTHl3D8Hg0e?table=tblsGKHK8l7wxaox
        
        Args:
            url: Lark table URL
            
        Returns:
            Tuple of (wiki_token, table_id) or None if parsing fails
        """
        try:
            parsed = urlparse(url)
            
            # Extract wiki_token from path
            # Pattern: /base/{wiki_token}
            path_match = re.match(r'/base/([^/?]+)', parsed.path)
            if not path_match:
                self.logger.error(f"無法從 URL 路徑解析 wiki_token: {parsed.path}")
                return None
            
            wiki_token = path_match.group(1)
            
            # Extract table_id from query parameters
            query_params = parse_qs(parsed.query)
            if 'table' not in query_params:
                self.logger.error(f"URL 中缺少 table 參數: {parsed.query}")
                return None
            
            table_id = query_params['table'][0]
            
            self.logger.info(f"成功解析 URL: wiki_token={wiki_token}, table_id={table_id}")
            return wiki_token, table_id
            
        except Exception as e:
            self.logger.error(f"URL 解析失敗: {e}")
            return None
    
    def extract_table_info(self, wiki_token: str, table_id: str) -> Optional[Dict]:
        """
        Extract basic table information
        
        Args:
            wiki_token: Wiki token
            table_id: Table ID
            
        Returns:
            Table information dictionary or None if failed
        """
        try:
            # Convert wiki_token to obj_token
            obj_token = self.client.resolve_app_token(wiki_token)
            if not obj_token:
                self.logger.error("無法解析 wiki_token 到 obj_token")
                return None
            
            # Since direct table info API might not be available, 
            # we'll construct basic info from what we have
            table_info = {
                'table_id': table_id,
                'name': f'Table_{table_id}',  # Default name, will be updated if possible
                'obj_token': obj_token,
                'wiki_token': wiki_token
            }
            
            self.logger.info(f"構建表格資訊: {table_info.get('name', 'N/A')}")
            return table_info
                
        except Exception as e:
            self.logger.error(f"獲取表格資訊異常: {e}")
            return None
    
    def extract_table_schema(self, wiki_token: str, table_id: str) -> Optional[List[Dict]]:
        """
        Extract table field schema
        
        Args:
            wiki_token: Wiki token
            table_id: Table ID
            
        Returns:
            List of field definitions or None if failed
        """
        try:
            schema_data = self.client.get_table_schema(wiki_token, table_id)
            if schema_data:
                fields = schema_data.get('items', [])
                self.logger.info(f"成功獲取表格結構: {len(fields)} 個欄位")
                return fields
            else:
                self.logger.error("獲取表格結構失敗")
                return None
                
        except Exception as e:
            self.logger.error(f"獲取表格結構異常: {e}")
            return None
    
    def extract_table_records(self, wiki_token: str, table_id: str) -> Optional[List[Dict]]:
        """
        Extract all table records
        
        Args:
            wiki_token: Wiki token
            table_id: Table ID
            
        Returns:
            List of table records or None if failed
        """
        try:
            records = self.client.get_table_records(wiki_token, table_id)
            if records:
                self.logger.info(f"成功獲取表格記錄: {len(records)} 筆")
                return records
            else:
                self.logger.error("獲取表格記錄失敗")
                return None
                
        except Exception as e:
            self.logger.error(f"獲取表格記錄異常: {e}")
            return None
    
    def extract_all_data(self, url: str) -> Optional[Dict]:
        """
        Extract all data from a Lark table URL
        
        Args:
            url: Lark table URL
            
        Returns:
            Complete data dictionary or None if failed
        """
        self.logger.info(f"開始提取 Lark 表格資料: {url}")
        
        # Parse URL
        parsed_result = self.parse_lark_url(url)
        if not parsed_result:
            return None
        
        wiki_token, table_id = parsed_result
        
        # Extract all data
        table_info = self.extract_table_info(wiki_token, table_id)
        table_schema = self.extract_table_schema(wiki_token, table_id)
        table_records = self.extract_table_records(wiki_token, table_id)
        
        if not all([table_info, table_schema, table_records]):
            self.logger.error("部分資料提取失敗")
            return None
        
        # Compile results
        result = {
            'extraction_info': {
                'timestamp': datetime.now().isoformat(),
                'source_url': url,
                'wiki_token': wiki_token,
                'table_id': table_id,
                'extractor_version': '1.0'
            },
            'table_info': table_info,
            'table_schema': table_schema,
            'table_records': table_records,
            'summary': {
                'total_fields': len(table_schema),
                'total_records': len(table_records),
                'table_name': table_info.get('name', 'N/A')
            }
        }
        
        self.logger.info(f"資料提取完成: {result['summary']['table_name']}")
        self.logger.info(f"  - 欄位數: {result['summary']['total_fields']}")
        self.logger.info(f"  - 記錄數: {result['summary']['total_records']}")
        
        return result
    
    def save_to_file(self, data: Dict, output_file: str = None) -> str:
        """
        Save extracted data to JSON file
        
        Args:
            data: Extracted data dictionary
            output_file: Output file path (optional)
            
        Returns:
            Path to saved file
        """
        if not output_file:
            # Create temp directory if it doesn't exist
            temp_dir = "temp"
            os.makedirs(temp_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            table_name = data['summary']['table_name'].replace(' ', '_')
            output_file = os.path.join(temp_dir, f"lark_data_{table_name}_{timestamp}.json")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"資料已儲存至: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"儲存檔案失敗: {e}")
            raise
    
    def print_summary(self, data: Dict):
        """
        Print data summary to console
        
        Args:
            data: Extracted data dictionary
        """
        print("\n" + "="*60)
        print("📊 Lark 資料提取摘要")
        print("="*60)
        
        # Basic info
        print(f"📋 表格名稱: {data['summary']['table_name']}")
        print(f"🔗 來源 URL: {data['extraction_info']['source_url']}")
        print(f"⏰ 提取時間: {data['extraction_info']['timestamp']}")
        
        # Statistics
        print(f"\n📈 統計資訊:")
        print(f"  - 欄位數量: {data['summary']['total_fields']}")
        print(f"  - 記錄數量: {data['summary']['total_records']}")
        
        # Field summary
        print(f"\n📝 欄位摘要:")
        for i, field in enumerate(data['table_schema'][:10], 1):  # Show first 10 fields
            field_name = field.get('field_name', 'N/A')
            field_type = field.get('type', 'N/A')
            print(f"  {i:2d}. {field_name} ({field_type})")
        
        if len(data['table_schema']) > 10:
            print(f"  ... 還有 {len(data['table_schema']) - 10} 個欄位")
        
        # Record preview
        print(f"\n📄 記錄預覽:")
        for i, record in enumerate(data['table_records'][:3], 1):  # Show first 3 records
            print(f"  記錄 {i}: {record.get('record_id', 'N/A')}")
            fields = record.get('fields', {})
            for field_name, field_value in list(fields.items())[:3]:  # Show first 3 fields
                # Truncate long values
                if isinstance(field_value, str) and len(field_value) > 50:
                    field_value = field_value[:50] + "..."
                print(f"    - {field_name}: {field_value}")
            if len(fields) > 3:
                print(f"    ... 還有 {len(fields) - 3} 個欄位")
        
        if len(data['table_records']) > 3:
            print(f"  ... 還有 {len(data['table_records']) - 3} 筆記錄")
        
        print("="*60)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Extract raw data from Lark tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/lark_data_extractor.py "https://tcgaming.larksuite.com/base/MKdDwAgbwiVbzDkSkTHl3D8Hg0e?table=tblsGKHK8l7wxaox"
  python tools/lark_data_extractor.py "https://tcgaming.larksuite.com/base/MKdDwAgbwiVbzDkSkTHl3D8Hg0e?table=tblsGKHK8l7wxaox" --output my_data.json
        """
    )
    
    parser.add_argument(
        'url',
        help='Lark table URL'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output JSON file path (optional)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress detailed output'
    )
    
    args = parser.parse_args()
    
    try:
        # Create extractor
        extractor = LarkDataExtractor()
        
        # Set logging level
        if args.quiet:
            extractor.logger.setLevel(logging.WARNING)
        
        # Extract data
        data = extractor.extract_all_data(args.url)
        if not data:
            print("❌ 資料提取失敗")
            sys.exit(1)
        
        # Save to file
        output_file = extractor.save_to_file(data, args.output)
        
        # Print summary
        if not args.quiet:
            extractor.print_summary(data)
        
        print(f"\n✅ 資料提取完成，已儲存至: {output_file}")
        
    except KeyboardInterrupt:
        print("\n❌ 使用者中斷操作")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 執行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()