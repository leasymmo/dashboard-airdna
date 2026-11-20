#!/usr/bin/env python3
"""
Scraper Airbnb multi-communes pour la Métropole de Lyon et sa périphérie.
Prend en charge : Bron, Meyzieu, Caluire-et-Cuire, Genas, Chassieu, Décines-Charpieu,
Vaulx-en-Velin, Rillieux-la-Pape, Saint-Priest, Vénissieux, Saint-Fons, Francheville,
Oullins, Tassin-la-Demi-Lune, Écully.
"""

import os
import re
import sys
import json
import time
import argparse
import unicodedata
import pandas as pd
import pyairbnb

def normalize_str(s):
    """Supprime les accents et met en minuscules pour faciliter la recherche."""
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

OUTPUT_DIR = "scraping/data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COMMUNE_CONFIGS = {
    "Bron": {
        "slug": "bron",
        "display_name": "Bron",
        "default_occ": 0.58,
        "keywords": ["bron"],
        "lat_bounds": (45.715, 45.765),
        "lon_bounds": (4.880, 4.945),
        "sectors": [
            {
                "name": "Bron Centre / Église / Hôtel de Ville",
                "ne_lat": 45.748, "ne_long": 4.925,
                "sw_lat": 45.730, "sw_long": 4.895
            },
            {
                "name": "Bron Nord (Les Genêts / Terraillon / Fort)",
                "ne_lat": 45.760, "ne_long": 4.938,
                "sw_lat": 45.740, "sw_long": 4.890
            },
            {
                "name": "Bron Sud (Parilly / Univ Lyon 2 / Hôpitaux)",
                "ne_lat": 45.735, "ne_long": 4.930,
                "sw_lat": 45.715, "sw_long": 4.882
            }
        ]
    },
    "Caluire-et-Cuire": {
        "slug": "caluire",
        "display_name": "Caluire-et-Cuire",
        "default_occ": 0.60,
        "keywords": ["caluire", "cuire"],
        "lat_bounds": (45.775, 45.830),
        "lon_bounds": (4.820, 4.880),
        "sectors": [
            {
                "name": "Caluire Ouest (Cuire / Vassieux / Le Bourg)",
                "ne_lat": 45.810, "ne_long": 4.850,
                "sw_lat": 45.778, "sw_long": 4.825
            },
            {
                "name": "Caluire Est (Saint-Clair / Bissardon)",
                "ne_lat": 45.800, "ne_long": 4.870,
                "sw_lat": 45.775, "sw_long": 4.845
            },
            {
                "name": "Caluire Nord (Montessuy / Vernay / Crépieux)",
                "ne_lat": 45.828, "ne_long": 4.875,
                "sw_lat": 45.800, "sw_long": 4.835
            }
        ]
    },
    "Meyzieu": {
        "slug": "meyzieu",
        "display_name": "Meyzieu",
        "default_occ": 0.55,
        "keywords": ["meyzieu"],
        "lat_bounds": (45.738, 45.805),
        "lon_bounds": (4.970, 5.050),
        "sectors": [
            {
                "name": "Meyzieu Ouest (Gare / Centre / Tram T3)",
                "ne_lat": 45.780, "ne_long": 5.015,
                "sw_lat": 45.750, "sw_long": 4.970
            },
            {
                "name": "Meyzieu Est (Grand Large / Mathiolan)",
                "ne_lat": 45.800, "ne_long": 5.045,
                "sw_lat": 45.765, "sw_long": 5.000
            },
            {
                "name": "Meyzieu Sud (ZI / Peyssilieu)",
                "ne_lat": 45.760, "ne_long": 5.040,
                "sw_lat": 45.738, "sw_long": 4.980
            }
        ]
    },
    "Genas": {
        "slug": "genas",
        "display_name": "Genas",
        "default_occ": 0.55,
        "keywords": ["genas"],
        "lat_bounds": (45.710, 45.755),
        "lon_bounds": (5.000, 5.080),
        "sectors": [
            {
                "name": "Genas Centre / Vurey / Azieu",
                "ne_lat": 45.750, "ne_long": 5.070,
                "sw_lat": 45.715, "sw_long": 5.000
            }
        ]
    },
    "Chassieu": {
        "slug": "chassieu",
        "display_name": "Chassieu",
        "default_occ": 0.58,
        "keywords": ["chassieu"],
        "lat_bounds": (45.720, 45.765),
        "lon_bounds": (4.945, 5.015),
        "sectors": [
            {
                "name": "Chassieu Centre / Eurexpo / Sept Chemins",
                "ne_lat": 45.760, "ne_long": 5.010,
                "sw_lat": 45.725, "sw_long": 4.950
            }
        ]
    },
    "Décines-Charpieu": {
        "slug": "decines",
        "display_name": "Décines-Charpieu",
        "default_occ": 0.58,
        "keywords": ["décines", "decines", "charpieu"],
        "lat_bounds": (45.750, 45.790),
        "lon_bounds": (4.935, 5.000),
        "sectors": [
            {
                "name": "Décines Centre / Tram T3 / Mairie",
                "ne_lat": 45.775, "ne_long": 4.975,
                "sw_lat": 45.750, "sw_long": 4.935
            },
            {
                "name": "Décines Grand Large / Groupama Stadium / OL Vallée",
                "ne_lat": 45.790, "ne_long": 5.000,
                "sw_lat": 45.765, "sw_long": 4.965
            }
        ]
    },
    "Vaulx-en-Velin": {
        "slug": "vaulx_en_velin",
        "display_name": "Vaulx-en-Velin",
        "default_occ": 0.55,
        "keywords": ["vaulx-en-velin", "vaulx en velin", "vaulx"],
        "lat_bounds": (45.750, 45.805),
        "lon_bounds": (4.900, 4.965),
        "sectors": [
            {
                "name": "Vaulx Sud (La Soie / Carré de Soie)",
                "ne_lat": 45.775, "ne_long": 4.945,
                "sw_lat": 45.750, "sw_long": 4.905
            },
            {
                "name": "Vaulx Centre / Village / Grappinière",
                "ne_lat": 45.805, "ne_long": 4.965,
                "sw_lat": 45.770, "sw_long": 4.900
            }
        ]
    },
    "Rillieux-la-Pape": {
        "slug": "rillieux",
        "display_name": "Rillieux-la-Pape",
        "default_occ": 0.56,
        "keywords": ["rillieux-la-pape", "rillieux la pape", "rillieux"],
        "lat_bounds": (45.800, 45.845),
        "lon_bounds": (4.870, 4.940),
        "sectors": [
            {
                "name": "Rillieux Ville Nouvelle / Crépieux Est",
                "ne_lat": 45.825, "ne_long": 4.915,
                "sw_lat": 45.800, "sw_long": 4.870
            },
            {
                "name": "Rillieux Village / Osterode / Vancia",
                "ne_lat": 45.845, "ne_long": 4.940,
                "sw_lat": 45.820, "sw_long": 4.890
            }
        ]
    },
    "Saint-Priest": {
        "slug": "saint_priest",
        "display_name": "Saint-Priest",
        "default_occ": 0.57,
        "keywords": ["saint-priest", "saint priest", "st priest", "st-priest"],
        "lat_bounds": (45.670, 45.730),
        "lon_bounds": (4.900, 4.990),
        "sectors": [
            {
                "name": "Saint-Priest Centre / Gare / Manissieux",
                "ne_lat": 45.715, "ne_long": 4.990,
                "sw_lat": 45.680, "sw_long": 4.935
            },
            {
                "name": "Saint-Priest Porte des Alpes / Parc Tech",
                "ne_lat": 45.730, "ne_long": 4.950,
                "sw_lat": 45.695, "sw_long": 4.900
            }
        ]
    },
    "Vénissieux": {
        "slug": "venissieux",
        "display_name": "Vénissieux",
        "default_occ": 0.58,
        "keywords": ["vénissieux", "venissieux"],
        "lat_bounds": (45.680, 45.730),
        "lon_bounds": (4.850, 4.915),
        "sectors": [
            {
                "name": "Vénissieux Nord (Gare / Parilly)",
                "ne_lat": 45.730, "ne_long": 4.910,
                "sw_lat": 45.705, "sw_long": 4.860
            },
            {
                "name": "Vénissieux Sud (Minguettes / Charréard)",
                "ne_lat": 45.710, "ne_long": 4.915,
                "sw_lat": 45.680, "sw_long": 4.850
            }
        ]
    },
    "Saint-Fons": {
        "slug": "saint_fons",
        "display_name": "Saint-Fons",
        "default_occ": 0.56,
        "keywords": ["saint-fons", "saint fons", "st fons", "st-fons"],
        "lat_bounds": (45.690, 45.725),
        "lon_bounds": (4.835, 4.880),
        "sectors": [
            {
                "name": "Saint-Fons Centre / Gare / Clochettes",
                "ne_lat": 45.725, "ne_long": 4.880,
                "sw_lat": 45.690, "sw_long": 4.835
            }
        ]
    },
    "Francheville": {
        "slug": "francheville",
        "display_name": "Francheville",
        "default_occ": 0.58,
        "keywords": ["francheville"],
        "lat_bounds": (45.720, 45.760),
        "lon_bounds": (4.740, 4.795),
        "sectors": [
            {
                "name": "Francheville le Haut / le Bas / Châter",
                "ne_lat": 45.760, "ne_long": 4.795,
                "sw_lat": 45.720, "sw_long": 4.740
            }
        ]
    },
    "Oullins": {
        "slug": "oullins",
        "display_name": "Oullins",
        "default_occ": 0.60,
        "keywords": ["oullins", "pierre-bénite", "pierre bénite", "pierre benite", "oullin"],
        "lat_bounds": (45.695, 45.735),
        "lon_bounds": (4.785, 4.835),
        "sectors": [
            {
                "name": "Oullins Centre / Métro B / La Saulaie",
                "ne_lat": 45.735, "ne_long": 4.830,
                "sw_lat": 45.710, "sw_long": 4.790
            },
            {
                "name": "Oullins Sud / Pierre-Bénite / Hôpital Lyon Sud",
                "ne_lat": 45.715, "ne_long": 4.835,
                "sw_lat": 45.695, "sw_long": 4.785
            }
        ]
    },
    "Tassin-la-Demi-Lune": {
        "slug": "tassin",
        "display_name": "Tassin-la-Demi-Lune",
        "default_occ": 0.62,
        "keywords": ["tassin-la-demi-lune", "tassin la demi lune", "tassin"],
        "lat_bounds": (45.748, 45.782),
        "lon_bounds": (4.748, 4.805),
        "sectors": [
            {
                "name": "Tassin Centre / Horloge / Gare",
                "ne_lat": 45.770, "ne_long": 4.795,
                "sw_lat": 45.748, "sw_long": 4.750
            },
            {
                "name": "Tassin Nord / Alai / Trois Renards",
                "ne_lat": 45.782, "ne_long": 4.805,
                "sw_lat": 45.760, "sw_long": 4.760
            }
        ]
    },
    "Écully": {
        "slug": "ecully",
        "display_name": "Écully",
        "default_occ": 0.62,
        "keywords": ["ecully", "écully"],
        "lat_bounds": (45.765, 45.805),
        "lon_bounds": (4.755, 4.815),
        "sectors": [
            {
                "name": "Écully Centre / Le Pérollier",
                "ne_lat": 45.790, "ne_long": 4.795,
                "sw_lat": 45.765, "sw_long": 4.755
            },
            {
                "name": "Écully Grandes Écoles / Centrale / Nord",
                "ne_lat": 45.805, "ne_long": 4.815,
                "sw_lat": 45.775, "sw_long": 4.770
            }
        ]
    }
}

def extract_nightly_price(item):
    """Extrait le prix par nuitée à partir des données tarifaires Airbnb."""
    price_data = item.get('price', {})
    for b in price_data.get('break_down', []):
        desc = b.get('description', '')
        m = re.search(r'x\s*([\d\s,]+)\s*€', desc)
        if m:
            val = m.group(1).replace(' ', '').replace('\xa0', '').replace(',', '.')
            try:
                return float(val)
            except ValueError:
                pass
    unit = price_data.get('unit', {})
    amount = unit.get('amount', 0)
    if amount and amount > 0:
        return float(amount)
    return None

def extract_room_type(title_str, name_str):
    """Déduit le type d'hébergement Airbnb."""
    text = f"{title_str} {name_str}".lower()
    if 'chambre privée' in text or 'private room' in text or 'chambre chez' in text:
        return "Private room"
    elif 'chambre partagée' in text or 'shared room' in text:
        return "Shared room"
    elif 'hôtel' in text or 'hotel' in text:
        return "Hotel room"
    return "Entire home/apt"

def extract_property_type(title_str):
    """Extrait le type de bien (ex: Appartement, Maison, Loft, Studio)."""
    if '⋅' in title_str:
        return title_str.split('⋅')[0].strip()
    elif '·' in title_str:
        return title_str.split('·')[0].strip()
    return "Appartement"

def extract_capacity(title_str, name_str, room_type):
    """Déduit la capacité d'accueil, le nombre de chambres et de lits."""
    text = f"{title_str} {name_str}".lower()
    acc = 2
    bed = 1.0
    
    # Capacité voyageurs
    m_acc = re.search(r'(\d+)\s*(?:personnes|voyageurs|pers\b|guests|p\b)', text)
    if m_acc:
        try:
            acc = int(m_acc.group(1))
        except ValueError:
            pass
    elif 't1' in text or 'studio' in text:
        acc = 2
    elif 't2' in text:
        acc = 4
    elif 't3' in text:
        acc = 6
    elif 't4' in text or 'maison' in text:
        acc = 8
    elif room_type == 'Private room':
        acc = 2
        
    # Nombre de chambres
    m_bed = re.search(r'(\d+)\s*(?:chambres?|ch\b|bed\b|bedrooms?)', text)
    if m_bed:
        try:
            bed = float(m_bed.group(1))
        except ValueError:
            pass
    elif 'studio' in text or 't1' in text:
        bed = 1.0
    elif 't2' in text:
        bed = 1.0
    elif 't3' in text:
        bed = 2.0
    elif 't4' in text:
        bed = 3.0
    elif acc >= 6:
        bed = 2.0
        
    m_lits = re.search(r'(\d+)\s*(?:lits?|beds?)', text)
    beds = float(m_lits.group(1)) if m_lits else max(1.0, round(acc / 2))
    
    return min(max(acc, 1), 16), max(1.0, bed), beds

def is_item_in_commune(item, cfg, all_configs):
    """Vérifie si l'annonce appartient bien à la commune ciblée."""
    coords = item.get('coordinates', {})
    lat = coords.get('latitude')
    lon = coords.get('longitud')
    
    if lat is None or lon is None:
        return False
        
    min_lat, max_lat = cfg['lat_bounds']
    min_lon, max_lon = cfg['lon_bounds']
    if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
        return False
        
    title = item.get('title', '').lower()
    name = item.get('name', '').lower()
    full_text = f"{title} {name}"
    
    city_in_title = ""
    if '⋅' in item.get('title', ''):
        city_in_title = item.get('title', '').split('⋅')[-1].strip().lower()
    elif '·' in item.get('title', ''):
        city_in_title = item.get('title', '').split('·')[-1].strip().lower()
        
    # 1. Correspondance exacte sur les mots-clés de la commune
    for kw in cfg['keywords']:
        if kw in city_in_title:
            return True
            
    # 2. Rejet si une autre commune connue est explicitement mentionnée dans le titre
    other_kws = ["lyon", "1er", "2e", "3e", "4e", "5e", "6e", "7e", "8e", "9e", "arrondissement",
                 "villeurbanne", "sainte-foy", "saint-cyr", "collonges", "champagne", "charbonnières",
                 "craponne", "la mulatière", "saint-genis-laval", "mions", "corbas", "feyzin"]
    for other_commune, other_cfg in all_configs.items():
        if other_commune != cfg['display_name']:
            other_kws.extend(other_cfg['keywords'])
            
    if any(okw in city_in_title for okw in other_kws):
        return False
        
    # 3. Mention de la commune dans le titre/nom
    for kw in cfg['keywords']:
        if kw in full_text:
            return True
            
    # 4. Coordonnées valides et aucune mention de ville concurrente
    return True

def scrape_commune(commune_name, config, all_configs, check_in="2026-10-15", check_out="2026-10-17"):
    print("=" * 70)
    print(f"🚀 SCRAPING AIRBNB - COMMUNE DE {config['display_name'].upper()}")
    print("=" * 70)
    
    sectors = config['sectors']
    all_raw_items = []
    seen_ids = set()
    
    for i, sec in enumerate(sectors, 1):
        print(f"\n[{i}/{len(sectors)}] Scan du secteur : {sec['name']}...")
        try:
            res = pyairbnb.search_all(
                check_in=check_in,
                check_out=check_out,
                ne_lat=sec['ne_lat'],
                ne_long=sec['ne_long'],
                sw_lat=sec['sw_lat'],
                sw_long=sec['sw_long'],
                zoom_value=14,
                price_min=10,
                price_max=1000,
                currency="EUR",
                language="fr"
            )
            
            nb_new = 0
            for item in res:
                rid = item.get('room_id')
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    all_raw_items.append(item)
                    nb_new += 1
                    
            print(f"  -> {len(res)} annonces scannées | {nb_new} nouveaux logements uniques ajoutés.")
            time.sleep(1.2)
        except Exception as e:
            print(f"  ⚠️ Erreur sur le secteur {sec['name']} : {e}")
            
    print("\n" + "-" * 70)
    print(f"Total annonces brutes collectées dans la zone : {len(all_raw_items)}")
    
    raw_path = os.path.join(OUTPUT_DIR, f"{config['slug']}_raw.json")
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(all_raw_items, f, ensure_ascii=False, indent=2)
    print(f"📁 Données brutes sauvegardées : {raw_path}")
    
    rows = []
    est_occ = config['default_occ']
    
    for it in all_raw_items:
        if not is_item_in_commune(it, config, all_configs):
            continue
            
        rid = it.get('room_id')
        coords = it.get('coordinates', {})
        lat = coords.get('latitude')
        lon = coords.get('longitud')
        
        p = extract_nightly_price(it)
        rating_obj = it.get('rating', {})
        rating_val = float(rating_obj.get('value', 0)) if rating_obj.get('value') else None
        nb_reviews = int(rating_obj.get('reviewCount', 0)) if rating_obj.get('reviewCount') else 0
        
        title = it.get('title', '')
        name = it.get('name', '')
        prop_type = extract_property_type(title)
        room_type = extract_room_type(title, name)
        acc, bedrooms, beds = extract_capacity(title, name, room_type)
        
        badges = it.get('badges', [])
        primary_line = ""
        structured = it.get('structuredContent', {})
        if structured and structured.get('primaryLine'):
            primary_line = " ".join([m.get('body', '') for m in structured.get('primaryLine', [])])
            
        is_pro = 'professionnel' in primary_line.lower()
        is_superhost = 'SUPERHOST' in [b.upper() for b in badges] or 'Superhôte' in primary_line
        
        monthly_rev = (p * est_occ * 30.5) if p else None
        annual_rev = (monthly_rev * 12) if monthly_rev else None
        revpar = (p * est_occ) if p else None
        
        row = {
            'id': rid,
            'listing_url': f"https://www.airbnb.fr/rooms/{rid}",
            'name': name,
            'host_id': 0,
            'host_url': "",
            'host_name': f"Hôte {config['display_name']}",
            'host_since': None,
            'host_response_time': None,
            'host_response_rate': None,
            'host_is_superhost': 't' if is_superhost else 'f',
            'is_superhost': is_superhost,
            'host_listings_count': 5 if is_pro else 1,
            'host_total_listings_count': 5 if is_pro else 1,
            'neighbourhood_cleansed': config['display_name'],
            'latitude': lat,
            'longitude': lon,
            'property_type': prop_type,
            'room_type': room_type,
            'accommodates': acc,
            'bathrooms': 1.0,
            'bathrooms_clean': 1.0,
            'bathrooms_text': "1 salle de bain",
            'bedrooms': bedrooms,
            'beds': beds,
            'amenities': "[]",
            'price': f"${p:.2f}" if p else "",
            'price_clean': p,
            'minimum_nights': 2,
            'maximum_nights': 365,
            'has_availability': 't',
            'availability_30': 15,
            'availability_60': 30,
            'availability_90': 45,
            'availability_365': 180,
            'is_active': True,
            'number_of_reviews': nb_reviews,
            'number_of_reviews_ltm': min(nb_reviews, 12),
            'number_of_reviews_l30d': 1,
            'first_review': None,
            'last_review': None,
            'review_scores_rating': rating_val if (rating_val and rating_val > 0) else None,
            'review_scores_accuracy': rating_val if (rating_val and rating_val > 0) else None,
            'review_scores_cleanliness': rating_val if (rating_val and rating_val > 0) else None,
            'review_scores_checkin': rating_val if (rating_val and rating_val > 0) else None,
            'review_scores_communication': rating_val if (rating_val and rating_val > 0) else None,
            'review_scores_location': rating_val if (rating_val and rating_val > 0) else None,
            'review_scores_value': rating_val if (rating_val and rating_val > 0) else None,
            'license': "",
            'has_license': False,
            'calculated_host_listings_count': 5 if is_pro else 1,
            'calculated_host_listings_count_entire_homes': 4 if is_pro else 1,
            'calculated_host_listings_count_private_rooms': 0,
            'reviews_per_month': round(nb_reviews / 24, 2) if nb_reviews else 0.0,
            'host_segment': "Petite conciergerie / Pro (6-20 biens)" if is_pro else "Particulier (1 bien)",
            'stay_type': "Court séjour (1-2 nuits)",
            'estimated_occupancy_rate': est_occ,
            'estimated_monthly_rev': monthly_rev,
            'estimated_annual_rev': annual_rev,
            'revpar': revpar,
            'price_per_guest': (p / acc) if (p and acc) else None,
            'has_wifi': True,
            'has_kitchen': room_type == "Entire home/apt",
            'has_washer': True,
            'has_air_conditioning': any(w in name.lower() or w in title.lower() for w in ['clim', 'climatisation', 'climatisé', 'ac']),
            'has_workspace': True,
            'has_elevator': 'ascenseur' in name.lower() or 'ascenseur' in title.lower()
        }
        rows.append(row)
        
    df_clean = pd.DataFrame(rows)
    csv_path = os.path.join(OUTPUT_DIR, f"{config['slug']}_cleaned.csv")
    df_clean.to_csv(csv_path, index=False)
    
    print(f"📊 Fichier prêt à l'emploi : {csv_path} ({len(df_clean)} annonces retenues)")
    if len(df_clean) > 0:
        print(f"📈 Indicateurs clés pour {config['display_name']} :")
        print(f"  • Prix moyen constaté (ADR) : {df_clean['price_clean'].mean():.1f} € / nuit")
        print(f"  • Prix médian constaté       : {df_clean['price_clean'].median():.0f} € / nuit")
        print(f"  • Note moyenne voyageurs     : {df_clean['review_scores_rating'].mean():.2f} / 5")
        print(f"  • Logements entiers          : {(df_clean['room_type'] == 'Entire home/apt').mean()*100:.1f} %")
        print(f"  • Part de gestionnaires pros : {(df_clean['host_segment'] != 'Particulier (1 bien)').mean()*100:.1f} %")
    return df_clean

def main():
    parser = argparse.ArgumentParser(description="Scraper Airbnb pour les communes de la Métropole de Lyon")
    parser.add_argument("--communes", nargs="+", default=["all"], help="Communes à scraper : all ou noms séparés par des espaces")
    args = parser.parse_args()
    
    to_scrape = []
    if "all" in args.communes or "ALL" in args.communes:
        to_scrape = list(COMMUNE_CONFIGS.keys())
    else:
        for c in args.communes:
            norm_c = normalize_str(c)
            matched = False
            for k in COMMUNE_CONFIGS:
                if norm_c in normalize_str(k) or any(norm_c in normalize_str(kw) for kw in COMMUNE_CONFIGS[k]['keywords']):
                    if k not in to_scrape:
                        to_scrape.append(k)
                    matched = True
                    break
            if not matched:
                print(f"⚠️ Commune non reconnue : {c}")
                
    print(f"🎯 Communes sélectionnées pour le scraping ({len(to_scrape)}) : {to_scrape}")
    
    results = {}
    for comm in to_scrape:
        cfg = COMMUNE_CONFIGS[comm]
        df = scrape_commune(comm, cfg, COMMUNE_CONFIGS)
        results[comm] = df
        time.sleep(1.5)  # Pause entre chaque commune
        
    print("\n" + "=" * 70)
    print("🎉 SCRAPING TERMINÉ POUR TOUTES LES COMMUNES DEMANDÉES !")
    for comm, df in results.items():
        print(f"  • {comm:<20} : {len(df):>4} annonces nettoyées et enregistrées.")
    print("=" * 70)

if __name__ == "__main__":
    main()
