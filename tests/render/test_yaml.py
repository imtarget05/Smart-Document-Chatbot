"""Spin-down prevention: every service in render.yaml must declare per-service
keep-alive config (keep_alive / auto_stop) and web services must document
their health-check path."""

from pathlib import Path

import yaml

RENDER_YAML = Path(__file__).resolve().parents[2] / "render.yaml"


def test_render_yaml_has_keep_alive():
    with open(RENDER_YAML) as f:
        config = yaml.safe_load(f)
    services = config.get("services", [])
    assert services, "render.yaml must define at least one service"
    for svc in services:
        assert "keep_alive" in svc or "auto_stop" in svc, (
            f"service {svc.get('name')!r} missing per-service keep-alive config"
        )
        if svc.get("type") == "web":
            assert svc.get("healthCheckPath"), (
                f"service {svc.get('name')!r} missing documented healthCheckPath"
            )
