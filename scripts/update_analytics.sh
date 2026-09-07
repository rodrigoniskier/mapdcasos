#!/bin/bash
set -e

cd /home/mapdcasos/mapdcasos

PYTHON="/home/mapdcasos/.virtualenvs/mapdcasos/bin/python"

git pull --ff-only origin main

$PYTHON manage.py export_analytics

CHANGED=$($PYTHON - <<'PY'
import json
import subprocess
from pathlib import Path

current = json.loads(
    Path("analytics/summary.json").read_text(encoding="utf-8")
)

try:
    previous = json.loads(
        subprocess.check_output(
            ["git", "show", "HEAD:analytics/summary.json"],
            text=True
        )
    )
except Exception:
    print("1")
    raise SystemExit

current.pop("generated_at", None)
previous.pop("generated_at", None)

print("1" if current != previous else "0")
PY
)

if [ "$CHANGED" = "0" ]; then
    git restore analytics/summary.json
    echo "Sem alterações nas métricas."
    exit 0
fi

git add analytics/summary.json
git commit -m "Update MAPD Casos analytics"
git push origin main

echo "Analytics atualizados no GitHub."
