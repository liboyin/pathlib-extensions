#! /bin/bash
set -euo pipefail
# deployment dependencies are installed as root, but current user is vscode
pip --disable-pip-version-check --no-cache-dir install -e .[dev]
# use native installer of Claude Code
curl -fsSL https://claude.ai/install.sh | bash
# Install standalone Codex for direct CLI review, without prompting or launching a session.
curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh
