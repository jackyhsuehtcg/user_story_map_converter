# User Story Map Converter

一個將 Lark 多維表格的父子關係資料轉換為互動式 User Story Map 心智圖的系統。

## 🏗️ 專案架構

### 核心功能
- **資料整合**: 讀取 Lark 多維表格資料
- **心智圖生成**: 將結構化資料轉換為視覺化心智圖
- **多團隊管理**: Web 介面管理多個團隊的 Lark 資料來源
- **多格式匯出**: 支援 HTML、PNG、JPG、Markdown、PDF 等格式
- **響應式設計**: 參考 macOS 風格的 Glass 設計，支援日夜模式

### 技術架構

```
user_story_map_converter/
├── app.py                 # Flask 主程式
├── config.yaml           # 系統設定檔
├── requirements.txt       # 依賴管理
├── core/                 # 核心業務邏輯
│   ├── lark_client.py   # Lark API 客戶端
│   ├── tree_builder.py  # 樹狀結構建構
│   ├── mindmap_generator.py  # 心智圖生成
│   └── task_manager.py  # 背景任務管理
├── models/              # 資料模型
│   ├── database.py      # 資料庫操作
│   ├── team.py         # 團隊模型
│   └── task.py         # 任務模型
├── routes/              # Web 路由
│   ├── main.py         # 主頁路由
│   ├── teams.py        # 團隊管理
│   └── export.py       # 匯出功能
├── static/              # 靜態檔案
├── templates/           # HTML 模板
├── logs/               # 日誌檔案
└── exports/            # 匯出檔案存放
```

### 資料流程

```
Lark API → lark_client → tree_builder → Markdown → markmap-cli → HTML/PNG
```

## 🛠️ 技術棧

- **後端框架**: Flask + SQLAlchemy
- **資料庫**: SQLite
- **前端框架**: Bootstrap
- **設定管理**: YAML + PyYAML
- **心智圖生成**: Markmap (markmap-cli)
- **背景任務**: Python threading

## 🚀 快速開始

### 環境需求

- Python 3.8+
- Node.js (用於 markmap-cli)

### 安裝步驟

1. 克隆專案
```bash
git clone https://github.com/jackyhsuehtcg/user_story_map_converter.git
cd user_story_map_converter
```

2. 安裝 Python 依賴
```bash
pip install -r requirements.txt
```

3. 安裝 markmap-cli
```bash
npm install -g markmap-cli
```

4. 配置設定檔
```bash
cp config.yaml.example config.yaml
# 編輯 config.yaml 設定你的 Lark 應用憑證
```

5. 啟動應用
```bash
python app.py
```

### 測試

執行測試腳本驗證 Lark 客戶端功能：

```bash
python temp/test_lark_client.py
```

## 📋 功能特性

### Web 介面
- 多團隊 User Story Map 縮圖展示
- 點選縮圖展開大圖瀏覽
- 手動刷新機制，避免即時更新造成的效能問題
- 側邊工具欄提供管理功能入口

### 匯出功能
- **HTML**: 完整互動式心智圖
- **PNG/JPG**: 靜態圖片格式
- **Markdown**: 純文字格式
- **PDF**: 列印友好格式

### 設計特色
- macOS 風格的 Glass 設計
- 日夜模式切換
- 統一的對話框和通知樣式
- 響應式佈局

## 🔧 配置說明

### config.yaml 設定範例

```yaml
# Lark 應用配置
lark:
  app_id: "your_app_id"
  app_secret: "your_app_secret"
  base_url: "https://open.larksuite.com/open-apis"

# 團隊配置
teams:
  - name: "Team A"
    wiki_token: "your_wiki_token"
    table_id: "your_table_id"
    enabled: true
  
# 系統配置
system:
  debug: false
  log_level: "INFO"
  export_path: "exports/"
  
# API 限制配置
api:
  timeout: 30
  max_retries: 3
  rate_limit_enabled: true
  requests_per_minute: 100
```

## 📊 監控與日誌

### 日誌層級
- **DEBUG**: API 請求詳細、Token 刷新過程、樹狀結構建構
- **INFO**: 重要操作完成、系統啟動、資料獲取完成
- **WARNING**: 可重試錯誤、速率限制觸發、任務執行時間過長
- **ERROR**: 功能失敗、認證失敗、網路異常、處理失敗
- **CRITICAL**: 系統級錯誤、所有重試失敗、核心服務無法啟動

### 效能指標
- API 請求成功率
- 平均回應時間
- Token 有效性
- 速率限制使用率
- 系統運行時間

## 🔐 安全性

- Token 自動刷新和快取機制
- 線程安全的認證管理
- 敏感資訊不記錄到日誌
- 配置檔案與程式碼分離

---

## 🛠️ 實作細節

### Lark API 客戶端 (lark_client.py)

#### 核心特性
- **線程安全**: 使用 threading.Lock 保護共享資源
- **自動重試**: 指數退避重試機制處理瞬時錯誤
- **智慧速率限制**: 動態調整請求頻率避免 API 限制
- **錯誤分類**: 針對不同錯誤類型採用不同處理策略
- **Token 管理**: 自動刷新和快取機制

#### 兩階段 Token 系統
```python
# Step 1: Wiki Token → Obj Token 轉換
def resolve_app_token(self, wiki_token: str) -> Optional[str]:
    """Convert wiki_token to obj_token via /wiki/v2/spaces/get_node"""
    
# Step 2: 使用 Obj Token 存取表格資料
def get_table_records(self, wiki_token: str, table_id: str) -> List[Dict]:
    """Get table records using two-token system"""
```

#### 錯誤處理架構
```python
class LarkErrorType(Enum):
    AUTHENTICATION = "authentication"  # 認證失敗
    RATE_LIMIT = "rate_limit"         # 速率限制
    FIELD_ERROR = "field_error"       # 欄位錯誤
    NETWORK = "network"               # 網路錯誤
    SERVER = "server"                 # 伺服器錯誤
    UNKNOWN = "unknown"               # 未知錯誤
```

#### 效能監控
```python
def get_performance_metrics(self) -> Dict[str, Any]:
    """綜合效能指標監控"""
    return {
        'requests_total': self.metrics['requests_total'],
        'requests_failed': self.metrics['requests_failed'],
        'success_rate': calculated_success_rate,
        'avg_response_time': self.metrics['avg_response_time'],
        'auth_token_valid': self.auth_manager.is_token_valid(),
        'rate_limit_utilization': current_utilization,
        'uptime': system_uptime
    }
```

### 樹狀結構建構器 (tree_builder.py)

#### 父子關係解析
- 自動識別 Lark 表格中的父子關係欄位
- 建立完整的樹狀結構資料
- 處理循環參照和孤兒節點
- 支援多層級巢狀結構

#### 資料驗證
- 檢查資料完整性
- 驗證父子關係的邏輯正確性
- 提供資料清理和修復建議

### 心智圖生成器 (mindmap_generator.py)

#### Markdown 轉換
```python
def generate_mindmap_markdown(self, tree_data: Dict) -> str:
    """將樹狀資料轉換為 Markmap 相容的 Markdown"""
    
def export_to_formats(self, markdown: str, output_path: str) -> Dict[str, str]:
    """使用 markmap-cli 匯出多種格式"""
```

#### 支援格式
- **HTML**: 互動式心智圖，支援縮放、摺疊、搜尋
- **PNG**: 高解析度靜態圖片
- **SVG**: 向量圖形格式
- **PDF**: 列印友好格式

### 任務管理器 (task_manager.py)

#### 背景任務處理
```python
class TaskManager:
    def __init__(self, app_context):
        self.app_context = app_context
        self.task_queue = queue.Queue()
        self.worker_threads = []
        
    def submit_task(self, task_type: str, **kwargs) -> str:
        """提交背景任務"""
        
    def get_task_status(self, task_id: str) -> Dict:
        """獲取任務狀態"""
```

#### 任務類型
- **資料同步**: 從 Lark 獲取最新資料
- **心智圖生成**: 建立新的心智圖
- **格式匯出**: 生成各種格式的檔案
- **定期清理**: 清理過期的匯出檔案

### 資料庫設計

#### 團隊模型 (Team)
```python
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    wiki_token = db.Column(db.String(255), nullable=False)
    table_id = db.Column(db.String(100), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### 任務模型 (Task)
```python
class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)  # UUID
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    task_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    progress = db.Column(db.Integer, default=0)
    result_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
```

### API 端點設計

#### 主要路由
```python
# 首頁展示
@app.route('/')
def index():
    """展示所有團隊的心智圖縮圖"""

# 團隊管理
@app.route('/teams')
def teams():
    """團隊設定管理頁面"""

# 心智圖刷新
@app.route('/refresh/<int:team_id>')
def refresh_mindmap(team_id):
    """觸發特定團隊的心智圖刷新"""

# 匯出功能
@app.route('/export/<int:team_id>/<format>')
def export_mindmap(team_id, format):
    """匯出指定格式的心智圖"""
```

### 前端設計

#### Glass 風格實作
```css
/* macOS 風格 Glass 效果 */
.glass-container {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

/* 日夜模式切換 */
[data-theme="dark"] .glass-container {
    background: rgba(0, 0, 0, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.1);
}
```

#### 響應式佈局
- 使用 Bootstrap Grid 系統
- 支援手機、平板、桌面多種螢幕尺寸
- 縮圖自適應排列
- 觸控友好的操作介面

### 部署與維護

#### 容器化部署
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "app.py"]
```

#### 監控與維護
- 日誌輪轉機制
- 效能指標收集
- 錯誤通知系統
- 定期備份機制

### 擴展性考量

#### 插件架構
- 支援自定義資料來源
- 可擴展的匯出格式
- 主題系統
- 第三方整合 API

#### 效能優化
- 資料快取機制
- 增量更新策略
- 分散式任務處理
- CDN 靜態資源加速

---

## 🤝 貢獻指南

1. Fork 此專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📝 授權條款

此專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 📞 聯絡方式

- 專案維護者: Jacky Hsu
- Email: jacky.h@tc-gaming.com
- GitHub: [@jackyhsuehtcg](https://github.com/jackyhsuehtcg)

## 🙏 致謝

感謝 [jira_sync_v3](https://github.com/jackyhsuehtcg/jira_sync_v3) 專案提供的 Lark API 整合經驗和最佳實踐。