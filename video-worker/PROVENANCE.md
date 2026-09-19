# Provenance — vendored MAIA video core

This package vendors the pure FFmpeg core from the sibling **MAIA** project so
that Smart-Document-Chatbot stays **standalone** (no cross-repo runtime or build
dependency), as required by the Service Desk / Video plan constraints.

## Source

| Item | Value |
|---|---|
| Source repo | `imtarget05/MAIA` (`https://github.com/imtarget05/MAIA`) |
| Source commit | `31ff2ab60efc997e686590c3928625d8b30d66ee` (branch `codex/maia-service-desk-v1`) |
| Vendored files | `src/maia/video/encoder.py`, `src/maia/video/pipeline.py` |
| Also ported in spirit | `src/maia/video/worker.py`, `storage.py`, `schemas.compute_idempotency_key` |

### SHA-256 at vendoring time

| Source file | SHA-256 |
|---|---|
| `src/maia/video/encoder.py` | `aa278f0c9b0f1693a49d86608e11760c935a777093d748e3d868e9ccf987b371` |
| `src/maia/video/pipeline.py` | `d869aa8d5cdf720ea6157f9c3dbaa580dc139b474c5cf1c1fc713fda0461682f` |
| `src/maia/video/schemas.py` | `bc1bc7b142e9c1614b215436a5dc3ba66176cf6ad9088295694242283c55b374` |

## What was copied verbatim

- `video_worker/encoder.py` — byte-identical to the source (verified by the
  hashes above).

## What was adapted

- `video_worker/pipeline.py` — byte-identical except for:
  1. the two `maia.video.*` imports replaced by a local relative import, and
     `compute_idempotency_key` inlined from `schemas.py`;
  2. a **bug fix** (see below).
- `worker.py`, `storage.py`, `store.py`, `config.py` were **written for SDC**,
  modelled on the MAIA equivalents but adapted to this repo's queue (`video_jobs`,
  ADR-004) and storage (Cloudflare R2 instead of MinIO).

## Divergence: forced even output dimensions (bug fix)

MAIA's transcode filter is
`scale={w}:{h}:force_original_aspect_ratio=decrease`. For 1280x720 → 480p this
produces **853x480 (odd width)**, which `libx264` + `yuv420p` rejects with
`width not divisible by 2` (ffmpeg exit 187) — the job fails and no video is
written. The vendored copy appends `:force_divisible_by=2`, producing 854x480.
This was reproduced and fixed here (real ffmpeg 9.0.1, macOS). **MAIA still has
the original bug** and should be patched separately.

## License

Both projects are owned by the same author (`imtarget05`). MAIA has no root
`LICENSE` file at the vendored commit; `THIRD_PARTY_NOTICES.md` records MIT for
bundled third-party components. This vendored first-party code is copied from
the author's own repository with the commit and hashes recorded above.