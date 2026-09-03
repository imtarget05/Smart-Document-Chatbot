# Canary / Blue-Green on Render (Phase3)

Render free has no native traffic splitting. Strategy: Preview + Manual Promote.

## Flow

1. Push to `release/*` branch -> Render creates Preview environment (if `previewsEnabled` in dashboard).
   - Enable in Render Dashboard: Service -> Settings -> Previews -> Enable for `main`.
2. CI detects preview URL from `RENDER_PREVIEW_URL` secret.
3. Run E2E + smoke:
   ```bash
   python scripts/production_smoke.py --base-url $RENDER_PREVIEW_URL
   npx playwright test e2e/chat-ui.spec.ts --project=chromium
   ```
4. If smoke passes, manual promote: Render Dashboard -> Preview -> Promote to Production, or `render-deploy-action` with `RENDER_SERVICE_ID`.

## Automation (future)

- For true canary (10% -> 50% -> 100%), migrate to Cloud Run / K8s with Istio/Argo Rollouts.
- Render paid `scaling` supports `minInstances` but not canary; use `blueGreen: true` in `render.yaml` when Render adds it.

## Rollback

- Render -> Deploys -> Rollback to previous SHA in 1 click.
- Verify via `docs/render-smoke-test.md` curl checks.

## Render scaling (capacity)

Free tier: `plan: free` single instance. Paid: set
```yaml
scaling:
  minInstances: 2
  maxInstances: 5
  targetCPUPercent: 70
  targetMemoryPercent: 80
```
See `render.yaml` comments and `docs/CAPACITY.md`.
