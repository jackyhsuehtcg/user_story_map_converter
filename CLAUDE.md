# User Story Map Converter - 實作設計文件

## 專案概述

User Story Map Converter 是一個將 Lark 多維表格的父子關係資料轉換為互動式 User Story Map 心智圖的 Web 應用程式。系統提供 Gmail 風格的管理介面，支援多團隊管理和心智圖生成。

## 核心功能

- **資料整合**: 從 Lark 多維表格讀取結構化資料
- **心智圖生成**: 將樹狀結構轉換為互動式心智圖
- **多團隊管理**: 支援多個團隊的 Lark 資料來源管理
- **即時刷新**: 手動觸發資料同步與心智圖更新
- **Criteria 浮動提示**: 滑鼠懸停顯示使用者故事的接受條件

## 系統架構

### 目錄結構

```
user_story_map_converter/
├── app.py                 # Flask 主程式 (包含所有路由和 SimpleMindmapGenerator)
├── config.yaml           # 系統設定檔
├── requirements.txt       # 依賴管理
├── core/                 # 核心業務邏輯
│   ├── __init__.py
│   ├── lark_client.py   # Lark API 客戶端
│   ├── tree_builder.py  # 樹狀結構建構
│   └── team_manager.py  # 團隊管理與檔案操作
├── tools/               # 開發工具
│   ├── __init__.py
│   ├── lark_data_extractor.py  # Lark 資料提取工具
│   └── tree_analyzer.py       # 樹狀結構分析工具
├── static/              # 靜態檔案
│   └── css/
│       └── style.css
├── templates/           # HTML 模板
│   ├── base.html
│   ├── index.html
│   ├── teams.html
│   └── mindmap.html
├── logs/               # 日誌檔案存放
├── exports/            # 匯出檔案存放
└── temp/               # 臨時檔案與鎖定檔案
```

### 技術棧

- **後端框架**: Flask 2.3.2
- **HTTP 請求**: requests 2.31.0
- **設定管理**: PyYAML 6.0.1
- **資料儲存**: JSON 檔案
- **前端框架**: Bootstrap 5
- **心智圖生成**: markmap-cli (外部工具)

### 分層架構

- **資料處理層**: `core/lark_client.py`, `core/tree_builder.py`
- **業務邏輯層**: `core/team_manager.py`, `app.py` (SimpleMindmapGenerator)
- **表現層**: `app.py` (路由), `templates/`, `static/`
- **支援模組**: `tools/`

## 資料流程

```
Lark API → lark_client → tree_builder → SimpleMindmapGenerator → markmap-cli → HTML 匯出
```

## 核心模組說明

### 1. Lark API 客戶端 (`core/lark_client.py`)

**功能**：
- 處理 Lark API 認證與請求
- 支援重試機制和速率限制
- 提供 wiki_token 到 obj_token 的轉換
- 批次獲取表格記錄

**主要類別**：
- `LarkClient`: 主要客戶端類別
- `LarkResponse`: 統一的回應格式
- `LarkErrorType`: 錯誤類型枚舉

**重要方法**：
- `get_table_records()`: 獲取表格記錄
- `resolve_app_token()`: 解析 wiki_token 到 obj_token
- `get_table_schema()`: 獲取表格結構

### 2. 樹狀結構建構器 (`core/tree_builder.py`)

**功能**：
- 將 Lark 記錄轉換為樹狀結構
- 處理 Story 編號格式驗證
- 建立父子關係映射
- 提供統計資訊

**主要類別**：
- `TreeBuilder`: 樹狀結構建構器
- `TreeNode`: 樹狀節點資料類別

**重要方法**：
- `build_tree()`: 建構完整樹狀結構
- `_filter_records()`: 過濾和驗證記錄
- `_build_tree_structure()`: 建立父子關係

### 3. 團隊管理器 (`core/team_manager.py`)

**功能**：
- 管理團隊設定檔案 (teams.json)
- 處理檔案鎖定防止並發衝突
- 管理匯出檔案的生命週期
- 提供團隊狀態查詢

**主要類別**：
- `TeamManager`: 團隊管理器

**重要方法**：
- `get_all_teams()`: 獲取所有團隊列表
- `team_lock()`: 團隊鎖定上下文管理器
- `add_team()`, `update_team()`, `delete_team()`: 團隊 CRUD 操作

### 4. 心智圖生成器 (`app.py` - SimpleMindmapGenerator)

**功能**：
- 將樹狀結構轉換為 Markmap 相容的 Markdown
- 生成 JIRA 連結
- 注入自定義 CSS 和 JavaScript
- 實現 Criteria 浮動提示功能

**重要方法**：
- `generate_markdown_from_tree()`: 生成 Markdown 內容
- `generate_html_with_markmap()`: 使用 markmap-cli 生成 HTML
- `_inject_custom_styles_and_scripts()`: 注入自定義樣式和腳本

## Web 路由說明

### 主要頁面

- `GET /`: 儀表板 - 顯示所有團隊概況
- `GET /teams`: 團隊管理 - 團隊 CRUD 操作
- `GET /mindmap/<team_id>`: 心智圖查看 - 顯示團隊心智圖

### API 端點

- `GET /api/teams`: 獲取所有團隊
- `POST /api/teams`: 新增團隊
- `PUT /api/teams/<team_id>`: 更新團隊
- `DELETE /api/teams/<team_id>`: 刪除團隊
- `POST /api/teams/<team_id>/refresh`: 刷新團隊資料
- `POST /api/teams/<team_id>/test-connection`: 測試連接
- `POST /api/teams/<team_id>/clear-mindmaps`: 清空心智圖

## 設定檔案說明

### config.yaml

```yaml
app:
  secret_key: "your-secret-key"

lark:
  app_id: "your-lark-app-id"
  app_secret: "your-lark-app-secret"
  timeout: 30
  max_retries: 3
  requests_per_minute: 100

logging:
  level: "INFO"

jira:
  base_url: "https://jira.tc-gaming.co/jira"
  issue_url_template: "{base_url}/browse/{tcg_number}"
  link_target: "_blank"
  link_title_template: "Open {tcg_number} in JIRA"
```

## 日誌系統

### 日誌層級規範

- **DEBUG**: API 請求詳細資訊、Token 刷新過程、樹狀結構建構過程
- **INFO**: 重要操作完成 (系統啟動、資料獲取完成、心智圖生成成功)
- **WARNING**: 可重試錯誤 (API 請求失敗、速率限制觸發、注入樣式失敗)
- **ERROR**: 功能失敗 (認證失敗、網路異常、檔案操作失敗)
- **CRITICAL**: 系統級錯誤 (所有重試失敗、認證完全失敗)

### 日誌檔案

- `logs/`: 主要日誌目錄 (由 .gitignore 排除)

## 並發控制

### 檔案鎖定機制

- 使用 `temp/.lock_<team_id>` 檔案防止同時處理同一團隊
- 鎖定檔案超過 10 分鐘自動失效
- 使用 Python 的 `contextmanager` 確保鎖定檔案正確釋放

### 心智圖檔案管理

- 每個團隊只保留最新的一個心智圖檔案
- 自動清理舊的心智圖檔案
- 檔案命名格式: `{team_id}_{timestamp}.html`

## 錯誤處理

### API 錯誤分類

- `AUTHENTICATION`: 認證失敗
- `RATE_LIMIT`: 速率限制
- `FIELD_ERROR`: 欄位錯誤
- `NETWORK`: 網路異常
- `SERVER`: 伺服器錯誤
- `UNKNOWN`: 未知錯誤

### 重試機制

- 指數退避重試
- 最多重試 3 次
- 根據錯誤類型決定是否重試

## 前端功能

### Gmail 風格儀表板

- 左側固定導覽邊欄
- 統計資訊面板
- 團隊狀態卡片
- Toast 通知系統

### 心智圖功能

- 互動式心智圖瀏覽
- JIRA 連結整合
- Criteria 浮動提示
- 響應式設計

## 部署說明

### 環境需求

```bash
# Python 依賴
pip install -r requirements.txt

# 外部工具
npm install -g markmap-cli
```

### 啟動應用

```bash
python app.py
```

訪問 http://localhost:8889 查看應用。

### 目錄權限

確保以下目錄存在且可寫入：
- `logs/`
- `exports/`
- `temp/`
- `static/`

## 開發工具

### tools/lark_data_extractor.py

- 從 Lark URL 提取資料的命令列工具
- 支援資料驗證和格式化
- 輸出 JSON 格式的原始資料

### tools/tree_analyzer.py

- 分析樹狀結構的工具
- 提供統計資訊和驗證功能
- 支援多種輸出格式

## 安全考量

- 設定檔案不納入版本控制
- 使用環境變數管理敏感資訊
- API 請求使用 HTTPS
- 檔案操作使用絕對路徑
- 防止路徑遍歷攻擊

## 效能優化

- 使用快取機制減少 API 請求
- 批次處理 API 請求
- 智慧型速率限制
- 檔案操作最小化

## 維護指南

### 日誌監控

定期檢查日誌檔案，關注：
- ERROR 和 CRITICAL 級別的日誌
- API 請求失敗率
- 心智圖生成成功率

### 檔案清理

- 定期清理過期的日誌檔案
- 清理舊的匯出檔案
- 清理臨時檔案和鎖定檔案

### 設定更新

- 定期更新 Lark API 認證資訊
- 根據使用量調整速率限制
- 更新 JIRA 連結設定