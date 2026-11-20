#!/usr/bin/env python3
"""
Pipeline Industriel Complet d'Extraction Airbnb (Grand Lyon) :
1. Génère neighbourhoods.csv et neighbourhoods.geojson (25 secteurs)
2. Scrape le calendrier 365 jours jour par jour -> calendar_grand_lyon.csv.gz
3. Scrape les 90 colonnes d'Inside Airbnb -> listings_grand_lyon.csv.gz
Le tout sécurisé via FlameProxies en rotation résidentielle.
"""

import sys
import argparse
import subprocess

def run_step(title, command):
    print("\n" + "=" * 60)
    print(f"🚀 ÉTAPE : {title}")
    print("=" * 60)
    res = subprocess.run(command, shell=True)
    if res.returncode != 0:
        print(f"❌ Erreur lors de l'exécution de : {command}")
        sys.exit(res.returncode)

def main():
    parser = argparse.ArgumentParser(description="Pipeline d'extraction industrielle Airbnb pour la Métropole de Lyon")
    parser.add_argument("--max", type=int, default=None, help="Nombre max d'annonces à traiter (pour tester)")
    parser.add_argument("--threads", type=int, default=12, help="Nombre de threads parallèles (défaut: 12)")
    parser.add_argument("--communes", nargs="+", default=None, help="Communes spécifiques à scraper")
    args = parser.parse_args()

    max_arg = f"--max {args.max}" if args.max else ""
    threads_arg = f"--threads {args.threads}"
    communes_arg = f"--communes {' '.join(args.communes)}" if args.communes else ""

    # 1. GeoJSON & CSV zonage
    run_step(
        "Génération des contours officiels (neighbourhoods.geojson & csv)",
        "./venv/bin/python scraping/export_geojson.py"
    )

    # 2. Calendrier 365 jours
    run_step(
        "Extraction du calendrier 365 jours journalier (calendar_grand_lyon.csv.gz)",
        f"./venv/bin/python scraping/fetch_full_calendars.py {threads_arg} {max_arg} {communes_arg}"
    )

    # 3. Fiches complètes 90 colonnes
    run_step(
        "Extraction des fiches complètes 90 colonnes (listings_grand_lyon.csv.gz)",
        f"./venv/bin/python scraping/fetch_full_listings.py {threads_arg} {max_arg} {communes_arg}"
    )

    print("\n" + "=" * 60)
    print("🎉 PIPELINE TERMINÉ AVEC SUCCÈS !")
    print("=" * 60)
    print("Les fichiers générés au format officiel Inside Airbnb sont disponibles dans le dossier data/ :")
    print("  • data/neighbourhoods.geojson       (25 secteurs officiels)")
    print("  • data/neighbourhoods.csv           (25 secteurs)")
    print("  • data/calendar_grand_lyon.csv.gz   (calendrier unifié 365j)")
    print("  • data/listings_grand_lyon.csv.gz   (90 colonnes unifiées)")

if __name__ == "__main__":
    main()
