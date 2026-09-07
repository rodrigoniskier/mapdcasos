#!/bin/bash
set -e

cd /home/mapdcasos/mapdcasos

PYTHON="/home/mapdcasos/.virtualenvs/mapdcasos/bin/python"

$PYTHON manage.py export_analytics

git add analytics/summary.json

if git diff --cached --quiet; then
    echo "Sem alterações nas métricas."
    exit 0
fi

git commit -m "Update MAPD Casos analytics"
git push origin main

echo "Analytics atualizados no GitHub."
