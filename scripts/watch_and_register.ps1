# Waits for the Claude Desktop app to fully exit, then re-inserts the
# 'canvas' MCP entry into claude_desktop_config.json so the next launch
# loads it. Logs to scripts\register.log.
$log = Join-Path $PSScriptRoot "register.log"
"$(Get-Date -Format o) watcher started, waiting for Claude to exit..." | Out-File $log -Encoding utf8

while (Get-Process -Name "Claude" -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 2
}
Start-Sleep -Seconds 3  # let the app finish flushing its config on shutdown

$py = Join-Path $PSScriptRoot "register_canvas.py"
$result = & python $py 2>&1
"$(Get-Date -Format o) Claude exited; patch result: $result" | Out-File $log -Append -Encoding utf8
