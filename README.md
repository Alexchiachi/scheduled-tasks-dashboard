# 排程任務監測儀表板 (Scheduled Tasks Dashboard)

[![Zen Web Standards](https://img.shields.io/badge/Design-Zen%20Web%20Standards-82663F?style=flat-square)](https://github.com/Alexchiachi/zen-web-standards)
[![License: MIT](https://img.shields.io/badge/License-MIT-2A2520?style=flat-square)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/Deploy-GitHub%20Pages-547050?style=flat-square)](https://alexchiachi.github.io/scheduled-tasks-dashboard/)

> 大道至簡 · 全天候自動化巡檢、執行結果留痕與健康度看板。  
> 專為 Antigravity 2.0 與全域自動化排程打造的輕量監控與歷史紀錄系統。

---

## 🌟 系統亮點

1. **結果與說明即時留痕**：只要排程任務完成，守護引擎全自動（或指令回報）立即將「執行狀態」、「成果說明」與「完整日誌」寫入儀表板。
2. **每筆執行獨立分頁報告 (Dedicated Run Pages)**：每筆排程執行紀錄皆自動生成專屬靜態 HTML 頁面（`runs/<run_id>.html`），包含完整成果說明、日誌高亮代碼框、執行耗時、排程規格，並支援一鍵複製與匯出 Markdown。
3. **大道至簡紙墨美學**：嚴格遵循 `zen-web-standards`，米白紙底（`#FAF6EF`）、墨色文字（`#2A2520`）、直角細線無圓角、零 Cookie 追蹤合規。
4. **直觀健康度監測**：
   - 納管任務總數、24 小時執行頻次、系統成功率指標。
   - 12 個常規任務狀態矩陣（週期 Cron、最後執行時間、即時狀態）。
   - 歷史紀錄時間軸（支援成功/警訊/失敗篩選、任務過濾、即時全文搜尋、展開查看詳細日誌，並可點擊開啟獨立分頁）。
5. **離線/線上雙模秒開**：
   - 本地離線：雙擊 `index.html` 或各獨立分頁即可完整瀏覽（資料已雙向預編譯）。
   - 線上發布：Push 到 GitHub 後，GitHub Actions 自動發布至 GitHub Pages。

---

## 🚀 快速上手

### 1. 任務完成時自動回報 (`record_task.py`)

在任何排程任務的 Prompt 步驟結尾、或 Python 腳本最後一行加入：

```bash
python3 /Users/chienchiachi/Documents/GitHub/scheduled-tasks-dashboard/tools/record_task.py \
  --task "daily-gardener" \
  --status "success" \
  --summary "第二心智演化日誌撰寫完畢，雙基地已同步，Obsidian已成功推送到GitHub。" \
  --duration "42s" \
  --push
```

#### 參數說明
| 參數 | 必要 | 預設值 | 說明 |
| :--- | :---: | :---: | :--- |
| `--task` | 是 | - | 任務標識符號 slug（例如 `audit`, `daily-gardener`, `morning-brief`） |
| `--status` | 否 | `success` | 執行狀態：`success` (成功)、`warning` (警訊)、`error` (失敗) |
| `--summary` | 是 | - | 執行成果說明摘要（展示於時間軸首行） |
| `--duration` | 否 | `-` | 任務耗時（例如 `15s`, `1m 20s`） |
| `--details` | 否 | - | 詳細日誌文字、產出檔案清單或例外 Stacktrace |
| `--details-file` | 否 | - | 指定日誌檔案路徑，自動讀取並寫入 details |
| `--push` | 否 | `False` | 寫入完成後自動執行 `git commit` 並推送到遠端 GitHub Pages |

---

### 2. 本地預覽儀表板

直接以瀏覽器開啟本地檔案：
```bash
open /Users/chienchiachi/Documents/GitHub/scheduled-tasks-dashboard/index.html
```
或使用輕量 HTTP 伺服器：
```bash
cd /Users/chienchiachi/Documents/GitHub/scheduled-tasks-dashboard && python3 -m http.server 8080
```
瀏覽器開啟：`http://localhost:8080`

---

## 🛠️ 維護與管理工具

### 自動同步 Antigravity 2.0 排程配置
若在 Antigravity 2.0 新增或調整了排程（`~/.gemini/config/sidecars/`），執行此命令自動同步任務資訊與 Cron 說明：
```bash
python3 tools/sync_sidecars.py
```

### 重新手動編譯儀表板
```bash
python3 tools/build.py
```

---

## 📁 專案目錄結構

```
scheduled-tasks-dashboard/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Pages 自動發布 CI/CD
├── data/
│   ├── tasks.json              # 納管排程任務清單與健康統計
│   └── runs.json               # 執行歷史紀錄庫
├── tools/
│   ├── record_task.py          # 核心寫入 CLI 工具
│   ├── sync_sidecars.py        # Sidecar 排程配置同步器
│   └── build.py                # 靜態雙模編譯腳本
├── template.html               # 儀表板 HTML 核心模板
├── index.html                  # 預編譯靜態發布頁面
├── docs/
│   └── ARCHITECTURE.md         # 系統架構手冊
├── LICENSE                     # MIT 授權
└── README.md                   # 專案指引
```

---

## 📜 大道至簡落款

遵循大道至簡紙墨標準，直角平正，負熵常安。
