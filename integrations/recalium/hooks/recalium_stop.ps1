# Recalium Stop hook (Claude Code, Windows / PowerShell 7+).
# Reminds the agent to persist durable outcomes to Recalium. Never blocks.

$ErrorActionPreference = 'SilentlyContinue'
$url = if ($env:RECALIUM_URL) { $env:RECALIUM_URL } else { 'http://localhost:8000' }

try {
    $null = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri "$url/api/health"
    [Console]::Error.WriteLine("Reminder: persist durable outcomes to Recalium via ingest_memory (include source_metadata + a stable idempotency_key).")
}
catch { }

exit 0
