"""Fetch Oura Ring data and push to TRMNL display."""

import os
import sys
from datetime import date, datetime

import cache
from oura_client import OuraClient
from trmnl_client import TRMNLClient


# SVG chart viewBox dimensions — the <svg> tag in the template must match
CHART_W = 480
CHART_H = 50
CHART_PAD = 2


def build_hr_line(readings):
    """Build SVG path strings (line + filled area) from heart rate readings.

    Returns a dict with 'hr_line_path' (line) and 'hr_area_path' (filled area).
    The SVG structure lives in the template; only numeric path data is substituted,
    which is safe from HTML-escaping.
    """
    empty = {"hr_line_path": "", "hr_area_path": ""}

    points = []
    for r in readings or []:
        bpm = r.get("bpm")
        ts = r.get("timestamp")
        if bpm is None or ts is None:
            continue
        try:
            dt = datetime.fromisoformat(ts)
            points.append((dt, bpm))
        except (ValueError, TypeError):
            continue

    if len(points) < 2:
        return empty

    points.sort(key=lambda p: p[0])

    # Resample to ~60 evenly-spaced points for a smoother line
    bucket_count = 60
    t_min = points[0][0].timestamp()
    t_max = points[-1][0].timestamp()
    t_range = t_max - t_min or 1
    bucket_size = t_range / bucket_count

    buckets = [[] for _ in range(bucket_count)]
    for dt, bpm in points:
        idx = min(int((dt.timestamp() - t_min) / bucket_size), bucket_count - 1)
        buckets[idx].append(bpm)

    sampled = []
    last_avg = None
    for i, bucket in enumerate(buckets):
        if bucket:
            avg = sum(bucket) / len(bucket)
            sampled.append((i, avg))
            last_avg = avg
        elif last_avg is not None:
            # Carry forward so the line stays continuous
            sampled.append((i, last_avg))

    if len(sampled) < 2:
        return empty

    bpms = [v for _, v in sampled]
    bpm_min = min(bpms) - 3
    bpm_max = max(bpms) + 3
    bpm_range = bpm_max - bpm_min or 1

    plot_w = CHART_W - CHART_PAD * 2
    plot_h = CHART_H - CHART_PAD * 2

    coords = []
    for i, bpm in sampled:
        x = CHART_PAD + (i / (bucket_count - 1)) * plot_w
        y = CHART_PAD + (1 - (bpm - bpm_min) / bpm_range) * plot_h
        coords.append((round(x, 1), round(y, 1)))

    line_parts = [f"M{coords[0][0]},{coords[0][1]}"]
    for x, y in coords[1:]:
        line_parts.append(f"L{x},{y}")
    line_path = " ".join(line_parts)

    baseline_y = CHART_PAD + plot_h
    area_path = line_path + f" L{coords[-1][0]},{baseline_y} L{coords[0][0]},{baseline_y} Z"

    return {"hr_line_path": line_path, "hr_area_path": area_path}


def main():
    oura_token = os.environ.get("OURA_TOKEN")
    trmnl_uuid = os.environ.get("TRMNL_PLUGIN_UUID")

    if not oura_token:
        print("Error: OURA_TOKEN environment variable is required")
        sys.exit(1)
    if not trmnl_uuid:
        print("Error: TRMNL_PLUGIN_UUID environment variable is required")
        sys.exit(1)

    oura = OuraClient(oura_token)
    trmnl = TRMNLClient(trmnl_uuid)

    print(f"Fetching Oura data for {date.today().isoformat()}...")
    fresh = oura.get_all()

    # Merge with cache: sections missing fresh data fall back to cached values
    data = cache.merge_with_cache(fresh)
    for section in ("sleep", "readiness", "activity", "heart_rate"):
        src = "fresh" if fresh.get(section) else ("cached" if data.get(section) else "none")
        print(f"  {section}: {src}")

    # Flatten nested dicts into merge variables with prefixed keys
    # Collect timestamps from each data source to find the most recent
    timestamps = []
    for section in data.values():
        if section and "timestamp" in section:
            timestamps.append(section["timestamp"])

    if timestamps:
        latest = max(timestamps)
        try:
            dt = datetime.fromisoformat(latest)
            merge_vars = {"updated_at": dt.strftime("%b %d, %I:%M %p")}
        except (ValueError, TypeError):
            merge_vars = {"updated_at": latest}
    else:
        merge_vars = {"updated_at": date.today().isoformat()}

    if data["sleep"]:
        for k, v in data["sleep"].items():
            merge_vars[f"sleep_{k}"] = v if v is not None else "--"
    else:
        merge_vars["sleep_score"] = "--"
        merge_vars["sleep_total_sleep"] = "--"
        merge_vars["sleep_deep_sleep"] = "--"
        merge_vars["sleep_rem_sleep"] = "--"
        merge_vars["sleep_efficiency"] = "--"
        merge_vars["sleep_restfulness"] = "--"

    if data["readiness"]:
        for k, v in data["readiness"].items():
            merge_vars[f"readiness_{k}"] = v if v is not None else "--"
        # Format temperature deviation
        temp = data["readiness"].get("temperature_deviation")
        if temp is not None:
            sign = "+" if temp >= 0 else ""
            merge_vars["readiness_temperature_deviation"] = f"{sign}{temp:.1f}\u00b0"
    else:
        merge_vars["readiness_score"] = "--"
        merge_vars["readiness_temperature_deviation"] = "--"
        merge_vars["readiness_hrv_balance"] = "--"
        merge_vars["readiness_recovery_index"] = "--"
        merge_vars["readiness_resting_heart_rate"] = "--"
        merge_vars["readiness_sleep_balance"] = "--"

    if data["activity"]:
        for k, v in data["activity"].items():
            merge_vars[f"activity_{k}"] = v if v is not None else "--"
        # Format steps with comma separator
        steps = data["activity"].get("steps")
        if steps is not None:
            merge_vars["activity_steps"] = f"{steps:,}"
        # Format calories
        cals = data["activity"].get("total_calories")
        if cals is not None:
            merge_vars["activity_total_calories"] = f"{cals:,}"
        active_cals = data["activity"].get("active_calories")
        if active_cals is not None:
            merge_vars["activity_active_calories"] = f"{active_cals:,}"
    else:
        merge_vars["activity_score"] = "--"
        merge_vars["activity_steps"] = "--"
        merge_vars["activity_total_calories"] = "--"
        merge_vars["activity_active_calories"] = "--"
        merge_vars["activity_high_activity_time"] = "--"
        merge_vars["activity_medium_activity_time"] = "--"
        merge_vars["activity_low_activity_time"] = "--"

    if data["heart_rate"]:
        readings = data["heart_rate"].pop("readings", [])
        for k, v in data["heart_rate"].items():
            merge_vars[f"hr_{k}"] = v if v is not None else "--"
        # Add unit labels
        for field in ["resting_hr", "avg_hr", "max_hr", "min_hr"]:
            val = data["heart_rate"].get(field)
            if val is not None:
                merge_vars[f"hr_{field}_display"] = f"{val} bpm"
            else:
                merge_vars[f"hr_{field}_display"] = "--"
        # Generate heart rate line chart (SVG path data)
        merge_vars.update(build_hr_line(readings))
    else:
        merge_vars["hr_resting_hr"] = "--"
        merge_vars["hr_resting_hr_display"] = "--"
        merge_vars["hr_avg_hr"] = "--"
        merge_vars["hr_avg_hr_display"] = "--"
        merge_vars["hr_max_hr"] = "--"
        merge_vars["hr_min_hr"] = "--"
        merge_vars["hr_line_path"] = ""
        merge_vars["hr_area_path"] = ""

    print(f"Pushing {len(merge_vars)} variables to TRMNL...")
    result = trmnl.push(merge_vars)
    print(f"Done: {result}")


if __name__ == "__main__":
    main()
