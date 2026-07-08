# Recalium SessionStart hook (Claude Code, Windows / PowerShell 7+).
# Checks the local memory service and injects a usage reminder as session context.
# Exits 0 even when Recalium is down so it never blocks a session.

$ErrorActionPreference = 'SilentlyContinue'
$url = if ($env:RECALIUM_URL) { $env:RECALIUM_URL } else { 'http://localhost:8000' }

try {
    $null = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri "$url/api/health"
    $ctx = "Recalium memory is available at $url (MCP: $url/mcp/sse). Before starting, call retrieve_memory to recall relevant prior context. After finishing, call ingest_memory to store durable, source-backed memory. Always check item provenance before trusting a result."
    $payload = @{ hookSpecificOutput = @{ hookEventName = 'SessionStart'; additionalContext = $ctx } }
    $payload | ConvertTo-Json -Depth 5 -Compress
}
catch {
    [Console]::Error.WriteLine("Recalium memory service not reachable at $url - start it to enable cross-session memory.")
}

exit 0
