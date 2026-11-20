# 🏙️ Lyon Short-Term Rental Intelligence - Dashboard Conciergerie

Tableau de bord d'analyse de marché et de veille concurrentielle développé spécifiquement pour une **société de conciergerie et de gestion locative courte durée (Airbnb)** à Lyon.

L'outil exploite directement les données ouvertes d'**Inside Airbnb** (annonces détaillées, disponibilités, calendrier prévisionnel sur 12 mois, profils des hôtes et avis).

---

## 🚀 Démarrage Rapide

Pour lancer le dashboard sur votre machine :

```bash
./run.sh
```

Ou manuellement :

```bash
./venv/bin/streamlit run app.py
```

Le tableau de bord s'ouvrira automatiquement à l'adresse [http://localhost:8501](http://localhost:8501).

---

## 📊 Fonctionnalités Métier Développées

Le dashboard a été conçu sur-mesure pour répondre aux besoins opérationnels et stratégiques d'une conciergerie :

### 1. 📊 Vue d'Ensemble & Marché
* **Indicateurs financiers clés (KPIs) :**
  * **ADR (Average Daily Rate)** : Prix moyen par nuitée constaté.
  * **Prix Médian** : Pour neutraliser les valeurs extrêmes des biens de grand luxe.
  * **Taux d'occupation estimé** : Basé sur le modèle Inside Airbnb / San Francisco Model (nombre d'avis lissés).
  * **RevPAR (Revenue Per Available Room)** : Revenu moyen généré par nuitée disponible.
  * **Revenu mensuel et annuel moyen** estimé par logement.
* **Typologie du parc :** Répartition par type de bien (logement entier, chambre), capacité d'accueil et politique de durée minimale de séjour (court séjour vs bail mobilité 30+ nuits).
* **Conformité réglementaire :** Suivi du taux d'annonces disposant d'un numéro d'enregistrement officiel délivré par la Ville de Lyon.

### 2. 🗺️ Cartographie & Analyse par Arrondissement
* **Carte interactive (Mapbox / Scatter)** : Visualisation de chaque bien sur la métropole lyonnaise, avec code couleur selon le prix par nuit et taille proportionnelle à la capacité d'accueil.
* **Benchmark comparatif des 9 arrondissements** : Classement par prix moyen, taux d'occupation, et revenu mensuel moyen (du 1er au 9e arrondissement).

### 3. 🏢 Concurrence & Intelligence Conciergerie
* **Top Gestionnaires & Conciergeries de Lyon** : Classement en temps réel des plus gros acteurs du marché local (ex. Hosting Services, Agence Cocoonr, La Nuitée, Checkmyguest, WeHost...).
* **Structure du marché** : Part des monopropriétaires (particuliers louant occasionnellement) vs professionnels / conciergeries (multi-annonces).
* **Impact du badge Superhost** : Comparaison chiffrée de la prime tarifaire et du gain d'occupation apportés par le statut Superhost.
* **Module Prospection Conciergerie** : Filtre automatisé détectant les annonces actives ayant des notes de propreté ou de communication fragiles (< 4.7/5) = cibles prioritaires pour proposer vos services de conciergerie !

### 4. 📅 Calendrier, Disponibilités & Saisonnalité
* **Exploitation de 3,3 millions de dates** du calendrier Inside Airbnb sur 12 mois.
* Suivi de la courbe d'occupation mois par mois pour anticiper les temps forts (ex: **Fête des Lumières en décembre**, salons professionnels à Eurexpo, tourisme estival).
* Recommandations tarifaires saisonnières pour maximiser le RevPAR.

### 5. 💡 Simulateur de Prix & Proposition de Mandat
* **Outil commercial d'estimation en rendez-vous propriétaire :**
  * Paramètres : Arrondissement, type de bien, nombre de chambres/salles de bain, capacité d'accueil, équipements (clim, ascenseur, espace télétravail), niveau de prestation visé.
  * Estimation instantanée : Prix par nuit recommandé (ADR basse/moyenne/haute saison), taux d'occupation réaliste.
  * Calculateur de mandat : Chiffre d'affaires brut estimé, commission conciergerie réglable (15% à 30%), et revenu net pour le propriétaire.
  * Affichage des 5 meilleurs comparables directs dans le même quartier.

### 6. 📋 Explorateur d'Annonces & Export CSV
* Table complète avec moteur de recherche textuel (titre, hôte).
* Bouton d'export CSV pour retraiter les données sous Excel ou votre CRM.

---

## 🔄 Mise à Jour des Données Inside Airbnb

Inside Airbnb publie de nouveaux relevés périodiques (trimestriels). Pour mettre à jour les données :

1. Modifiez l'URL de la date dans `download_data.py` (ou relancez le script avec la dernière date disponible).
2. Exécutez :
   ```bash
   ./venv/bin/python download_data.py
   ./venv/bin/python process_data.py
   ```
3. Les données seront automatiquement converties au format Parquet ultra-rapide et rechargées dans Streamlit.
