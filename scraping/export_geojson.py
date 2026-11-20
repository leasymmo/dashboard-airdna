#!/usr/bin/env python3
"""
Générateur des fichiers officiels de zonage géographique de la Métropole de Lyon :
- neighbourhoods.csv
- neighbourhoods.geojson
Combine les 9 arrondissements de Lyon (Inside Airbnb) avec les 16 communes périphériques.
"""

import json
import os
import requests
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

COMMUNES_MAPPING = {
    "69266": "Villeurbanne",
    "69029": "Bron",
    "69034": "Caluire-et-Cuire",
    "69271": "Chassieu",
    "69275": "Décines-Charpieu",
    "69081": "Écully",
    "69089": "Francheville",
    "69277": "Genas",
    "69282": "Meyzieu",
    "69149": "Oullins",
    "69286": "Rillieux-la-Pape",
    "69199": "Saint-Fons",
    "69290": "Saint-Priest",
    "69244": "Tassin-la-Demi-Lune",
    "69256": "Vaulx-en-Velin",
    "69259": "Vénissieux"
}

def generate_grand_lyon_geo():
    orig_geojson_path = os.path.join(DATA_DIR, "neighbourhoods.geojson")
    with open(orig_geojson_path, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
        
    existing_sectors = [feat["properties"].get("neighbourhood") for feat in geojson_data["features"]]
    print(f"📦 Secteurs d'origine dans neighbourhoods.geojson : {len(existing_sectors)}")
    
    # Récupération des polygones officiels via l'API du gouvernement français
    print("🌍 Téléchargement des contours géographiques officiels des 16 communes périphériques...")
    for code, name in COMMUNES_MAPPING.items():
        if name in existing_sectors:
            print(f"  • {name} déjà présent, ignoré.")
            continue
            
        url = f"https://geo.api.gouv.fr/communes/{code}?fields=nom,code&geometry=contour&format=geojson"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            feat = resp.json()
            # Standardisation des propriétés au format Inside Airbnb
            geom_type = feat.get("geometry", {}).get("type")
            coords = feat.get("geometry", {}).get("coordinates")
            
            # Inside Airbnb utilise souvent MultiPolygon
            if geom_type == "Polygon":
                coords = [coords]
                geom_type = "MultiPolygon"
                
            standardized_feature = {
                "type": "Feature",
                "geometry": {
                    "type": geom_type,
                    "coordinates": coords
                },
                "properties": {
                    "neighbourhood": name,
                    "neighbourhood_group": "Grand Lyon Est" if name in ["Genas", "Meyzieu", "Chassieu", "Décines-Charpieu", "Saint-Priest", "Bron", "Vaulx-en-Velin"] else (
                        "Grand Lyon Nord" if name in ["Caluire-et-Cuire", "Rillieux-la-Pape"] else (
                            "Grand Lyon Ouest" if name in ["Tassin-la-Demi-Lune", "Écully", "Francheville"] else "Grand Lyon Sud"
                        )
                    )
                }
            }
            geojson_data["features"].append(standardized_feature)
            print(f"  ✅ {name} ajouté ({geom_type})")
        else:
            print(f"  ⚠️ Erreur pour {name} (code {code}) : status {resp.status_code}")
            
    # Export neighbourhoods.geojson
    out_geojson_path = os.path.join(DATA_DIR, "neighbourhoods.geojson")
    with open(out_geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=2)
    print(f"\n📁 Fichier GeoJSON mis à jour : {out_geojson_path} ({len(geojson_data['features'])} secteurs)")
    
    # Export neighbourhoods.csv
    rows = []
    for feat in geojson_data["features"]:
        p = feat["properties"]
        rows.append({
            "neighbourhood_group": p.get("neighbourhood_group", ""),
            "neighbourhood": p.get("neighbourhood")
        })
    df_neigh = pd.DataFrame(rows).sort_values("neighbourhood")
    out_csv_path = os.path.join(DATA_DIR, "neighbourhoods.csv")
    df_neigh.to_csv(out_csv_path, index=False)
    print(f"📁 Fichier CSV mis à jour : {out_csv_path} ({len(df_neigh)} lignes)")

if __name__ == "__main__":
    generate_grand_lyon_geo()
