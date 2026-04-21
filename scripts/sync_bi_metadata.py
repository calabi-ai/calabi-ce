#!/usr/bin/env python3
"""
Calabi CE — Sync CalabiIQ (Superset) metadata into the catalogue.

Run on every fresh install AND can be re-run to pick up newly created
dashboards/charts. Idempotent: creates-or-updates, never duplicates.

Usage:
    python sync_bi_metadata.py            # one-shot sync
    python sync_bi_metadata.py --watch    # continuous (re-sync every 5 min)

Sync scope:
    1. CalabiIQ Analytics dashboard service in catalogue
    2. All published dashboards (name, title, source URL via gateway)
    3. All charts used by those dashboards, with dashboard linkage
"""
import argparse
import os
import re
import sys
import time
from typing import Any

import requests


CATALOGUE_URL = os.environ.get("CATALOGUE_URL", "http://calabi-catalogue:8585")
BI_URL        = os.environ.get("BI_URL",        "http://calabi-bi:8088")
GATEWAY_URL   = os.environ.get("CALABI_URL",    "http://localhost:8080")

CATALOGUE_USER = os.environ.get("CATALOGUE_USER", "ce-admin@calabi.dev")
CATALOGUE_PW   = os.environ.get("CATALOGUE_PASSWORD", "Q2FsYWJpQENFMjAyNSE=")
BI_USER        = os.environ.get("BI_USER",    "admin")
BI_PW          = os.environ.get("BI_PASSWORD", "admin")

SERVICE_NAME = "calabi_superset"
SERVICE_DISPLAY = "CalabiIQ Analytics"


def slugify(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text.strip().lower())
    return re.sub(r"_+", "_", s).strip("_") or "unknown"


class Catalogue:
    def __init__(self, base: str, email: str, password_b64: str):
        self.base = base.rstrip("/")
        self.s = requests.Session()
        r = self.s.post(f"{self.base}/api/v1/users/login", json={
            "email": email, "password": password_b64,
        }, timeout=30)
        if r.status_code != 200:
            # Fallback to default OM admin during first-run before ce-admin exists
            r = self.s.post(f"{self.base}/api/v1/users/login", json={
                "email": "admin@open-metadata.org", "password": "YWRtaW4=",
            }, timeout=30)
        r.raise_for_status()
        self.token = r.json()["accessToken"]
        self.s.headers.update({"Authorization": f"Bearer {self.token}"})

    def ensure_service(self) -> None:
        url = f"{self.base}/api/v1/services/dashboardServices/name/{SERVICE_NAME}"
        r = self.s.get(url, timeout=30)
        if r.status_code == 200:
            return  # exists
        r = self.s.post(f"{self.base}/api/v1/services/dashboardServices", json={
            "name": SERVICE_NAME,
            "displayName": SERVICE_DISPLAY,
            "serviceType": "Superset",
            "description": "CalabiIQ BI dashboards and analytics. Data assets ingested from Superset.",
            "connection": {"config": {
                "type": "Superset", "hostPort": BI_URL,
                "connection": {"username": BI_USER, "password": BI_PW, "provider": "db"},
            }},
        }, timeout=30)
        if not r.ok:
            print(f"  WARN: could not create dashboard service: {r.status_code} {r.text[:200]}", file=sys.stderr)

    def upsert_chart(self, chart: dict) -> str | None:
        name = slugify(chart["slice_name"] or f"chart_{chart['id']}")
        display = chart["slice_name"] or f"Chart {chart['id']}"
        viz = chart.get("viz_type", "Other")

        # Check if exists
        fqn = f"{SERVICE_NAME}.{name}"
        r = self.s.get(f"{self.base}/api/v1/charts/name/{fqn}", timeout=30)
        if r.status_code == 200:
            return r.json()["fullyQualifiedName"]

        r = self.s.post(f"{self.base}/api/v1/charts", json={
            "name": name,
            "displayName": display,
            "description": f"CalabiIQ chart: {display} (viz: {viz})",
            "chartType": "Other",
            "service": SERVICE_NAME,
            "sourceUrl": f"{GATEWAY_URL}/superset/explore/?slice_id={chart['id']}",
        }, timeout=30)
        if r.status_code == 201:
            return r.json()["fullyQualifiedName"]
        # Common noise: 409 already exists — treat as OK
        return fqn if r.status_code == 409 else None

    def upsert_dashboard(self, dash: dict, chart_fqns: list[str]) -> None:
        name = slugify(dash["dashboard_title"] or f"dash_{dash['id']}")
        display = dash["dashboard_title"] or f"Dashboard {dash['id']}"
        url = f"{GATEWAY_URL}/superset/dashboard/{dash['id']}/"

        payload = {
            "name": name,
            "displayName": display,
            "description": f"CalabiIQ dashboard: {display}",
            "sourceUrl": url,
            "service": SERVICE_NAME,
            "charts": chart_fqns,
        }

        fqn = f"{SERVICE_NAME}.{name}"
        r = self.s.get(f"{self.base}/api/v1/dashboards/name/{fqn}?fields=charts", timeout=30)
        if r.status_code == 200:
            # Exists — PATCH it
            existing = r.json()
            patch_ops = []
            if existing.get("displayName") != display:
                patch_ops.append({"op": "replace", "path": "/displayName", "value": display})
            if existing.get("sourceUrl") != url:
                patch_ops.append({"op": "replace", "path": "/sourceUrl", "value": url})
            if patch_ops:
                pr = self.s.patch(f"{self.base}/api/v1/dashboards/{existing['id']}",
                                  json=patch_ops,
                                  headers={"Content-Type": "application/json-patch+json"},
                                  timeout=30)
                if not pr.ok:
                    print(f"  WARN: patch {name} failed: {pr.status_code}", file=sys.stderr)
            # Relink charts via PUT (full replace)
            if chart_fqns:
                self.s.put(f"{self.base}/api/v1/dashboards", json=payload, timeout=30)
            return

        r = self.s.post(f"{self.base}/api/v1/dashboards", json=payload, timeout=30)
        if not r.ok:
            print(f"  WARN: create {name} failed: {r.status_code} {r.text[:200]}", file=sys.stderr)

    def list_existing_dashboards(self) -> set[str]:
        r = self.s.get(f"{self.base}/api/v1/dashboards?service={SERVICE_NAME}&limit=500",
                       timeout=30)
        if not r.ok: return set()
        return {d["name"] for d in r.json().get("data", [])}

    def delete_dashboard(self, name: str) -> None:
        fqn = f"{SERVICE_NAME}.{name}"
        r = self.s.get(f"{self.base}/api/v1/dashboards/name/{fqn}", timeout=30)
        if r.status_code != 200: return
        did = r.json()["id"]
        self.s.delete(f"{self.base}/api/v1/dashboards/{did}?hardDelete=true&recursive=true",
                      timeout=30)


class Superset:
    def __init__(self, base: str, user: str, pw: str):
        self.base = base.rstrip("/")
        self.s = requests.Session()
        r = self.s.post(f"{self.base}/api/v1/security/login", json={
            "username": user, "password": pw, "provider": "db", "refresh": True,
        }, timeout=30)
        r.raise_for_status()
        self.token = r.json()["access_token"]
        self.s.headers.update({"Authorization": f"Bearer {self.token}"})

    def dashboards(self) -> list[dict]:
        r = self.s.get(f"{self.base}/api/v1/dashboard/?q=(page_size:200)", timeout=30)
        r.raise_for_status()
        return [d for d in r.json().get("result", []) if d.get("published")]

    def charts_for(self, dashboard_id: int) -> list[dict]:
        r = self.s.get(f"{self.base}/api/v1/dashboard/{dashboard_id}/charts", timeout=30)
        if not r.ok: return []
        return r.json().get("result", [])


def sync_once() -> tuple[int, int]:
    cat = Catalogue(CATALOGUE_URL, CATALOGUE_USER, CATALOGUE_PW)
    ss  = Superset(BI_URL, BI_USER, BI_PW)

    cat.ensure_service()
    live_dashboards = ss.dashboards()
    live_names = {slugify(d["dashboard_title"] or f"dash_{d['id']}") for d in live_dashboards}

    dash_count = 0
    chart_count = 0

    for dash in live_dashboards:
        charts = ss.charts_for(dash["id"])
        chart_fqns = []
        for c in charts:
            # charts_for returns structured differently — normalize
            cid = c.get("id") or c.get("slice_id")
            if not cid: continue
            fqn = cat.upsert_chart({
                "id": cid,
                "slice_name": c.get("slice_name") or c.get("form_data", {}).get("slice_name"),
                "viz_type": c.get("viz_type") or c.get("form_data", {}).get("viz_type"),
            })
            if fqn:
                chart_fqns.append(fqn)
                chart_count += 1
        cat.upsert_dashboard(dash, chart_fqns)
        dash_count += 1

    # Prune dashboards that no longer exist in Superset
    existing = cat.list_existing_dashboards()
    stale = existing - live_names
    for name in stale:
        cat.delete_dashboard(name)
        print(f"  Removed stale dashboard: {name}")

    return dash_count, chart_count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true",
                    help="Run continuously, re-syncing every --interval seconds")
    ap.add_argument("--interval", type=int, default=300,
                    help="Seconds between sync runs in --watch mode (default: 300)")
    args = ap.parse_args()

    while True:
        try:
            dc, cc = sync_once()
            print(f"Synced: {dc} dashboards, {cc} charts (CalabiIQ → catalogue)")
        except Exception as e:
            print(f"Sync error: {e}", file=sys.stderr)
            if not args.watch:
                return 1
        if not args.watch:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
