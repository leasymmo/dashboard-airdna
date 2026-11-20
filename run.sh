#!/bin/bash
cd "$(dirname "$0")"

# Vérification de l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    /usr/local/bin/python3.12 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install streamlit pandas numpy "plotly<6" folium streamlit-folium scikit-learn requests pyarrow
fi

# Téléchargement et traitement des données si nécessaire
if [ ! -f "data/listings_cleaned.parquet" ]; then
    echo "Préparation des données de Lyon depuis Inside Airbnb..."
    ./venv/bin/python download_data.py
    ./venv/bin/python process_data.py
fi

echo "Démarrage du Dashboard Conciergerie Lyon..."
./venv/bin/streamlit run app.py
