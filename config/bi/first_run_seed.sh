#!/bin/bash
# =============================================================================
# Calabi CE — First-run seed for CalabiIQ BI
# =============================================================================
# Runs on every calabi-bi start. Only seeds sample data when there are zero
# dashboards (i.e. fresh volume). Safe to re-run: does nothing if data exists.
# =============================================================================
set -e

DASH_COUNT=$(
  python -c "
import sys
try:
    from superset import create_app
    app = create_app()
    with app.app_context():
        from superset import db
        from superset.models.dashboard import Dashboard
        print(db.session.query(Dashboard).count())
except Exception as e:
    print('0', file=sys.stderr)
    print('0')
" 2>/dev/null | tail -n 1
)

if [ "${DASH_COUNT:-0}" != "0" ]; then
  echo "CalabiIQ: $DASH_COUNT dashboards already present — skipping seed."
  exit 0
fi

echo "CalabiIQ: first run — loading sample data (offline, ~1–2 min)..."
superset load-examples 2>&1 | tail -3

echo "CalabiIQ: curating dashboards to Calabi-branded set..."
python /app/pythonpath/seed_sample_data.py

echo "CalabiIQ: sample data ready."
