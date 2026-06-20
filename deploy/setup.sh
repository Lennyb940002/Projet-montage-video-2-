#!/usr/bin/env bash
set -euo pipefail
# Oracle Cloud Always Free / Ubuntu 22.04 — installe et lance le service 24/7.
sudo apt-get update
sudo apt-get install -y ffmpeg python3-venv git
cd /home/ubuntu
[ -d auto-montage ] || git clone <REPO_URL> auto-montage
cd auto-montage
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# secrets : créer ~/.automontage/settings.json (token upload-post, user, gemini,
# telegram_bot_token, telegram_chat_id) AVANT de démarrer le service.
mkdir -p ~/.automontage
sudo cp deploy/automontage-dist.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now automontage-dist
echo "OK — logs: journalctl -u automontage-dist -f"
