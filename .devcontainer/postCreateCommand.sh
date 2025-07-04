#! /bin/bash
# deployment dependencies are installed as root, but current user is vscode
pip --disable-pip-version-check --no-cache-dir install -e .[dev]
# install nodeJS for AI code assistants
sudo apt-get update
sudo apt-get install -y --no-install-recommends nodejs npm
# npx @google/gemini-cli
# npx @anthropic-ai/claude-code
