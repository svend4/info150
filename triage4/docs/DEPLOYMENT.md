# triage4 — Deployment guide

Phase 13 preparation. This guide covers how to run triage4 in
realistic deployment environments: a Docker container, a
systemd-managed companion-computer install, and a denied-comms edge
profile. **No customer is targeted yet** — the patterns here are
written to make deployment a one-day task when one appears, not to
ship a specific production instance.

**Safety reminder:** triage4 is decision-support research code. None
of these profiles imply clinical use. See `docs/REGULATORY.md` and
`docs/SAFETY_CASE.md` for the framing.

## 0. Footprint

Base install (no SDKs):

| Component | Size | Notes |
|---|---|---|
| Python runtime | ~40 MB | `python:3.12-slim` |
| numpy + scipy | ~80 MB | wheel |
| fastapi + uvicorn | ~15 MB | wheel |
| triage4 + deps | ~10 MB | wheel |
| **Total image** | **< 200 MB** | verified via `docker image ls` |

Memory budget at rest: ~80 MB resident. One worker handles the
reference 8-casualty benchmark in ~1 second.

## 1. Deployment profiles

### 1.1 Container (Docker / Podman)

`Dockerfile` builds a single-stage slim image with an unprivileged
user (`triage`), a `HEALTHCHECK`, and no external SDKs.

```bash
docker build -t triage4:0.1.0 .
docker run --rm -p 8000:8000 triage4:0.1.0
curl http://localhost:8000/health
# → {"ok": true, "nodes": 8}
```

`docker-compose.yml` adds a read-only filesystem, dropped
capabilities, `no-new-privileges`, and a proxy profile:

```bash
docker compose up -d
docker compose --profile edge up -d   # enables the nginx proxy
docker compose down
```

**Why these flags matter:**

- `read_only: true` + `tmpfs: /tmp` — triage4 does not need to write
  anywhere persistent at runtime.
- `cap_drop: ALL` — triage4 does not need any Linux capability.
- `no-new-privileges: true` — blocks `setuid` exploitation paths.
- `HEALTHCHECK` — orchestrators can restart a hung worker.

### 1.2 systemd companion-computer install

`deploy/triage4.service` is a sandboxed unit that:

- runs as user `triage`, never root,
- applies `NoNewPrivileges`, `ProtectSystem=strict`,
  `MemoryDenyWriteExecute`, `SystemCallFilter=@system-service`,
- caps memory at 1 GB and file descriptors at 4096,
- loads secrets from `/etc/triage4/env` (chmod 600).

Install:

```bash
sudo useradd --system --home /opt/triage4 --shell /sbin/nologin triage
sudo python3.12 -m venv /opt/triage4/venv
sudo /opt/triage4/venv/bin/pip install triage4
sudo mkdir /etc/triage4
sudo cp configs/production.yaml /etc/triage4/
sudo cp deploy/triage4.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now triage4
```

Logs: `journalctl -u triage4 -f`

### 1.3 Edge / denied-comms profile

Use `configs/edge.yaml`. Enables:

- CRDT sync (`state_graph/crdt_graph.py`) with a replica ID drawn
  from `TRIAGE4_REPLICA_ID`,
- Marker codec (`integrations/marker_codec.py`) with a 24 h default
  `max_age` and secret from `TRIAGE4_MARKER_SECRET`,
- Tighter low-battery warning (25% vs 20%) — edge power is scarce,
- Reduced telemetry retention (3 days vs 7).

## 2. Configuration

All runtime config flows through **one YAML file** selected by the
`TRIAGE4_CONFIG` environment variable. The repo ships three
reference configs:

| File | Profile | Uses |
|---|---|---|
| `configs/sim.yaml` | simulation / demos | the existing 8-casualty benchmark |
| `configs/production.yaml` | cloud or forward operating base | conservative thresholds, loopback bridges, operator gates on |
| `configs/edge.yaml` | companion computer | CRDT + markers enabled, tighter power |

**Intentional simplicity.** Complex configuration is an anti-pattern
for decision-support code. triage4 uses flat YAML with ~20 keys; if
a deployment needs more, that is a signal to extend modules, not the
config.

## 3. Secrets

Three environment-variable slots are reserved. Every one MUST be
set before exposing the API to anything beyond localhost:

| Env var | Purpose | Min length |
|---|---|---|
| `TRIAGE4_MARKER_SECRET` | HMAC key for `marker_codec` | 32 bytes recommended (8 required) |
| `TRIAGE4_DASHBOARD_TOKEN` | Bearer token for the API | 32 bytes |
| `TRIAGE4_TLS_CERT_PATH` | Path to TLS certificate bundle | n/a |

`configs/production.yaml` deliberately leaves these blank so an
unconfigured deployment fails loud rather than shipping insecure
defaults. See RISK_REGISTER **SEC-001 / SEC-002 / SEC-003**.

Generating keys:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 4. Networking

triage4 binds `0.0.0.0:8000` inside the container and `127.0.0.1:8000`
on systemd — the public surface should always go through a reverse
proxy with TLS, not directly to uvicorn.

`configs/nginx.conf` is a minimal reverse-proxy template with:

- TLS 1.2+ only,
- security headers (`X-Content-Type-Options`, `X-Frame-Options`,
  `Strict-Transport-Security`),
- a `limit_req_zone` for rate-limiting,
- a commented-out bearer-token check (fill in before shipping).

## 5. Observability

triage4 writes structured logs when `telemetry.structured_json: true`
(both production and edge profiles default to on). Recommended
scraping:

- **Logs** — `journalctl -o json` on systemd,
  `docker logs --tail=...` in containers.
- **Metrics** — not yet exposed. Phase 13 proper will add a
  `/metrics` endpoint (Prometheus) behind the same auth gate.
- **Traces** — out of scope for Phase 13-prep.

## 6. Upgrade / rollback

Image:

```bash
docker pull triage4:0.1.1
docker compose up -d --force-recreate api
# rollback:
docker compose up -d --force-recreate api \
    --scale api=0
docker tag triage4:0.1.0 triage4:latest
docker compose up -d
```

systemd:

```bash
sudo /opt/triage4/venv/bin/pip install --upgrade triage4
sudo systemctl restart triage4
# rollback:
sudo /opt/triage4/venv/bin/pip install triage4==0.1.0
sudo systemctl restart triage4
```

**No in-place migrations.** triage4 state is mission-local (in-memory
graphs + optional offline markers), so upgrades are stateless. This
is intentional — regulated medical software is hard enough without
a schema-evolution layer on top.

## 7. Pre-deployment checklist

Before any deployment that reaches more than the developer's laptop:

- [ ] `TRIAGE4_MARKER_SECRET`, `TRIAGE4_DASHBOARD_TOKEN`, TLS cert
      all set and ≥ minimum length.
- [ ] `configs/<profile>.yaml` reviewed; no default blank secrets.
- [ ] Reverse proxy in front of the API — no direct uvicorn
      exposure.
- [ ] TLS cert chains valid; HSTS enabled.
- [ ] Logs captured and retained per local policy
      (`telemetry.retention_days`).
- [ ] Image passes `docker scout cves triage4:<tag>` or equivalent
      (not CI-gated yet; tracked as **CI-003**).
- [ ] No real PHI in logs, configs, or test fixtures (RISK
      **DATA-005**).
- [ ] SBOM generated and archived: `cyclonedx-py -o sbom.json`.
- [ ] Runbook for incident response exists and has been tested
      (at least once).
- [ ] Rollback path rehearsed.
- [ ] `pytest -q` + `ruff check` + `mypy` + smoke-benchmark all
      green on the deployed commit.

## 8. Non-goals

- **No Kubernetes manifests.** If a deployment outgrows a single
  container, Helm charts can come later.
- **No multi-tenancy.** triage4 is a single-mission tool; isolation
  between missions is a deployment-layer concern, not an app-layer
  one.
- **No database.** triage4 is stateless across restarts.
  Observation history lives in `EvidenceMemory` in-process.
- **No user accounts.** The dashboard uses a bearer token —
  multi-operator ACLs come if a customer needs them.
- **No CI/CD template.** The existing GitHub Actions workflow is
  enough for the project's current scale.

## 9. Open questions (for Phase 13 proper)

- Prometheus metrics endpoint + authenticated scrape.
- Centralised log shipping (Loki / ELK) with a log-redaction filter
  for any accidental PHI.
- Signed releases (cosign / sigstore) once we have a real release
  cadence.
- Multi-region deployment pattern — CRDT sync already works,
  deployment layout around it is undesigned.
- Offline-first installer for air-gapped sites (tarball + SHA256).

Tracked in `ROADMAP.md` under Phase 13 proper.
