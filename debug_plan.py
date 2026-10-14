import os, requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
BASE = "https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1"
HEADERS = {
    "DB-Client-Id": os.getenv("DB_CLIENT_ID"),
    "DB-Api-Key": os.getenv("DB_API_KEY"),
    "accept": "application/xml",
}

now = datetime.now()
print("Laptop time:", now)

for eva in ["8011160", "8098160"]:  # Berlin Hbf, Berlin Hbf (tief)
    for h in [0, 1]:
        t = now + timedelta(hours=h)
        url = f"{BASE}/plan/{eva}/{t:%y%m%d}/{t:%H}"
        r = requests.get(url, headers=HEADERS)
        print("\nURL:", url)
        print("Status:", r.status_code, "| Length:", len(r.text))
        print(r.text[:600])
