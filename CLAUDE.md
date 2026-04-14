# trmnl-oura — project notes for Claude

Fetches Oura Ring data on a schedule (GitHub Actions, every 15 min) and pushes merge variables to a TRMNL private plugin webhook for display.

## Key files

- `main.py` — entry point. Assembles merge_variables and pushes via `TRMNLClient`.
- `oura_client.py` — Oura API v2 client (sleep, readiness, activity, heart rate, spo2).
- `trmnl_client.py` — thin wrapper around the TRMNL custom_plugins POST endpoint.
- `cache.py` — persists the last successful Oura response so sections missing fresh data fall back to cached values.
- `markup/*.html` — TRMNL layout templates (full, half_vertical, half_horizontal, quadrant). **These are source of truth but TRMNL does not pull them — changes must be pasted into the TRMNL plugin editor manually.**
- `.github/workflows/` — the scheduled workflow that runs `main.py`.

## Gotchas

### TRMNL 2KB merge_variables limit
The `POST https://trmnl.com/api/custom_plugins/{uuid}` endpoint returns HTTP 422 if the JSON `merge_variables` body exceeds ~2KB. `main.py` has a guard that measures payload size and progressively shrinks the HR chart bucket count (40 → 30 → 20 → 12) before dropping the chart entirely. Preserve this guard when adding new merge variables, and don't add large strings without accounting for the ceiling.

### Oura `daily_activity` query window quirk
`daily_activity` is flaky about which records it returns for narrow windows:
- `start_date == end_date` can return 0 items even when the day has data.
- `yesterday → today` can omit today's (partial) record, leaving only yesterday — so the display shows stale steps/calories.

Always query `yesterday → today+1` and pick the most recent `day`. Other daily_* endpoints haven't shown this issue, but if a similar "empty/stale when data exists" pattern appears, widen the window past the target date.

### Oura `sleep` endpoint includes naps
The `sleep` endpoint returns every sleep session — naps, rests, and the main nightly session. Picking the last item can give you a nap with tiny durations and no HRV/breath data. Filter to `type == "long_sleep"` and pick the longest; fall back to the longest session of any type.

### HRV source
"HRV" in the templates is pulled from `sleep_average_hrv` (raw average HRV in ms from the main sleep session), not `readiness_hrv_balance` (0–100 contributor score). This was an explicit user preference.

### Use TRMNL framework classes — no custom CSS
TRMNL rejects plugins for publication with "too many inline styles". Markup in `markup/*.html` must use only the framework utility classes (`flex`, `flex--row/col`, `flex--center-y`, `flex--left`, `flex--between`, `gap--*`, `p--*`, `mb--*`, `border--h-*`, `stretch-x/y`, `grid grid--cols-*`, `col--span-*`, `title`, `value`, `label`, `description`). Do not add `<style>` blocks or custom classes to do layout. If alignment is off, fix it by applying the same framework classes to every cell, not by introducing custom CSS.

### Icon alignment
The section icons are Unicode glyphs (★ ◔ ▲ ◆ ♥) with inconsistent vertical metrics. They're wrapped in a uniform `1em × 1em` inline-flex box with a `translateY(-1px)` nudge; heart (♥) gets `translateY(0)` since it sits differently. Don't revert this to naive inline rendering.

## Secrets

Two GitHub Actions secrets on this repo:
- `OURA_TOKEN` — Oura personal access token from https://cloud.ouraring.com/personal-access-tokens
- `TRMNL_PLUGIN_UUID` — UUID from the TRMNL private plugin's webhook URL

## Working style

Commit and push routine changes without asking. Trigger manual workflow runs via `gh workflow run "Update TRMNL Display" --ref main` to verify fixes before the next scheduled run.
