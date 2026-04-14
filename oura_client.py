"""Oura Ring API v2 client."""

from typing import Optional

import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


BASE_URL = "https://api.ouraring.com/v2/usercollection"


class OuraClient:
    def __init__(self, token: str, tz: Optional[ZoneInfo] = None):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        # Use the configured display timezone to determine what "today" means,
        # so UTC-based GitHub runners query the correct local date.
        self.tz = tz or ZoneInfo("America/Los_Angeles")

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        resp = self.session.get(f"{BASE_URL}/{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _today(self):
        return datetime.now(self.tz).date()

    def _today_params(self) -> dict:
        today = self._today().isoformat()
        return {"start_date": today, "end_date": today}

    def get_daily_sleep(self) -> Optional[dict]:
        # daily_sleep has the score and contributor scores
        daily = self._get("daily_sleep", self._today_params())
        daily_items = daily.get("data", [])

        # sleep has the actual durations in seconds — use a 2-day window to catch last night
        yesterday = (self._today() - timedelta(days=1)).isoformat()
        today = self._today().isoformat()
        sleep = self._get("sleep", {"start_date": yesterday, "end_date": today})
        sleep_items = sleep.get("data", [])

        # Fall back to yesterday's daily_sleep score if today's isn't available yet
        if not daily_items:
            daily = self._get("daily_sleep", {"start_date": yesterday, "end_date": yesterday})
            daily_items = daily.get("data", [])

        if not daily_items:
            return None

        score_item = daily_items[-1]
        contributors = score_item.get("contributors", {})

        result = {
            "score": score_item.get("score"),
            "timestamp": score_item.get("timestamp"),
            "efficiency": contributors.get("efficiency"),
            "restfulness": contributors.get("restfulness"),
            "total_sleep": "--",
            "deep_sleep": "--",
            "rem_sleep": "--",
            "light_sleep": "--",
        }

        # Oura's sleep endpoint returns every sleep session (naps, rests, etc.).
        # Prefer the main nightly session ("long_sleep"); fall back to the
        # longest session if none is tagged that way. Nap sessions don't
        # populate average_hrv / average_breath.
        long_sleeps = [s for s in sleep_items if s.get("type") == "long_sleep"]
        if long_sleeps:
            s = max(long_sleeps, key=lambda x: x.get("total_sleep_duration") or 0)
        elif sleep_items:
            s = max(sleep_items, key=lambda x: x.get("total_sleep_duration") or 0)
        else:
            s = None

        if s:
            result["total_sleep"] = _seconds_to_hm(s.get("total_sleep_duration"))
            result["deep_sleep"] = _seconds_to_hm(s.get("deep_sleep_duration"))
            result["rem_sleep"] = _seconds_to_hm(s.get("rem_sleep_duration"))
            result["light_sleep"] = _seconds_to_hm(s.get("light_sleep_duration"))
            result["average_hrv"] = s.get("average_hrv")
            result["average_breath"] = s.get("average_breath")
            result["average_heart_rate"] = s.get("average_heart_rate")
            result["lowest_heart_rate"] = s.get("lowest_heart_rate")

        return result

    def get_daily_readiness(self) -> Optional[dict]:
        data = self._get("daily_readiness", self._today_params())
        items = data.get("data", [])
        if not items:
            yesterday = (self._today() - timedelta(days=1)).isoformat()
            data = self._get("daily_readiness", {"start_date": yesterday, "end_date": yesterday})
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
        # Oura's daily_activity endpoint can return 0 items for a single-day
        # query (start == end) even when data exists, so always query a 2-day
        # window and take the most recent `day`.
        today = self._today().isoformat()
        yesterday = (self._today() - timedelta(days=1)).isoformat()
        data = self._get("daily_activity", {"start_date": yesterday, "end_date": today})
        items = data.get("data", [])
        if not items:
            return None
        item = max(items, key=lambda it: it.get("day") or "")
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
        today = self._today().isoformat()
        yesterday = (self._today() - timedelta(days=1)).isoformat()
        data = self._get("heartrate", {
            "start_datetime": f"{yesterday}T22:00:00",
            "end_datetime": f"{today}T23:59:59",
        })
        items = data.get("data", [])
        if not items:
            return None

        # Fallback resting HR from raw samples; main.py prefers the sleep
        # session's `average_heart_rate` when available.
        rest_bpms = [r["bpm"] for r in items if r.get("source") == "rest" and "bpm" in r]
        all_bpms = [r["bpm"] for r in items if "bpm" in r]

        resting_hr = None
        if rest_bpms:
            resting_hr = round(sum(rest_bpms) / len(rest_bpms))
        elif all_bpms:
            sorted_bpms = sorted(all_bpms)
            tenth = max(1, len(sorted_bpms) // 10)
            resting_hr = round(sum(sorted_bpms[:tenth]) / tenth)

        avg_hr = round(sum(all_bpms) / len(all_bpms)) if all_bpms else None
        max_hr = max(all_bpms) if all_bpms else None
        min_hr = min(all_bpms) if all_bpms else None

        return {
            "resting_hr": resting_hr,
            "avg_hr": avg_hr,
            "max_hr": max_hr,
            "min_hr": min_hr,
            "reading_count": len(all_bpms),
            "timestamp": items[-1].get("timestamp"),
            "readings": items,
        }

    def get_daily_spo2(self) -> Optional[dict]:
        data = self._get("daily_spo2", self._today_params())
        items = data.get("data", [])
        if not items:
            yesterday = (self._today() - timedelta(days=1)).isoformat()
            data = self._get("daily_spo2", {"start_date": yesterday, "end_date": yesterday})
            items = data.get("data", [])
        if not items:
            return None
        item = items[-1]
        # spo2_percentage is a nested dict with "average" key
        spo2 = item.get("spo2_percentage") or {}
        return {
            "average": spo2.get("average"),
            "timestamp": item.get("timestamp") or item.get("day"),
        }

    def get_all(self) -> dict:
        return {
            "sleep": self.get_daily_sleep(),
            "readiness": self.get_daily_readiness(),
            "activity": self.get_daily_activity(),
            "heart_rate": self.get_heart_rate(),
            "spo2": self.get_daily_spo2(),
        }


def _seconds_to_hm(seconds: Optional[int]) -> Optional[str]:
    if seconds is None:
        return None
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m"
