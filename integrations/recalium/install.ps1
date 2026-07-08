<#
.SYNOPSIS
    Recalium multi-agent connector installer (Windows / PowerShell 7+).

.DESCRIPTION
    Wires Claude Code, GitHub Copilot, Codex, and Cursor to the local Recalium
    memory MCP server. Idempotent, backs up modified files (*.bak), writes no
    secrets. Safe to re-run.

.PARAMETER Url
    Override the MCP SSE endpoint (default http://localhost:8000/mcp/sse).

.PARAMETER DryRun
    Show what would change without writing anything.

.PARAMETER All
    Also wire user-level configs (Codex %USERPROFILE%\.codex\config.toml and the
    VS Code user mcp.json) in addition to repo-level files.

.EXAMPLE
    pwsh integrations/recalium/install.ps1 -DryRun
    pwsh integrations/recalium/install.ps1
    pwsh integrations/recalium/install.ps1 -All
#>
[CmdletBinding()]
param(
    [string]$Url = "http://localhost:8000/mcp/sse",
    [switch]$DryRun,
    [switch]$All
)

$ErrorActionPreference = "Stop"

$Kit = $PSScriptRoot
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$SseObj = [ordered]@{ type = "sse"; url = $Url }
$UrlObj = [ordered]@{ url = $Url }

# Claude Code hook commands. $CLAUDE_PROJECT_DIR is expanded by Claude Code at runtime.
$SsCmd   = 'powershell -NoProfile -ExecutionPolicy Bypass -File "$CLAUDE_PROJECT_DIR\integrations\recalium\hooks\recalium_session_start.ps1"'
$StopCmd = 'powershell -NoProfile -ExecutionPolicy Bypass -File "$CLAUDE_PROJECT_DIR\integrations\recalium\hooks\recalium_stop.ps1"'

function Ensure-Dir([string]$Path) {
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
}

function Merge-Mcp([string]$File, [string]$Key, $Obj) {
    if ($DryRun) { Write-Host "  DRY: merge $Key.recalium -> $File"; return }
    Ensure-Dir $File
    $data = [ordered]@{}
    if (Test-Path $File) {
        $raw = Get-Content -Raw -Path $File
        if ($raw -and $raw.Trim()) {
            try { $data = $raw | ConvertFrom-Json -AsHashtable }
            catch { Write-Warning "  $File is not valid JSON; skipping"; return }
        }
    }
    if (-not $data.Contains($Key)) { $data[$Key] = [ordered]@{} }
    $existing = $data[$Key]['recalium']
    $same = $false
    if ($existing) {
        $same = ($existing.url -eq $Obj.url)
        if ($Obj.Contains('type')) { $same = $same -and ($existing.type -eq $Obj.type) }
    }
    if ($same) {
        Write-Host "  = $File already current ($Key.recalium)"; return
    }
    if (Test-Path $File) { Copy-Item $File "$File.bak" -Force }
    $data[$Key]['recalium'] = $Obj
    ($data | ConvertTo-Json -Depth 20) | Set-Content -Path $File -Encoding utf8
    Write-Host "  + $Key.recalium -> $File"
}

function Install-File([string]$Src, [string]$Dest) {
    if ($DryRun) { Write-Host "  DRY: copy -> $Dest"; return }
    Ensure-Dir $Dest
    if ((Test-Path $Dest) -and ((Get-FileHash $Src).Hash -eq (Get-FileHash $Dest).Hash)) {
        Write-Host "  = $Dest already current"; return
    }
    if (Test-Path $Dest) { Copy-Item $Dest "$Dest.bak" -Force }
    Copy-Item $Src $Dest -Force
    Write-Host "  + $Dest"
}

function Test-HasRecalium($arr) {
    foreach ($group in $arr) {
        foreach ($h in $group.hooks) {
            if ($h.command -like "*recalium*") { return $true }
        }
    }
    return $false
}

function Add-ClaudeHooks {
    $File = Join-Path $RepoRoot ".claude\settings.json"
    if ($DryRun) { Write-Host "  DRY: append recalium hooks -> .claude/settings.json"; return }
    Ensure-Dir $File
    $data = [ordered]@{}
    if (Test-Path $File) {
        $raw = Get-Content -Raw -Path $File
        if ($raw -and $raw.Trim()) { $data = $raw | ConvertFrom-Json -AsHashtable }
    }
    if (-not $data.Contains("hooks")) { $data["hooks"] = [ordered]@{} }
    $hooks = $data["hooks"]
    $changed = $false
    foreach ($evt in @("SessionStart", "Stop")) {
        $cmd = if ($evt -eq "SessionStart") { $SsCmd } else { $StopCmd }
        if (-not $hooks.Contains($evt)) { $hooks[$evt] = @() }
        if (-not (Test-HasRecalium $hooks[$evt])) {
            $hooks[$evt] = @($hooks[$evt]) + @{ hooks = @(@{ type = "command"; command = $cmd; timeout = 15 }) }
            $changed = $true
        }
    }
    if (-not $changed) { Write-Host "  = .claude/settings.json already has recalium hooks"; return }
    if (Test-Path $File) { Copy-Item $File "$File.bak" -Force }
    ($data | ConvertTo-Json -Depth 20) | Set-Content -Path $File -Encoding utf8
    Write-Host "  + appended recalium SessionStart + Stop hooks -> .claude/settings.json"
}

function Install-CodexUser {
    $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
    $File = Join-Path $codexHome "config.toml"
    if ($DryRun) { Write-Host "  DRY: ensure [mcp_servers.recalium] -> $File"; return }
    if (-not (Test-Path $codexHome)) { New-Item -ItemType Directory -Force -Path $codexHome | Out-Null }
    if ((Test-Path $File) -and (Select-String -Path $File -Pattern '^\[mcp_servers\.recalium\]' -Quiet)) {
        Write-Host "  = $File already has [mcp_servers.recalium]"; return
    }
    if (Test-Path $File) { Copy-Item $File "$File.bak" -Force }
    $block = "`n[mcp_servers.recalium]`ncommand = `"npx`"`nargs = [`"-y`", `"mcp-remote`", `"$Url`"]`n"
    Add-Content -Path $File -Value $block
    Write-Host "  + [mcp_servers.recalium] -> $File"
}

function Install-VscodeUser {
    $File = Join-Path $env:APPDATA "Code\User\mcp.json"
    Merge-Mcp -File $File -Key "servers" -Obj $SseObj
}

Write-Host "Recalium connector installer"
Write-Host "  endpoint: $Url"
Write-Host "  repo:     $RepoRoot"
if ($DryRun) { Write-Host "  (dry-run - no files will be written)" }

Write-Host ""
Write-Host "Repo-level MCP configs:"
Merge-Mcp -File (Join-Path $RepoRoot ".mcp.json")       -Key "mcpServers" -Obj $SseObj
Merge-Mcp -File (Join-Path $RepoRoot ".vscode\mcp.json") -Key "servers"    -Obj $SseObj
Merge-Mcp -File (Join-Path $RepoRoot ".cursor\mcp.json") -Key "mcpServers" -Obj $UrlObj

Write-Host ""
Write-Host "Skills and rules:"
Install-File (Join-Path $Kit "claude-code\skill\SKILL.md")       (Join-Path $RepoRoot ".claude\skills\recalium-memory\SKILL.md")
Install-File (Join-Path $Kit "codex\skill\SKILL.md")            (Join-Path $RepoRoot ".codex\skills\recalium-memory\SKILL.md")
Install-File (Join-Path $Kit "github-copilot\skill\SKILL.md")   (Join-Path $RepoRoot ".github\skills\recalium-memory\SKILL.md")
Install-File (Join-Path $Kit "cursor\rules\recalium-memory.mdc") (Join-Path $RepoRoot ".cursor\rules\recalium-memory.mdc")

Write-Host ""
Write-Host "Claude Code hooks:"
Add-ClaudeHooks

if ($All) {
    Write-Host ""
    Write-Host "User-level configs (-All):"
    Install-CodexUser
    Install-VscodeUser
}

Write-Host ""
Write-Host "Done. Next steps:"
Write-Host "  1. Ensure Recalium is running (health: $($Url -replace '/mcp/sse','/api/health'))."
Write-Host "  2. Reload your editor and start the 'recalium' MCP server."
Write-Host "  3. Codex/Cursor pick up the config on next launch."
