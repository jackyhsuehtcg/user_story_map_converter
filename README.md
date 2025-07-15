# User Story Map Converter

將 Lark 多維表格的階層式資料轉換為互動式 User Story Map 心智圖的 Web 應用程式。

## 功能特色

- 🔄 **自動同步**: 從 Lark 多維表格讀取結構化資料
- 🗺️ **互動式心智圖**: 生成可互動的 User Story Map 視覺化
- 👥 **多團隊支援**: 管理多個團隊的不同資料來源
- 📱 **響應式設計**: Gmail 風格的現代化 Web 介面
- 🎯 **智慧提示**: 滑鼠懸停顯示使用者故事的接受條件
- 🔗 **JIRA 整合**: 自動生成 JIRA 連結

## 系統架構

```
user_story_map_converter/
├── app.py                 # Flask 主程式
├── config.yaml           # 系統設定檔
├── requirements.txt       # 依賴管理
├── core/                 # 核心業務邏輯
│   ├── lark_client.py   # Lark API 客戶端
│   ├── tree_builder.py  # 樹狀結構建構
│   └── team_manager.py  # 團隊管理與檔案操作
├── tools/               # 開發工具
│   ├── lark_data_extractor.py  # Lark 資料提取工具
│   └── tree_analyzer.py       # 樹狀結構分析工具
├── static/              # 靜態檔案
├── templates/           # HTML 模板
├── logs/               # 日誌檔案
├── exports/            # 匯出檔案存放
└── temp/               # 臨時檔案
```

## 技術棧

- **後端框架**: Flask
- **資料儲存**: JSON 檔案
- **前端框架**: Bootstrap 5
- **心智圖生成**: markmap-cli
- **設定管理**: PyYAML
- **HTTP 請求**: requests

## 資料流程

```
Lark API → lark_client → tree_builder → SimpleMindmapGenerator → markmap-cli → HTML 匯出
```

## 快速開始

### 環境需求

- Python 3.8+
- Node.js (用於 markmap-cli)

### 安裝依賴

```bash
# 安裝 Python 依賴
pip install -r requirements.txt

# 安裝 markmap-cli
npm install -g markmap-cli
```

### 設定檔案

複製並修改設定檔案：

```bash
cp config.yaml.example config.yaml
```

編輯 `config.yaml` 設定 Lark API 認證資訊：

```yaml
app:
  secret_key: \"your-secret-key\"

lark:
  app_id: \"your-lark-app-id\"
  app_secret: \"your-lark-app-secret\"
  timeout: 30
  max_retries: 3
  requests_per_minute: 100

logging:
  level: \"INFO\"

jira:
  base_url: \"https://your-jira-domain.com\"
  issue_url_template: \"{base_url}/browse/{tcg_number}\"
  link_target: \"_blank\"
  link_title_template: \"Open {tcg_number} in JIRA\"
```

### 啟動應用

```bash
python app.py
```

訪問 http://localhost:8889 開始使用。

## 使用方式

### 1. 新增團隊

1. 訪問 \"團隊管理\" 頁面
2. 點擊 \"新增團隊\" 按鈕
3. 填入團隊名稱和 Lark 表格 URL
4. 儲存設定

### 2. 生成心智圖

1. 在儀表板點擊 \"同步\" 按鈕
2. 系統將自動從 Lark 獲取資料
3. 生成心智圖並儲存
4. 點擊 \"查看\" 按鈕查看心智圖

### 3. 查看心智圖

- 互動式瀏覽心智圖
- 滑鼠懸停查看 Criteria 資訊
- 點擊 JIRA 連結跳轉到對應工單

## Lark 表格格式要求

您的 Lark 表格需要包含以下欄位：

- **Story**: 使用者故事編號 (格式: Story-XXX-YYYYY)
- **Title**: 使用者故事標題
- **Parent**: 父級故事編號 (可選)
- **Criteria**: 接受條件 (可選)
- **TCG**: JIRA 工單編號 (可選)

### 範例表格結構

| Story | Title | Parent | Criteria | TCG |
|-------|-------|---------|----------|-----|
| Story-ARD-00001 | 登入畫面 | | 用戶可以進行基本的帳號管理操作 | |
| Story-ARD-00002 | 登入畫面 - 輸入帳號密碼 | Story-ARD-00001 | | TCG-109453 |
| Story-ARD-00003 | 登入畫面 - 忘記密碼 | Story-ARD-00001 | | TCG-109454 |

## 功能說明

### 儀表板

- 顯示所有團隊概況
- 即時狀態更新
- 統計資訊面板
- 快速操作按鈕

### 團隊管理

- 新增/編輯/刪除團隊
- 測試 Lark 連接
- 清空心智圖
- 管理團隊設定

### 心智圖查看

- 互動式心智圖瀏覽
- 支援縮放和平移
- JIRA 連結整合
- Criteria 浮動提示

## 開發工具

### 資料提取工具

```bash
python tools/lark_data_extractor.py <lark_url>
```

### 樹狀結構分析工具

```bash
python tools/tree_analyzer.py <json_file>
```

## 並發控制

系統使用檔案鎖定機制防止同時處理同一團隊的資料，確保資料一致性。

## 錯誤處理

- 自動重試機制
- 詳細錯誤日誌
- 使用者友好的錯誤提示
- 多種錯誤類型分類

## 安全性

- 設定檔案不納入版本控制
- API 請求使用 HTTPS
- 檔案操作安全檢查
- 防止路徑遍歷攻擊

## 貢獻指南

1. Fork 本專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 授權條款

本專案採用 MIT 授權條款 - 查看 [LICENSE](LICENSE) 檔案了解詳情。

## 常見問題

### Q: 如何獲取 Lark API 認證資訊？
A: 請參考 [Lark 開發者文件](https://open.larksuite.com/) 建立應用程式並獲取 app_id 和 app_secret。

### Q: 支援哪些 Lark 表格格式？
A: 支援標準的多維表格格式，需要包含 Story、Title、Parent 等基本欄位。

### Q: 如何自訂 JIRA 連結？
A: 在 `config.yaml` 中修改 `jira` 區段的設定。

### Q: 心智圖無法顯示怎麼辦？
A: 檢查 markmap-cli 是否正確安裝，以及瀏覽器是否支援 JavaScript。

## 支援

如有問題或建議，請：
1. 查看 [Issues](https://github.com/your-username/user_story_map_converter/issues) 頁面
2. 建立新的 Issue
3. 聯絡開發團隊