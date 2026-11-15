# RCA — informe-anestesia-diario cron did NOT fire in production (2026-11-13 Guatemala)

## Question
Confirm whether the daily anesthesia report cron `informe-anestesia-diario` (18:00 America/Guatemala = 00:00 UTC 2026-11-14, `POST /api/cron/informe-anestesia-diario`) fired in PRODUCTION and sent its email.

## Verdict
**The webhook NEVER fired.** No request reached the backend, no email was sent. This is NOT an auth/secret problem and NOT a recipient env-var problem — both are healthy. The failure is on the **platform cron-scheduler** side: the entry declared in `.emergent/crons.yml` was not registered/synced into the production scheduler at the last deploy.

## Evidence
Deployment `novavision-finanzas`, active run `ac2e75d1-e8f0-46ff-adfc-c2b8bcbccb69` (redeploy, success, 2026-11-12 22:49 UTC). Frontend = cloudflare.

### 1. Production logs — last 24h (covers 00:00 UTC 2026-11-14)
Filtering for `informe-anestesia | Informe de anestesia | email/send | cron/` and excluding the gcal-sync noise, the ONLY cron activity in the entire window was:
```
INFO: 104.22.93.101:0 - "POST /api/cron/cierre-diario HTTP/1.1" 200 OK
INFO:httpx:HTTP Request: POST https://integrations.emergentagent.com/api/v1/email/send "HTTP/1.1 202 Accepted" ×2
```
- NO `POST /api/cron/informe-anestesia-diario` access-log line (not even a rejected 401/403 — uvicorn logs every request, so a bad-secret call would still appear).
- NO backend line `Informe de anestesia <fecha> enviado: N ok, M errores, X procedimientos` from `_run_cron_informe_anestesia`.
- NO additional `email/send` calls beyond the cierre-diario pair.
- `produccion-medico-diario` (17:00 Guatemala = 23:00 UTC, also in window) likewise did NOT fire.

So at ~00:00 UTC 2026-11-14 the older `cierre-diario` cron fired and sent email successfully, but the newer `informe-anestesia-diario` (same `0 18 * * *` / America/Guatemala schedule) produced no request at all.

### 2. Source config is correct (`.emergent/crons.yml`)
```yaml
- name: informe-anestesia-diario
  cron: "0 18 * * *"
  timezone: "America/Guatemala"
  endpoint: "{{BASE_URL}}/api/cron/informe-anestesia-diario"
  method: POST
  enabled: true
```
Identical scheduling to `cierre-diario`, which works. The route (`backend/routes/email_service.py`) is wired correctly: `POST /cron/informe-anestesia-diario` validates `Authorization: Bearer <WEBHOOK_CRON_SECRET>` (401 otherwise), returns `202 {status: accepted}`, and backgrounds `_run_cron_informe_anestesia`, which logs the `enviado: N ok…` line.

### 3. Secrets are healthy (active run, verified via list_secrets)
- `WEBHOOK_CRON_SECRET` — present, non-empty, `matches_expected: true` (equals the source `.env` value). No auth/secret mismatch.
- `INFORME_ANESTESIA_EMAILS` — present, non-empty. Recipients ARE configured.

## Root cause
The production cron scheduler only has the older `cierre-diario` entry registered and firing. The two newer entries declared (and `enabled: true`) in `.emergent/crons.yml` — `informe-anestesia-diario` and `produccion-medico-diario` — were never registered into the scheduler, so no POST was ever issued to those endpoints. The cron-sync from `.emergent/crons.yml` at the last deploy did not pick up / register the newer crons. Platform-side (cron registry/sync), not the app code and not the secrets.

## Impact
Today's (2026-11-13 Guatemala) anesthesia report email was **not sent to anyone**. The app endpoint itself is healthy and would have sent to the configured `INFORME_ANESTESIA_EMAILS` recipients had the scheduler called it.

## Recommended fixes
1. **Platform:** Re-sync / register the production cron scheduler from `.emergent/crons.yml`. The scheduler is missing `informe-anestesia-diario` (and `produccion-medico-diario`), both declared `enabled: true`; only `cierre-diario` is registered. This needs an Emergent platform fix to the cron-sync/registration.
2. **User (redeploy):** Trigger a fresh redeploy to force a re-sync of `.emergent/crons.yml`; afterward confirm tomorrow at 18:00 Guatemala that `POST /api/cron/informe-anestesia-diario` appears with 202 and the `Informe de anestesia … enviado` log line.
3. **User (interim, today's missed report):** Send today's report manually from the app via the authenticated admin endpoint `POST /api/quirofano/anesthesia/daily-report/enviar` (roles admin/superadmin/anestesia) — it reuses the same send path and configured recipients.
