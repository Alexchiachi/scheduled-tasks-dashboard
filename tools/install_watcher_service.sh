#!/usr/bin/env bash
# install_watcher_service.sh: 將全自動排程監測守護引擎註冊為 macOS LaunchAgent
# 開機與登入後自動常駐守護，每 30 秒自動偵測完成的排程，全自動寫入並推送，免指令！

set -e

PLIST_NAME="com.antigravity.tasks-dashboard-watcher"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
# 使用 scratch 路徑避免 macOS ~/Documents/ TCC 沙盒權限阻擋
REPO_DIR="$HOME/.gemini/antigravity/scratch/scheduled-tasks-dashboard"
PYTHON_BIN="/usr/bin/python3"

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$REPO_DIR/data"

echo "📦 正在建立 macOS 守護進程配置: ${PLIST_PATH} ..."

cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_BIN}</string>
        <string>${REPO_DIR}/tools/auto_watch.py</string>
        <string>--daemon</string>
        <string>--interval</string>
        <string>30</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>${REPO_DIR}</string>
    <key>StandardOutPath</key>
    <string>${REPO_DIR}/data/watcher.log</string>
    <key>StandardErrorPath</key>
    <string>${REPO_DIR}/data/watcher.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>
</dict>
</plist>
EOF

echo "🚀 載入並啟動常駐守護進程..."
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load -w "$PLIST_PATH"

echo "✅ 成功啟動！排程監測已全自動常駐背景，無需任何手動指令。"
echo "📄 運作日誌位於: ${REPO_DIR}/data/watcher.log"
