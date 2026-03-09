#!/bin/bash
set -euo pipefail

# PRDforge — one-command install
# Usage:
#   ./install.sh                  # Interactive (auto-detect client)
#   ./install.sh --claude-code    # Claude Code (HTTP transport)
#   ./install.sh --claude-desktop # Claude Desktop (stdio transport)
#   ./install.sh --uninstall      # Remove MCP config + optionally stop services

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}▸${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}!${NC} $1"; }
err()   { echo -e "${RED}✗${NC} $1" >&2; }
die()   { err "$1"; exit 1; }

CLAUDE_CODE_CONFIG="$HOME/.claude/mcp.json"
CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
MCP_SERVER_NAME="prd-forge"
GHCR_PREFIX="ghcr.io/tommass/prdforge"

# ─── Argument parsing ────────────────────────────────────────────────
MODE=""
FORCE=false
BUILD_LOCAL=false
for arg in "$@"; do
  case "$arg" in
    --claude-code)    MODE="code" ;;
    --claude-desktop) MODE="desktop" ;;
    --uninstall)      MODE="uninstall" ;;
    --force)          FORCE=true ;;
    --build)          BUILD_LOCAL=true ;;
    -h|--help)
      echo "Usage: ./install.sh [--claude-code|--claude-desktop|--uninstall] [--force] [--build]"
      echo ""
      echo "  --claude-code     Configure for Claude Code (HTTP transport)"
      echo "  --claude-desktop  Configure for Claude Desktop (stdio transport)"
      echo "  --uninstall       Remove MCP config + optionally stop services"
      echo "  --force           Overwrite existing config without asking"
      echo "  --build           Build images locally instead of pulling from ghcr.io"
      exit 0 ;;
    *) die "Unknown option: $arg" ;;
  esac
done

# ─── JSON merge helper (uses python3, no jq dependency) ──────────────
json_set_mcp() {
  local config_file="$1"
  local entry_json="$2"
  python3 -c "
import json, sys, os

path = sys.argv[1]
entry = json.loads(sys.argv[2])
data = {}
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
data.setdefault('mcpServers', {}).update(entry)
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
" "$config_file" "$entry_json"
}

json_remove_mcp() {
  local config_file="$1"
  python3 -c "
import json, sys, os

path = sys.argv[1]
key = sys.argv[2]
if not os.path.exists(path):
    sys.exit(0)
with open(path) as f:
    data = json.load(f)
servers = data.get('mcpServers', {})
if key in servers:
    del servers[key]
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    print(f'Removed {key}')
else:
    print(f'{key} not found in config')
" "$config_file" "$MCP_SERVER_NAME"
}

# ─── Uninstall ────────────────────────────────────────────────────────
if [ "$MODE" = "uninstall" ]; then
  info "Removing $MCP_SERVER_NAME from MCP configs..."
  for cfg in "$CLAUDE_CODE_CONFIG" "$CLAUDE_DESKTOP_CONFIG"; do
    if [ -f "$cfg" ]; then
      result=$(json_remove_mcp "$cfg")
      ok "$result ($cfg)"
    fi
  done

  echo ""
  read -rp "Also stop Docker services and remove data? (y/N) " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    info "Stopping services..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" down -v
    ok "Services stopped and volumes removed"
  fi
  echo ""
  ok "PRDforge uninstalled"
  exit 0
fi

# ─── Prerequisites ───────────────────────────────────────────────────
info "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || die "docker not found. Install Docker Desktop: https://docs.docker.com/desktop/"
docker info >/dev/null 2>&1 || die "Docker daemon not running. Start Docker Desktop first."
command -v python3 >/dev/null 2>&1 || die "python3 not found"

ok "Prerequisites OK"

# ─── Auto-detect client if not specified ─────────────────────────────
if [ -z "$MODE" ]; then
  echo ""
  info "Select Claude client to configure:"
  echo "  1) Claude Code  (HTTP transport — recommended)"
  echo "  2) Claude Desktop (stdio transport)"
  echo ""
  read -rp "Choice [1]: " choice
  case "${choice:-1}" in
    1) MODE="code" ;;
    2) MODE="desktop" ;;
    *) die "Invalid choice" ;;
  esac
fi

# ─── Check for existing config ───────────────────────────────────────
if [ "$MODE" = "code" ]; then
  CONFIG_FILE="$CLAUDE_CODE_CONFIG"
elif [ "$MODE" = "desktop" ]; then
  CONFIG_FILE="$CLAUDE_DESKTOP_CONFIG"
fi

if [ -f "$CONFIG_FILE" ] && [ "$FORCE" = false ]; then
  if python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
sys.exit(0 if '$MCP_SERVER_NAME' in data.get('mcpServers', {}) else 1)
" "$CONFIG_FILE" 2>/dev/null; then
    warn "$MCP_SERVER_NAME already configured in $CONFIG_FILE"
    read -rp "Overwrite? (y/N) " answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
      info "Skipping config. Use --force to overwrite."
    fi
  fi
fi

# ─── Start Docker services ──────────────────────────────────────────
echo ""

COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

if [ "$BUILD_LOCAL" = true ]; then
  info "Building and starting Docker services locally..."
  docker compose -f "$COMPOSE_FILE" up -d --build 2>&1 | tail -5
else
  # Try pre-built images from ghcr.io, fall back to local build
  PROD_COMPOSE="$SCRIPT_DIR/docker-compose.prod.yml"
  if docker pull "$GHCR_PREFIX-mcp-server:latest" >/dev/null 2>&1 && \
     docker pull "$GHCR_PREFIX-ui:latest" >/dev/null 2>&1; then
    ok "Pulled pre-built images from ghcr.io"
    COMPOSE_FILE="$PROD_COMPOSE"
    info "Starting Docker services (pre-built)..."
    docker compose -f "$COMPOSE_FILE" up -d 2>&1 | tail -5
  else
    warn "Pre-built images not available, building locally..."
    docker compose -f "$COMPOSE_FILE" up -d --build 2>&1 | tail -5
  fi
fi

info "Waiting for services to be healthy..."
attempts=0
max_attempts=30
while [ $attempts -lt $max_attempts ]; do
  if docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null | python3 -c "
import sys, json
lines = sys.stdin.read().strip().split('\n')
services = [json.loads(l) for l in lines if l.strip()]
healthy = all(s.get('Health','') == 'healthy' or s.get('State','') == 'running' for s in services)
sys.exit(0 if healthy and len(services) >= 3 else 1)
" 2>/dev/null; then
    break
  fi
  sleep 2
  attempts=$((attempts + 1))
  printf "."
done
echo ""

if [ $attempts -ge $max_attempts ]; then
  warn "Services took too long to start. Check: docker compose logs"
else
  ok "Docker services running"
fi

# ─── Configure MCP ──────────────────────────────────────────────────
echo ""
if [ "$MODE" = "code" ]; then
  info "Configuring Claude Code ($CONFIG_FILE)..."

  MCP_ENTRY="{\"$MCP_SERVER_NAME\": {\"type\": \"http\", \"url\": \"http://localhost:8080/mcp/\"}}"
  json_set_mcp "$CONFIG_FILE" "$MCP_ENTRY"
  ok "Claude Code MCP config written"

elif [ "$MODE" = "desktop" ]; then
  info "Configuring Claude Desktop ($CONFIG_FILE)..."

  # Create venv for stdio transport
  VENV_DIR="$SCRIPT_DIR/mcp_server/.venv"
  if [ ! -d "$VENV_DIR" ]; then
    info "Creating Python venv..."
    python3 -m venv "$VENV_DIR"
  fi
  info "Installing MCP server dependencies..."
  "$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/mcp_server/requirements.txt"
  ok "Python venv ready"

  PYTHON_PATH="$VENV_DIR/bin/python"
  SERVER_PATH="$SCRIPT_DIR/mcp_server/server.py"

  MCP_ENTRY="{\"$MCP_SERVER_NAME\": {\"command\": \"$PYTHON_PATH\", \"args\": [\"$SERVER_PATH\"], \"env\": {\"DATABASE_URL\": \"postgresql://prdforge:prdforge@localhost:5432/prdforge\"}}}"
  json_set_mcp "$CONFIG_FILE" "$MCP_ENTRY"
  ok "Claude Desktop MCP config written"
fi

# ─── Validate ────────────────────────────────────────────────────────
echo ""
info "Validating..."

if curl -sf http://localhost:8080/mcp/ -o /dev/null 2>/dev/null; then
  ok "MCP server responding (http://localhost:8080/mcp/)"
else
  warn "MCP server not responding yet — may still be starting"
fi

if curl -sf http://localhost:8088/health -o /dev/null 2>/dev/null; then
  ok "Web UI responding (http://localhost:8088)"
else
  warn "Web UI not responding yet — may still be starting"
fi

# ─── Done ────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}PRDforge installed successfully!${NC}"
echo ""
echo "  Web UI:     http://localhost:8088"
echo "  MCP Server: http://localhost:8080/mcp/"
echo ""
if [ "$MODE" = "code" ]; then
  echo "  → Restart Claude Code to connect"
elif [ "$MODE" = "desktop" ]; then
  echo "  → Restart Claude Desktop (Cmd+Q, reopen)"
fi
echo ""
