#!/usr/bin/env bash
# One-command update for PythonAnywhere.   Usage:  deploy      (after running the one-time alias setup in README)
set -euo pipefail

USER_NAME="${USER:-muhammadnouman}"
APP_DIR="$HOME/muhammad-nouman-portfolio"
VENV="$HOME/.virtualenvs/nouman"
WSGI="/var/www/${USER_NAME}_pythonanywhere_com_wsgi.py"

cd "$APP_DIR"
source "$VENV/bin/activate"

echo "==> Pulling latest code"
git pull

echo "==> Installing requirements"
pip install -q -r requirements.txt

echo "==> Applying migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Reloading the web app"
touch "$WSGI"

echo "Done. Live at https://${USER_NAME}.pythonanywhere.com"
