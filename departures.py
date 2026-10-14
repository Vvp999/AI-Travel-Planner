import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE = "https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1"
HEADERS = {
    "DB-Client-Id": os.getenv("DB_CLIENT_ID"),
    "DB-Api-Key": os.getenv("DB_API_KEY"),
    "accept": "application/xml",
}


def get_station_ids(name):
    """Return all IDs for a station: the main EVA number plus its meta IDs."""
    r = requests.get(f"{BASE}/station/{name}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    station = ET.fromstring(r.text).find("station")
    if station is None:
        return []
    ids = [station.get("eva")]
    meta = station.get("meta")
    if meta:
        ids += meta.split("|")
    return ids


def get_departures(ids, when=None):
    """Return planned departures for one hour, checking every station ID."""
    when = when or datetime.now()
    date = when.strftime("%y%m%d")
    hour = when.strftime("%H")

    trains, seen = [], set()
    for eva in ids:
        r = requests.get(f"{BASE}/plan/{eva}/{date}/{hour}", headers=HEADERS, timeout=10)
        if r.status_code != 200:
            continue
        for s in ET.fromstring(r.text).findall("s"):
            tl, dp = s.find("tl"), s.find("dp")
            if tl is None or dp is None or s.get("id") in seen:
                continue  # no departure (train ends here) or duplicate
            seen.add(s.get("id"))
            pt = dp.get("pt", "")  # format YYMMDDHHmm
            trains.append({
                "train": f"{tl.get('c', '')} {dp.get('l') or tl.get('n', '')}",
                "time": f"{pt[6:8]}:{pt[8:10]}" if len(pt) >= 10 else "?",
                "platform": dp.get("pp", "?"),
                "destination": dp.get("ppth", "").split("|")[-1],
            })
    return sorted(trains, key=lambda t: t["time"])


if __name__ == "__main__":
    station_name = "Berlin Hbf"
    ids = get_station_ids(station_name)
    print("Station IDs:", ids)

    deps = get_departures(ids)
    print("Trains found:", len(deps))
    print("-" * 50)
    for t in deps:
        print(f"{t['time']}  {t['train']:<10} Pl. {t['platform']:<4} -> {t['destination']}")
