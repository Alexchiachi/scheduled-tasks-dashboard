#!/usr/bin/env python3
"""
build.py: 大道至簡 · 排程任務監測儀表板建置引擎
1. 將 data/tasks.json 與 data/runs.json 注入 index.html 模板中，確保離線與線上秒開。
2. 為每一筆執行的排程任務生成獨立分頁 HTML (runs/<run_id>.html)，提供專屬完整說明與日誌報告。
"""
import html
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
    template_run_file = BASE_DIR / "template_run.html"
    runs_dir = BASE_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # 1. 讀取 tasks.json
    tasks = []
    task_map = {}
    if tasks_file.exists():
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                tasks = json.load(f)
                for t in tasks:
                    task_map[t["id"]] = t
        except Exception as e:
            print(f"⚠️ 讀取 tasks.json 失敗: {e}")

    # 2. 讀取 runs.json
    runs = []
    if runs_file.exists():
        try:
            with open(runs_file, "r", encoding="utf-8") as f:
                runs = json.load(f)
        except Exception as e:
            print(f"⚠️ 讀取 runs.json 失敗: {e}")

    # 3. 建置主頁面 index.html
    if template_file.exists():
        with open(template_file, "r", encoding="utf-8") as f:
            index_html = f.read()

        tasks_json_str = json.dumps(tasks, ensure_ascii=False, indent=2)
        runs_json_str = json.dumps(runs, ensure_ascii=False, indent=2)

        # 替換 script 標籤內嵌資料
        pattern_tasks = r'(<script id="initial-tasks" type="application/json">)(.*?)(</script>)'
        replacement_tasks = rf'\g<1>\n{tasks_json_str}\n\g<3>'
        if re.search(pattern_tasks, index_html, flags=re.DOTALL):
            index_html = re.sub(pattern_tasks, replacement_tasks, index_html, flags=re.DOTALL)

        pattern_runs = r'(<script id="initial-runs" type="application/json">)(.*?)(</script>)'
        replacement_runs = rf'\g<1>\n{runs_json_str}\n\g<3>'
        if re.search(pattern_runs, index_html, flags=re.DOTALL):
            index_html = re.sub(pattern_runs, replacement_runs, index_html, flags=re.DOTALL)

        with open(index_file, "w", encoding="utf-8") as f:
            f.write(index_html)
        print(f"✅ 主儀表板編譯完成: index.html ({len(tasks)} 任務, {len(runs)} 紀錄)")
    else:
        print(f"❌ 找不到 template.html")

    # 4. 建置每一筆執行的獨立分頁 runs/<run_id>.html
    if template_run_file.exists():
        with open(template_run_file, "r", encoding="utf-8") as f:
            run_tpl = f.read()

        generated_pages = 0
        for r in runs:
            run_id = r.get("id")
            if not run_id:
                continue

            task_id = r.get("task_id", "")
            task_info = task_map.get(task_id, {})
            task_name = r.get("task_name") or task_info.get("name") or task_id
            status = r.get("status", "success")
            status_label = "執行成功" if status == "success" else ("執行失敗" if status == "error" else "需留意")
            status_badge_class = f"badge-{status}"
            duration = r.get("duration", "-")
            formatted_time = r.get("formatted_time") or r.get("timestamp", "-")
            schedule = task_info.get("schedule") or task_info.get("cron") or "常態排程"
            cron = task_info.get("cron", "-")
            task_desc = task_info.get("description", "Antigravity 2.0 自動化背景任務")

            raw_summary = r.get("summary", "")
            summary_clean = raw_summary.replace('"', '&quot;').replace('\n', ' ')
            summary_html = "<br>".join([html.escape(line) for line in raw_summary.split("\n") if line.strip()])

            raw_details = r.get("details", "")
            details_text = html.escape(raw_details) if raw_details else "無額外詳細日誌輸出。"

            # 替換獨立分頁佔位符
            page_content = run_tpl
            replacements = {
                "{{TASK_NAME}}": html.escape(task_name),
                "{{TASK_ID}}": html.escape(task_id),
                "{{RUN_ID}}": html.escape(run_id),
                "{{STATUS_LABEL}}": status_label,
                "{{STATUS_BADGE_CLASS}}": status_badge_class,
                "{{DURATION}}": html.escape(duration),
                "{{FORMATTED_TIME}}": html.escape(formatted_time),
                "{{SCHEDULE}}": html.escape(schedule),
                "{{CRON}}": html.escape(cron),
                "{{TASK_DESCRIPTION}}": html.escape(task_desc),
                "{{SUMMARY_HTML}}": summary_html,
                "{{SUMMARY_CLEAN}}": summary_clean,
                "{{DETAILS_TEXT}}": details_text,
                "{{LOG_LENGTH}}": str(len(raw_details))
            }

            for placeholder, val in replacements.items():
                page_content = page_content.replace(placeholder, val)

            target_run_file = runs_dir / f"{run_id}.html"
            with open(target_run_file, "w", encoding="utf-8") as rf:
                rf.write(page_content)
            generated_pages += 1

        print(f"📄 獨立分頁生成完畢: 共建立/更新 {generated_pages} 個獨立報告分頁於 runs/*.html")
    else:
        print(f"⚠️ 找不到 template_run.html，跳過獨立分頁生成。")


if __name__ == "__main__":
    build()
