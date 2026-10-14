import os, requests
from dotenv import load_dotenv

load_dotenv()
BASE = "https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1"
HEADERS = {
    "DB-Client-Id": os.getenv("DB_CLIENT_ID"),
    "DB-Api-Key": os.getenv("DB_API_KEY"),
    "accept": "application/xml",
}

r = requests.get(f"{BASE}/station/Berlin Hbf", headers=HEADERS)
print(r.status_code)
print(r.text[:1000])
