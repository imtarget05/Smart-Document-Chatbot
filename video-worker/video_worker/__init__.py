"""SDC video-worker — durable DB queue consumer that runs FFmpeg off-web.

Vendors the pure FFmpeg core from MAIA (see PROVENANCE.md); no runtime
dependency on the MAIA repo.
"""
from __future__ import annotations

__all__ = ["config", "encoder", "pipeline", "storage", "store", "worker"]