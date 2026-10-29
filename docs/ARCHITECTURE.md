# 排程任務監測系統架構與維護指南 (Architecture & Operations)

## 一、 系統核心目標

本系統專為 Antigravity 2.0 與常態排程任務（Scheduled Tasks）打造，解決「背景排程無感執行、結果難以追蹤、缺乏統一健康看板」的痛點。

系統具備三大核心特質：
1. **執行留痕（Execution Traceability）**：只要任何背景排程或自動化腳本執行完畢，一行指令即可將「狀態（成功/警訊/失敗）」、「成果說明摘要」與「完整診斷日誌」寫入儀表板。
2. **大道至簡紙墨美學（Zen Web Standards）**：米白紙底（`#FAF6EF`）、墨色文字（`#2A2520`）、直角無圓角（`border-radius: 0`）、細線分割、零 Cookie 追蹤合規。
3. **雙模啟動與零伺服器維護（Zero-Server Architecture）**：
   - **離線/本地模式**：透過 `build.py` 將最新資料內嵌於 `index.html`，直接雙擊 `file://` 協議即可離線秒開。
   - **線上發布模式**：透過 GitHub Pages 與 GitHub Actions 自動部署，全世界任何裝置隨時檢視最新運維狀態。

---

## 二、 目錄與資料流架構

```
scheduled-tasks-dashboard/
├── .github/
│   └── workflows/
│       └── deploy.yml        # GitHub Actions 自動部署至 GitHub Pages
├── data/
│   ├── tasks.json            # 註冊任務清單、Cron 週期、目前狀態與累計統計
│   └── runs.json             # 歷史執行紀錄（包含成果說明、日誌、耗時）
├── tools/
│   ├── record_task.py        # 任務回報 CLI 工具（完成任務時寫入結果並可一鍵推送）
│   ├── sync_sidecars.py      # 自動掃描本機 ~/.gemini/config/sidecars/ 任務配置
│   └── build.py              # 靜態雙模編譯引擎
├── template.html             # 儀表板 HTML 核心模板
├── index.html                # 編譯後的可發布儀表板（可直接雙擊瀏覽）
├── docs/
│   └── ARCHITECTURE.md       # 本架構手冊
├── LICENSE                   # MIT 授權條款
└── README.md                 # 專案說明與操作指南
```

### 資料流轉圖

```
[Antigravity 2.0 排程任務]
           │
           │ (定時觸發執行)
           ▼
[背景完成任務作業]
           │
           │ (執行回報腳本)
           ▼
[tools/record_task.py] ───► 更新 [data/runs.json] & [data/tasks.json]
           │
           ├───► 執行 [tools/build.py] (編譯至 index.html)
           │
           └───► (可選 --push) Git Commit & Push ───► [GitHub Pages 上線]
```

---

## 三、 CLI 工具操作規格

### 1. 任務完成回報與結果寫入 (`record_task.py`)

在任務執行完成時調用：

```bash
python3 tools/record_task.py \
  --task "<task_id>" \
  --status "<success|warning|error>" \
  --summary "<一句話成果摘要>" \
  [--duration "<耗時>"] \
  [--details "<詳細日誌或多行說明>"] \
  [--details-file "<日誌檔案路徑>"] \
  [--push]
```

- `--task` (必要)：任務的 slug 標識符（例如 `audit`, `daily-gardener`, `morning-brief`）。
- `--status` (預設 `success`)：`success` (綠燈正常)、`warning` (橘燈警訊)、`error` (紅燈失敗)。
- `--summary` (必要)：核心執行成果說明（直接展示在儀表板時間軸上）。
- `--details` (選填)：詳細診斷資訊、生成的檔案路徑、或例外錯誤訊息。
- `--push` (選填)：自動 `git commit` 並 `git push` 到 GitHub 遠端倉庫。

### 2. 本機排程掃描與同步 (`sync_sidecars.py`)

當本機新增或修改了 Antigravity 2.0 的 Sidecar 定時任務時，執行此腳本自動同步到 `tasks.json`：

```bash
python3 tools/sync_sidecars.py
```

### 3. 靜態儀表板編譯 (`build.py`)

```bash
python3 tools/build.py
```

---

## 四、 現有 Sidecar 任務掛載範例

在 `~/.gemini/config/sidecars/<task>/sidecar.json` 中的 `args[4]` 結尾加上一行回報指令：

```json
"完成後執行回報：python3 /Users/chienchiachi/Documents/GitHub/scheduled-tasks-dashboard/tools/record_task.py --task audit --status success --summary '電腦健康巡檢完成' --push"
```
