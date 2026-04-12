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

1. In your [TRMNL dashboard](https://trmnl.com/plugin_settings), create a new **Private Plugin**
2. Copy the plugin UUID from the webhook URL (the part after `/api/custom_plugins/`)
3. Paste the contents of each file in [`markup/`](markup/) into the matching markup tab (Full / Half Horizontal / Half Vertical / Quadrant)

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
| `readiness_status` | Optimal |
| `readiness_hrv_label` | Good |
| `readiness_temperature_deviation` | +0.2° |
| `readiness_recovery_index` | 90 |
| `readiness_sleep_balance` | 85 |
| `sleep_score` | 85 |
| `sleep_status` | Good |
| `sleep_total_sleep` | 7h 42m |
| `sleep_deep_sleep` | 1h 20m |
| `sleep_rem_sleep` | 1h 50m |
| `sleep_light_sleep` | 4h 30m |
| `sleep_efficiency` | 92 |
| `sleep_avg_breath` | 14.2 |
| `sleep_restless_label` | Low |
| `activity_score` | 72 |
| `activity_status` | Meet daily targets |
| `activity_steps` | 8,432 |
| `activity_total_calories` | 2,100 |
| `activity_active_calories` | 420 |
| `activity_high_activity_time` | 45m |
| `activity_medium_activity_time` | 1h 20m |
| `activity_low_activity_time` | 3h 15m |

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

The chart is an inline `<svg>` in the template with a fixed `viewBox="0 0 480 50"`. Two `<path>` elements get their `d` attribute populated from merge variables:

- `hr_line_path` — the line itself
- `hr_area_path` — the same line closed along the baseline for a light fill

Path data is pure numeric text (`M`, `L`, `Z` plus coordinates), so it renders correctly even if TRMNL HTML-escapes merge variable values. `build_hr_line()` in [`main.py`](main.py) resamples the raw Oura BPM readings into 60 evenly-spaced time buckets, scales them to the chart's coordinate space, and emits both paths.

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
