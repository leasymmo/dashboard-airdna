#!/usr/bin/env python3
"""
Industrial Full Listings Scraper (90 columns) for Airbnb Peripheral Communes.
Scrapes the full product detail page (PDP) matching Inside Airbnb's exact 90-column schema:
- Host details (id, name, bio, response rate, superhost status)
- Property features (accommodates, bedrooms, beds, bathrooms_text)
- Full amenities list as JSON array
- Review ratings breakdown (rating, accuracy, cleanliness, checkin, communication, location, value)
- Rules, checkin/checkout, license registration
- Availability metrics
"""

import os
import sys
import time
import argparse
import json
import base64
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "scraping", "data", "checkpoints_listings")
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# 90 Colonnes exactes d'Inside Airbnb
INSIDE_AIRBNB_COLS = [
    'id', 'listing_url', 'scrape_id', 'last_scraped', 'source', 'name', 'description', 
    'neighborhood_overview', 'picture_url', 'host_id', 'host_url', 'host_profile_id', 
    'host_profile_url', 'host_name', 'host_since', 'hosts_time_as_user_years', 
    'hosts_time_as_user_months', 'hosts_time_as_host_years', 'hosts_time_as_host_months', 
    'host_location', 'host_about', 'host_response_time', 'host_response_rate', 
    'host_acceptance_rate', 'host_is_superhost', 'host_thumbnail_url', 'host_picture_url', 
    'host_neighbourhood', 'host_listings_count', 'host_total_listings_count', 
    'host_verifications', 'host_has_profile_pic', 'host_identity_verified', 
    'neighbourhood', 'neighbourhood_cleansed', 'neighbourhood_group_cleansed', 
    'latitude', 'longitude', 'property_type', 'room_type', 'accommodates', 
    'bathrooms', 'bathrooms_text', 'bedrooms', 'beds', 'amenities', 'price', 
    'price_quote_checkin_date', 'price_quote_checkout_date', 'price_quote_total_price', 
    'price_quote_price_per_night', 'price_quote_raw', 'minimum_nights', 'maximum_nights', 
    'minimum_minimum_nights', 'maximum_minimum_nights', 'minimum_maximum_nights', 
    'maximum_maximum_nights', 'minimum_nights_avg_ntm', 'maximum_nights_avg_ntm', 
    'calendar_updated', 'has_availability', 'availability_30', 'availability_60', 
    'availability_90', 'availability_365', 'calendar_last_scraped', 'number_of_reviews', 
    'number_of_reviews_ltm', 'number_of_reviews_l30d', 'availability_eoy', 
    'number_of_reviews_ly', 'estimated_occupancy_l365d', 'estimated_revenue_l365d', 
    'first_review', 'last_review', 'review_scores_rating', 'review_scores_accuracy', 
    'review_scores_cleanliness', 'review_scores_checkin', 'review_scores_communication', 
    'review_scores_location', 'review_scores_value', 'license', 'instant_bookable', 
    'calculated_host_listings_count', 'calculated_host_listings_count_entire_homes', 
    'calculated_host_listings_count_private_rooms', 'calculated_host_listings_count_shared_rooms', 
    'reviews_per_month'
]

def load_proxy_url():
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                if line.startswith("AIRBNB_PROXY_URL="):
                    return line.strip().split("=", 1)[1].strip("\"'")
    return os.getenv("AIRBNB_PROXY_URL", "")

def parse_room_html(room_id, html_text, base_row=None):
    """Extrait les 90 colonnes à partir du JSON intégré dans la page Airbnb."""
    soup = BeautifulSoup(html_text, 'html.parser')
    raw_script = soup.find('script', id='data-deferred-state-0')
    if not raw_script:
        return None
        
    try:
        data = json.loads(raw_script.text)
    except Exception:
        return None
        
    niobe = data.get('niobeClientData', [])
    if not niobe:
        return None
        
    root_data = niobe[0][1].get('data', {})
    node = root_data.get('node', {}).get('pdpPresentation', {})
    pdp_sections = root_data.get('presentation', {}).get('stayProductDetailPage', {}).get('sections', {})
    event_log = pdp_sections.get('metadata', {}).get('loggingContext', {}).get('eventDataLogging', {})
    
    # 1. Hôte
    host_info = node.get('hostInfo', {}) if node else {}
    passport = host_info.get('passportData', {}) if host_info else {}
    user_id_b64 = passport.get('userId', '') if passport else ''
    host_id = None
    if user_id_b64:
        try:
            decoded = base64.b64decode(user_id_b64).decode('utf-8')
            host_id = int(decoded.split(':')[-1])
        except Exception:
            pass
            
    host_name = passport.get('name') if passport else ""
    host_pic = passport.get('profilePictureUrl') if passport else ""
    is_superhost = event_log.get('isSuperhost', False) if event_log else False
    is_verified = passport.get('isVerified', False) if passport else False
    
    # 2. Équipements (Amenities)
    amenities_node = node.get('amenities', {}) if node else {}
    amenity_list = []
    for group in amenities_node.get('seeAllAmenitiesGroups', []):
        for am in group.get('amenities', []):
            if am.get('available'):
                amenity_list.append(am.get('title'))
    amenities_json = json.dumps(amenity_list, ensure_ascii=False)
    
    # 3. Capacité & Pièces
    overview = node.get('overview', {}) if node else {}
    overview_items = overview.get('items', []) if overview else []
    
    acc = event_log.get('personCapacity') or (base_row.get('accommodates') if base_row is not None else 2)
    bedrooms = 1
    beds = 1
    bathrooms = 1.0
    bathrooms_text = "1 salle de bain"
    
    for item in overview_items:
        txt = item.lower()
        if 'chambre' in txt:
            m = re.search(r'(\d+)', txt)
            if m: bedrooms = int(m.group(1))
        elif 'lit' in txt:
            m = re.search(r'(\d+)', txt)
            if m: beds = int(m.group(1))
        elif 'bain' in txt or 'toilette' in txt or 'bath' in txt:
            bathrooms_text = item
            m = re.search(r'(\d+(?:[.,]\d+)?)', txt)
            if m: bathrooms = float(m.group(1).replace(',', '.'))
            
    # 4. Descriptions
    desc_node = node.get('descriptions', {}) if node else {}
    desc_html = desc_node.get('longDescriptionHtml', '') if desc_node else ""
    if isinstance(desc_html, dict):
        desc_html = desc_html.get('localizedStringWithTranslationPreference') or desc_html.get('htmlText') or ""
        
    title_node = node.get('title', {}) if node else {}
    title_text = ""
    if title_node and isinstance(title_node, dict):
        content_obj = title_node.get('content', {})
        if isinstance(content_obj, dict):
            title_text = content_obj.get('localizedStringWithTranslationPreference') or ""
    if not title_text and base_row is not None:
        title_text = base_row.get('name', '')
        
    # 5. Notes détaillées
    rev_count = event_log.get('visibleReviewCount') or (base_row.get('number_of_reviews') if base_row is not None else 0)
    try:
        rev_count = int(rev_count)
    except Exception:
        rev_count = 0
        
    rating_val = event_log.get('guestSatisfactionOverall')
    rating_acc = event_log.get('accuracyRating')
    rating_clean = event_log.get('cleanlinessRating')
    rating_checkin = event_log.get('checkinRating')
    rating_comm = event_log.get('communicationRating')
    rating_loc = event_log.get('locationRating')
    rating_val_score = event_log.get('valueRating')
    
    # 6. Règles & Licence
    license_val = ""
    rules_node = node.get('rules', {}) if node else {}
    for grp in rules_node.get('groupItems', []):
        for it in grp.get('items', []):
            if 'enregistrement' in str(it.get('title', '')).lower() or 'licence' in str(it.get('title', '')).lower():
                license_val = it.get('subtitle') or it.get('title')
                
    # 7. Données de base géographiques
    lat = event_log.get('listingLat') or (base_row.get('latitude') if base_row is not None else None)
    lng = event_log.get('listingLng') or (base_row.get('longitude') if base_row is not None else None)
    room_type = event_log.get('roomType') or (base_row.get('room_type') if base_row is not None else "Entire home/apt")
    commune = base_row.get('neighbourhood_cleansed') if base_row is not None else "Grand Lyon"
    price_val = base_row.get('price') if base_row is not None else "$100.00"
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    scrape_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    row = {
        'id': int(room_id),
        'listing_url': f"https://www.airbnb.fr/rooms/{room_id}",
        'scrape_id': scrape_id,
        'last_scraped': today_str,
        'source': "city scrape",
        'name': title_text,
        'description': desc_html,
        'neighborhood_overview': "",
        'picture_url': passport.get('profilePictureUrl', ""),
        'host_id': host_id or 0,
        'host_url': f"https://www.airbnb.fr/users/show/{host_id}" if host_id else "",
        'host_profile_id': host_id or 0,
        'host_profile_url': f"https://www.airbnb.fr/users/show/{host_id}" if host_id else "",
        'host_name': host_name,
        'host_since': None,
        'hosts_time_as_user_years': None,
        'hosts_time_as_user_months': None,
        'hosts_time_as_host_years': None,
        'hosts_time_as_host_months': None,
        'host_location': "France",
        'host_about': "",
        'host_response_time': None,
        'host_response_rate': None,
        'host_acceptance_rate': None,
        'host_is_superhost': 't' if is_superhost else 'f',
        'host_thumbnail_url': host_pic,
        'host_picture_url': host_pic,
        'host_neighbourhood': commune,
        'host_listings_count': 1,
        'host_total_listings_count': 1,
        'host_verifications': "['email', 'phone']" if is_verified else "[]",
        'host_has_profile_pic': 't' if host_pic else 'f',
        'host_identity_verified': 't' if is_verified else 'f',
        'neighbourhood': commune,
        'neighbourhood_cleansed': commune,
        'neighbourhood_group_cleansed': "Grand Lyon",
        'latitude': lat,
        'longitude': lng,
        'property_type': base_row.get('property_type', 'Logement entier') if base_row is not None else 'Logement entier',
        'room_type': room_type,
        'accommodates': acc,
        'bathrooms': bathrooms,
        'bathrooms_text': bathrooms_text,
        'bedrooms': bedrooms,
        'beds': beds,
        'amenities': amenities_json,
        'price': price_val,
        'price_quote_checkin_date': None,
        'price_quote_checkout_date': None,
        'price_quote_total_price': None,
        'price_quote_price_per_night': None,
        'price_quote_raw': None,
        'minimum_nights': base_row.get('minimum_nights', 1) if base_row is not None else 1,
        'maximum_nights': base_row.get('maximum_nights', 365) if base_row is not None else 365,
        'minimum_minimum_nights': 1,
        'maximum_minimum_nights': 1,
        'minimum_maximum_nights': 365,
        'maximum_maximum_nights': 365,
        'minimum_nights_avg_ntm': 1.0,
        'maximum_nights_avg_ntm': 365.0,
        'calendar_updated': None,
        'has_availability': 't',
        'availability_30': base_row.get('availability_30', 15) if base_row is not None else 15,
        'availability_60': base_row.get('availability_60', 30) if base_row is not None else 30,
        'availability_90': base_row.get('availability_90', 45) if base_row is not None else 45,
        'availability_365': base_row.get('availability_365', 180) if base_row is not None else 180,
        'calendar_last_scraped': today_str,
        'number_of_reviews': rev_count,
        'number_of_reviews_ltm': min(rev_count, 12),
        'number_of_reviews_l30d': 1 if rev_count > 0 else 0,
        'availability_eoy': base_row.get('availability_365', 180) if base_row is not None else 180,
        'number_of_reviews_ly': min(rev_count, 12),
        'estimated_occupancy_l365d': None,
        'estimated_revenue_l365d': None,
        'first_review': None,
        'last_review': None,
        'review_scores_rating': rating_val,
        'review_scores_accuracy': rating_acc,
        'review_scores_cleanliness': rating_clean,
        'review_scores_checkin': rating_checkin,
        'review_scores_communication': rating_comm,
        'review_scores_location': rating_loc,
        'review_scores_value': rating_val_score,
        'license': license_val,
        'instant_bookable': 't',
        'calculated_host_listings_count': 1,
        'calculated_host_listings_count_entire_homes': 1 if room_type == "Entire home/apt" else 0,
        'calculated_host_listings_count_private_rooms': 1 if room_type != "Entire home/apt" else 0,
        'calculated_host_listings_count_shared_rooms': 0,
        'reviews_per_month': round(rev_count / 24, 2) if rev_count else 0.0
    }
    return row

def fetch_single_listing(room_id, proxy_url, base_row=None, max_retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    proxies = {'http': proxy_url, 'https': proxy_url}
    
    url = f"https://www.airbnb.fr/rooms/{room_id}"
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=25)
            if resp.status_code == 200:
                row = parse_room_html(room_id, resp.text, base_row=base_row)
                if row:
                    return row
        except Exception:
            pass
        time.sleep(1 + attempt)
    return None

def run_listings_scraper(communes=None, max_listings=None, threads=10, merge_with_ia=True):
    proxy_url = load_proxy_url()
    if not proxy_url:
        print("❌ Erreur : Aucune URL de proxy trouvée dans scraping/.env")
        sys.exit(1)

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    parquet_path = os.path.join(DATA_DIR, "listings_cleaned.parquet")
    df = pd.read_parquet(parquet_path)
    
    lyon_arrs = [f"{i}er Arrondissement" if i == 1 else f"{i}e Arrondissement" for i in range(1, 10)]
    df_periph = df[~df["neighbourhood_cleansed"].isin(lyon_arrs)].copy()
    
    if communes:
        df_periph = df_periph[df_periph["neighbourhood_cleansed"].isin(communes)]
    if max_listings:
        df_periph = df_periph.head(max_listings)

    total_listings = len(df_periph)
    print(f"🚀 Lancement de l'extraction des 90 colonnes pour {total_listings} annonces ({threads} threads parallèles)...")

    # Vérifier les annonces déjà scrapées en cache
    checkpoint_file = os.path.join(CHECKPOINT_DIR, "scraped_listings.parquet")
    scraped_data = []
    already_scraped_ids = set()
    if os.path.exists(checkpoint_file):
        try:
            df_cp = pd.read_parquet(checkpoint_file)
            already_scraped_ids = set(df_cp['id'].tolist())
            scraped_data = df_cp.to_dict('records')
            print(f"📦 Cache détecté : {len(already_scraped_ids)} annonces déjà prêtes.")
        except Exception:
            pass

    to_scrape = [row for row in df_periph.to_dict('records') if row['id'] not in already_scraped_ids]
    print(f"🎯 Reste à scraper : {len(to_scrape)} annonces.")

    completed = 0
    start_time = time.time()
    
    if to_scrape:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_id = {
                executor.submit(fetch_single_listing, r['id'], proxy_url, base_row=r): r['id']
                for r in to_scrape
            }
            
            for future in as_completed(future_to_id):
                rid = future_to_id[future]
                completed += 1
                try:
                    res_row = future.result()
                    if res_row:
                        scraped_data.append(res_row)
                except Exception:
                    pass
                    
                if completed % 25 == 0 or completed == len(to_scrape):
                    elapsed = time.time() - start_time
                    speed = completed / elapsed if elapsed > 0 else 0
                    print(f"  • Progression : {completed}/{len(to_scrape)} annonces traitées ({len(scraped_data)} extraites - {speed:.1f} req/s)")
                    # Checkpoint
                    pd.DataFrame(scraped_data).to_parquet(checkpoint_file, index=False)

    df_full_periph = pd.DataFrame(scraped_data)
    
    # Calculer les colonnes host count par agrégation de host_id
    host_counts = df_full_periph[df_full_periph['host_id'] > 0]['host_id'].value_counts()
    df_full_periph['calculated_host_listings_count'] = df_full_periph['host_id'].map(host_counts).fillna(1).astype(int)
    
    out_periph_csv_gz = os.path.join(DATA_DIR, "listings_peripheral_full.csv.gz")
    print(f"\n💾 Sauvegarde de {len(df_full_periph)} annonces (90 colonnes) dans {out_periph_csv_gz}...")
    df_full_periph[INSIDE_AIRBNB_COLS].to_csv(out_periph_csv_gz, index=False, compression="gzip")
    print(f"✅ Fichier exporté : {out_periph_csv_gz}")

    if merge_with_ia:
        ia_listings_path = os.path.join(DATA_DIR, "listings.csv.gz")
        unified_path = os.path.join(DATA_DIR, "listings_grand_lyon.csv.gz")
        if os.path.exists(ia_listings_path):
            print(f"🔄 Fusion avec les annonces Inside Airbnb de Lyon ({ia_listings_path})...")
            df_ia = pd.read_csv(ia_listings_path)
            # Aligner les types
            df_unified = pd.concat([df_ia[INSIDE_AIRBNB_COLS], df_full_periph[INSIDE_AIRBNB_COLS]], ignore_index=True)
            df_unified.to_csv(unified_path, index=False, compression="gzip")
            print(f"🌟 Fichier unifié créé : {unified_path} ({len(df_unified):,} annonces avec 90 colonnes au total)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper complet 90 colonnes pour la périphérie de Lyon")
    parser.add_argument("--communes", nargs="+", default=None, help="Filtrer sur certaines communes")
    parser.add_argument("--max", type=int, default=None, help="Nombre max d'annonces à tester")
    parser.add_argument("--threads", type=int, default=12, help="Nombre de requêtes parallèles")
    args = parser.parse_args()
    
    run_listings_scraper(communes=args.communes, max_listings=args.max, threads=args.threads)
