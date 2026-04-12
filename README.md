# Oura Stats for TRMNL

Display your [Oura Ring](https://ouraring.com) health data on a [TRMNL](https://usetrmnl.com) e-ink display.

## Layout

The **full** layout shows a two-row dashboard:

- **Top row** — Readiness, Sleep, and Activity scores with key contributor stats
- **Bottom row** — Body Insights (temperature, respiration, restlessness) and Heart Rate (resting/average/range plus a 24-hour line chart of BPM over time)

Three additional layouts are included for TRMNL mashups:

- `half_horizontal.html` (800×240) — single row: Readiness / Sleep / Activity
- `half_vertical.html` (400×480) — stacked: Readiness, Sleep, Activity, Heart Rate
- `quadrant.html` (400×240) — 2×2 grid with just the four main scores

## Setup

### 1. Get your Oura API token

1. Go to [cloud.ouraring.com/personal-access-tokens](https://cloud.ouraring.com/personal-access-tokens)
2. Create a new personal access token
3. Copy the token

### 2. Create a TRMNL Private Plugin

You need a **Private Plugin** with a **Webhook** strategy so this repo can `POST` merge variables to it. Follow these steps exactly:

1. Sign in at [usetrmnl.com](https://usetrmnl.com) and open the [Plugins](https://usetrmnl.com/plugins) page.
2. Click **Add New → Private Plugin** (sometimes labeled "Custom Plugin").
3. Fill in the plugin details:
   - **Name:** `Oura Stats` (or whatever you like)
   - **Strategy:** select **Webhook** (so the plugin receives pushed data rather than polling a URL)
   - **Refresh rate:** `15 minutes` (or match your desired cadence — this repo's GitHub Action runs every 15 min)
   - **Dark mode:** optional; the templates are designed to work in both
4. Click **Save**. TRMNL generates a **Webhook URL** of the form:
   ```
   https://usetrmnl.com/api/custom_plugins/{UUID}
   ```
   Copy only the `{UUID}` portion (everything after `/custom_plugins/`) — that's what you'll store as `TRMNL_PLUGIN_UUID`.
5. Open the plugin's **Edit Markup** screen. You'll see four layout tabs: **Full**, **Half Horizontal**, **Half Vertical**, **Quadrant**.
6. For each tab, paste the contents of the matching file from [`markup/`](markup/):
   - `markup/full.html` → **Full** tab
   - `markup/half_horizontal.html` → **Half Horizontal** tab
   - `markup/half_vertical.html` → **Half Vertical** tab
   - `markup/quadrant.html` → **Quadrant** tab
7. Click **Save** on each tab. You can click **Preview** to see a render — it'll show placeholder values until the first real push arrives.
8. Back on the plugin detail page, **Install** the plugin to your TRMNL device and assign it to a playlist slot so it actually appears on the screen.

> **Note:** Whenever you change anything in `markup/*.html` in this repo, you must re-paste the updated markup into the corresponding TRMNL tab. TRMNL does **not** pull markup from GitHub automatically — the repo is source-of-truth for your own reference, but the plugin editor holds the live copy.

> **Payload limit:** TRMNL rejects pushes where `merge_variables` JSON exceeds roughly 2 KB with an HTTP 422. `main.py` already contains a size guard that progressively shrinks the heart rate chart if the payload grows too large; don't add large free-text merge variables without accounting for the ceiling.

### 3. Deploy

#### Option A: GitHub Actions (recommended)

1. Fork this repo
2. Go to **Settings > Secrets and variables > Actions**
3. Add two repository secrets:
   - `OURA_TOKEN` — your Oura personal access token
   - `TRMNL_PLUGIN_UUID` — your TRMNL plugin UUID
4. Enable the workflow under **Actions**

The workflow runs every 15 minutes and pushes updated data to your TRMNL display. It uses `actions/cache@v4` to persist the last known data between runs, so sections that temporarily return empty (for example, activity data early in the day) fall back to their most recent values instead of displaying blanks.

#### Option B: Run locally

```bash
cp .env.example .env
# Edit .env with your tokens

pip install -r requirements.txt
python main.py
```

Set up a cron job to run periodically:

```bash
# Every 15 minutes
*/15 * * * * cd /path/to/trmnl-oura && /path/to/python main.py
```

The local cache lives at `.cache/last_data.json` (ignored by git).

## How data refreshing works

Each run fetches sleep, readiness, activity, and heart rate from the Oura API. For each section:

- If fresh data is returned, it's used and written to the cache
- If the fetch returns empty (Oura hasn't generated today's document yet), the last cached values are used
- Sleep, readiness, and activity all fall back to yesterday's date before giving up, since new daily documents become available at different times during the morning

The `updated_at` variable shows the timestamp of the most recent piece of real data (not the time the script ran), so you can tell at a glance how stale the display is.

## Merge Variables Reference

The following variables are available in your TRMNL markup templates:

### Scores and statuses

| Variable | Example |
|---|---|
| `readiness_score` | 78 |
| `readiness_temperature_deviation` | +0.2° |
| `readiness_recovery_index` | 90 |
| `readiness_sleep_balance` | 85 |
| `sleep_score` | 85 |
| `sleep_total_sleep` | 7h 42m |
| `sleep_deep_sleep` | 1h 20m |
| `sleep_rem_sleep` | 1h 50m |
| `sleep_light_sleep` | 4h 30m |
| `sleep_efficiency` | 92 |
| `readiness_hrv_balance` | 86 (templates display this as "AVG HRV" — Oura's 0–100 contributor score, not raw HRV ms) |
| `sleep_average_breath` | 14.2 |
| `activity_score` | 72 |
| `activity_steps` | 8,432 |
| `activity_total_calories` | 2,100 |
| `activity_active_calories` | 420 |
| `activity_high_activity_time` | 45m |
| `activity_medium_activity_time` | 1h 20m |
| `activity_low_activity_time` | 3h 15m |
| `spo2_average` | 97.5% |

### Heart rate

| Variable | Example |
|---|---|
| `hr_resting_hr` | 58 |
| `hr_resting_hr_display` | 58 bpm |
| `hr_avg_hr` | 72 |
| `hr_avg_hr_display` | 72 bpm |
| `hr_min_hr` | 52 |
| `hr_max_hr` | 145 |
| `hr_line_path` | SVG path `d` for the HR line |
| `hr_area_path` | SVG path `d` for the filled area under the line |

### Meta

| Variable | Example |
|---|---|
| `updated_at` | Apr 11, 08:32 AM |

## How the heart rate chart works

The chart is an inline `<svg>` in the template with a fixed `viewBox="0 0 480 60"`. Two `<path>` elements get their `d` attribute populated from merge variables:

- `hr_line_path` — the line itself
- `hr_area_path` — the same line closed along the baseline for a light fill

Path data is pure numeric text (`M`, `L`, `Z` plus integer coordinates), so it renders correctly even if TRMNL HTML-escapes merge variable values. `build_hr_line()` in [`main.py`](main.py) resamples the raw Oura BPM readings into 40 evenly-spaced time buckets (shrinking further if needed to stay under TRMNL's 2 KB payload limit), scales them to the chart's coordinate space, and emits both paths.

## Files

- `main.py` — orchestrator: fetch, merge with cache, build chart data, push to TRMNL
- `oura_client.py` — Oura API v2 client with yesterday fallbacks
- `trmnl_client.py` — TRMNL webhook client
- `cache.py` — persistent per-section cache (`.cache/last_data.json`)
- `markup/full.html` — 800×480 full-screen layout
- `markup/half_horizontal.html` — 800×240 layout
- `markup/half_vertical.html` — 400×480 layout
- `markup/quadrant.html` — 400×240 layout
- `.github/workflows/update.yml` — scheduled GitHub Action

## License

MIT
