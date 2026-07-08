#!/usr/bin/env bash
#
# Recalium multi-agent connector installer (Linux/macOS).
#
# Wires Claude Code, GitHub Copilot, Codex, and Cursor to the local Recalium
# memory MCP server. Idempotent, backs up modified files (*.bak), writes no
# secrets. Safe to re-run.
#
# Usage:
#   bash integrations/recalium/install.sh [--dry-run] [--all] [--url <sse-url>]
#
#   --dry-run   Show what would change without writing anything.
#   --all       Also wire user-level configs (Codex ~/.codex/config.toml,
#               VS Code user mcp.json) in addition to repo-level files.
#   --url URL   Override the MCP SSE endpoint (default http://localhost:8000/mcp/sse).
#
set -euo pipefail

URL="http://localhost:8000/mcp/sse"
DRY_RUN=0
DO_USER=0

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) URL="${2:?--url needs a value}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --all) DO_USER=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT="$SCRIPT_DIR"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SSE_OBJ="$(printf '{"type":"sse","url":"%s"}' "$URL")"
URL_OBJ="$(printf '{"url":"%s"}' "$URL")"
OPENCODE_OBJ="$(printf '{"type":"remote","url":"%s","enabled":true}' "$URL")"

# Claude Code hook commands. Single-quoted so $CLAUDE_PROJECT_DIR is expanded by
# Claude Code at runtime, not by this script.
SS_CMD='bash "$CLAUDE_PROJECT_DIR/integrations/recalium/hooks/recalium_session_start.sh"'
STOP_CMD='bash "$CLAUDE_PROJECT_DIR/integrations/recalium/hooks/recalium_stop.sh"'

log() { printf '%s\n' "$*"; }
tilde() { printf '%s' "${1/#$HOME/~}"; }

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for safe JSON merges." >&2
  exit 1
fi

# Merge {key: {recalium: obj}} into a JSON file. Idempotent, backs up on change.
merge_mcp_json() {
  local file="$1" key="$2" obj="$3"
  if [[ $DRY_RUN -eq 1 ]]; then log "  DRY: merge $key.recalium -> $(tilde "$file")"; return 0; fi
  mkdir -p "$(dirname "$file")"
  RC_FILE="$file" RC_KEY="$key" RC_OBJ="$obj" python3 - <<'PY'
import json, os, shutil, sys
file = os.environ["RC_FILE"]; key = os.environ["RC_KEY"]; obj = json.loads(os.environ["RC_OBJ"])
data = {}
if os.path.exists(file):
    with open(file, encoding="utf-8") as f:
        raw = f.read().strip()
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print(f"  ! {file} is not valid JSON; skipping", file=sys.stderr); raise SystemExit
if not isinstance(data, dict):
    print(f"  ! {file} top-level is not an object; skipping", file=sys.stderr); raise SystemExit
container = data.setdefault(key, {})
if container.get("recalium") == obj:
    print(f"  = {file} already current ({key}.recalium)"); raise SystemExit
if os.path.exists(file):
    shutil.copyfile(file, file + ".bak")
container["recalium"] = obj
with open(file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2); f.write("\n")
print(f"  + {key}.recalium -> {file}")
PY
}

# Copy a file, backing up on change; skip when identical.
install_file() {
  local src="$1" dest="$2"
  if [[ $DRY_RUN -eq 1 ]]; then log "  DRY: copy -> $(tilde "$dest")"; return 0; fi
  mkdir -p "$(dirname "$dest")"
  if [[ -f "$dest" ]] && cmp -s "$src" "$dest"; then log "  = $(tilde "$dest") already current"; return 0; fi
  [[ -f "$dest" ]] && cp "$dest" "$dest.bak"
  cp "$src" "$dest"
  log "  + $(tilde "$dest")"
}

# Append Recalium SessionStart + Stop hooks, preserving existing hooks.
append_claude_hooks() {
  local file="$REPO_ROOT/.claude/settings.json"
  if [[ $DRY_RUN -eq 1 ]]; then log "  DRY: append recalium hooks -> .claude/settings.json"; return 0; fi
  mkdir -p "$(dirname "$file")"
  RC_FILE="$file" RC_SS="$SS_CMD" RC_STOP="$STOP_CMD" python3 - <<'PY'
import json, os, shutil
file = os.environ["RC_FILE"]; ss = os.environ["RC_SS"]; stop = os.environ["RC_STOP"]
data = {}
if os.path.exists(file):
    with open(file, encoding="utf-8") as f:
        raw = f.read().strip()
    if raw:
        data = json.loads(raw)
hooks = data.setdefault("hooks", {})
def ensure(event, cmd):
    arr = hooks.setdefault(event, [])
    for group in arr:
        for h in group.get("hooks", []):
            if "recalium" in (h.get("command") or ""):
                return False
    arr.append({"hooks": [{"type": "command", "command": cmd, "timeout": 15}]})
    return True
changed = ensure("SessionStart", ss) | ensure("Stop", stop)
if not changed:
    print("  = .claude/settings.json already has recalium hooks"); raise SystemExit
if os.path.exists(file):
    shutil.copyfile(file, file + ".bak")
with open(file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2); f.write("\n")
print("  + appended recalium SessionStart + Stop hooks -> .claude/settings.json")
PY
}

install_codex_user() {
  local codex_home="${CODEX_HOME:-$HOME/.codex}"
  local file="$codex_home/config.toml"
  if [[ $DRY_RUN -eq 1 ]]; then log "  DRY: ensure [mcp_servers.recalium] -> $(tilde "$file")"; return 0; fi
  mkdir -p "$codex_home"
  if [[ -f "$file" ]] && grep -q '^\[mcp_servers\.recalium\]' "$file"; then
    log "  = $(tilde "$file") already has [mcp_servers.recalium]"; return 0
  fi
  [[ -f "$file" ]] && cp "$file" "$file.bak"
  {
    [[ -f "$file" && -s "$file" ]] && printf '\n'
    printf '[mcp_servers.recalium]\ncommand = "npx"\nargs = ["-y", "mcp-remote", "%s"]\n' "$URL"
  } >> "$file"
  log "  + [mcp_servers.recalium] -> $(tilde "$file")"
}

install_vscode_user() {
  local file
  case "$(uname -s)" in
    Darwin) file="$HOME/Library/Application Support/Code/User/mcp.json" ;;
    *) file="$HOME/.config/Code/User/mcp.json" ;;
  esac
  merge_mcp_json "$file" "servers" "$SSE_OBJ"
}

install_hermes_user() {
  local file="${HERMES_HOME:-$HOME/.hermes}/config.yaml"
  if [[ $DRY_RUN -eq 1 ]]; then log "  DRY: ensure mcp_servers.recalium -> $(tilde "$file")"; return 0; fi
  if ! python3 -c "import yaml" >/dev/null 2>&1; then
    log "  ! PyYAML not available — skipping Hermes (see integrations/recalium/hermes/SETUP.md)"; return 0
  fi
  mkdir -p "$(dirname "$file")"
  RC_FILE="$file" RC_URL="$URL" python3 - <<'PY'
import os, shutil, yaml
file = os.environ["RC_FILE"]; url = os.environ["RC_URL"]
data = {}
if os.path.exists(file):
    with open(file, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
if not isinstance(data, dict):
    print(f"  ! {file} is not a mapping; skipping"); raise SystemExit
servers = data.setdefault("mcp_servers", {})
obj = {"command": "npx", "args": ["-y", "mcp-remote", url]}
if servers.get("recalium") == obj:
    print(f"  = {file} already current (mcp_servers.recalium)"); raise SystemExit
if os.path.exists(file):
    shutil.copyfile(file, file + ".bak")
servers["recalium"] = obj
with open(file, "w", encoding="utf-8") as f:
    yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
print(f"  + mcp_servers.recalium -> {file}")
PY
}

log "Recalium connector installer"
log "  endpoint: $URL"
log "  repo:     $REPO_ROOT"
[[ $DRY_RUN -eq 1 ]] && log "  (dry-run — no files will be written)"

log ""
log "Repo-level MCP configs:"
merge_mcp_json "$REPO_ROOT/.mcp.json" "mcpServers" "$SSE_OBJ"
merge_mcp_json "$REPO_ROOT/.vscode/mcp.json" "servers" "$SSE_OBJ"
merge_mcp_json "$REPO_ROOT/.cursor/mcp.json" "mcpServers" "$URL_OBJ"
merge_mcp_json "$REPO_ROOT/opencode.json" "mcp" "$OPENCODE_OBJ"

log ""
log "Skills & rules:"
install_file "$KIT/claude-code/skill/SKILL.md"        "$REPO_ROOT/.claude/skills/recalium-memory/SKILL.md"
install_file "$KIT/codex/skill/SKILL.md"              "$REPO_ROOT/.codex/skills/recalium-memory/SKILL.md"
install_file "$KIT/github-copilot/skill/SKILL.md"     "$REPO_ROOT/.github/skills/recalium-memory/SKILL.md"
install_file "$KIT/cursor/rules/recalium-memory.mdc"  "$REPO_ROOT/.cursor/rules/recalium-memory.mdc"
install_file "$KIT/pi/skill/SKILL.md"                 "$REPO_ROOT/.pi/skills/recalium-memory/SKILL.md"

log ""
log "Claude Code hooks:"
append_claude_hooks

if [[ $DO_USER -eq 1 ]]; then
  log ""
  log "User-level configs (--all):"
  install_codex_user
  install_vscode_user
  merge_mcp_json "$HOME/.config/opencode/opencode.json" "mcp" "$OPENCODE_OBJ"
  install_file "$KIT/pi/skill/SKILL.md" "$HOME/.pi/agent/skills/recalium-memory/SKILL.md"
  install_hermes_user
fi

log ""
log "Done. Next steps:"
log "  1. Ensure Recalium is running (GET $(printf '%s' "$URL" | sed 's#/mcp/sse#/api/health#'))."
log "  2. Reload your editor and start the 'recalium' MCP server."
log "  3. Codex/Cursor pick up the config on next launch."
