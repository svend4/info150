"""Smoke tests for Phase 13-prep deployment artefacts.

These tests verify that the shipped deployment files exist, parse,
and declare the flags we rely on (unprivileged user, read-only FS,
no blank secrets in production configs). They run on pure YAML /
text parsing and need no Docker / systemd to execute.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relpath: str) -> str:
    return (_REPO_ROOT / relpath).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "relpath",
    [
        "Dockerfile",
        ".dockerignore",
        "docker-compose.yml",
        "deploy/triage4.service",
        "configs/nginx.conf",
        "configs/production.yaml",
        "configs/edge.yaml",
        "configs/sim.yaml",
        "docs/DEPLOYMENT.md",
    ],
)
def test_deployment_artefact_exists(relpath):
    assert (_REPO_ROOT / relpath).exists(), f"missing {relpath}"


def test_dockerfile_runs_as_unprivileged_user():
    dockerfile = _read("Dockerfile")
    assert "USER triage" in dockerfile
    assert "useradd" in dockerfile


def test_dockerfile_has_healthcheck():
    dockerfile = _read("Dockerfile")
    assert "HEALTHCHECK" in dockerfile


def test_compose_runs_read_only_and_drops_capabilities():
    compose = yaml.safe_load(_read("docker-compose.yml"))
    api = compose["services"]["api"]
    assert api["read_only"] is True
    assert api["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in api["security_opt"]


def test_compose_api_binds_localhost_only():
    compose = yaml.safe_load(_read("docker-compose.yml"))
    api = compose["services"]["api"]
    assert any(str(p).startswith("127.0.0.1:") for p in api["ports"])


def test_production_config_has_no_inline_secrets():
    cfg = yaml.safe_load(_read("configs/production.yaml"))
    security = cfg["security"]
    # Env-var slots only — never inline strings.
    for key in ("marker_secret_env", "dashboard_token_env", "tls_cert_env"):
        val = security[key]
        assert val, f"{key} must not be blank"
        assert val.startswith("TRIAGE4_"), (
            f"{key} must reference a TRIAGE4_* env var, got {val!r}"
        )


def test_production_config_disables_autonomous_dispatch():
    cfg = yaml.safe_load(_read("configs/production.yaml"))
    op = cfg["operator"]
    assert op["allow_autonomous_waypoint_dispatch"] is False
    assert op["require_confirmation_on_immediate"] is True


def test_edge_config_enables_denied_comms_surface():
    cfg = yaml.safe_load(_read("configs/edge.yaml"))
    dc = cfg["denied_comms"]
    assert dc["crdt_enabled"] is True
    assert dc["marker_codec_enabled"] is True
    assert dc["marker_max_age_s"] >= 3600


def test_systemd_unit_uses_sandboxing():
    unit = _read("deploy/triage4.service")
    for flag in (
        "NoNewPrivileges=true",
        "ProtectSystem=strict",
        "ProtectHome=true",
        "PrivateTmp=true",
        "MemoryDenyWriteExecute=true",
    ):
        assert flag in unit, f"missing {flag}"


def test_systemd_unit_runs_as_triage_user_not_root():
    unit = _read("deploy/triage4.service")
    assert "User=triage" in unit
    assert "Group=triage" in unit
    assert "User=root" not in unit


def test_nginx_conf_enforces_tls_and_security_headers():
    conf = _read("configs/nginx.conf")
    assert "ssl_protocols TLSv1.2 TLSv1.3" in conf
    for header in (
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Strict-Transport-Security",
    ):
        assert header in conf, f"missing header {header}"
