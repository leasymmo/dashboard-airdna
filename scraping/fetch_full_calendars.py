#!/usr/bin/env python3
"""
Industrial Calendar Scraper for Airbnb Peripheral Communes.
Fetches 365 days of availability and pricing per listing using rotating residential proxies.
Outputs schema identical to Inside Airbnb's calendar.csv.gz:
['listing_id', 'date', 'available', 'minimum_nights', 'maximum_nights']
"""

import os
import sys
import time
import argparse
import gzip
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import pyairbnb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

def load_proxy_url():
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                if line.startswith("AIRBNB_PROXY_URL="):
                    return line.strip().split("=", 1)[1].strip("\"'")
    return os.getenv("AIRBNB_PROXY_URL", "")

def fetch_single_calendar(api_key, room_id, proxy_url, max_retries=3):
    """Fetches full 12 months for a single listing."""
    for attempt in range(max_retries):
        try:
            # Query calendar for next 12 months
            cal_data = pyairbnb.calendarinfo.get(
                api_key, 
                str(room_id), 
                month=11, 
                year=2026, 
                proxy_url=proxy_url, 
                timeout=25
            )
            if not cal_data or not isinstance(cal_data, list):
                return []
                
            days_rows = []
            for month_data in cal_data:
                for d in month_data.get("days", []):
                    c_date = d.get("calendarDate")
                    if not c_date:
                        continue
                    days_rows.append({
                        "listing_id": room_id,
                        "date": c_date,
                        "available": "t" if d.get("available") else "f",
                        "minimum_nights": d.get("minNights", 1),
                        "maximum_nights": d.get("maxNights", 365)
                    })
            return days_rows
        except Exception as e:
            if attempt == max_retries - 1:
                return []
            time.sleep(1 + attempt)
    return []

def run_calendar_scraper(communes=None, max_listings=None, threads=10, merge_with_ia=True):
    proxy_url = load_proxy_url()
    if not proxy_url:
        print("❌ Erreur : Aucune URL de proxy trouvée dans scraping/.env")
        sys.exit(1)
        
    print(f"🔒 Chargement de la clé API Airbnb via le proxy résidentiel...")
    api_key = pyairbnb.get_api_key(proxy_url=proxy_url)
    print(f"✅ Clé API active : {api_key[:12]}...")

    # Charger les annonces cibles
    parquet_path = os.path.join(DATA_DIR, "listings_cleaned.parquet")
    df = pd.read_parquet(parquet_path)
    
    # Exclure Lyon intramuros (déjà dans Inside Airbnb)
    lyon_arrs = [f"{i}er Arrondissement" if i == 1 else f"{i}e Arrondissement" for i in range(1, 10)]
    df_periph = df[~df["neighbourhood_cleansed"].isin(lyon_arrs)].copy()
    
    if communes:
        df_periph = df_periph[df_periph["neighbourhood_cleansed"].isin(communes)]
        
    if max_listings:
        df_periph = df_periph.head(max_listings)
        
    total_listings = len(df_periph)
    print(f"🚀 Démarrage du scraping des calendriers pour {total_listings} logements ({threads} threads parallèles)...")

    out_csv_gz = os.path.join(DATA_DIR, "calendar_peripheral.csv.gz")
    checkpoint_dir = os.path.join(BASE_DIR, "scraping", "data", "checkpoints_cal")
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    room_ids = df_periph["id"].tolist()
    all_days = []
    completed = 0
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_id = {executor.submit(fetch_single_calendar, api_key, rid, proxy_url): rid for rid in room_ids}
        
        for future in as_completed(future_to_id):
            rid = future_to_id[future]
            completed += 1
            try:
                days = future.result()
                if days:
                    all_days.extend(days)
            except Exception as e:
                pass
                
            if completed % 50 == 0 or completed == total_listings:
                elapsed = time.time() - start_time
                speed = completed / elapsed if elapsed > 0 else 0
                print(f"  • Progression : {completed}/{total_listings} annonces ({len(all_days):,} jours extraits - {speed:.1f} req/s)")

    print(f"\n💾 Sauvegarde de {len(all_days):,} lignes dans {out_csv_gz}...")
    df_cal = pd.DataFrame(all_days, columns=["listing_id", "date", "available", "minimum_nights", "maximum_nights"])
    df_cal.to_csv(out_csv_gz, index=False, compression="gzip")
    print(f"✅ Fichier exporté avec succès : {out_csv_gz}")

    if merge_with_ia:
        ia_cal_path = os.path.join(DATA_DIR, "calendar.csv.gz")
        unified_path = os.path.join(DATA_DIR, "calendar_grand_lyon.csv.gz")
        if os.path.exists(ia_cal_path):
            print(f"🔄 Fusion avec le calendrier Inside Airbnb de Lyon ({ia_cal_path})...")
            df_ia = pd.read_csv(ia_cal_path)
            df_unified = pd.concat([df_ia, df_cal], ignore_index=True)
            df_unified.to_csv(unified_path, index=False, compression="gzip")
            print(f"🌟 Fichier unifié créé : {unified_path} ({len(df_unified):,} lignes au total)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper de calendrier 365 jours pour les communes périphériques")
    parser.add_argument("--communes", nargs="+", default=None, help="Filtrer sur certaines communes")
    parser.add_argument("--max", type=int, default=None, help="Nombre max d'annonces à scraper (ex: pour tester)")
    parser.add_argument("--threads", type=int, default=12, help="Nombre de requêtes parallèles")
    args = parser.parse_args()
    
    run_calendar_scraper(communes=args.communes, max_listings=args.max, threads=args.threads)
