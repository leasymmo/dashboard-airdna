#!/bin/bash
cd "$(dirname "$0")/.."

echo "=============================================================="
echo "    SCRAPING AIRBNB - GRAND LYON & MÉTROPOLE"
echo "=============================================================="
echo "1) Scraper TOUTES les communes périphériques (16 communes)"
echo "2) Scraper une ou plusieurs communes spécifiques"
echo "3) Fusionner uniquement les fichiers scraping/data/*_cleaned.csv"
echo "=============================================================="

read -p "Votre choix (1-3) [défaut: 1] : " choix
choix=${choix:-1}

case $choix in
  1)
    echo "Lancement du scraping complet sur l'ensemble de la métropole..."
    ./venv/bin/python scraping/scrape_villeurbanne.py
    ./venv/bin/python scraping/scrape_communes.py --communes all
    ./venv/bin/python scraping/merge_with_dashboard.py
    ;;
  2)
    echo "Communes disponibles : Bron, Caluire, Meyzieu, Genas, Chassieu, Decines, Vaulx, Rillieux, Saint-Priest, Venissieux, Saint-Fons, Francheville, Oullins, Tassin, Ecully"
    read -p "Nom(s) de la ou des commune(s) à scraper (séparés par un espace) : " comms
    ./venv/bin/python scraping/scrape_communes.py --communes $comms
    ./venv/bin/python scraping/merge_with_dashboard.py
    ;;
  3)
    ./venv/bin/python scraping/merge_with_dashboard.py
    ;;
  *)
    echo "Choix invalide."
    exit 1
    ;;
esac

echo ""
echo "✅ Opération terminée ! Les données sont prêtes et intégrées dans le Dashboard Streamlit."
