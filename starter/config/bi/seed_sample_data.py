#!/usr/bin/env python3
"""
Calabi CE — Seed sample data and curate dashboards.

Run once on first start, after `superset load-examples`. It:
  1. Renames the "examples" DB to "Calabi Sample Data"
  2. Keeps 5 Superset example dashboards with real data
  3. Renames them to Calabi-branded titles
  4. Deletes the remaining unused example dashboards

Idempotent — safe to re-run; only acts when the expected source
dashboards exist.
"""
import os
import sys

from sqlalchemy import create_engine, text

# Map source dashboard title (from superset load-examples) → Calabi title
RENAME_MAP = {
    "Sales Dashboard":           "Sales Performance",
    "FCC New Coder Survey 2018": "Customer Analytics",
    "Video Game Sales":          "Marketing Attribution",
    "World Bank's Data":         "Operations Overview",
    "COVID Vaccine Dashboard":   "Data Quality Monitor",
}


def main() -> int:
    uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not uri:
        # Fallback: derive from DATABASE_* envs (matches superset_config.py)
        user = os.environ.get("DATABASE_USER", "calabi")
        pw   = os.environ.get("DATABASE_PASSWORD", "calabi_ce_2025")
        host = os.environ.get("DATABASE_HOST", "postgres")
        port = os.environ.get("DATABASE_PORT", "5432")
        db   = os.environ.get("DATABASE_DB", "calabi_bi")
        uri  = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"

    engine = create_engine(uri)
    keep_titles = set(RENAME_MAP.keys()) | set(RENAME_MAP.values())

    with engine.begin() as c:
        # 1. Rename sample database
        c.execute(
            text("UPDATE dbs SET database_name = :n, verbose_name = :n "
                 "WHERE database_name = :o"),
            {"n": "Calabi Sample Data", "o": "examples"},
        )

        # 2. Find dashboards to delete (anything not in the keep list)
        to_delete = [r[0] for r in c.execute(
            text("SELECT id FROM dashboards WHERE dashboard_title <> ALL(:k)"),
            {"k": list(keep_titles)},
        )]

        for did in to_delete:
            c.execute(text("DELETE FROM dashboard_slices WHERE dashboard_id = :i"), {"i": did})
            c.execute(text("DELETE FROM dashboard_user WHERE dashboard_id = :i"), {"i": did})
            c.execute(text("DELETE FROM dashboards WHERE id = :i"), {"i": did})

        # 3. Rename to Calabi titles (with friendly slugs)
        for old, new in RENAME_MAP.items():
            slug = new.lower().replace(" ", "-")
            c.execute(
                text("UPDATE dashboards SET dashboard_title = :t, slug = :s, "
                     "published = true WHERE dashboard_title = :o"),
                {"t": new, "s": slug, "o": old},
            )

    # Report
    with engine.connect() as c:
        titles = [r[0] for r in c.execute(
            text("SELECT dashboard_title FROM dashboards ORDER BY dashboard_title")
        )]
        charts = c.execute(text("SELECT COUNT(*) FROM slices")).scalar()
        datasets = c.execute(text("SELECT COUNT(*) FROM tables")).scalar()

    print(f"Calabi sample data seeded: {len(titles)} dashboards, "
          f"{charts} charts, {datasets} datasets")
    for t in titles:
        print(f"  - {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
