#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

echo "Starting SkillFlow AI backend on http://10.0.128.20:8000"
echo "API docs: http://10.0.128.20:8000/docs"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
