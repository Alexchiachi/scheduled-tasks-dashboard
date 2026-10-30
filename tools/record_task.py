#!/usr/bin/env python3
"""
record_task.py: 排程任務完成回報與結果寫入工具
只要任何排程任務執行完畢，調用此腳本即可將執行結果與說明寫入儀表板，
並可自動建置及一鍵 Push 至 GitHub 倉庫發布。

用法範例：
    python3 tools/record_task.py \
        --task daily-gardener \
        --status success \
        --summary "第二心智演化日誌撰寫完畢，雙基地已同步，Obsidian已成功推送到GitHub。" \
        --duration "38s" \
        --push
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def run_cmd(cmd, cwd=None, check=False):
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    res = subprocess.run(
        cmd,
        cwd=cwd or BASE_DIR,
        capture_output=True,
        text=True,
        env=env
    )
    if check and res.returncode != 0:
        err = res.stderr.strip() if res.stderr else res.stdout.strip()
        raise RuntimeError(f"Command failed ({' '.join(cmd)}): {err}")
    return res


def record_task(
    task_id: str,
    status: str = "success",
    summary: str = "",
    details: str = "",
    duration: str = "-",
    title: str = None,
    push: bool = False
):
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    timestamp_iso = now.isoformat()
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # 1. 讀取或同步 tasks.json
    tasks_file = BASE_DIR / "data" / "tasks.json"
    tasks = []
    if tasks_file.exists():
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except Exception as e:
            print(f"⚠️ 讀取 tasks.json 出錯: {e}")

    task_entry = None
    for t in tasks:
        if t["id"] == task_id:
            task_entry = t
            break

    # 若任務未在 tasks.json 中（可能新建立），自動補充
    if not task_entry:
        task_name = title or task_id
        task_entry = {
            "id": task_id,
            "name": task_name,
            "cron": "-",
            "schedule": "手動或自訂排程",
            "status": status,
            "last_run": formatted_time,
            "last_duration": duration,
            "last_summary": summary,
            "total_runs": 0,
            "success_count": 0,
            "description": summary
        }
        tasks.append(task_entry)
    else:
        if title:
            task_entry["name"] = title
        task_entry["status"] = status
        task_entry["last_run"] = formatted_time
        task_entry["last_duration"] = duration
        task_entry["last_summary"] = summary

    task_entry["total_runs"] = task_entry.get("total_runs", 0) + 1
    if status == "success":
        task_entry["success_count"] = task_entry.get("success_count", 0) + 1

    # 寫回 tasks.json
    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    # 2. 寫入 runs.json
    runs_file = BASE_DIR / "data" / "runs.json"
    runs = []
    if runs_file.exists():
        try:
            with open(runs_file, "r", encoding="utf-8") as f:
                runs = json.load(f)
        except Exception as e:
            print(f"⚠️ 讀取 runs.json 出錯: {e}")

    run_id = f"run_{now.strftime('%Y%m%d_%H%M%S')}_{task_id}"
    new_run = {
        "id": run_id,
        "task_id": task_id,
        "task_name": task_entry.get("name", task_id),
        "status": status,  # success, warning, error
        "timestamp": timestamp_iso,
        "formatted_time": formatted_time,
        "duration": duration,
        "summary": summary,
        "details": details.strip()
    }

    # 最新執行放在最前面
    runs.insert(0, new_run)
    # 限制歷史總量最多保留 1000 筆，避免無限制膨脹
    if len(runs) > 1000:
        runs = runs[:1000]

    with open(runs_file, "w", encoding="utf-8") as f:
        json.dump(runs, f, ensure_ascii=False, indent=2)

    print(f"📝 [紀錄成功] 任務: {task_entry.get('name')} | 狀態: {status} | 時間: {formatted_time}")
    print(f"   說明: {summary}")

    # 3. 自動執行儀表板靜態編譯
    build_script = BASE_DIR / "tools" / "build.py"
    if build_script.exists():
        run_cmd(["python3", str(build_script)], check=False)

    # 4. 若指定 --push，自動提交並推送到 GitHub
    if push:
        print("🚀 [自動推送] 正在推送到 GitHub 遠端倉庫...")
        commit_msg = f"chore(monitor): 記錄 [{task_entry.get('name')}] 執行成果 ({status})"
        
        run_cmd(["git", "add", "data/", "index.html", "runs/"])
        commit_res = run_cmd(["git", "commit", "-m", commit_msg])
        if commit_res.returncode == 0:
            print(f"✅ Git 提交完成: {commit_msg}")
        else:
            print(f"ℹ️ Git 無需額外提交或變更已包含")

        push_res = run_cmd(["git", "push", "origin", "main"])
        if push_res.returncode == 0:
            print("🎉 GitHub 遠端推送成功！儀表板已更新上線。")
        else:
            err_msg = push_res.stderr.strip() or push_res.stdout.strip()
            print(f"⚠️ 推送失敗或遠端尚未建立: {err_msg}")


def main():
    parser = argparse.ArgumentParser(description="記錄排程任務執行結果與說明至儀表板")
    parser.add_argument("--task", required=True, help="任務標識符號 slug (例如: daily-gardener, morning-brief)")
    parser.add_argument("--status", choices=["success", "warning", "error"], default="success", help="執行狀態")
    parser.add_argument("--summary", required=True, help="執行結果說明摘要")
    parser.add_argument("--details", default="", help="詳細日誌、產出清單或補充報告 (可多行)")
    parser.add_argument("--details-file", help="從指定檔案讀取詳細日誌內容")
    parser.add_argument("--duration", default="-", help="任務耗時 (例如: 15s, 1m 20s)")
    parser.add_argument("--title", help="任務自訂中文名稱")
    parser.add_argument("--push", action="store_true", help="記錄後立即自動 Git Commit 並 Push 到遠端")

    args = parser.parse_args()

    details_content = args.details
    if args.details_file and os.path.exists(args.details_file):
        try:
            with open(args.details_file, "r", encoding="utf-8") as df:
                details_content = df.read()
        except Exception as e:
            print(f"⚠️ 讀取 details-file 出錯: {e}")

    record_task(
        task_id=args.task,
        status=args.status,
        summary=args.summary,
        details=details_content,
        duration=args.duration,
        title=args.title,
        push=args.push
    )


if __name__ == "__main__":
    main()
