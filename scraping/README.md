# 🕷️ Module de Scraping Airbnb - Grand Lyon & Métropole

Ce module professionnel permet de collecter les données Airbnb pour l'ensemble des 25 secteurs du Grand Lyon (Lyon 1er à 9e + 16 communes périphériques de la Métropole) :

* **Villeurbanne**, **Caluire-et-Cuire**, **Vénissieux**, **Saint-Priest**, **Décines-Charpieu**, **Bron**, **Vaulx-en-Velin**, **Meyzieu**, **Tassin-la-Demi-Lune**, **Écully**, **Oullins**, **Rillieux-la-Pape**, **Genas**, **Saint-Fons**, **Chassieu**, **Francheville**.

---

## 🛡️ Architecture & Sécurité Anti-Ban (FlameProxies)

Le scraping intensif s'exécute à travers un **pool de proxies résidentiels rotatifs français** (configuré dans `scraping/.env`). 
- **Rotation par requête** : Chaque appel HTTP utilise une IP résidentielle différente (Orange, Free, SFR, Bouygues).
- **Zéro blocage WAF / Akamai** : Aucun risque de blocage d'IP ni de captcha.

---

## 📂 Nouveaux Outils Industriels (Standard Inside Airbnb)

Ce pipeline produit des fichiers **100 % conformes au schéma officiel d'Inside Airbnb** :

1. **`export_geojson.py`** :
   - Récupère les contours cadastraux officiels des 16 communes via l'API de l'IGN / gouvernement français (`geo.api.gouv.fr`).
   - Génère `data/neighbourhoods.geojson` (polygones des 25 secteurs) et `data/neighbourhoods.csv`.

2. **`fetch_full_calendars.py`** :
   - Extrait jour par jour les **365 jours de disponibilité et prix** via l'API `PdpAvailabilityCalendar` en multithreading.
   - Génère `data/calendar_peripheral.csv.gz` et fusionne avec Lyon -> `data/calendar_grand_lyon.csv.gz` (colonnes : `listing_id, date, available, minimum_nights, maximum_nights`).

3. **`fetch_full_listings.py`** :
   - Scrape les fiches détaillées complètes et extrait les **90 colonnes exactes** d'Inside Airbnb :
     - Identifiant unique hôte (`host_id`), nom, photo, biographie, ancienneté.
     - Les 6 sous-notes d'avis (`accuracy`, `cleanliness`, `checkin`, `communication`, `location`, `value`).
     - Liste complète des équipements (`amenities`) au format JSON.
     - Heures d'arrivée/départ, règlement intérieur, numéro d'enregistrement officiel (`license`).
   - Génère `data/listings_peripheral_full.csv.gz` et fusionne -> `data/listings_grand_lyon.csv.gz`.

4. **`run_full_extract.py`** :
   - Orchestrateur global exécutant les 3 étapes d'affilée de façon automatisée.

---

## 🚀 Commandes d'Exécution

### 1. Lancer le pipeline complet (Extraction industrielle)
```bash
# Pour scraper l'ensemble des communes avec 12 threads parallèles :
./venv/bin/python scraping/run_full_extract.py --threads 12

# Pour tester sur un échantillon (ex: 20 annonces) :
./venv/bin/python scraping/run_full_extract.py --max 20 --threads 4

# Pour cibler des communes spécifiques :
./venv/bin/python scraping/run_full_extract.py --communes Meyzieu Genas Décines-Charpieu
```

### 2. Lancer les scripts individuellement
```bash
# A. Mettre à jour les contours géographiques (25 secteurs)
./venv/bin/python scraping/export_geojson.py

# B. Extraire les calendriers 365 jours
./venv/bin/python scraping/fetch_full_calendars.py --threads 12

# C. Extraire les fiches complètes (90 colonnes)
./venv/bin/python scraping/fetch_full_listings.py --threads 12
```

---

## 📊 Fichiers Produits dans `data/`

| Fichier | Format | Description |
|:---|:---:|:---|
| **`neighbourhoods.geojson`** | GeoJSON | Contours vectoriels officiels des 25 secteurs du Grand Lyon. |
| **`neighbourhoods.csv`** | CSV | Liste des secteurs et groupements territoriaux. |
| **`calendar_grand_lyon.csv.gz`** | CSV.GZ | Calendrier 365 jours complet (3.3M+ lignes). |
| **`listings_grand_lyon.csv.gz`** | CSV.GZ | Fiches exhaustives avec les 90 colonnes d'Inside Airbnb. |
