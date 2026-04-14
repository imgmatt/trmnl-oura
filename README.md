# Oura Stats for TRMNL

Display your [Oura Ring](https://ouraring.com) health data on a [TRMNL](https://usetrmnl.com) e-ink display.

## Layout

The **full** layout shows four score tiles of equal weight — Readiness, Sleep, Activity, and Heart Rate — with a slim 24-hour BPM trend strip underneath.

Three additional layouts are included for TRMNL mashups:

- `half_horizontal.html` (800×240) — four score tiles in one row (Readiness, Sleep, Activity, Heart Rate)
- `half_vertical.html` (400×480) — 2×2 grid of Readiness, Sleep, Activity, Heart Rate
- `quadrant.html` (400×240) — four compact score-only tiles in one row

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
8. **(Optional) Upload the plugin icon.** In the plugin settings, there's an **Icon** or **Image** upload field. Export [`assets/icon.svg`](assets/icon.svg) to a PNG (any small square size like 96×96 or 240×240 works) and upload it — you can do this with Inkscape, an online SVG→PNG converter, or by opening the SVG in a browser and screenshotting.
9. Back on the plugin detail page, **Install** the plugin to your TRMNL device and assign it to a playlist slot so it actually appears on the screen.

> **Note:** Whenever you change anything in `markup/*.html` in this repo, you must re-paste the updated markup into the corresponding TRMNL tab. TRMNL does **not** pull markup from GitHub automatically — the repo is source-of-truth for your own reference, but the plugin editor holds the live copy.

> **Payload limit:** TRMNL rejects pushes where `merge_variables` JSON exceeds roughly 2 KB with an HTTP 422. `main.py` already contains a size guard that progressively shrinks the heart rate chart if the payload grows too large; don't add large free-text merge variables without accounting for the ceiling.

### 3. Deploy

#### Option A: GitHub Actions (recommended)

This runs the updater for you in the cloud every 15 minutes — no server, no laptop-left-on, no cron. If you've never used GitHub before, follow these steps exactly.

1. **Create a free GitHub account** at [github.com/signup](https://github.com/signup) if you don't have one.
2. **Fork this repository.** On this repo's page, click the **Fork** button in the top-right corner. On the next screen, leave all defaults and click **Create fork**. You'll land on your own copy at `https://github.com/<your-username>/trmnl-oura`. All further steps happen on **your** fork, not the original.
3. **Add your two secrets.** Secrets are encrypted values the workflow can read but nobody (including you, after saving) can see in plaintext.
   1. On your fork, click the **Settings** tab (in the top navbar of the repo, near "Insights"). If you don't see it, make sure you're on your fork and not the original.
   2. In the left sidebar, expand **Secrets and variables** and click **Actions**.
   3. Click the green **New repository secret** button.
   4. For **Name**, type exactly `OURA_TOKEN` (all caps, underscore). For **Secret**, paste your Oura personal access token from Step 1. Click **Add secret**.
   5. Click **New repository secret** again. For **Name**, type exactly `TRMNL_PLUGIN_UUID`. For **Secret**, paste just the UUID portion of your TRMNL webhook URL (the part after `/custom_plugins/`). Click **Add secret**.
   6. You should now see both `OURA_TOKEN` and `TRMNL_PLUGIN_UUID` listed under "Repository secrets".
4. **Enable GitHub Actions on your fork.** Forks have Actions disabled by default as a safety measure.
   1. Click the **Actions** tab in the top navbar.
   2. You'll see a yellow banner: _"Workflows aren't being run on this forked repository."_ Click the green **I understand my workflows, go ahead and enable them** button.
   3. In the list, you should now see a workflow named **Update TRMNL Display**. Click it.
5. **Run it once manually to verify it works.**
   1. On the workflow page, click the **Run workflow** dropdown on the right side.
   2. Leave the branch as `main` and click the green **Run workflow** button.
   3. Wait ~15 seconds, then refresh the page. You should see a new run appear. Click into it — if it shows a green checkmark, data has been pushed to TRMNL. If it shows a red X, click the failed job to see the error (most common causes: typo in the secret name, wrong token/UUID, or TRMNL plugin not saved yet).
6. **You're done.** The workflow is scheduled via cron (`*/15 * * * *`) and will now run every 15 minutes automatically. You can watch runs under the **Actions** tab at any time.

> **Note on GitHub's free tier:** Public repos get unlimited Actions minutes. Private repos include 2,000 free minutes/month, and this workflow uses roughly 13 seconds × 96 runs/day × 30 days ≈ 625 minutes/month — well within the free allowance even if you make your fork private.

The workflow uses `actions/cache@v4` to persist the last known data between runs, so sections that temporarily return empty (for example, activity data early in the day) fall back to their most recent values instead of displaying blanks.

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
| `readiness_resting_heart_rate` | 88 (Oura's 0–100 contributor score) |
| `sleep_score` | 85 |
| `sleep_total_sleep` | 7h 42m |
| `sleep_deep_sleep` | 1h 20m |
| `sleep_rem_sleep` | 1h 50m |
| `sleep_light_sleep` | 4h 30m |
| `sleep_efficiency` | 92 |
| `sleep_restfulness` | 78 |
| `readiness_hrv_balance` | 86 (Oura's 0–100 contributor score) |
| `sleep_average_hrv` | 42 (templates display this as "HRV" — raw average HRV in ms from the main sleep session) |
| `sleep_average_breath` | 14.2 |
| `sleep_average_heart_rate` | 63 (raw avg HR in bpm during the main sleep session) |
| `sleep_lowest_heart_rate` | 58 (lowest HR in bpm during the main sleep session) |
| `activity_score` | 72 |
| `activity_steps` | 8,432 |
| `activity_total_calories` | 2,100 |
| `activity_active_calories` | 420 |
| `activity_high_activity_time` | 45m |
| `activity_medium_activity_time` | 1h 20m |
| `activity_low_activity_time` | 3h 15m |
| `activity_sedentary_time` | 6h 09m |
| `activity_equivalent_walking_distance` | 10,144 (meters) |
| `spo2_average` | 97.5% |

### Heart rate

| Variable | Example |
|---|---|
| `hr_resting_hr` | 58 (sourced from the main sleep session's `average_heart_rate` — Oura's integrated resting HR — falling back to a computed value from rest-source samples) |
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
