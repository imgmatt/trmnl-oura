"""Oura Ring API v2 client."""

from typing import Optional

import requests
from datetime import date, timedelta


BASE_URL = "https://api.ouraring.com/v2/usercollection"


class OuraClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        resp = self.session.get(f"{BASE_URL}/{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _today_params(self) -> dict:
        today = date.today().isoformat()
        return {"start_date": today, "end_date": today}

    def get_daily_sleep(self) -> Optional[dict]:
        # daily_sleep has the score and contributor scores
        daily = self._get("daily_sleep", self._today_params())
        daily_items = daily.get("data", [])

        # sleep has the actual durations in seconds
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        today = date.today().isoformat()
        sleep = self._get("sleep", {"start_date": yesterday, "end_date": today})
        sleep_items = sleep.get("data", [])

        if not daily_items:
            return None

        score_item = daily_items[-1]
        contributors = score_item.get("contributors", {})

        result = {
            "score": score_item.get("score"),
            "efficiency": contributors.get("efficiency"),
            "restfulness": contributors.get("restfulness"),
            "total_sleep": "--",
            "deep_sleep": "--",
            "rem_sleep": "--",
        }

        if sleep_items:
            s = sleep_items[-1]
            result["total_sleep"] = _seconds_to_hm(s.get("total_sleep_duration"))
            result["deep_sleep"] = _seconds_to_hm(s.get("deep_sleep_duration"))
            result["rem_sleep"] = _seconds_to_hm(s.get("rem_sleep_duration"))

        return result

    def get_daily_readiness(self) -> Optional[dict]:
        data = self._get("daily_readiness", self._today_params())
        items = data.get("data", [])
        if not items:
            return None
        item = items[-1]
        contributors = item.get("contributors", {})
        return {
            "score": item.get("score"),
            "timestamp": item.get("timestamp"),
            "temperature_deviation": item.get("temperature_deviation"),
            "temperature_trend_deviation": item.get("temperature_trend_deviation"),
            "hrv_balance": contributors.get("hrv_balance"),
            "recovery_index": contributors.get("recovery_index"),
            "resting_heart_rate": contributors.get("resting_heart_rate"),
            "sleep_balance": contributors.get("sleep_balance"),
        }

    def get_daily_activity(self) -> Optional[dict]:
        data = self._get("daily_activity", self._today_params())
        items = data.get("data", [])
        if not items:
            return None
        item = items[-1]
        return {
            "score": item.get("score"),
            "timestamp": item.get("timestamp"),
            "steps": item.get("steps"),
            "active_calories": item.get("active_calories"),
            "total_calories": item.get("total_calories"),
            "equivalent_walking_distance": item.get("equivalent_walking_distance"),
            "high_activity_time": _seconds_to_hm(item.get("high_activity_time")),
            "medium_activity_time": _seconds_to_hm(item.get("medium_activity_time")),
            "low_activity_time": _seconds_to_hm(item.get("low_activity_time")),
            "sedentary_time": _seconds_to_hm(item.get("sedentary_time")),
        }

    def get_heart_rate(self) -> Optional[dict]:
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        data = self._get("heartrate", {
            "start_datetime": f"{yesterday}T22:00:00",
            "end_datetime": f"{today}T23:59:59",
        })
        items = data.get("data", [])
        if not items:
            return None

        # Find resting HR (source == "rest" or lowest BPM readings)
        rest_readings = [r for r in items if r.get("source") == "rest"]
        all_bpms = [r["bpm"] for r in items if "bpm" in r]

        resting_hr = None
        if rest_readings:
            resting_hr = min(r["bpm"] for r in rest_readings)
        elif all_bpms:
            # Approximate resting as the 10th percentile
            sorted_bpms = sorted(all_bpms)
            idx = max(0, len(sorted_bpms) // 10)
            resting_hr = sorted_bpms[idx]

        avg_hr = round(sum(all_bpms) / len(all_bpms)) if all_bpms else None
        max_hr = max(all_bpms) if all_bpms else None
        min_hr = min(all_bpms) if all_bpms else None

        return {
            "resting_hr": resting_hr,
            "avg_hr": avg_hr,
            "max_hr": max_hr,
            "min_hr": min_hr,
            "reading_count": len(all_bpms),
        }

    def get_all(self) -> dict:
        return {
            "sleep": self.get_daily_sleep(),
            "readiness": self.get_daily_readiness(),
            "activity": self.get_daily_activity(),
            "heart_rate": self.get_heart_rate(),
        }


def _seconds_to_hm(seconds: Optional[int]) -> Optional[str]:
    if seconds is None:
        return None
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m"
