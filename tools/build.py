#!/usr/bin/env python3
"""
build.py: 大道至簡 · 排程任務監測儀表板建置引擎
將 data/tasks.json 與 data/runs.json 注入 index.html 模板中，
確保離線 file:// 存取與線上 GitHub Pages 皆能秒開無阻。
"""
import json
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def build():
    tasks_file = BASE_DIR / "data" / "tasks.json"
    runs_file = BASE_DIR / "data" / "runs.json"
    template_file = BASE_DIR / "template.html"
    index_file = BASE_DIR / "index.html"

    # 讀取 tasks.json
    tasks = []
    if tasks_file.exists():
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except Exception as e:
            print(f"⚠️ 讀取 tasks.json 失敗: {e}")

    # 讀取 runs.json
    runs = []
    if runs_file.exists():
        try:
            with open(runs_file, "r", encoding="utf-8") as f:
                runs = json.load(f)
        except Exception as e:
            print(f"⚠️ 讀取 runs.json 失敗: {e}")

    if not template_file.exists():
        if index_file.exists():
            template_file = index_file
        else:
            print(f"❌ 找不到 template.html 或 index.html")
            return

    with open(template_file, "r", encoding="utf-8") as f:
        html = f.read()

    tasks_json_str = json.dumps(tasks, ensure_ascii=False, indent=2)
    runs_json_str = json.dumps(runs, ensure_ascii=False, indent=2)

    # 替換 script 標籤內嵌資料
    pattern_tasks = r'(<script id="initial-tasks" type="application/json">)(.*?)(</script>)'
    replacement_tasks = rf'\g<1>\n{tasks_json_str}\n\g<3>'
    if re.search(pattern_tasks, html, flags=re.DOTALL):
        html = re.sub(pattern_tasks, replacement_tasks, html, flags=re.DOTALL)
    
    pattern_runs = r'(<script id="initial-runs" type="application/json">)(.*?)(</script>)'
    replacement_runs = rf'\g<1>\n{runs_json_str}\n\g<3>'
    if re.search(pattern_runs, html, flags=re.DOTALL):
        html = re.sub(pattern_runs, replacement_runs, html, flags=re.DOTALL)

    with open(index_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 儀表板編譯完成！已同步 {len(tasks)} 個任務與 {len(runs)} 筆執行紀錄至 index.html")


if __name__ == "__main__":
    build()
