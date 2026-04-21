#!/usr/bin/env python3
"""
Calabi Starter — Sync Data Engineering metadata into the catalogue.

Registers pipeline service + DAGs from Airflow, and connection metadata
from Airbyte, so the Calabi UI's /explore and /data-engineering pages
see them as live assets.

Usage:
    python sync_de_metadata.py            # one-shot sync
    python sync_de_metadata.py --watch    # continuous re-sync every 5 min

Pipelines registered as OM "PipelineService" (Airflow) + individual Pipeline
entities (DAGs). Airbyte connections are future work (will register when
Calabi Connect UI is live).
"""
import argparse
import os
import re
import sys
import time
from base64 import b64encode

import requests


CATALOGUE_URL    = os.environ.get("CATALOGUE_URL",    "http://calabi-catalogue:8585")
AIRFLOW_URL      = os.environ.get("AIRFLOW_URL",      "http://airflow-webserver:8080")
GATEWAY_URL      = os.environ.get("CALABI_URL",       "http://localhost:8081")

CATALOGUE_USER   = os.environ.get("CATALOGUE_USER",   "ce-admin@calabi.dev")
CATALOGUE_PW     = os.environ.get("CATALOGUE_PASSWORD", "Q2FsYWJpQENFMjAyNSE=")
AIRFLOW_USER     = os.environ.get("AIRFLOW_USER",     "admin")
AIRFLOW_PW       = os.environ.get("AIRFLOW_PASSWORD", "admin")

PIPELINE_SERVICE_NAME = "calabi_airflow"
PIPELINE_SERVICE_DISPLAY = "Calabi Airflow"


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
            r = self.s.post(f"{self.base}/api/v1/users/login", json={
                "email": "admin@open-metadata.org", "password": "YWRtaW4=",
            }, timeout=30)
        r.raise_for_status()
        self.s.headers.update({"Authorization": f"Bearer {r.json()['accessToken']}"})

    def ensure_pipeline_service(self) -> None:
        url = f"{self.base}/api/v1/services/pipelineServices/name/{PIPELINE_SERVICE_NAME}"
        r = self.s.get(url, timeout=30)
        if r.status_code == 200:
            return
        r = self.s.post(f"{self.base}/api/v1/services/pipelineServices", json={
            "name": PIPELINE_SERVICE_NAME,
            "displayName": PIPELINE_SERVICE_DISPLAY,
            "serviceType": "Airflow",
            "description": "Calabi orchestration engine. DAGs and tasks ingested from Airflow.",
            "connection": {"config": {
                "type": "Airflow",
                "hostPort": AIRFLOW_URL,
                "connection": {
                    "type": "Backend",
                },
            }},
        }, timeout=30)
        if not r.ok:
            print(f"  WARN: could not create pipeline service: {r.status_code} {r.text[:200]}",
                  file=sys.stderr)

    def upsert_pipeline(self, dag: dict) -> None:
        name = slugify(dag["dag_id"])
        display = dag.get("dag_display_name") or dag["dag_id"]
        desc = dag.get("description") or f"Airflow DAG: {display}"
        url = f"{GATEWAY_URL}/airflow/dags/{dag['dag_id']}/grid"

        payload = {
            "name": name,
            "displayName": display,
            "description": desc,
            "sourceUrl": url,
            "service": PIPELINE_SERVICE_NAME,
            "tasks": [
                {"name": slugify(f"task_{i}"), "displayName": f"Task {i+1}"}
                for i in range(1)  # tasks enumeration is future work
            ],
        }

        fqn = f"{PIPELINE_SERVICE_NAME}.{name}"
        r = self.s.get(f"{self.base}/api/v1/pipelines/name/{fqn}", timeout=30)
        if r.status_code == 200:
            existing = r.json()
            ops = []
            if existing.get("displayName") != display:
                ops.append({"op": "replace", "path": "/displayName", "value": display})
            if existing.get("description") != desc:
                ops.append({"op": "replace", "path": "/description", "value": desc})
            if existing.get("sourceUrl") != url:
                ops.append({"op": "replace", "path": "/sourceUrl", "value": url})
            if ops:
                self.s.patch(
                    f"{self.base}/api/v1/pipelines/{existing['id']}",
                    json=ops,
                    headers={"Content-Type": "application/json-patch+json"},
                    timeout=30,
                )
            return

        r = self.s.post(f"{self.base}/api/v1/pipelines", json=payload, timeout=30)
        if not r.ok:
            print(f"  WARN: create {name} failed: {r.status_code} {r.text[:200]}", file=sys.stderr)

    def list_existing_pipelines(self) -> set[str]:
        r = self.s.get(
            f"{self.base}/api/v1/pipelines?service={PIPELINE_SERVICE_NAME}&limit=500",
            timeout=30,
        )
        if not r.ok: return set()
        return {d["name"] for d in r.json().get("data", [])}

    def delete_pipeline(self, name: str) -> None:
        fqn = f"{PIPELINE_SERVICE_NAME}.{name}"
        r = self.s.get(f"{self.base}/api/v1/pipelines/name/{fqn}", timeout=30)
        if r.status_code != 200: return
        pid = r.json()["id"]
        self.s.delete(
            f"{self.base}/api/v1/pipelines/{pid}?hardDelete=true&recursive=true",
            timeout=30,
        )


class Airflow:
    def __init__(self, base: str, user: str, pw: str):
        self.base = base.rstrip("/")
        self.s = requests.Session()
        creds = b64encode(f"{user}:{pw}".encode()).decode()
        self.s.headers.update({"Authorization": f"Basic {creds}"})

    def dags(self) -> list[dict]:
        out = []
        offset = 0
        while True:
            r = self.s.get(f"{self.base}/api/v1/dags",
                           params={"limit": 100, "offset": offset},
                           timeout=30)
            if not r.ok: break
            data = r.json()
            dags = data.get("dags", [])
            out.extend(dags)
            if len(dags) < 100: break
            offset += 100
        return out


def wait_for_services() -> bool:
    """Wait up to 5 minutes for Airflow to be reachable."""
    for _ in range(60):
        try:
            r = requests.get(f"{AIRFLOW_URL}/health", timeout=5)
            if r.ok:
                return True
        except Exception:
            pass
        time.sleep(5)
    return False


def sync_once() -> int:
    if not wait_for_services():
        print("  WARN: Airflow not reachable — skipping DE sync", file=sys.stderr)
        return 0

    cat = Catalogue(CATALOGUE_URL, CATALOGUE_USER, CATALOGUE_PW)
    af  = Airflow(AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PW)

    cat.ensure_pipeline_service()
    live_dags = af.dags()
    live_names = {slugify(d["dag_id"]) for d in live_dags}

    for dag in live_dags:
        cat.upsert_pipeline(dag)

    existing = cat.list_existing_pipelines()
    stale = existing - live_names
    for name in stale:
        cat.delete_pipeline(name)

    return len(live_dags)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=int, default=300)
    args = ap.parse_args()

    while True:
        try:
            n = sync_once()
            print(f"Synced: {n} Airflow DAGs → catalogue")
        except Exception as e:
            print(f"DE sync error: {e}", file=sys.stderr)
            if not args.watch:
                return 1
        if not args.watch:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
