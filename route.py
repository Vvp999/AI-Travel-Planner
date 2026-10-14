import requests
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from departures import BASE, HEADERS, get_station_ids

_cache = {}


def get_plan(eva, when, retries=3):
    """Fetch (and cache) the timetable for one station ID and one hour.
    Retries if DB rate-limits us; never caches a failed request."""
    key = (eva, when.strftime("%y%m%d%H"))
    if key in _cache:
        return _cache[key]

    for attempt in range(retries):
        r = requests.get(f"{BASE}/plan/{eva}/{when:%y%m%d}/{when:%H}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            _cache[key] = ET.fromstring(r.text)
            return _cache[key]
        if r.status_code == 404:
            _cache[key] = None  # no timetable for this ID/hour: safe to cache
            return None
        if r.status_code == 429:  # too many requests
            wait = 15 * (attempt + 1)
            print(f"    (DB rate limit, waiting {wait}s...)")
            time.sleep(wait)
            continue
        return None  # other error: don't cache, try again next time
    return None

def parse_time(pt):
    return datetime.strptime(pt, "%y%m%d%H%M")


def find_arrival(trip, dest_ids, dep_time, max_hours=7):
    """Find when a trip arrives at the destination by matching its trip ID."""
    for h in range(max_hours + 1):
        when = dep_time + timedelta(hours=h)
        for eva in dest_ids:
            plan = get_plan(eva, when)
            if plan is None:
                continue
            for s in plan.findall("s"):
                ar = s.find("ar")
                if ar is not None and s.get("id", "").startswith(trip):
                    return parse_time(ar.get("pt")), ar.get("pp")
    return None, None


def find_direct_trains(origin, destination, start=None, hours=3,
                       long_distance_only=True, max_results=5):
    """Return direct trains from origin to destination departing in the next hours."""
    start = start or datetime.now()
    origin_ids = get_station_ids(origin)
    dest_ids = get_station_ids(destination)
    long_distance = {"ICE", "IC", "EC", "ECE", "FLX", "RJ", "RJX", "NJ"}

    results, seen = [], set()
    for h in range(hours):
        when = start + timedelta(hours=h)
        for eva in origin_ids:
            plan = get_plan(eva, when)
            if plan is None:
                continue
            for s in plan.findall("s"):
                tl, dp = s.find("tl"), s.find("dp")
                if tl is None or dp is None:
                    continue
                if long_distance_only and tl.get("c") not in long_distance:
                    continue
                stops = dp.get("ppth", "").split("|")
                if not any(destination.lower() in stop.lower() for stop in stops):
                    continue
                dep_time = parse_time(dp.get("pt"))
                trip = s.get("id", "").rsplit("-", 1)[0]
                if dep_time < start or trip in seen:
                    continue
                seen.add(trip)
                results.append({
                    "train": f"{tl.get('c')} {tl.get('n')}",
                    "departure": dep_time,
                    "platform": dp.get("pp"),
                    "trip": trip,
                })

    results = sorted(results, key=lambda r: r["departure"])[:max_results]
    for r in results:
        arr_time, arr_pl = find_arrival(r["trip"], dest_ids, r["departure"], max_hours=12)
        r["arrival"] = arr_time
        r["arrival_platform"] = arr_pl
        r["duration_min"] = int((arr_time - r["departure"]).total_seconds() // 60) if arr_time else None
    return results


if __name__ == "__main__":
    origin, destination = "Berlin Hbf", "München Hbf"
    print(f"Direct trains {origin} -> {destination}\n")
    for r in find_direct_trains(origin, destination):
        arr = r["arrival"].strftime("%H:%M") if r["arrival"] else "?"
        dur = f"{r['duration_min'] // 60}h{r['duration_min'] % 60:02d}" if r["duration_min"] else "?"
        print(f"{r['departure']:%H:%M} -> {arr}  {r['train']:<9} Pl. {r['platform']:<4} ({dur})")
