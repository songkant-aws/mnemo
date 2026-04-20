#!/bin/zsh
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
exec python3 "$DIR/scripts/install_codex_plugin.py"
