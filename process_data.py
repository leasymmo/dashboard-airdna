import os
import re
import pandas as pd
import numpy as np

print("--- Starting Data Processing for Lyon Conciergerie Dashboard ---")

# Specific columns we need
COLS = [
    'id', 'listing_url', 'name', 'host_id', 'host_url', 'host_name',
    'host_since', 'host_response_time', 'host_response_rate',
    'host_is_superhost', 'host_listings_count', 'host_total_listings_count',
    'neighbourhood_cleansed', 'latitude', 'longitude',
    'property_type', 'room_type', 'accommodates', 'bathrooms',
    'bathrooms_text', 'bedrooms', 'beds', 'amenities', 'price',
    'minimum_nights', 'maximum_nights', 'has_availability',
    'availability_30', 'availability_60', 'availability_90', 'availability_365',
    'number_of_reviews', 'number_of_reviews_ltm', 'number_of_reviews_l30d',
    'first_review', 'last_review', 'review_scores_rating',
    'review_scores_accuracy', 'review_scores_cleanliness',
    'review_scores_checkin', 'review_scores_communication',
    'review_scores_location', 'review_scores_value', 'license',
    'calculated_host_listings_count',
    'calculated_host_listings_count_entire_homes',
    'calculated_host_listings_count_private_rooms',
    'reviews_per_month'
]

print("Reading listings.csv.gz with selected columns...")
df = pd.read_csv('data/listings.csv.gz', usecols=COLS)
print(f"Loaded {len(df):,} listings.")

# Clean price ($120.00 -> 120.0)
df['price_clean'] = (
    df['price']
    .astype(str)
    .str.replace('$', '', regex=False)
    .str.replace(',', '', regex=False)
    .str.strip()
)
df['price_clean'] = pd.to_numeric(df['price_clean'], errors='coerce')

# Parse bathrooms from bathrooms_text if bathrooms is null
def extract_bathrooms(row):
    if pd.notna(row['bathrooms']):
        return float(row['bathrooms'])
    text = str(row['bathrooms_text']).lower()
    match = re.search(r'(\d+(\.\d+)?)', text)
    if match:
        return float(match.group(1))
    if 'half-bath' in text or 'shared' in text:
        return 0.5
    return 1.0

df['bathrooms_clean'] = df.apply(extract_bathrooms, axis=1)

# Superhost boolean
df['is_superhost'] = df['host_is_superhost'].astype(str).str.lower().isin(['t', 'true', '1'])

# Active status
df['is_active'] = df['availability_365'] > 0

# Host category for Conciergerie analysis
def get_host_type(count):
    if pd.isna(count) or count <= 1:
        return "Particulier (1 bien)"
    elif count <= 5:
        return "Multi-propriétaire (2-5 biens)"
    elif count <= 20:
        return "Petite conciergerie / Pro (6-20 biens)"
    else:
        return "Grande conciergerie / Agence (21+ biens)"

df['host_segment'] = df['calculated_host_listings_count'].apply(get_host_type)

# Policy length category
def get_stay_type(nights):
    if pd.isna(nights) or nights <= 2:
        return "Court séjour (1-2 nuits)"
    elif nights <= 6:
        return "Moyen séjour (3-6 nuits)"
    elif nights <= 29:
        return "Semaine / Quinzaine (7-29 nuits)"
    else:
        return "Mois / Bail mobilité (30+ nuits)"

df['stay_type'] = df['minimum_nights'].apply(get_stay_type)

# License status (French regulation)
df['has_license'] = df['license'].notna() & (df['license'].str.strip() != '') & (df['license'].str.lower() != 'exempt')

# Estimated Occupancy Rate (Modèle C : Synthèse hybride Avis proratisés min 15j + Calendrier 30/60j)
df['first_review_dt'] = pd.to_datetime(df['first_review'], errors='coerce')
scrape_ref_date = pd.to_datetime('2026-09-17')
age_days = (scrape_ref_date - df['first_review_dt']).dt.days
eff_days = age_days.fillna(365.0).clip(lower=15.0, upper=365.0)

# Modèle A (Avis proratisés sur ancienneté réelle avec plancher de 15 jours)
mod_a = (df['number_of_reviews_ltm'].fillna(0) / 0.5 * 3.0) / eff_days

# Modèle B (Remplissage réel calendrier 30 & 60 jours avec uplift lead time)
occ_30 = (1.0 - (df['availability_30'].fillna(30) / 30.0)).clip(lower=0.0, upper=1.0)
occ_60 = (1.0 - (df['availability_60'].fillna(60) / 60.0)).clip(lower=0.0, upper=1.0)
mod_b = (occ_30 * 1.25 + occ_60 * 1.5) / 2.0

# Modèle C (Synthèse hybride moyenne de A et B plafonnée à 95% pour les annonces actives)
mod_c = ((mod_a + mod_b) / 2.0).clip(lower=0.0, upper=0.95)

# Taux final : 0 si inactif ou 0 dispo 365
df['estimated_occupancy_rate'] = np.where(
    df['is_active'] & (df['availability_365'] > 0),
    mod_c,
    0.0
)
df.drop(columns=['first_review_dt'], inplace=True)

# For active listings, calculate financial KPIs
df['estimated_monthly_rev'] = np.where(
    df['is_active'] & df['price_clean'].notna(),
    df['price_clean'] * df['estimated_occupancy_rate'] * 30.5,
    np.nan
)
df['estimated_annual_rev'] = df['estimated_monthly_rev'] * 12
df['revpar'] = np.where(
    df['is_active'] & df['price_clean'].notna(),
    df['price_clean'] * df['estimated_occupancy_rate'],
    np.nan
)
df['price_per_guest'] = df['price_clean'] / df['accommodates'].clip(lower=1)

# Key amenities flags
amenities_str = df['amenities'].fillna('').astype(str).str.lower()
df['has_wifi'] = amenities_str.str.contains('wifi')
df['has_kitchen'] = amenities_str.str.contains('kitchen|cuisine')
df['has_washer'] = amenities_str.str.contains('washer|lave-linge')
df['has_air_conditioning'] = amenities_str.str.contains('air conditioning|climatisation')
df['has_workspace'] = amenities_str.str.contains('workspace|bureau')
df['has_elevator'] = amenities_str.str.contains('elevator|ascenseur')
df['has_parking'] = amenities_str.str.contains('parking|garage')
df['has_balcony'] = amenities_str.str.contains('balcony|balcon|terrasse|patio')
df['has_baby_crib'] = amenities_str.str.contains('crib|lit bébé|lit pour bébé')
df['has_dishwasher'] = amenities_str.str.contains('dishwasher|lave-vaisselle')
df['has_coffee_machine'] = amenities_str.str.contains('coffee|nespresso|cafeti')
df['has_tv'] = amenities_str.str.contains('tv|télévision')
df['has_self_checkin'] = amenities_str.str.contains('self check-in|serrure connectée|boîte à clé|lockbox')
df['has_bathtub'] = amenities_str.str.contains('bathtub|baignoire')

print("Saving cleaned listings to data/listings_cleaned.parquet...")
df.to_parquet('data/listings_cleaned.parquet', index=False)
print("Done saving listings.")

# Pre-aggregate calendar data & build calendar parquet
print("Processing calendar data for seasonality...")
import duckdb

con = duckdb.connect()
src_csv = 'data/calendar_grand_lyon.csv.gz' if os.path.exists('data/calendar_grand_lyon.csv.gz') else 'data/calendar.csv.gz'

print(f"Converting {src_csv} to data/calendar.parquet...")
con.execute(f"""
    COPY (
        SELECT listing_id, date, available = 't' as is_available, strftime(date, '%Y-%m') as month
        FROM read_csv_auto('{src_csv}')
    ) TO 'data/calendar.parquet' (FORMAT PARQUET, COMPRESSION 'ZSTD');
""")

calendar_monthly = con.execute("""
    SELECT 
        month,
        COUNT(*) as total_days,
        SUM(CASE WHEN is_available THEN 1 ELSE 0 END) as available_days,
        SUM(CASE WHEN NOT is_available THEN 1 ELSE 0 END) as booked_days,
        ROUND(SUM(CASE WHEN NOT is_available THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as occupancy_rate
    FROM 'data/calendar.parquet'
    GROUP BY month
    ORDER BY month
""").df()

calendar_monthly.to_parquet('data/calendar_monthly.parquet', index=False)
print("Saved calendar_monthly.parquet:")
print(calendar_monthly)

print("--- All Data Preprocessing Complete! ---")
