#!/usr/bin/env python3
"""
Script de fusion des données scrapées (Villeurbanne, Bron, Meyzieu, Caluire-et-Cuire...)
avec le jeu de données principal Inside Airbnb de Lyon (data/listings_cleaned.parquet).
Idempotent et capable d'intégrer automatiquement tous les fichiers scraping/data/*_cleaned.csv.
"""

import os
import glob
import shutil
import pandas as pd

MAIN_PARQUET = "data/listings_cleaned.parquet"
BACKUP_PARQUET = "data/listings_cleaned_backup_lyon_only.parquet"
DATA_DIR = "scraping/data"

def merge_datasets():
    if not os.path.exists(BACKUP_PARQUET) and not os.path.exists(MAIN_PARQUET):
        print(f"❌ Erreur : Aucun fichier source ({MAIN_PARQUET} ou {BACKUP_PARQUET}) n'a été trouvé.")
        return
        
    # 1. Sauvegarde initiale du fichier Lyon intramuros si non existante
    if not os.path.exists(BACKUP_PARQUET) and os.path.exists(MAIN_PARQUET):
        shutil.copyfile(MAIN_PARQUET, BACKUP_PARQUET)
        print(f"💾 Sauvegarde originale créée : {BACKUP_PARQUET}")
        
    # Toujours partir de la base propre Lyon intramuros pour garantir l'idempotence
    base_file = BACKUP_PARQUET if os.path.exists(BACKUP_PARQUET) else MAIN_PARQUET
    df_base = pd.read_parquet(base_file)
    print(f"📦 Base Lyon intramuros chargée : {len(df_base):,} annonces")
    
    # 2. Recherche de tous les fichiers de communes nettoyées
    csv_files = sorted(glob.glob(os.path.join(DATA_DIR, "*_cleaned.csv")))
    if not csv_files:
        print(f"❌ Aucun fichier '*_cleaned.csv' trouvé dans {DATA_DIR}.")
        return
        
    print(f"\n🔍 Fichiers de communes scrapées détectés ({len(csv_files)}) :")
    for f in csv_files:
        print(f"  • {os.path.basename(f)}")
        
    # 3. Chargement et déduplication
    existing_ids = set(df_base['id'])
    dfs_to_add = []
    
    for csv_file in csv_files:
        df_commune = pd.read_csv(csv_file)
        commune_name = df_commune['neighbourhood_cleansed'].iloc[0] if 'neighbourhood_cleansed' in df_commune.columns and len(df_commune) > 0 else os.path.basename(csv_file)
        
        # Filtre les annonces déjà présentes (ex: dans Lyon ou une autre commune limitrophe)
        df_unique = df_commune[~df_commune['id'].isin(existing_ids)]
        nb_unique = len(df_unique)
        print(f"  ➕ {commune_name} : {len(df_commune)} annonces lues | {nb_unique} nouvelles annonces uniques")
        
        if nb_unique > 0:
            dfs_to_add.append(df_unique)
            existing_ids.update(df_unique['id'])
            
    # 4. Concaténation globale
    if dfs_to_add:
        df_all_scraped = pd.concat(dfs_to_add, ignore_index=True)
        df_merged = pd.concat([df_base, df_all_scraped], ignore_index=True)
    else:
        df_merged = df_base
        
    # 5. Sauvegarde
    df_merged.to_parquet(MAIN_PARQUET, index=False)
    
    print("\n" + "=" * 70)
    print(f"✅ FUSION RÉUSSIE ! {MAIN_PARQUET} contient désormais {len(df_merged):,} annonces.")
    print("=" * 70)
    print("\n📊 Répartition complète par Secteur / Arrondissement / Commune :")
    breakdown = df_merged['neighbourhood_cleansed'].value_counts()
    for name, cnt in breakdown.items():
        print(f"  • {name:<25} : {cnt:>5,} annonces")
    print("=" * 70)

if __name__ == "__main__":
    merge_datasets()
