#!/usr/bin/env bash
# install.sh — paradox-jarvis-client one-line installer (Linux).
#
# The repo is public, so no token is needed:
#
#   curl -fsSL https://raw.githubusercontent.com/chinmayshastry05-cpu/paradox-jarvis-client/main/install.sh | bash
#
# What it does: clone the repo, set up uv + Python venv,
# install deps, install Ollama and pull a starter model, then launch
# the setup wizard (`jarvis setup`).
#
# Flags:
#   --no-model    Skip the Ollama starter-model pull
#   --no-wizard   Skip launching the setup wizard
#
# Environment overrides:
#   GITHUB_TOKEN       Optional: only when cloning a private fork (used once, never persisted)
#   OPENJARVIS_HOME    Install root (default: $HOME/.openjarvis)
#   OPENJARVIS_REPO_URL  git repo URL (default: this repo)
#   JARVIS_STARTER_MODEL Ollama starter model (default: qwen3:0.6b)
#
# When GITHUB_TOKEN is set it is used once for the clone (via an HTTP header,
# never in the URL, never printed, never written to disk). Re-runs skip the clone.

set -euo pipefail

NO_MODEL=0
NO_WIZARD=0
for arg in "$@"; do
    case "$arg" in
        --no-model) NO_MODEL=1 ;;
        --no-wizard) NO_WIZARD=1 ;;
        *) echo "install.sh: unknown arg: $arg" >&2; exit 2 ;;
    esac
done

OPENJARVIS_HOME="${OPENJARVIS_HOME:-$HOME/.openjarvis}"
OPENJARVIS_REPO_URL="${OPENJARVIS_REPO_URL:-https://github.com/chinmayshastry05-cpu/paradox-jarvis-client.git}"
STARTER_MODEL="${JARVIS_STARTER_MODEL:-qwen3:0.6b}"
SRC_DIR="$OPENJARVIS_HOME/src"
VENV_DIR="$SRC_DIR/.venv"
BIN_DIR="$HOME/.local/bin"

command -v git >/dev/null 2>&1 || { echo "install.sh: git is required (e.g. sudo apt install git)." >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "install.sh: curl is required (e.g. sudo apt install curl)." >&2; exit 1; }

mkdir -p "$OPENJARVIS_HOME" "$BIN_DIR"

# ---- clone (plain public clone; token header only when GITHUB_TOKEN is set) ----
if [[ -d "$SRC_DIR/.git" ]]; then
    echo "install.sh: repo already cloned at $SRC_DIR; skipping clone."
elif [[ -e "$SRC_DIR" ]]; then
    echo "install.sh: $SRC_DIR exists but is not a git checkout; remove it and re-run." >&2
    exit 1
else
    echo "install.sh: cloning $OPENJARVIS_REPO_URL into $SRC_DIR ..."
    # NOTE: -c goes BEFORE `clone`: it applies to the fetch itself.
    # `git clone -c ...` would only write the header into the new repo's
    # config (persisting the token) without authenticating the fetch.
    # GitHub's git-over-HTTPS requires Basic auth (token as password);
    # Bearer auth is rejected with "invalid credentials".
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        _basic="$(printf '%s' "x-access-token:$GITHUB_TOKEN" | base64 -w0)"
        git -c http.extraHeader="Authorization: Basic $_basic" \
            clone "$OPENJARVIS_REPO_URL" "$SRC_DIR"
        unset _basic
    else
        # Public repo: plain clone, no auth.
        git clone "$OPENJARVIS_REPO_URL" "$SRC_DIR"
    fi
fi

# ---- uv ----
if command -v uv >/dev/null 2>&1; then
    UV="uv"
    echo "install.sh: using uv from PATH ($(uv --version))."
else
    echo "install.sh: installing uv ..."
    curl -fsSL https://astral.sh/uv/install.sh | sh
    UV="$HOME/.local/bin/uv"
    "$UV" --version
fi

# ---- venv + deps (uv.lock pins every transitive dep) ----
echo "install.sh: syncing Python venv and dependencies ..."
"$UV" sync --project "$SRC_DIR"
JARVIS_BIN="$VENV_DIR/bin/jarvis"
[[ -x "$JARVIS_BIN" ]] || { echo "install.sh: jarvis entry point missing after sync." >&2; exit 1; }

# ---- jarvis shim on PATH ----
ln -sf "$JARVIS_BIN" "$BIN_DIR/jarvis"
echo "install.sh: linked $BIN_DIR/jarvis -> $JARVIS_BIN"

# ---- Ollama + starter model ----
if command -v ollama >/dev/null 2>&1; then
    echo "install.sh: ollama already installed ($(ollama --version))."
else
    echo "install.sh: installing Ollama ..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
if [[ "$NO_MODEL" -eq 0 ]]; then
    if ! ollama list >/dev/null 2>&1; then
        echo "install.sh: starting ollama serve in the background ..."
        nohup ollama serve > "$OPENJARVIS_HOME/ollama.log" 2>&1 &
        for _ in $(seq 1 30); do
            sleep 1
            ollama list >/dev/null 2>&1 && break
        done
    fi
    echo "install.sh: pulling starter model $STARTER_MODEL ..."
    # Best-effort: a registry flake must not nuke the whole install.
    # The user can retry later with: ollama pull "$STARTER_MODEL"
    if ! ollama pull "$STARTER_MODEL"; then
        echo "install.sh: WARNING: could not pull $STARTER_MODEL."
        echo "  Retry later with: ollama pull $STARTER_MODEL"
    fi
else
    echo "install.sh: --no-model set; skipping starter-model pull."
fi

# ---- setup wizard ----
if [[ "$NO_WIZARD" -eq 0 ]]; then
    echo "install.sh: launching the setup wizard ..."
    "$JARVIS_BIN" setup
else
    echo "install.sh: --no-wizard set; skipping setup wizard."
fi

cat <<EOF

Paradox Jarvis (client edition) installed.
  repo:   $SRC_DIR
  venv:   $VENV_DIR
  config: $OPENJARVIS_HOME/config.toml

Make sure $BIN_DIR is on your PATH, then run:
  jarvis setup    (re-run the wizard any time)
  jarvis doctor   (verify the setup)
EOF
