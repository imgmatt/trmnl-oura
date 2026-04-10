"""Fetch Oura Ring data and push to TRMNL display."""

import os
import sys
from datetime import date

from oura_client import OuraClient
from trmnl_client import TRMNLClient


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
    data = oura.get_all()

    # Flatten nested dicts into merge variables with prefixed keys
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
        for k, v in data["heart_rate"].items():
            merge_vars[f"hr_{k}"] = v if v is not None else "--"
        # Add unit labels
        for field in ["resting_hr", "avg_hr", "max_hr", "min_hr"]:
            val = data["heart_rate"].get(field)
            if val is not None:
                merge_vars[f"hr_{field}_display"] = f"{val} bpm"
            else:
                merge_vars[f"hr_{field}_display"] = "--"
    else:
        merge_vars["hr_resting_hr"] = "--"
        merge_vars["hr_resting_hr_display"] = "--"
        merge_vars["hr_avg_hr"] = "--"
        merge_vars["hr_avg_hr_display"] = "--"
        merge_vars["hr_max_hr"] = "--"
        merge_vars["hr_min_hr"] = "--"

    print(f"Pushing {len(merge_vars)} variables to TRMNL...")
    result = trmnl.push(merge_vars)
    print(f"Done: {result}")


if __name__ == "__main__":
    main()
