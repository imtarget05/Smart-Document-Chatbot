"""Entrypoint: ``python -m video_worker [concurrency]``."""
from __future__ import annotations

import logging
import sys
import threading

from .config import Settings
from .storage import build_storage
from .store import build_store
from .worker import VideoWorker

logger = logging.getLogger("sdc.video_worker")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = Settings()
    problems = settings.readiness_errors()
    if problems:
        logger.error("video-worker not ready: %s", "; ".join(problems))
        return 2

    concurrency = int(sys.argv[1]) if len(sys.argv) > 1 else max(settings.concurrency, 1)
    store = build_store(settings)
    storage = build_storage(settings)

    if not store.available():
        logger.error("video-worker not ready: database is unreachable")
        return 2

    workers = [VideoWorker(settings, store, storage) for _ in range(concurrency)]
    logger.info(
        "starting %d video worker(s): %s (storage=%s)",
        len(workers), [w.worker_id for w in workers], settings.storage_provider,
    )
    threads = [
        threading.Thread(target=w.run_forever, name=w.worker_id, daemon=True)
        for w in workers
    ]
    for t in threads:
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        for w in workers:
            w.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())