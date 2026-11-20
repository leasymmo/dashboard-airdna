import os
import urllib.request
import gzip
import shutil

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

BASE_URL = "https://data.insideairbnb.com/france/auvergne-rhone-alpes/lyon/2026-09-17"

FILES = [
    ("listings.csv.gz", f"{BASE_URL}/data/listings.csv.gz"),
    ("calendar.csv.gz", f"{BASE_URL}/data/calendar.csv.gz"),
    ("neighbourhoods.csv", f"{BASE_URL}/visualisations/neighbourhoods.csv"),
    ("neighbourhoods.geojson", f"{BASE_URL}/visualisations/neighbourhoods.geojson")
]

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

for fname, url in FILES:
    dest_path = os.path.join(DATA_DIR, fname)
    if os.path.exists(dest_path):
        print(f"File {fname} already exists, skipping.")
        continue
    print(f"Downloading {fname} from {url}...")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(dest_path, 'wb') as out_file:
        shutil.copyfileobj(resp, out_file)
    print(f"Saved {fname} ({os.path.getsize(dest_path):,} bytes)")

print("All downloads finished!")
