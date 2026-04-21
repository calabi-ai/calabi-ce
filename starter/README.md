# Calabi Starter Edition

Calabi Starter = Community Edition + **Data Engineering module**

## What you get beyond CE

The Starter tier adds 5 additional services on top of Community Edition, all wired through the same `localhost:8081` gateway:

| Service | Role | Port (direct) |
|---|---|---|
| **Airflow** | Orchestration (DAGs, schedulers) | :8082 |
| **Airbyte** | Ingestion engine (sources + destinations) | :8086 |
| **Jupyter Notebooks** | Interactive transformation / exploration | :8888 |
| **VS Code IDE** | In-browser authoring | :8084 |
| **Calabi Connect** | Branded Airbyte UI (coming soon) | — |

All of these light up **Data Engineering** and **Data Quality** modules in the Calabi Platform UI (both locked in CE, unlocked in Starter).

## Quick start

```bash
cp .env.example .env          # optional — defaults work out of the box
docker compose up -d
open http://localhost:8081
```

First-time boot: ~20–30 min (catalogue migrations + BI sample data + Airflow init).
Subsequent starts: ~1 min.

## Access

| URL | Purpose |
|---|---|
| http://localhost:8081 | Calabi Platform (single sign-on for all modules) |
| http://localhost:8081/bi-analytics | BI dashboards (5 sample + charts) |
| http://localhost:8081/data-engineering | Data Engineering module |
| http://localhost:8081/explore | Unified data asset catalogue |
| http://localhost:8082 | Airflow direct (admin / admin) |
| http://localhost:8888 | Jupyter Lab (token: `calabi-notebooks-2025`) |
| http://localhost:8084 | VS Code (password: `calabi-ide-2025`) |

**Login:** `ce-admin@calabi.dev` / `Calabi@CE2025!`

## How it extends CE

1. Starts with the **exact CE images** (`calabi-bi:1.0.2`, `calabi-license-proxy:1.0.1`) and the same Postgres/OpenSearch backends.
2. Swaps the catalogue image to `calabi-catalogue-starter:1.0.0` — identical to CE catalogue 1.0.5 except the embedded gating.js unlocks Data Engineering + Data Quality.
3. Adds 5 Data Engineering containers (Airflow web/scheduler, Airbyte server/db, Jupyter, IDE).
4. On first run, `starter-setup` registers Airflow DAGs as pipeline entities in the catalogue (`sync_de_metadata.py`).

No UI code changes — the Calabi Platform UI's native Data Engineering page dynamically queries these backends through the gateway.

## Resource requirements

| Tier | CPU | RAM | Disk |
|---|---|---|---|
| CE | 4 | 8 GB | 10 GB |
| **Starter** | 6 | 12 GB | 20 GB |

## Tear down

```bash
docker compose down          # stop, keep volumes
docker compose down -v       # stop + delete all data (fresh install next time)
```

## Upgrading from CE

If you have a running CE install and want to switch to Starter:

```bash
cd ../                        # CE directory
docker compose down           # keep volumes
cd starter/
docker compose up -d          # new stack, same volumes via shared names
```

CE and Starter use different compose project names + volume/container name prefixes, so they don't collide.
