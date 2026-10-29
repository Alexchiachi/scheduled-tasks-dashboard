#!/usr/bin/env python3
"""
sync_sidecars.py: 自動掃描 Antigravity 2.0 排程任務目錄 (~/.gemini/config/sidecars/)
將所有註冊的排程任務資訊與 Cron 規則同步至 data/tasks.json
"""
import glob
import json
import os
import sys
from pathlib import Path


def parse_cron_to_human(cron_str: str) -> str:
    """將標準 5 欄位 Cron 轉為人性化中文說明"""
    parts = cron_str.strip().split()
    if len(parts) != 5:
        return cron_str
    
    minute, hour, dom, month, dow = parts
    
    # 星期對照
    weekday_map = {
        "0": "日", "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "日"
    }
    
    time_str = f"{int(hour):02d}:{int(minute):02d}" if hour.isdigit() and minute.isdigit() else f"{hour}:{minute}"
    
    if dom == "*" and month == "*":
        if dow == "*":
            return f"每日 {time_str}"
        elif dow in weekday_map:
            return f"每週{weekday_map[dow]} {time_str}"
        elif "," in dow:
            days = "、".join([f"週{weekday_map.get(d, d)}" for d in dow.split(",")])
            return f"每{days} {time_str}"
        elif "-" in dow:
            s, e = dow.split("-")
            return f"每週{weekday_map.get(s, s)}至週{weekday_map.get(e, e)} {time_str}"
    
    return f"Cron ({cron_str})"


def sync_sidecars(base_dir: Path = None):
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent

    sidecars_pattern = os.path.expanduser("~/.gemini/config/sidecars/*/sidecar.json")
    sidecar_files = glob.glob(sidecars_pattern)

    tasks_file = base_dir / "data" / "tasks.json"
    tasks_file.parent.mkdir(parents=True, exist_ok=True)

    existing_tasks = {}
    if tasks_file.exists():
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for t in data:
                    existing_tasks[t["id"]] = t
        except Exception as e:
            print(f"⚠️ 讀取現有 tasks.json 失敗: {e}，將建立新紀錄")

    synced_tasks = []
    for sf in sorted(sidecar_files):
        slug = os.path.basename(os.path.dirname(sf))
        try:
            with open(sf, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            
            cron = ""
            args = cfg.get("args", [])
            if args and len(args) > 0:
                cron = args[0]
            
            display_name = cfg.get("display_name", slug)
            prompt = args[4] if len(args) >= 5 else ""
            human_schedule = parse_cron_to_human(cron)

            # 保留現有統計數據
            prev = existing_tasks.get(slug, {})
            task_info = {
                "id": slug,
                "name": display_name,
                "cron": cron,
                "schedule": human_schedule,
                "status": prev.get("status", "idle"),  # idle, success, warning, error
                "last_run": prev.get("last_run", None),
                "last_duration": prev.get("last_duration", "-"),
                "last_summary": prev.get("last_summary", "尚無執行紀錄"),
                "total_runs": prev.get("total_runs", 0),
                "success_count": prev.get("success_count", 0),
                "description": prompt.strip()[:200] + ("..." if len(prompt.strip()) > 200 else "")
            }
            synced_tasks.append(task_info)
        except Exception as ex:
            print(f"❌ 讀取 {sf} 出錯: {ex}")

    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump(synced_tasks, f, ensure_ascii=False, indent=2)

    print(f"✅ 成功同步 {len(synced_tasks)} 個排程任務至 {tasks_file}")
    return synced_tasks


if __name__ == "__main__":
    sync_sidecars()
