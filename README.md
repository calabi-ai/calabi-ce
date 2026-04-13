<p align="center">
  <img src="assets/calabi-logo.png" alt="Calabi" width="80" />
</p>

<h1 align="center">Calabi</h1>

<p align="center">
  The unified data intelligence platform — catalog, analytics, quality, governance, and AI in one install.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-ELv2-blue.svg" alt="License" /></a>
  <a href="https://github.com/calabi-ai/calabi-ce/releases"><img src="https://img.shields.io/badge/version-1.0.0-purple.svg" alt="Version" /></a>
  <a href="https://calabi.bifrost.examroom.ai/docs/"><img src="https://img.shields.io/badge/docs-calabi.dev-green.svg" alt="Documentation" /></a>
</p>

---

## What is Calabi?

Calabi replaces multiple standalone data tools with a single, unified platform. Instead of managing separate products for data cataloging, BI dashboards, data quality, and governance, Calabi brings them together under one interface.

**Community Edition includes:**

| Module | Description |
|--------|-------------|
| **Data Catalog** | Metadata discovery, table and column-level documentation, search across all data assets |
| **CalabiIQ Analytics** | Interactive dashboards, SQL workspace, chart builder (powered by Superset) |
| **Data Governance** | Classification, tagging, glossary management, lineage tracking |
| **Data Exploration** | Unified search across databases, schemas, tables, dashboards, and charts |

---

## Quick Start

**Requirements:** Docker 24+, Docker Compose v2, 4 CPU, 8 GB RAM

```bash
git clone https://github.com/calabi-ai/calabi-ce.git
cd calabi-ce
cp .env.example .env
docker compose up -d
```

Wait 2-3 minutes for all services to initialize, then open:

| Service | URL |
|---------|-----|
| Calabi Platform | [http://localhost:8080](http://localhost:8080) |
| CalabiIQ BI (direct) | [http://localhost:8088](http://localhost:8088) |

**Login:** `ce-admin@calabi.dev` / `Calabi@CE2025!`

### Verify Installation

```bash
# Check all services are healthy
docker compose ps

# View logs
docker compose logs -f calabi-catalogue
```

---

## Architecture

```
                         +------------------+
                         |   Load Balancer  |
                         |   (localhost)    |
                         +--------+---------+
                                  |
                         +--------+---------+
                         | calabi-gateway   |
                         |    nginx :8080   |
                         +--------+---------+
                                  |
              +-------------------+-------------------+
              |                   |                   |
    +---------+--------+ +-------+-------+ +---------+--------+
    | calabi-catalogue | | calabi-bi     | | calabi-license   |
    | Platform UI/API  | | CalabiIQ BI   | | -proxy           |
    | :8585            | | Superset :8088| | CE limits :8090  |
    +--------+---------+ +-------+-------+ +------------------+
              |                   |
              +-------------------+
                        |
              +---------+---------+
              |    PostgreSQL     |
              |    + OpenSearch   |
              +-------------------+
```

**7 containers** | ~4 GB RAM | ~2 GB disk

---

## Configuration

All configuration is managed through environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `CALABI_PORT` | `8080` | Gateway port (main access point) |
| `POSTGRES_USER` | `calabi` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `calabi_ce_2025` | PostgreSQL password |
| `SUPERSET_SECRET_KEY` | (auto) | Superset session encryption key |
| `SUPERSET_LOAD_EXAMPLES` | `no` | Load sample Superset dashboards |
| `CE_MAX_CATALOGUE_USERS` | `5` | Maximum users (CE limit) |
| `CE_MAX_CATALOGUE_ASSETS` | `500` | Maximum data assets (CE limit) |

For production deployments, change all default passwords.

---

## CE Limits

Community Edition is free with the following limits:

| Resource | Limit |
|----------|-------|
| Users | 5 |
| Data assets | 500 |
| Authentication | Basic (username/password) |
| Support | GitHub Issues |

Need more? See [Upgrade Path](#upgrade-path) below.

---

## Upgrade Path

Calabi is available in four tiers. All tiers use the same images — a license key unlocks additional modules.

| | CE (Free) | Starter | Professional | Enterprise |
|---|---|---|---|---|
| Data Catalog | Yes | Yes | Yes | Yes |
| BI Analytics | Yes | Yes | Yes | Yes |
| Data Engineering | - | Yes | Yes | Yes |
| Data Quality | - | Yes | Yes | Yes |
| Data Science and AI | - | - | Yes | Yes |
| Cloud Operations | - | - | - | Yes |
| Users | 5 | 25 | 100 | Unlimited |
| Data assets | 500 | 10,000 | 100,000 | Unlimited |

Upgrading from CE requires no data migration — add a license key and restart.

Visit [calabi.bifrost.examroom.ai/docs/getting-started/tiers](https://calabi.bifrost.examroom.ai/docs/getting-started/tiers) for details.

---

## Common Operations

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Reset all data (destructive)
docker compose down -v

# View service status
docker compose ps

# View logs for a specific service
docker compose logs -f calabi-catalogue

# Restart a single service
docker compose restart calabi-gateway

# Pull latest images
docker compose pull
```

---

## Documentation

Full documentation is available at [calabi.bifrost.examroom.ai/docs](https://calabi.bifrost.examroom.ai/docs/).

- [Getting Started](https://calabi.bifrost.examroom.ai/docs/getting-started/quickstart)
- [Deployment Architecture](https://calabi.bifrost.examroom.ai/docs/platform/deployment)
- [Tier Comparison](https://calabi.bifrost.examroom.ai/docs/getting-started/tiers)

---

## Community

- [GitHub Issues](https://github.com/calabi-ai/calabi-ce/issues) -- Bug reports and feature requests
- [Documentation](https://calabi.bifrost.examroom.ai/docs/) -- Guides and reference

---

## Security

To report a security vulnerability, please email security@calabi.dev. See [SECURITY.md](SECURITY.md) for details.

---

## License

Calabi Community Edition is licensed under the [Elastic License 2.0 (ELv2)](LICENSE).

You are free to use, modify, and distribute Calabi for any purpose except offering it as a managed service to third parties. The underlying open-source components retain their original licenses.

---

<p align="center">
  Built by <a href="https://calabi.bifrost.examroom.ai/docs/">Calabi</a>
</p>
