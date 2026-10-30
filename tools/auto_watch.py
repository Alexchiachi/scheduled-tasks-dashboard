#!/usr/bin/env python3
"""
auto_watch.py: 全自動排程任務監測守護引擎（零指令、無感自動化）
自動監聽 Antigravity 2.0 對話資料庫與對話歷程，
當任何排程任務執行完成 (IDLE)，自動提取「成果說明」、「耗時」與「執行日誌」，
寫入 data/runs.json 與 data/tasks.json，重新編譯並自動 Push 到 GitHub 遠端。
"""
import argparse
import datetime
import glob
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_FILE = BASE_DIR / "data" / ".processed_conversations"


def log(msg):
    print(msg, flush=True)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    res = subprocess.run(
        cmd,
        cwd=cwd or BASE_DIR,
        capture_output=True,
        text=True,
        env=env
    )
    return res


def load_processed_ids() -> set:
    if not PROCESSED_FILE.exists():
        return set()
    try:
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception:
        return set()


def save_processed_id(cid: str):
    try:
        with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
            f.write(cid.strip() + "\n")
    except Exception as e:
        print(f"⚠️ 寫入 processed 失敗: {e}")


def load_sidecar_specs():
    """載入所有 Sidecar 定義作為匹配特徵"""
    sidecars_pattern = os.path.expanduser("~/.gemini/config/sidecars/*/sidecar.json")
    sidecar_map = {}
    for sf in glob.glob(sidecars_pattern):
        slug = os.path.basename(os.path.dirname(sf))
        try:
            with open(sf, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                args = cfg.get("args", [])
                prompt = args[4] if len(args) >= 5 else ""
                display_name = cfg.get("display_name", slug)
                cron = args[0] if args else ""
                
                # 特徵抽取：前 60 字元
                sig = prompt.strip()[:60]
                sidecar_map[slug] = {
                    "id": slug,
                    "name": display_name,
                    "cron": cron,
                    "sig": sig,
                    "full_prompt": prompt
                }
        except Exception:
            pass
    return sidecar_map


def match_sidecar(preview: str, title: str, sidecar_map: dict):
    """將對話特徵與 Sidecar 比對"""
    for slug, sc in sidecar_map.items():
        name = sc["name"]
        sig = sc["sig"]
        if (sig and sig in preview) or (preview and preview in sc["full_prompt"]) or (name and name in title):
            return sc
    return None


def parse_transcript(conversation_id: str):
    """解析對話日誌，提取最後結論、起訖時間、步驟數與錯誤狀態"""
    tpath = os.path.expanduser(f"~/.gemini/antigravity/brain/{conversation_id}/.system_generated/logs/transcript.jsonl")
    if not os.path.exists(tpath):
        return None

    steps = []
    try:
        with open(tpath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    steps.append(json.loads(line))
    except Exception as e:
        print(f"⚠️ 讀取 transcript.jsonl 失敗 ({conversation_id}): {e}")
        return None

    if not steps:
        return None

    start_iso = steps[0].get("created_at")
    end_iso = steps[-1].get("created_at")
    
    # 計算耗時
    duration_str = "-"
    if start_iso and end_iso:
        try:
            s_dt = datetime.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            e_dt = datetime.datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
            seconds = int((e_dt - s_dt).total_seconds())
            if seconds < 60:
                duration_str = f"{seconds}s"
            else:
                duration_str = f"{seconds // 60}m {seconds % 60}s"
        except Exception:
            pass

    has_error = False
    last_model_resp = ""
    error_details = []

    for s in steps:
        if s.get("status") == "ERROR":
            has_error = True
            err_c = s.get("content", "")
            if err_c:
                error_details.append(err_c[:300])
        if s.get("source") == "MODEL" and s.get("type") == "PLANNER_RESPONSE":
            c = s.get("content", "")
            if c:
                last_model_resp = c

    status = "error" if has_error else "success"
    if has_error and last_model_resp:
        status = "warning"

    # 清洗成果說明摘要（取前 200 字精華，去除 Markdown 標題符號）
    summary = ""
    if last_model_resp:
        lines = [l.strip() for l in last_model_resp.split("\n") if l.strip()]
        clean_lines = []
        for l in lines:
            # 去除前綴 #, *, -
            cl = re.sub(r'^[#*\-\s]+', '', l)
            if cl:
                clean_lines.append(cl)
        summary = " ".join(clean_lines)[:240]
        if len(" ".join(clean_lines)) > 240:
            summary += "..."
    else:
        summary = "排程任務執行完成，無額外輸出。"

    # 詳細內容
    details = last_model_resp.strip()
    if error_details:
        details += "\n\n=== 執行過程異常日誌 ===\n" + "\n".join(error_details)

    return {
        "status": status,
        "duration": duration_str,
        "summary": summary,
        "details": details,
        "end_iso": end_iso
    }


def scan_and_record(push: bool = True):
    db_path = os.path.expanduser("~/.gemini/antigravity/conversation_summaries.db")
    if not os.path.exists(db_path):
        return 0

    sidecar_map = load_sidecar_specs()
    processed_ids = load_processed_ids()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # 搜尋最近完成的對話（IDLE）
    rows = cur.execute("""
        SELECT conversation_id, title, preview, status, last_modified_time 
        FROM conversation_summaries 
        WHERE status = 'CASCADE_RUN_STATUS_IDLE'
        ORDER BY last_modified_time DESC LIMIT 50
    """).fetchall()

    new_records = 0

    for cid, title, preview, st, lmt in rows:
        if cid in processed_ids:
            continue

        matched = match_sidecar(preview, title, sidecar_map)
        if not matched:
            continue

        # 解析該對話日誌
        parsed = parse_transcript(cid)
        if not parsed:
            continue

        # 呼叫 record_task 模組寫入
        from record_task import record_task
        print(f"🤖 [自動捕獲] 偵測到排程完成: [{matched['name']}] (ID: {cid[:8]})")
        record_task(
            task_id=matched["id"],
            status=parsed["status"],
            summary=parsed["summary"],
            details=parsed["details"],
            duration=parsed["duration"],
            title=matched["name"],
            push=False  # 先批次寫入，最後統一 push
        )

        save_processed_id(cid)
        new_records += 1

    if new_records > 0:
        print(f"✨ 本次自動捕獲並記錄了 {new_records} 筆排程任務！")
        # 執行靜態編譯
        run_cmd(["python3", str(BASE_DIR / "tools" / "build.py")])

        if push:
            print("🚀 [自動推送] 正在同步到遠端 GitHub Pages...")
            run_cmd(["git", "add", "data/", "index.html", "runs/", "tasks/"])
            run_cmd(["git", "commit", "-m", f"chore(auto-monitor): 自動同步 {new_records} 筆最新排程成果"])
            push_res = run_cmd(["git", "push", "origin", "main"])
            if push_res.returncode == 0:
                print("🎉 遠端推送成功！儀表板已全自動更新。")
            else:
                print(f"ℹ️ 遠端推送回傳: {push_res.stderr.strip() or push_res.stdout.strip()}")
    else:
        # print("安靜守護中：暫無新增排程完成事件")
        pass

    return new_records


def daemon_loop(interval: int = 30, push: bool = True):
    print(f"👁️ 大道至簡 · 排程監測守護進程已啟動 (檢測間隔: {interval} 秒)", flush=True)
    print("   全天候自動捕獲完成任務，免指令、自動寫入、自動推送。", flush=True)
    try:
        while True:
            scan_and_record(push=push)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 守護進程已停止。", flush=True)


def main():
    parser = argparse.ArgumentParser(description="全自動排程任務監測守護引擎")
    parser.add_argument("--daemon", action="store_true", help="以守護模式持續監聽")
    parser.add_argument("--interval", type=int, default=30, help="守護檢測間隔秒數 (預設 30)")
    parser.add_argument("--no-push", action="store_true", help="不自動 push 到遠端")
    parser.add_argument("--once", action="store_true", help="僅執行一次掃描後退出")

    args = parser.parse_args()

    if args.daemon:
        daemon_loop(interval=args.interval, push=not args.no_push)
    else:
        scan_and_record(push=not args.no_push)


if __name__ == "__main__":
    main()
