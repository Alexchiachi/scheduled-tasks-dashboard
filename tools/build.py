#!/usr/bin/env python3
"""
build.py: 大道至簡 · 排程任務監測儀表板建置引擎
1. 將 data/tasks.json 與 data/runs.json 注入 index.html 模板中，確保離線與線上秒開。
2. 為每一筆執行的排程任務生成獨立分頁 HTML (runs/<run_id>.html)。
3. 為每個任務生成「歷史成果累積檔案庫」專屬頁面 (tasks/<task_id>.html)，完整呈現歷次成果演化脈絡。
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
    template_task_file = BASE_DIR / "template_task.html"

    runs_dir = BASE_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = BASE_DIR / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

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
    runs_by_task = {}
    if runs_file.exists():
        try:
            with open(runs_file, "r", encoding="utf-8") as f:
                runs = json.load(f)
                for r in runs:
                    tid = r.get("task_id", "")
                    if tid not in runs_by_task:
                        runs_by_task[tid] = []
                    runs_by_task[tid].append(r)
        except Exception as e:
            print(f"⚠️ 讀取 runs.json 失敗: {e}")

    # 更新 tasks 中的真實統計 (根據 runs.json 累計)
    for t in tasks:
        tid = t["id"]
        t_runs = runs_by_task.get(tid, [])
        t["total_runs"] = len(t_runs)
        success_runs = [r for r in t_runs if r.get("status") == "success"]
        t["success_count"] = len(success_runs)
        if t_runs:
            t["last_run"] = t_runs[0].get("formatted_time")
            t["last_status"] = t_runs[0].get("status")
            t["last_summary"] = t_runs[0].get("summary")
            t["last_duration"] = t_runs[0].get("duration")

    # 3. 建置主頁面 index.html
    if template_file.exists():
        with open(template_file, "r", encoding="utf-8") as f:
            index_html = f.read()

        tasks_json_str = json.dumps(tasks, ensure_ascii=False, indent=2)
        runs_json_str = json.dumps(runs, ensure_ascii=False, indent=2)

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
        print(f"✅ 主儀表板編譯完成: index.html ({len(tasks)} 任務, {len(runs)} 累積紀錄)")

    # 4. 建置每一筆執行的獨立分頁 runs/<run_id>.html
    if template_run_file.exists():
        with open(template_run_file, "r", encoding="utf-8") as f:
            run_tpl = f.read()

        generated_run_pages = 0
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
            task_total_runs = str(len(runs_by_task.get(task_id, [])))

            raw_summary = r.get("summary", "")
            summary_clean = raw_summary.replace('"', '&quot;').replace('\n', ' ')
            summary_html = "<br>".join([html.escape(line) for line in raw_summary.split("\n") if line.strip()])

            raw_details = r.get("details", "")
            details_text = html.escape(raw_details) if raw_details else "無額外詳細日誌輸出。"

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
                "{{LOG_LENGTH}}": str(len(raw_details)),
                "{{TASK_TOTAL_RUNS}}": task_total_runs
            }

            page_content = run_tpl
            for placeholder, val in replacements.items():
                page_content = page_content.replace(placeholder, val)

            target_run_file = runs_dir / f"{run_id}.html"
            with open(target_run_file, "w", encoding="utf-8") as rf:
                rf.write(page_content)
            generated_run_pages += 1

        print(f"📄 單期獨立分頁生成完畢: 共建立/更新 {generated_run_pages} 個分頁於 runs/*.html")

    # 5. 建置每個任務的「歷史成果累積檔案庫」專屬分頁 tasks/<task_id>.html
    if template_task_file.exists():
        with open(template_task_file, "r", encoding="utf-8") as f:
            task_tpl = f.read()

        generated_task_pages = 0
        for t in tasks:
            tid = t["id"]
            tname = t.get("name", tid)
            t_runs = runs_by_task.get(tid, [])
            total_runs = len(t_runs)
            success_runs = [r for r in t_runs if r.get("status") == "success"]
            success_rate = str(round((len(success_runs) / total_runs * 100))) if total_runs > 0 else "100"
            last_run_time = t.get("last_run", "尚無紀錄")
            cron = t.get("cron", "-")
            schedule = t.get("schedule", "常態排程")
            desc = t.get("description", "Antigravity 2.0 自動化背景任務")
            status = t.get("status", "idle")
            status_label = "正常運行中" if status == "success" else ("需留意" if status == "warning" else ("異常" if status == "error" else "待命狀態"))
            status_badge_class = f"badge-{status}"

            # 構建歷次累積成果時間軸 HTML
            if total_runs == 0:
                timeline_html = '<div class="timeline-card" style="text-align: center; color: var(--ink-muted); padding: 40px;">尚無歷史執行紀錄</div>'
            else:
                items = []
                for idx, r in enumerate(t_runs):
                    run_no = total_runs - idx
                    r_status = r.get("status", "success")
                    r_status_class = f"badge-{r_status}"
                    r_status_label = "執行成功" if r_status == "success" else ("執行失敗" if r_status == "error" else "需留意")
                    r_time = r.get("formatted_time") or r.get("timestamp", "-")
                    r_duration = r.get("duration", "-")
                    r_summary = r.get("summary", "")
                    r_summary_html = "<br>".join([html.escape(line) for line in r_summary.split("\n") if line.strip()])
                    r_details = html.escape(r.get("details", ""))
                    r_id = r.get("id", "")

                    btn_details = f'<button class="btn" onclick="toggleDetails(\'t-details-{idx}\')" style="font-size: 0.78rem;">🔍 頁內展開日誌</button>' if r_details else ''
                    box_details = f'<div id="t-details-{idx}" class="details-box"><pre class="details-pre">{r_details}</pre></div>' if r_details else ''

                    item_html = f"""
          <div class="timeline-card">
            <div class="timeline-head">
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span class="run-counter-badge">第 {run_no} 期</span>
                <span class="badge {r_status_class}">{r_status_label}</span>
                <span class="timeline-time tabular" style="font-size: 0.85rem; color: var(--ink-soft); font-weight: 600;">{html.escape(r_time)}</span>
                <span class="badge badge-idle tabular timeline-duration">{html.escape(r_duration)}</span>
              </div>
              <span class="tabular" style="font-size: 0.75rem; color: var(--ink-muted);">{html.escape(r_id)}</span>
            </div>

            <div class="run-summary-box">
              {r_summary_html}
            </div>

            <div class="run-actions">
              <div style="display: flex; gap: 8px; align-items: center;">
                <a href="../runs/{r_id}.html" target="_blank" class="btn btn-primary" style="font-size: 0.78rem;" title="在新分頁檢視此期完整獨立說明">
                  📄 檢視此期獨立報告 ↗
                </a>
                {btn_details}
              </div>
            </div>

            {box_details}
          </div>
                    """
                    items.append(item_html)
                timeline_html = "\n".join(items)

            page_content = task_tpl
            replacements = {
                "{{TASK_NAME}}": html.escape(tname or tid),
                "{{TASK_ID}}": html.escape(tid),
                "{{SCHEDULE}}": html.escape(schedule or "常態排程"),
                "{{CRON}}": html.escape(cron or "-"),
                "{{TASK_DESCRIPTION}}": html.escape(desc or ""),
                "{{TOTAL_RUNS}}": str(total_runs),
                "{{SUCCESS_RATE}}": success_rate,
                "{{LAST_RUN_TIME}}": html.escape(last_run_time or "尚無紀錄"),
                "{{STATUS_LABEL}}": status_label,
                "{{STATUS_BADGE_CLASS}}": status_badge_class,
                "{{TIMELINE_ITEMS_HTML}}": timeline_html
            }

            for placeholder, val in replacements.items():
                page_content = page_content.replace(placeholder, val)

            target_task_file = tasks_dir / f"{tid}.html"
            with open(target_task_file, "w", encoding="utf-8") as tf:
                tf.write(page_content)
            generated_task_pages += 1

        print(f"📜 任務累積歷史檔案庫生成完畢: 共建立/更新 {generated_task_pages} 個專屬任務檔案頁於 tasks/*.html")


if __name__ == "__main__":
    build()
