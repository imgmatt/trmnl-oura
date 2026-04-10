# TRMNL Oura Ring Display

Display your [Oura Ring](https://ouraring.com) health data on a [TRMNL](https://usetrmnl.com) e-ink display.

Shows a 2x2 dashboard with:
- **Sleep** — score, total duration, deep/REM breakdown, efficiency
- **Readiness** — score, HRV balance, temperature deviation, recovery
- **Activity** — score, steps, calories, activity time breakdown
- **Heart Rate** — resting HR, average, min/max range

## Setup

### 1. Get your Oura API token

1. Go to [cloud.ouraring.com/personal-access-tokens](https://cloud.ouraring.com/personal-access-tokens)
2. Create a new personal access token
3. Copy the token

### 2. Create a TRMNL Private Plugin

1. In your [TRMNL dashboard](https://trmnl.com/plugin_settings), create a new **Private Plugin**
2. Copy the plugin UUID from the webhook URL (the part after `/api/custom_plugins/`)
3. In the **Markup** tab, paste the contents of [`markup/full.html`](markup/full.html)

### 3. Deploy

#### Option A: GitHub Actions (recommended)

1. Fork this repo
2. Go to **Settings > Secrets and variables > Actions**
3. Add two repository secrets:
   - `OURA_TOKEN` — your Oura personal access token
   - `TRMNL_PLUGIN_UUID` — your TRMNL plugin UUID
4. Enable the workflow under **Actions**

The workflow runs every 15 minutes and pushes updated data to your TRMNL display.

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

## Merge Variables Reference

The following variables are available in your TRMNL markup template:

| Variable | Example |
|---|---|
| `sleep_score` | 85 |
| `sleep_total_sleep` | 7h 42m |
| `sleep_deep_sleep` | 1h 20m |
| `sleep_rem_sleep` | 1h 50m |
| `sleep_efficiency` | 92 |
| `readiness_score` | 78 |
| `readiness_hrv_balance` | 82 |
| `readiness_temperature_deviation` | +0.2° |
| `readiness_recovery_index` | 90 |
| `readiness_sleep_balance` | 85 |
| `activity_score` | 72 |
| `activity_steps` | 8,432 |
| `activity_total_calories` | 2,100 |
| `activity_high_activity_time` | 45m |
| `activity_medium_activity_time` | 1h 20m |
| `activity_low_activity_time` | 3h 15m |
| `hr_resting_hr_display` | 58 bpm |
| `hr_avg_hr_display` | 72 bpm |
| `hr_min_hr` | 52 |
| `hr_max_hr` | 145 |
| `updated_at` | 2026-04-09 |

## License

MIT
