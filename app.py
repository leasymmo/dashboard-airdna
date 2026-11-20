import os
import re
import json
import hashlib
import urllib.parse
import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
import duckdb
import importlib
import mandate_generator
importlib.reload(mandate_generator)
from mandate_generator import generate_mandate_pdf, generate_mandate_html

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Lyon Airbnb Market Intelligence | Conciergerie",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 1rem;
    }
    .kpi-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 0.3rem;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #10B981;
        margin-top: 0.2rem;
        font-weight: 500;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #F1F5F9;
        border-radius: 8px 8px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF5A5F !important;
        color: white !important;
    }
    .modal-chip {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .chip-superhost {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FDE68A;
    }
    .chip-segment {
        background-color: #EFF6FF;
        color: #1E40AF;
        border: 1px solid #DBEAFE;
    }
    .chip-license {
        background-color: #ECFDF5;
        color: #065F46;
        border: 1px solid #A7F3D0;
    }
    .score-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- AUTHENTICATION & SESSION PERSISTENCE ---
def check_authentication():
    """Gère l'authentification des associés avec session persistante lors des rafraîchissements."""
    # Vérification d'une demande explicite de déconnexion
    if st.query_params.get("logout") == "1":
        st.query_params.clear()
        st.session_state["authenticated"] = False
        st.rerun()

    # 1. Mot de passe configuré (via variable d'environnement, secrets Streamlit, ou valeur par défaut)
    configured_pwd = os.environ.get("CONCIERGERIE_PASSWORD")
    if not configured_pwd:
        try:
            configured_pwd = st.secrets.get("CONCIERGERIE_PASSWORD", "lyon2026")
        except Exception:
            configured_pwd = "lyon2026"

    # Sel cryptographique pour générer un jeton de session sécurisé et non réversible
    auth_salt = "lyon_conciergerie_secret_salt_2026"
    valid_token = hashlib.sha256(f"{configured_pwd}_{auth_salt}".encode("utf-8")).hexdigest()

    # Vérification du jeton persistant dans l'URL (survit aux rafraîchissements F5 / Cmd+R)
    url_token = st.query_params.get("auth")
    if url_token == valid_token:
        st.session_state["authenticated"] = True
        return True

    # Vérification en session state
    if st.session_state.get("authenticated", False):
        st.query_params["auth"] = valid_token
        return True

    # Utilisateur non authentifié : affichage de l'écran d'accès sécurisé
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_box, _ = st.columns([1, 1.4, 1])
    with col_box:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 25px; padding: 25px 20px 10px 20px; background: white; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                <div style="font-size: 42px; margin-bottom: 5px;">🏙️</div>
                <h2 style="color: #FF5A5F; margin: 0; font-size: 26px; font-weight: 700;">Espace Associés Conciergerie</h2>
                <h4 style="color: #1E293B; margin-top: 6px; font-size: 15px; font-weight: 600;">Market Intelligence & Rentabilité Lyon</h4>
                <p style="color: #64748B; font-size: 13px; margin-top: 4px;">Accès restreint. Veuillez saisir le mot de passe associé pour consulter les analyses et le simulateur.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.form("login_form"):
            entered_pwd = st.text_input("Mot de passe associé :", type="password", placeholder="Saisissez le mot de passe...")
            submit_btn = st.form_submit_button("Accéder au Dashboard 🔓", width="stretch")

            if submit_btn:
                if entered_pwd == configured_pwd:
                    st.session_state["authenticated"] = True
                    st.query_params["auth"] = valid_token
                    st.success("Connexion réussie ! Chargement...")
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect. Veuillez vérifier auprès de vos associés.")

        st.caption("🔒 Votre session est mémorisée : vous n'aurez pas besoin de ressaisir le mot de passe lors de vos actualisations.")

    return False

if not check_authentication():
    st.stop()

# --- INJECT LOGOUT BUTTON INTO stMainMenuPopover ---
_logout_script = """
(function() {
    function injectLogoutItem() {
        const menuList = document.querySelector(
            '[data-testid="stMainMenuList"], [data-testid="stMainMenuPopover"] ul, div[data-baseweb="popover"] ul, ul[role="menu"]'
        );
        if (!menuList) return;
        if (menuList.querySelector('#custom-logout-menu-item')) return;

        const divider = document.createElement('div');
        divider.className = 'custom-logout-divider';
        divider.setAttribute('role', 'separator');
        divider.style.height = '1px';
        divider.style.backgroundColor = '#E2E8F0';
        divider.style.margin = '4px 0';

        const li = document.createElement('li');
        li.id = 'custom-logout-menu-item';
        li.setAttribute('role', 'menuitem');
        li.setAttribute('tabindex', '0');
        li.setAttribute('data-testid', 'stMainMenuItem-logout');
        li.style.display = 'flex';
        li.style.alignItems = 'center';
        li.style.gap = '10px';
        li.style.padding = '10px 16px';
        li.style.cursor = 'pointer';
        li.style.color = '#DC2626';
        li.style.fontWeight = '600';
        li.style.fontSize = '14px';
        li.style.transition = 'background-color 0.15s ease';
        li.style.borderRadius = '4px';
        li.style.margin = '2px 4px';
        li.innerHTML = '<span style="font-size: 15px;">🔒</span><span>Déconnexion</span>';

        li.onmouseenter = function() { li.style.backgroundColor = '#FEE2E2'; };
        li.onmouseleave = function() { li.style.backgroundColor = 'transparent'; };

        li.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            const url = new URL(window.location.href);
            url.search = '?logout=1';
            window.location.href = url.toString();
        };

        menuList.appendChild(divider);
        menuList.appendChild(li);
    }

    // Observer pour détecter l'apparition du menu des 3 petits points
    const observer = new MutationObserver(function() {
        injectLogoutItem();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Listener direct sur le bouton des 3 petits points (stMainMenu)
    function attachMenuListener() {
        const btn = document.querySelector('[data-testid="stMainMenuButton"], [data-testid="stMainMenu"] button, [data-testid="stMainMenuPopover"] button, [data-testid="stMainMenu"]');
        if (btn && !btn._hasLogoutObserver) {
            btn._hasLogoutObserver = true;
            btn.addEventListener('click', function() {
                setTimeout(injectLogoutItem, 20);
                setTimeout(injectLogoutItem, 60);
                setTimeout(injectLogoutItem, 150);
                setTimeout(injectLogoutItem, 300);
            });
        }
    }
    attachMenuListener();
    setInterval(attachMenuListener, 500);
    injectLogoutItem();
})();
"""
_encoded_js = urllib.parse.quote(_logout_script)
_html_payload = (
    '<img src="x" style="display:none;" onerror="'
    'if(!window._logoutInjected){window._logoutInjected=true;'
    'var s=document.createElement(\'script\');'
    's.textContent=decodeURIComponent(\'' + _encoded_js + '\');'
    'document.head.appendChild(s);'
    '}">'
)
st.html(_html_payload, unsafe_allow_javascript=True)

# --- DATA CACHING ---
@st.cache_data(show_spinner="Chargement des données de Lyon...")
def load_data():
    listings_path = "data/listings_cleaned.parquet"
    calendar_path = "data/calendar_monthly.parquet"
    
    if not os.path.exists(listings_path):
        st.error("Les données n'ont pas encore été préparées. Veuillez exécuter 'python process_data.py'.")
        st.stop()
        
    df_listings = pd.read_parquet(listings_path)
    df_cal_market = pd.read_parquet(calendar_path) if os.path.exists(calendar_path) else pd.DataFrame()
    
    # Ensure all required amenity boolean columns exist
    amenity_keywords = {
        'has_wifi': 'wifi',
        'has_kitchen': 'kitchen|cuisine',
        'has_washer': 'washer|lave-linge',
        'has_air_conditioning': 'air conditioning|climatisation',
        'has_workspace': 'workspace|bureau',
        'has_elevator': 'elevator|ascenseur',
        'has_parking': 'parking|garage',
        'has_balcony': 'balcony|balcon|terrasse|patio',
        'has_baby_crib': 'crib|lit bébé|lit pour bébé',
        'has_dishwasher': 'dishwasher|lave-vaisselle',
        'has_coffee_machine': 'coffee|nespresso|cafeti',
        'has_tv': 'tv|télévision',
        'has_self_checkin': 'self check-in|serrure connectée|boîte à clé|lockbox',
        'has_bathtub': 'bathtub|baignoire'
    }
    if 'amenities' in df_listings.columns:
        am_str = df_listings['amenities'].fillna('').astype(str).str.lower()
        for col_name, kw in amenity_keywords.items():
            if col_name not in df_listings.columns:
                df_listings[col_name] = am_str.str.contains(kw)
                
    return df_listings, df_cal_market

df_raw, df_calendar_market = load_data()

@st.cache_data(show_spinner=False)
def query_calendar_forecast(listing_ids_tuple):
    if not listing_ids_tuple or not os.path.exists('data/calendar.parquet'):
        return pd.DataFrame()
    con = duckdb.connect()
    con.register('df_ids', pd.DataFrame({'listing_id': list(listing_ids_tuple)}))
    query = """
        SELECT 
            c.month,
            COUNT(*) as total_days,
            SUM(CASE WHEN c.is_available THEN 1 ELSE 0 END) as available_days,
            SUM(CASE WHEN NOT c.is_available THEN 1 ELSE 0 END) as booked_days,
            ROUND(SUM(CASE WHEN NOT c.is_available THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as occupancy_rate
        FROM 'data/calendar.parquet' c
        JOIN df_ids ids ON c.listing_id = ids.listing_id
        WHERE c.month <= '2027-09'
        GROUP BY c.month
        ORDER BY c.month
    """
    res = con.execute(query).df()
    con.close()
    return res

# --- SIDEBAR FILTERS ---
if os.path.exists("assets/airbnb_logo.svg"):
    st.sidebar.image("assets/airbnb_logo.svg", width=140)
else:
    st.sidebar.markdown("<h2 style='color: #FF5A5F; margin: 0;'>airbnb</h2>", unsafe_allow_html=True)
st.sidebar.title("Filtres Marché")

st.sidebar.markdown("---")
st.sidebar.markdown("##### 📍 Localisation & Logement")

# Arrondissement / Commune filter
arrondissements = sorted(df_raw['neighbourhood_cleansed'].dropna().unique())
selected_arrs = st.sidebar.multiselect(
    "Secteurs / Communes (Lyon & Métropole)",
    options=arrondissements,
    default=arrondissements
)

# Room type filter
room_types = sorted(df_raw['room_type'].dropna().unique())
selected_room_types = st.sidebar.multiselect(
    "Type d'hébergement",
    options=room_types,
    default=["Entire home/apt"] if "Entire home/apt" in room_types else room_types
)

# Accommodates filter
min_acc, max_acc = int(df_raw['accommodates'].min()), int(df_raw['accommodates'].max())
selected_acc = st.sidebar.slider(
    "Capacité d'accueil (voyageurs)",
    min_value=1,
    max_value=min(max_acc, 16),
    value=(1, 4)
)

# Bedrooms filter
selected_bedrooms = st.sidebar.slider(
    "Nombre de chambres",
    min_value=0,
    max_value=6,
    value=(0, 1),
    help="0 = Studio. Sélectionnez 6 pour 6 chambres et plus."
)

# Équipements requis
amenity_map = {
    "📶 Wifi": "has_wifi",
    "❄️ Climatisation": "has_air_conditioning",
    "🍳 Cuisine équipée": "has_kitchen",
    "🧺 Lave-linge": "has_washer",
    "🛗 Ascenseur": "has_elevator",
    "💻 Espace de travail dédié": "has_workspace",
    "🅿️ Parking": "has_parking",
    "🌿 Balcon / Terrasse": "has_balcony",
    "👶 Lit bébé / Bébé": "has_baby_crib",
    "🍽️ Lave-vaisselle": "has_dishwasher",
    "☕ Machine à café / Nespresso": "has_coffee_machine",
    "📺 Télévision": "has_tv",
    "🔑 Arrivée autonome": "has_self_checkin",
    "🛁 Baignoire": "has_bathtub"
}
selected_amenities = st.sidebar.multiselect(
    "Équipements requis",
    options=list(amenity_map.keys()),
    default=[],
    help="Sélectionnez un ou plusieurs équipements. Seules les annonces proposant TOUS les équipements sélectionnés seront affichées."
)

st.sidebar.markdown("---")
st.sidebar.markdown("##### 💰 Tarifs & Activité")

# Active status
only_active = st.sidebar.checkbox("Annonces actives uniquement (disponibles > 0 j)", value=True)

# Price range filter
valid_prices = df_raw['price_clean'].dropna()
p_min = int(valid_prices.min())
p_max = int(min(valid_prices.quantile(0.99), 500))
selected_price_range = st.sidebar.slider(
    "Fourchette de prix par nuit (€)",
    min_value=10,
    max_value=p_max,
    value=(10, p_max)
)

# Durée de séjour min/max (fourchette)
selected_stay_range = st.sidebar.slider(
    "Durée de séjour min/max (nuits)",
    min_value=1,
    max_value=30,
    value=(1, 30),
    help="Filtre sur le nombre de nuits minimum imposé par l'annonceur. Réglez sur 30 pour inclure les séjours de 30 nuits et plus."
)

# Taux d'occupation minimum
min_occupancy = st.sidebar.slider(
    "Taux d'occupation minimum (%)",
    min_value=0,
    max_value=90,
    value=0,
    step=5,
    help="0% = Tous les logements. Filtre sur le taux d'occupation estimé du logement."
)

st.sidebar.markdown("---")
st.sidebar.markdown("##### ⭐ Qualité & Réglementation")

# Superhost filter
superhost_filter = st.sidebar.radio(
    "Statut Superhost",
    options=["Tous", "Superhosts uniquement", "Hôtes standards"]
)

# Host segment filter (multiselect)
host_segment_order = [
    "Particulier (1 bien)",
    "Multi-propriétaire (2-5 biens)",
    "Petite conciergerie / Pro (6-20 biens)",
    "Grande conciergerie / Agence (21+ biens)"
]
host_segments = [s for s in host_segment_order if s in df_raw['host_segment'].unique()]
for s in sorted(df_raw['host_segment'].dropna().unique()):
    if s not in host_segments:
        host_segments.append(s)

selected_segments = st.sidebar.multiselect(
    "Type de gestionnaire",
    options=host_segments,
    default=host_segments,
    help="Sélectionnez un ou plusieurs types de gestionnaires (particuliers, multi-propriétaires, conciergeries pro)"
)

# Legal license filter
license_filter = st.sidebar.radio(
    "Immatriculation légale en mairie",
    options=["Toutes les annonces", "Immatriculées uniquement", "Non déclarées / En cours"],
    help="À Lyon, les meublés de tourisme doivent obligatoirement être enregistrés auprès de la Ville"
)

# Minimum reviews filter (Nombre minimum de commentaires)
min_reviews = st.sidebar.slider(
    "Nombre minimum de commentaires",
    min_value=0,
    max_value=50,
    value=1,
    step=1,
    help="0 = Tous les logements. Réglez sur 1 ou plus pour exclure les logements sans avis."
)

# Rating filter (Note Airbnb)
min_rating = st.sidebar.slider(
    "Note minimale Airbnb (⭐)",
    min_value=0.0,
    max_value=5.0,
    value=0.0,
    step=0.1,
    help="0.0 = Toutes les annonces. Choisissez par exemple 4.5 pour afficher uniquement les logements ayant au moins 4.5 / 5 étoiles."
)

# --- FILTERING LOGIC ---
mask = (
    df_raw['neighbourhood_cleansed'].isin(selected_arrs) &
    df_raw['room_type'].isin(selected_room_types) &
    (df_raw['accommodates'] >= selected_acc[0]) &
    (df_raw['accommodates'] <= selected_acc[1])
)

# Bedrooms filter
if selected_bedrooms[0] > 0 or selected_bedrooms[1] < 6:
    if selected_bedrooms[1] >= 6:
        mask &= (df_raw['bedrooms'] >= selected_bedrooms[0]) | (df_raw['bedrooms'].isna())
    else:
        mask &= (df_raw['bedrooms'] >= selected_bedrooms[0]) & (df_raw['bedrooms'] <= selected_bedrooms[1])

# Amenities filter
for eq in selected_amenities:
    col = amenity_map.get(eq)
    if col:
        if col not in df_raw.columns and 'amenities' in df_raw.columns:
            kw = eq.split(' ', 1)[-1].lower()
            df_raw[col] = df_raw['amenities'].fillna('').astype(str).str.lower().str.contains(kw)
        if col in df_raw.columns:
            mask &= (df_raw[col] == True)

# Tarifs & Activité filters
if only_active:
    mask &= df_raw['is_active']

# Price mask
mask &= (
    df_raw['price_clean'].isna() | 
    ((df_raw['price_clean'] >= selected_price_range[0]) & (df_raw['price_clean'] <= selected_price_range[1]))
)

# Stay range filter
if selected_stay_range[1] < 30:
    mask &= (df_raw['minimum_nights'] >= selected_stay_range[0]) & (df_raw['minimum_nights'] <= selected_stay_range[1])
else:
    if selected_stay_range[0] > 1:
        mask &= (df_raw['minimum_nights'] >= selected_stay_range[0])

# Minimum occupancy rate filter
if min_occupancy > 0:
    mask &= (df_raw['estimated_occupancy_rate'] >= (min_occupancy / 100.0))

# Qualité & Réglementation filters
if superhost_filter == "Superhosts uniquement":
    mask &= df_raw['is_superhost']
elif superhost_filter == "Hôtes standards":
    mask &= ~df_raw['is_superhost']

if len(selected_segments) < len(host_segments):
    mask &= df_raw['host_segment'].isin(selected_segments)

if license_filter == "Immatriculées uniquement":
    mask &= (df_raw['has_license'] == True)
elif license_filter == "Non déclarées / En cours":
    mask &= (df_raw['has_license'] == False)

# Minimum reviews filter
if min_reviews > 0:
    mask &= (df_raw['number_of_reviews'] >= min_reviews)

# Rating mask (Note Airbnb)
if min_rating > 0.0:
    mask &= (df_raw['review_scores_rating'] >= min_rating)

df = df_raw[mask].copy()

# --- RECUPERATION AUTOMATIQUE DE LA PHOTO PRINCIPALE (EN MEMOIRE) ---
@st.cache_data(ttl=86400, show_spinner=False)
def get_listing_image_bytes(listing_id, stored_url=None):
    """Télécharge et optimise l'image principale en mémoire (bytes) pour un affichage local instantané,
    évitant tout blocage CORS/CDN ou timeout du navigateur."""
    candidate_url = None
    if stored_url and pd.notna(stored_url):
        s_url = str(stored_url).strip()
        if s_url.startswith('http') and s_url.lower() != 'nan':
            candidate_url = s_url
            
    # Si pas d'URL stockée ou si vide, aller chercher sur Airbnb
    if not candidate_url:
        try:
            url = f"https://www.airbnb.fr/rooms/{listing_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'fr-FR,fr;q=0.9'
            }
            resp = requests.get(url, headers=headers, timeout=3)
            if resp.status_code == 200:
                m_og = re.search(r'<meta property="og:image" content="([^"]+)"', resp.text)
                if m_og:
                    candidate_url = m_og.group(1).replace('&amp;', '&')
                else:
                    m_mus = re.findall(r'https://[a-zA-Z0-9\._/-]+\.muscache\.com/pictures/[a-zA-Z0-9_/-]+\.(?:jpg|jpeg|png|webp)', resp.text)
                    if m_mus:
                        candidate_url = m_mus[0]
        except Exception:
            pass
            
    if not candidate_url:
        return None
        
    # Optimisation Airbnb CDN (convertir original 6 Mo en webp/jpg 720px ~60 Ko)
    fetch_url = candidate_url
    if '/pictures/' in fetch_url:
        fetch_url = fetch_url.replace('/pictures/', '/im/pictures/')
    if 'im_w' not in fetch_url:
        fetch_url += ('&' if '?' in fetch_url else '?') + 'im_w=720'
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        r = requests.get(fetch_url, headers=headers, timeout=4)
        if r.status_code == 200 and len(r.content) > 1000:
            return r.content
        if fetch_url != candidate_url:
            r2 = requests.get(candidate_url, headers=headers, timeout=4)
            if r2.status_code == 200 and len(r2.content) > 1000:
                return r2.content
    except Exception:
        pass
        
    return None

# --- FICHE COMPLETE DU LOGEMENT (MODALE INTERACTIVE) ---
@st.dialog("📋 Fiche Complète du Logement", width="large")
def show_listing_modal(listing_id):
    try:
        match = df_raw[df_raw['id'] == int(listing_id)]
    except Exception:
        match = df_raw[df_raw['id'] == listing_id]
        
    if match.empty:
        st.error(f"Détails de l'annonce introuvables pour l'identifiant {listing_id}.")
        return
        
    row = match.iloc[0]
    
    # Title & Sector
    st.markdown(f"### {row['name']}")
    st.markdown(f"📍 **{row.get('neighbourhood_cleansed', 'Lyon')}** &nbsp;•&nbsp; 🏠 **{row.get('room_type', 'Hébergement')}** *({row.get('property_type', 'Logement')})* &nbsp;•&nbsp; ID Airbnb: `{row['id']}`")
    
    col_img, col_info = st.columns([1.1, 1.4])
    
    with col_img:
        pic_data = get_listing_image_bytes(row['id'], row.get('picture_url'))
        if pic_data:
            st.image(pic_data, width="stretch")
        else:
            st.info("📷 Aucune photo disponible")
            
        listing_url = row.get('listing_url')
        if pd.notna(listing_url) and str(listing_url).startswith('http'):
            st.link_button("🌐 Voir l'annonce en direct sur Airbnb", str(listing_url), width="stretch", type="primary")
            
    with col_info:
        is_sh = bool(row.get('is_superhost'))
        badge_sh = "⭐ Superhôte" if is_sh else "👤 Hôte Standard"
        seg = row.get('host_segment', 'Standard')
        lic = row.get('license')
        has_lic = pd.notna(lic) and str(lic).strip() != '' and str(lic).lower() != 'nan'
        lic_txt = f"📜 N° légal : <code>{lic}</code>" if has_lic else "⚠️ *Non immatriculé / En cours*"
        
        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <span class="modal-chip chip-superhost">{badge_sh}</span>
            <span class="modal-chip chip-segment">🏢 {seg}</span>
            <div style="margin-top: 6px; font-size: 0.85rem; color: #475569;">{lic_txt}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown(f"• 👥 **Capacité d'accueil :** **{int(row.get('accommodates', 1))} voyageurs**")
        ch_cnt = int(row.get('bedrooms', 1)) if pd.notna(row.get('bedrooms')) else 1
        bed_cnt = int(row.get('beds', 1)) if pd.notna(row.get('beds')) else 1
        st.markdown(f"• 🛏️ **Chambres & Lits :** {ch_cnt} chambre(s) &nbsp;|&nbsp; {bed_cnt} lit(s)")
        b_clean = row.get('bathrooms_clean', 1)
        b_clean_str = f"{b_clean:.1f}".rstrip('0').rstrip('.') if pd.notna(b_clean) else "1"
        b_txt = row.get('bathrooms_text', '')
        b_txt_str = f" *({b_txt})*" if pd.notna(b_txt) and b_txt else ""
        st.markdown(f"• 🚿 **Salles de bain :** {b_clean_str} sdb{b_txt_str}")
        st.markdown(f"• ⏱️ **Séjour min / max :** {int(row.get('minimum_nights', 1))} à {int(row.get('maximum_nights', 365))} nuits *({row.get('stay_type', 'Court séjour')})*")
        st.markdown(f"• 📅 **Disponibilité :** {int(row.get('availability_30', 0))} j / 30 &nbsp;|&nbsp; {int(row.get('availability_365', 0))} j / an")

    st.markdown("---")
    st.markdown("#### 💰 Performance Financière & Tarification Estimée")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prix par nuit (ADR)", f"{row.get('price_clean', 0):.0f} €")
    occ_val = row.get('estimated_occupancy_rate', 0)
    occ_pct = (occ_val * 100) if pd.notna(occ_val) and occ_val <= 1.0 else (occ_val or 0)
    m2.metric("Taux d'occupation", f"{occ_pct:.1f} %")
    m3.metric("Revenu mensuel", f"{row.get('estimated_monthly_rev', 0):,.0f} €".replace(',', ' '))
    m4.metric("CA annuel estimé", f"{row.get('estimated_annual_rev', 0):,.0f} €".replace(',', ' '))
    
    sub1, sub2, sub3 = st.columns(3)
    sub1.caption(f"**RevPAR :** {row.get('revpar', 0):.1f} € / nuit dispo")
    sub2.caption(f"**Prix / voyageur :** {row.get('price_per_guest', 0):.1f} € / pers.")
    sub3.caption(f"**Activité 12 mois :** ~{row.get('estimated_bookings_l12m', 0):.0f} séjours ({row.get('estimated_booked_days_l12m', 0):.0f} nuits louées)")
    
    st.markdown("---")
    st.markdown("#### ⭐ Évaluations & Notes Détaillées des Voyageurs")
    nb_rev = int(row.get('number_of_reviews', 0)) if pd.notna(row.get('number_of_reviews')) else 0
    nb_rev_ltm = int(row.get('number_of_reviews_ltm', 0)) if pd.notna(row.get('number_of_reviews_ltm')) else 0
    rpm = row.get('reviews_per_month', 0)
    rpm_str = f"{rpm:.2f}" if pd.notna(rpm) else "0.00"
    st.markdown(f"⭐ **Note Globale : {row.get('review_scores_rating', 0):.2f} / 5** &nbsp;•&nbsp; **{nb_rev} avis au total** *({nb_rev_ltm} sur 12 mois • {rpm_str} avis/mois)*")
    
    def fmt_score(val):
        return f"**{val:.2f}** / 5" if pd.notna(val) else "*N/D*"
        
    r1, r2, r3 = st.columns(3)
    r4, r5, r6 = st.columns(3)
    with r1:
        st.markdown(f"<div class='score-box'>🧼 <strong>Propreté :</strong> {fmt_score(row.get('review_scores_cleanliness'))}</div>", unsafe_allow_html=True)
    with r2:
        st.markdown(f"<div class='score-box'>🎯 <strong>Précision :</strong> {fmt_score(row.get('review_scores_accuracy'))}</div>", unsafe_allow_html=True)
    with r3:
        st.markdown(f"<div class='score-box'>🔑 <strong>Arrivée :</strong> {fmt_score(row.get('review_scores_checkin'))}</div>", unsafe_allow_html=True)
    with r4:
        st.markdown(f"<div class='score-box'>💬 <strong>Communication :</strong> {fmt_score(row.get('review_scores_communication'))}</div>", unsafe_allow_html=True)
    with r5:
        st.markdown(f"<div class='score-box'>📍 <strong>Emplacement :</strong> {fmt_score(row.get('review_scores_location'))}</div>", unsafe_allow_html=True)
    with r6:
        st.markdown(f"<div class='score-box'>🏷️ <strong>Qualité / Prix :</strong> {fmt_score(row.get('review_scores_value'))}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 👤 Profil de l'Hôte & Données d'Exploitation")
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown(f"**Nom de l'hôte :** {row.get('host_name', 'Inconnu')}")
        st.markdown(f"**ID Hôte :** `{row.get('host_id', '')}`")
        if pd.notna(row.get('host_url')) and str(row.get('host_url')).startswith('http'):
            st.markdown(f"[🔗 Voir le profil Airbnb de l'hôte]({row['host_url']})")
    with h2:
        st.markdown(f"**Typologie :** {row.get('host_segment', 'Standard')}")
        st.markdown(f"**Parc géré :** {int(row.get('calculated_host_listings_count', row.get('host_listings_count', 1)))} annonce(s)")
    with h3:
        h_since = str(row.get('host_since', ''))[:10]
        st.markdown(f"**Membre depuis :** {h_since or 'N/C'}")
        resp_rate = row.get('host_response_rate')
        st.markdown(f"**Taux de réponse :** {resp_rate if pd.notna(resp_rate) else 'N/C'}")
        resp_time = row.get('host_response_time')
        st.markdown(f"**Délai de réponse :** {resp_time if pd.notna(resp_time) else 'N/C'}")

    st.markdown("---")
    st.markdown("#### 🛋️ Équipements & Prestations")
    eq_cols = st.columns(6)
    eq_cols[0].markdown(f"{'✅' if row.get('has_wifi') else '❌'} Wifi")
    eq_cols[1].markdown(f"{'✅' if row.get('has_air_conditioning') else '❌'} Climatisation")
    eq_cols[2].markdown(f"{'✅' if row.get('has_kitchen') else '❌'} Cuisine")
    eq_cols[3].markdown(f"{'✅' if row.get('has_washer') else '❌'} Lave-linge")
    eq_cols[4].markdown(f"{'✅' if row.get('has_elevator') else '❌'} Ascenseur")
    eq_cols[5].markdown(f"{'✅' if row.get('has_workspace') else '❌'} Bureau")
    
    raw_am = row.get('amenities')
    am_list = []
    if isinstance(raw_am, str):
        try:
            am_list = json.loads(raw_am)
        except Exception:
            am_list = [a.strip(' "[]') for a in raw_am.split(',') if a.strip()]
    elif isinstance(raw_am, (list, tuple)):
        am_list = list(raw_am)
        
    if am_list:
        clean_ams = sorted(set([str(a).strip() for a in am_list if str(a).strip()]))
        with st.expander(f"📦 Voir tous les {len(clean_ams)} équipements déclarés"):
            am_cols = st.columns(3)
            for i, am in enumerate(clean_ams):
                am_cols[i % 3].markdown(f"• {am}")
                
    desc = row.get('description')
    if pd.notna(desc) and str(desc).strip():
        with st.expander("📝 Description complète rédigée par l'hôte"):
            clean_desc = str(desc).replace('<br />', '\n').replace('<br>', '\n').replace('<b>', '**').replace('</b>', '**')
            st.markdown(clean_desc)
            
    st.markdown("---")
    if st.button("✕ Fermer la fiche", width="stretch"):
        st.rerun()

# --- TOP HEADER ---
st.markdown('<div class="main-header">🏙️ Lyon Short-Term Rental Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Tableau de bord d\'analyse de marché & veille concurrentielle pour société de conciergerie | Données source Inside Airbnb (Lyon)</div>', unsafe_allow_html=True)

# Alert if empty
if len(df) == 0:
    st.warning("Aucune annonce ne correspond aux filtres sélectionnés. Veuillez élargir vos critères dans la barre latérale.")
    st.stop()

# --- TABS DEFINITION ---
tab1, tab2, tab3, tab_amenities, tab4, tab5, tab6 = st.tabs([
    "📊 Vue d'Ensemble & Marché",
    "🗺️ Carte & Arrondissements",
    "🏢 Concurrence & Conciergeries",
    "🛋️ Équipements & Prestations",
    "📅 Calendrier & Saisonnalité",
    "💡 Simulateur Prix & Rentabilité",
    "📋 Explorateur d'Annonces"
])

# ==========================================================
# TAB 1: VUE D'ENSEMBLE DU MARCHÉ
# ==========================================================
with tab1:
    st.subheader("Indicateurs Clés de Performance (KPIs)")
    
    # Financial metrics on active listings with price
    active_priced = df[df['price_clean'].notna() & (df['price_clean'] > 0)]
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Annonces Filtrées</div>
            <div class="kpi-value">{len(df):,}</div>
            <div class="kpi-sub">{len(df)/len(df_raw)*100:.1f}% du parc total</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        adr = active_priced['price_clean'].mean() if len(active_priced) > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Prix Moyen (ADR)</div>
            <div class="kpi-value">{adr:.0f} €</div>
            <div class="kpi-sub">Par nuitée</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        med_price = active_priced['price_clean'].median() if len(active_priced) > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Prix Médian</div>
            <div class="kpi-value">{med_price:.0f} €</div>
            <div class="kpi-sub">Plus représentatif</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        avg_occ = df[df['is_active']]['estimated_occupancy_rate'].mean() * 100 if len(df[df['is_active']]) > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Taux d'Occup. Estimé</div>
            <div class="kpi-value">{avg_occ:.1f}%</div>
            <div class="kpi-sub">Sur base des réservations</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col5:
        avg_revpar = active_priced['revpar'].mean() if len(active_priced) > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">RevPAR Moyen</div>
            <div class="kpi-value">{avg_revpar:.1f} €</div>
            <div class="kpi-sub">Revenu / nuit dispo</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col6:
        avg_monthly = active_priced['estimated_monthly_rev'].mean() if len(active_priced) > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Revenu Mensuel Est.</div>
            <div class="kpi-value">{avg_monthly:.0f} €</div>
            <div class="kpi-sub">{avg_monthly*12:.0f} € / an</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Secondary KPIs Row
    scol1, scol2, scol3, scol4 = st.columns(4)
    with scol1:
        superhost_pct = df['is_superhost'].mean() * 100
        st.metric("Taux de Superhosts", f"{superhost_pct:.1f}%", help="Pourcentage d'annonces gérées par un Superhost")
    with scol2:
        pro_pct = (df['calculated_host_listings_count'] > 1).mean() * 100
        st.metric("Part des Professionnels / Multi-bailleurs", f"{pro_pct:.1f}%", help="Hôtes ayant au moins 2 annonces sur Airbnb")
    with scol3:
        avg_rating = df['review_scores_rating'].mean()
        st.metric("Note Moyenne Voyageurs", f"{avg_rating:.2f} / 5", help="Note moyenne globale sur les avis")
    with scol4:
        license_pct = df['has_license'].mean() * 100
        st.metric("Taux d'enregistrement (Licence)", f"{license_pct:.1f}%", help="Annonces avec numéro d'enregistrement officiel ville de Lyon")

    st.markdown("### Analyse de la Distribution des Prix et Types de Biens")
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        if len(active_priced) > 0:
            hist_sample = active_priced.sample(min(2000, len(active_priced)), random_state=42)
            fig_price = px.histogram(
                hist_sample,
                x='price_clean',
                nbins=40,
                title="Distribution des Prix par Nuitée (€)",
                labels={'price_clean': 'Prix par nuit (€)'},
                color_discrete_sequence=['#FF5A5F'],
                marginal="box"
            )
            fig_price.add_vline(x=adr, line_dash="dash", line_color="#0F172A", annotation_text=f"Moyenne: {adr:.0f}€")
            fig_price.add_vline(x=med_price, line_dash="dot", line_color="#10B981", annotation_text=f"Médiane: {med_price:.0f}€")
            fig_price.update_layout(bargap=0.05, template="plotly_white")
            st.plotly_chart(fig_price, width="stretch")
            
    with c_chart2:
        room_dist = df['room_type'].value_counts().reset_index()
        room_dist.columns = ['Type', 'Nombre']
        fig_room = px.pie(
            room_dist,
            names='Type',
            values='Nombre',
            title="Répartition par Type d'Hébergement",
            color_discrete_sequence=['#FF5A5F', '#00A699', '#FC642D', '#484848'],
            hole=0.4
        )
        fig_room.update_layout(template="plotly_white")
        st.plotly_chart(fig_room, width="stretch")

    c_chart3, c_chart4 = st.columns(2)
    with c_chart3:
        # Accommodates distribution
        acc_dist = df['accommodates'].value_counts().sort_index().reset_index()
        acc_dist.columns = ['Capacité (personnes)', 'Nombre']
        fig_acc = px.bar(
            acc_dist[acc_dist['Capacité (personnes)'] <= 10],
            x='Capacité (personnes)',
            y='Nombre',
            title="Capacité d'Accueil des Logements (Voyageurs)",
            color_discrete_sequence=['#00A699']
        )
        fig_acc.update_layout(template="plotly_white")
        st.plotly_chart(fig_acc, width="stretch")
        
    with c_chart4:
        # Stay policy distribution
        stay_dist = df['stay_type'].value_counts().reset_index()
        stay_dist.columns = ['Politique de séjour', 'Nombre']
        fig_stay = px.bar(
            stay_dist,
            x='Politique de séjour',
            y='Nombre',
            title="Politique de Durée Minimale de Séjour",
            color_discrete_sequence=['#3B82F6']
        )
        fig_stay.update_layout(template="plotly_white")
        st.plotly_chart(fig_stay, width="stretch")

# ==========================================================
# TAB 2: CARTE & ARRONDISSEMENTS
# ==========================================================
with tab2:
    st.subheader("Cartographie & Analyse Comparative (Lyon & Métropole)")
    
    # Map
    st.markdown("#### Localisation des Logements et Prix Constatés")
    
    @st.fragment
    def render_map_component(sample_data, selected_arrs_list):
        col_map_opt1, col_map_opt2 = st.columns([2, 1])
        with col_map_opt1:
            map_mode = st.radio(
                "Mode d'affichage (Leaflet 2D) :",
                options=[
                    "🗺️ Vue par Regroupement (Clusters)",
                    "📍 Vue par Points Individuels",
                    "🔥 Carte de Chaleur / Densité (HeatMap 2D)"
                ],
                horizontal=True
            )
        with col_map_opt2:
            st.markdown("""
            <div style="font-size: 0.85rem; padding: 6px 12px; background: #F8FAFC; border-radius: 8px; border: 1px solid #E2E8F0;">
                <b>Légende Prix :</b><br>
                🟢 < 70 € / nuit | 🟠 70 à 130 € / nuit | 🔴 > 130 € / nuit
            </div>
            """, unsafe_allow_html=True)
            
        map_sample = sample_data.dropna(subset=['latitude', 'longitude'])
        if len(map_sample) > 500:
            map_sample = map_sample.sample(500, random_state=42)
            st.caption("⚡ Affichage optimisé d'un échantillon représentatif de 500 annonces pour une fluidité maximale.")

        center_lat = float(map_sample['latitude'].median()) if len(map_sample) > 0 else 45.7578
        center_lon = float(map_sample['longitude'].median()) if len(map_sample) > 0 else 4.8320
        zoom = 13 if len(selected_arrs_list) == 1 else 12
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")

        if map_mode == "🗺️ Vue par Regroupement (Clusters)":
            target_layer = MarkerCluster(name="Annonces Airbnb").add_to(m)
        elif map_mode == "📍 Vue par Points Individuels":
            target_layer = m
        else:
            target_layer = None

        if target_layer is not None:
            for _, r in map_sample.iterrows():
                p = r['price_clean']
                color = "#10B981" if p < 70 else ("#F59E0B" if p <= 130 else "#EF4444")
                html = f"""<div style="font-family: sans-serif; font-size: 12px; min-width: 190px; line-height: 1.4;">
                    <b style="font-size: 13px; color: #1E293B;">{r['name'][:40]}...</b><br>
                    <span style="color: #64748B;">📍 {r['neighbourhood_cleansed']}</span><br>
                    💶 Prix : <b style="color: {color}; font-size: 13px;">{p:.0f} € / nuit</b><br>
                    📈 Rev. mensuel : <b>{r.get('estimated_monthly_rev', 0):.0f} €</b><br>
                    👥 {int(r.get('accommodates', 1))} pers. | ⭐ <b>{r.get('review_scores_rating', 0):.2f}/5</b><br>
                    <a href="{r.get('listing_url', '#')}" target="_blank" style="color: #FF5A5F; font-weight: bold; text-decoration: none;">Voir l'annonce Airbnb &rarr;</a>
                </div>"""
                folium.CircleMarker(
                    location=[r['latitude'], r['longitude']],
                    radius=5,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.85,
                    popup=folium.Popup(html, max_width=250)
                ).add_to(target_layer)
        else:
            heat_data = [[r['latitude'], r['longitude'], 1] for _, r in map_sample.iterrows()]
            HeatMap(heat_data, radius=18, blur=14, min_opacity=0.4).add_to(m)

        st_folium(m, height=530, width="stretch", returned_objects=[])

    render_map_component(active_priced, selected_arrs)
    
    st.markdown("---")
    st.markdown("#### Benchmark par Arrondissement")
    
    # Aggregation by Arrondissement
    arr_summary = df.groupby('neighbourhood_cleansed').agg(
        total_listings=('id', 'count'),
        active_listings=('is_active', 'sum'),
        avg_price=('price_clean', 'mean'),
        median_price=('price_clean', 'median'),
        avg_occupancy=('estimated_occupancy_rate', lambda x: x.mean() * 100),
        avg_revpar=('revpar', 'mean'),
        avg_monthly_rev=('estimated_monthly_rev', 'mean'),
        avg_rating=('review_scores_rating', 'mean'),
        superhost_pct=('is_superhost', lambda x: x.mean() * 100),
        license_pct=('has_license', lambda x: x.mean() * 100)
    ).reset_index().rename(columns={'neighbourhood_cleansed': 'Arrondissement'})
    
    arr_summary = arr_summary.sort_values('avg_price', ascending=False)
    
    col_chart_a, col_chart_b = st.columns(2)
    with col_chart_a:
        fig_arr_p = px.bar(
            arr_summary,
            x='Arrondissement',
            y='avg_price',
            title="Prix Moyen par Nuitée par Arrondissement (€)",
            color='avg_price',
            color_continuous_scale="Reds",
            labels={'avg_price': 'Prix Moyen (€)'}
        )
        fig_arr_p.update_layout(template="plotly_white")
        st.plotly_chart(fig_arr_p, width="stretch")
        
    with col_chart_b:
        fig_arr_rev = px.bar(
            arr_summary,
            x='Arrondissement',
            y='avg_monthly_rev',
            title="Revenu Mensuel Moyen Estimé par Logement (€)",
            color='avg_monthly_rev',
            color_continuous_scale="Greens",
            labels={'avg_monthly_rev': 'Revenu Mensuel (€)'}
        )
        fig_arr_rev.update_layout(template="plotly_white")
        st.plotly_chart(fig_arr_rev, width="stretch")
        
    st.markdown("#### Tableau Récapitulatif Détaillé par Arrondissement")
    st.dataframe(
        arr_summary.style.format({
            'avg_price': '{:.1f} €',
            'median_price': '{:.0f} €',
            'avg_occupancy': '{:.1f}%',
            'avg_revpar': '{:.1f} €',
            'avg_monthly_rev': '{:.0f} €',
            'avg_rating': '{:.2f} / 5',
            'superhost_pct': '{:.1f}%',
            'license_pct': '{:.1f}%'
        }),
        width="stretch"
    )

# ==========================================================
# TAB 3: CONCURRENCE & CONCIERGERIES
# ==========================================================
with tab3:
    st.subheader("Intelligence Concurrentielle & Acteurs de la Conciergerie à Lyon")
    
    col_conc1, col_conc2 = st.columns(2)
    
    with col_conc1:
        st.markdown("#### Top 15 des Plus Grands Gestionnaires à Lyon")
        top_hosts = (
            df.groupby(['host_id', 'host_name', 'host_segment'])
            .agg(
                nb_annonces=('id', 'count'),
                avg_price=('price_clean', 'mean'),
                avg_rating=('review_scores_rating', 'mean'),
                superhost=('is_superhost', 'first')
            )
            .reset_index()
            .sort_values('nb_annonces', ascending=False)
            .head(15)
        )
        
        fig_top_hosts = px.bar(
            top_hosts,
            x='nb_annonces',
            y='host_name',
            orientation='h',
            title="Gestionnaires avec le plus d'annonces à Lyon",
            color='avg_price',
            color_continuous_scale='Viridis',
            labels={'nb_annonces': 'Nombre d\'annonces', 'host_name': 'Hôte / Agence', 'avg_price': 'Prix moyen (€)'}
        )
        fig_top_hosts.update_layout(yaxis={'categoryorder': 'total ascending'}, template="plotly_white")
        st.plotly_chart(fig_top_hosts, width="stretch")
        
    with col_conc2:
        st.markdown("#### Typologie des Gestionnaires sur le Marché")
        segment_counts = df['host_segment'].value_counts().reset_index()
        segment_counts.columns = ['Segment', 'Annonces']
        
        fig_seg = px.pie(
            segment_counts,
            names='Segment',
            values='Annonces',
            title="Répartition du Parc par Profil de Propriétaire / Conciergerie",
            color_discrete_sequence=['#4F46E5', '#06B6D4', '#10B981', '#F59E0B'],
            hole=0.45
        )
        fig_seg.update_layout(template="plotly_white")
        st.plotly_chart(fig_seg, width="stretch")
        
    st.markdown("---")
    st.markdown("#### Impact du Statut Superhost sur la Performance")
    
    col_sh1, col_sh2, col_sh3 = st.columns(3)
    sh_comp = df.groupby('is_superhost').agg(
        prix_moyen=('price_clean', 'mean'),
        prix_median=('price_clean', 'median'),
        taux_occ=('estimated_occupancy_rate', lambda x: x.mean() * 100),
        rev_mensuel=('estimated_monthly_rev', 'mean'),
        note=('review_scores_rating', 'mean'),
        nb_avis=('number_of_reviews', 'mean')
    ).reset_index()
    sh_comp['Statut'] = sh_comp['is_superhost'].map({True: 'Superhost ⭐', False: 'Hôte Standard'})
    
    with col_sh1:
        fig_sh_p = px.bar(
            sh_comp,
            x='Statut',
            y='prix_moyen',
            title="Prix Moyen par Nuit (€)",
            color='Statut',
            color_discrete_map={'Superhost ⭐': '#FF5A5F', 'Hôte Standard': '#64748B'}
        )
        fig_sh_p.update_layout(template="plotly_white", showlegend=False)
        st.plotly_chart(fig_sh_p, width="stretch")
        
    with col_sh2:
        fig_sh_occ = px.bar(
            sh_comp,
            x='Statut',
            y='taux_occ',
            title="Taux d'Occupation Estimé (%)",
            color='Statut',
            color_discrete_map={'Superhost ⭐': '#FF5A5F', 'Hôte Standard': '#64748B'}
        )
        fig_sh_occ.update_layout(template="plotly_white", showlegend=False)
        st.plotly_chart(fig_sh_occ, width="stretch")
        
    with col_sh3:
        fig_sh_rev = px.bar(
            sh_comp,
            x='Statut',
            y='rev_mensuel',
            title="Revenu Mensuel Moyen Estimé (€)",
            color='Statut',
            color_discrete_map={'Superhost ⭐': '#FF5A5F', 'Hôte Standard': '#64748B'}
        )
        fig_sh_rev.update_layout(template="plotly_white", showlegend=False)
        st.plotly_chart(fig_sh_rev, width="stretch")

    st.markdown("---")
    st.markdown("### 🎯 Chasseur d'Opportunités : Prospection Conciergerie")
    st.write(
        "Identifiez en temps réel les logements concurrents en sous-performance (frictions de ménage/accueil, "
        "calendrier sous-rempli ou tarification mal ajustée) pour proposer vos services d'intendance et de conciergerie aux propriétaires."
    )

    # Precompute robust benchmark for potential gain from active listings
    valid_mkt_ref = df_raw[df_raw['is_active'] & (df_raw['estimated_annual_rev'] > 0)]
    if len(valid_mkt_ref) > 0:
        bench_arr_acc = valid_mkt_ref.groupby(['neighbourhood_cleansed', 'accommodates'])['estimated_annual_rev'].median().to_dict()
        bench_acc = valid_mkt_ref.groupby('accommodates')['estimated_annual_rev'].median().to_dict()
        bench_arr = valid_mkt_ref.groupby('neighbourhood_cleansed')['estimated_annual_rev'].median().to_dict()
        mkt_occ_ref = float(valid_mkt_ref['estimated_occupancy_rate'].median())
    else:
        bench_arr_acc, bench_acc, bench_arr = {}, {}, {}
        mkt_occ_ref = 0.50

    def calc_potential_gain(row):
        cur_rev = row.get('estimated_annual_rev', 0)
        if pd.isna(cur_rev) or cur_rev <= 0:
            return 0.0
        k = (row.get('neighbourhood_cleansed'), row.get('accommodates'))
        target_rev = bench_arr_acc.get(k, bench_acc.get(row.get('accommodates'), bench_arr.get(row.get('neighbourhood_cleansed'), cur_rev)))
        gain_rev = max(0.0, float(target_rev - cur_rev))
        occ = row.get('estimated_occupancy_rate', 0)
        price = row.get('price_clean', 0)
        if not pd.isna(occ) and not pd.isna(price) and occ < mkt_occ_ref:
            gain_occ = (mkt_occ_ref - occ) * 365 * price * 0.814
            return round(max(gain_rev, gain_occ))
        return round(gain_rev)

    # --- FILTERS PANEL ---
    with st.expander("🛠️ Filtres Avancés de Prospection & Ciblage", expanded=True):
        col_pf1, col_pf2 = st.columns([2, 1])
        with col_pf1:
            prosp_frictions = st.multiselect(
                "Angles d'attaque / Motifs de prospection :",
                options=[
                    "🧹 Propreté fragile (< seuil)",
                    "🔑 Arrivée / Check-in fragile (< seuil)",
                    "💬 Communication lente (< seuil)",
                    "⭐ Note globale fragile (< 4.75)",
                    "📉 Sous-occupation calendrier (< seuil)",
                    "❌ Hôtes non-Superhosts",
                    "💰 Fort manque à gagner (> 3 000 €/an)"
                ],
                default=[
                    "🧹 Propreté fragile (< seuil)",
                    "🔑 Arrivée / Check-in fragile (< seuil)",
                    "📉 Sous-occupation calendrier (< seuil)"
                ],
                help="Sélectionnez les vulnérabilités à cibler chez les propriétaires."
            )
        with col_pf2:
            friction_mode = st.radio(
                "Condition de ciblage :",
                options=["Au moins 1 motif (Recommandé)", "Tous les motifs cumulés"],
                horizontal=True,
                help="Au moins 1 motif = sélectionne toute annonce présentant l'un des critères cochés."
            )

        col_pf3, col_pf4, col_pf5 = st.columns(3)
        with col_pf3:
            available_hosts = [s for s in [
                "Particulier (1 bien)",
                "Multi-propriétaire (2-5 biens)",
                "Petite conciergerie / Pro (6-20 biens)",
                "Grande conciergerie / Agence (21+ biens)"
            ] if s in df['host_segment'].unique()]
            default_hosts = [s for s in ["Particulier (1 bien)", "Multi-propriétaire (2-5 biens)"] if s in available_hosts]
            if not default_hosts:
                default_hosts = available_hosts
            prosp_hosts = st.multiselect(
                "Profils d'hôtes ciblés :",
                options=available_hosts,
                default=default_hosts,
                help="Ciblez en priorité les propriétaires indépendants (particuliers & multi-propriétaires)."
            )
        with col_pf4:
            subscore_thresh = st.slider(
                "Seuil de friction sous-notes (⭐) :",
                min_value=4.50,
                max_value=4.95,
                value=4.80,
                step=0.05,
                help="4.80 est le seuil éliminatoire Airbnb pour le badge Superhôte. En dessous, l'annonce perd son statut."
            )
        with col_pf5:
            occ_thresh_pct = st.slider(
                "Seuil max de sous-occupation (%) :",
                min_value=15,
                max_value=65,
                value=45,
                step=5,
                help="Cible les logements dont le calendrier est anormalement vide par rapport au potentiel du marché."
            )

        col_pf6, col_pf7, col_pf8 = st.columns(3)
        with col_pf6:
            min_reviews_prosp = st.number_input(
                "Nombre minimum d'avis :",
                min_value=1,
                max_value=50,
                value=3,
                step=1,
                help="Exclut les annonces toutes récentes sans historique fiable."
            )
        with col_pf7:
            sort_by = st.selectbox(
                "Trier les opportunités par :",
                options=[
                    "💰 Manque à gagner (€/an) [Décroissant]",
                    "📉 Taux d'occupation [Croissant]",
                    "🧹 Note propreté [Croissante]",
                    "🔑 Note arrivée [Croissante]",
                    "⭐ Note globale [Croissante]",
                    "📝 Nombre d'avis [Décroissant]",
                    "💶 Prix par nuit [Décroissant]"
                ],
                index=0
            )
        with col_pf8:
            limit_n = st.selectbox(
                "Nombre de résultats affichés :",
                options=[25, 50, 100, "Toutes les cibles"],
                index=0
            )

    # Base candidate pool from filtered df
    base_cand = df[df['is_active'] & (df['number_of_reviews'] >= min_reviews_prosp)].copy()
    if prosp_hosts:
        base_cand = base_cand[base_cand['host_segment'].isin(prosp_hosts)]

    if len(base_cand) > 0:
        base_cand['potential_gain'] = base_cand.apply(calc_potential_gain, axis=1)

        # Build individual masks
        masks_dict = {
            "🧹 Propreté fragile (< seuil)": base_cand['review_scores_cleanliness'] < subscore_thresh,
            "🔑 Arrivée / Check-in fragile (< seuil)": base_cand['review_scores_checkin'] < subscore_thresh,
            "💬 Communication lente (< seuil)": base_cand['review_scores_communication'] < subscore_thresh,
            "⭐ Note globale fragile (< 4.75)": base_cand['review_scores_rating'] < 4.75,
            "📉 Sous-occupation calendrier (< seuil)": base_cand['estimated_occupancy_rate'] < (occ_thresh_pct / 100.0),
            "❌ Hôtes non-Superhosts": ~base_cand['is_superhost'],
            "💰 Fort manque à gagner (> 3 000 €/an)": base_cand['potential_gain'] >= 3000
        }

        active_masks = [masks_dict[f] for f in prosp_frictions if f in masks_dict]
        if active_masks:
            if friction_mode == "Au moins 1 motif (Recommandé)":
                combined_mask = active_masks[0]
                for m in active_masks[1:]:
                    combined_mask = combined_mask | m
            else:
                combined_mask = active_masks[0]
                for m in active_masks[1:]:
                    combined_mask = combined_mask & m
            df_opp = base_cand[combined_mask].copy()
        else:
            df_opp = base_cand.copy()

        # Sorting
        if sort_by == "💰 Manque à gagner (€/an) [Décroissant]":
            df_opp = df_opp.sort_values('potential_gain', ascending=False)
        elif sort_by == "📉 Taux d'occupation [Croissant]":
            df_opp = df_opp.sort_values('estimated_occupancy_rate', ascending=True)
        elif sort_by == "🧹 Note propreté [Croissante]":
            df_opp = df_opp.sort_values('review_scores_cleanliness', ascending=True)
        elif sort_by == "🔑 Note arrivée [Croissante]":
            df_opp = df_opp.sort_values('review_scores_checkin', ascending=True)
        elif sort_by == "⭐ Note globale [Croissante]":
            df_opp = df_opp.sort_values('review_scores_rating', ascending=True)
        elif sort_by == "📝 Nombre d'avis [Décroissant]":
            df_opp = df_opp.sort_values('number_of_reviews', ascending=False)
        elif sort_by == "💶 Prix par nuit [Décroissant]":
            df_opp = df_opp.sort_values('price_clean', ascending=False)
    else:
        df_opp = pd.DataFrame()

    # --- METRICS SUMMARY CARDS ---
    if len(df_opp) > 0:
        tot_leads = len(df_opp)
        tot_gain = df_opp['potential_gain'].sum()
        avg_gain = df_opp['potential_gain'].mean()
        avg_occ_prosp = df_opp['estimated_occupancy_rate'].mean() * 100

        col_km1, col_km2, col_km3, col_km4 = st.columns(4)
        with col_km1:
            st.metric("🎯 Leads Qualifiés", f"{tot_leads:,} annonces")
        with col_km2:
            st.metric("💰 Manque à Gagner Total", f"{tot_gain/1_000:,.1f} k€ / an")
        with col_km3:
            st.metric("📈 Gain Moyen / Logement", f"+{avg_gain:,.0f} € / an")
        with col_km4:
            st.metric("📉 Remplissage Moyen Cible", f"{avg_occ_prosp:.1f} %")

        # Diagnostics tags function
        def get_diagnostic_label(r):
            issues = []
            clean = r.get('review_scores_cleanliness')
            if not pd.isna(clean) and clean < subscore_thresh:
                issues.append(f"🧹 Ménage ({clean:.2f})")
            checkin = r.get('review_scores_checkin')
            if not pd.isna(checkin) and checkin < subscore_thresh:
                issues.append(f"🔑 Arrivée ({checkin:.2f})")
            comm = r.get('review_scores_communication')
            if not pd.isna(comm) and comm < subscore_thresh:
                issues.append(f"💬 Comm. ({comm:.2f})")
            occ = r.get('estimated_occupancy_rate')
            if not pd.isna(occ) and occ < (occ_thresh_pct / 100.0):
                issues.append(f"📉 Occ. ({occ*100:.0f}%)")
            rating = r.get('review_scores_rating')
            if not pd.isna(rating) and rating < 4.75:
                issues.append(f"⭐ Note ({rating:.2f})")
            gain = r.get('potential_gain', 0)
            if gain >= 4000:
                issues.append(f"💰 +{gain:,.0f}€")
            return " • ".join(issues[:3]) if issues else "Sous-optimisé"

        df_opp['diagnostic'] = df_opp.apply(get_diagnostic_label, axis=1)

        # Slice limit
        if limit_n != "Toutes les cibles":
            df_opp_disp = df_opp.head(int(limit_n)).copy().reset_index(drop=True)
        else:
            df_opp_disp = df_opp.copy().reset_index(drop=True)

        df_table = df_opp_disp.copy()
        df_table.insert(0, 'Fiche', '🔎 Ouvrir')
        df_table['host_display'] = (
            df_table['host_name'].fillna('Hôte') + ' (' +
            df_table['host_segment'].fillna('Standard').str.split('(').str[0].str.strip() + ')'
        )
        df_table['occupancy_pct'] = (df_table['estimated_occupancy_rate'] * 100).round(0)

        st.dataframe(
            df_table[[
                'id', 'Fiche', 'name', 'host_display', 'neighbourhood_cleansed',
                'price_clean', 'occupancy_pct', 'estimated_annual_rev', 'potential_gain',
                'diagnostic', 'review_scores_rating', 'review_scores_cleanliness',
                'review_scores_checkin', 'review_scores_communication',
                'number_of_reviews', 'listing_url'
            ]].rename(columns={
                'name': "Nom de l'annonce",
                'host_display': 'Hôte & Profil',
                'neighbourhood_cleansed': 'Arrondissement',
                'price_clean': 'Prix (€)',
                'occupancy_pct': 'Occ. (%)',
                'estimated_annual_rev': 'Rev. Actuel (€)',
                'potential_gain': '💰 Gain Potentiel (€/an)',
                'diagnostic': 'Diagnostic Clé',
                'review_scores_rating': 'Note ⭐',
                'review_scores_cleanliness': 'Propreté 🧹',
                'review_scores_checkin': 'Arrivée 🔑',
                'review_scores_communication': 'Comm. 💬',
                'number_of_reviews': 'Avis',
                'listing_url': 'URL Airbnb'
            }),
            column_config={
                'id': None,
                'Fiche': st.column_config.ButtonColumn('Fiche', width='small', key='btn_click_prosp'),
                'Prix (€)': st.column_config.NumberColumn(format="%d €"),
                'Occ. (%)': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
                'Rev. Actuel (€)': st.column_config.NumberColumn(format="%d €"),
                '💰 Gain Potentiel (€/an)': st.column_config.NumberColumn(format="+%d €", help="Gain annuel supplémentaire estimé en portant le logement aux standards optimisés de conciergerie."),
                'Note ⭐': st.column_config.NumberColumn(format="%.2f"),
                'Propreté 🧹': st.column_config.NumberColumn(format="%.2f"),
                'Arrivée 🔑': st.column_config.NumberColumn(format="%.2f"),
                'Comm. 💬': st.column_config.NumberColumn(format="%.2f"),
                'Avis': st.column_config.NumberColumn(format="%d"),
                'URL Airbnb': st.column_config.LinkColumn('Lien Airbnb', display_text='Voir sur Airbnb')
            },
            hide_index=True,
            width="stretch"
        )

        btn_prosp = st.session_state.get('btn_click_prosp')
        if btn_prosp:
            row_idx = btn_prosp.row if hasattr(btn_prosp, 'row') else btn_prosp.get('row')
            if row_idx is not None and 0 <= row_idx < len(df_opp_disp):
                sel_id = df_opp_disp.iloc[row_idx]['id']
                show_listing_modal(sel_id)

        # --- COMMERCIAL PITCH GENERATOR & EXPORT ---
        col_pitch_btn, col_csv_btn = st.columns([2, 1])
        with col_csv_btn:
            csv_prosp = df_opp_disp[[
                'id', 'name', 'host_name', 'host_segment', 'neighbourhood_cleansed',
                'price_clean', 'estimated_occupancy_rate', 'estimated_annual_rev',
                'potential_gain', 'diagnostic', 'review_scores_rating',
                'review_scores_cleanliness', 'review_scores_checkin',
                'review_scores_communication', 'number_of_reviews', 'listing_url'
            ]].to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Exporter les {len(df_opp_disp)} leads en CSV",
                data=csv_prosp,
                file_name="leads_prospection_conciergerie.csv",
                mime="text/csv"
            )

        with st.expander("💡 Générateur d'Argumentaire Commercial & Message d'Accroche", expanded=False):
            st.markdown("Sélectionnez l'un des propriétaires ciblés pour générer instantanément une accroche commerciale sur-mesure basée sur ses données réelles :")
            opp_choice_list = [
                f"{r['id']} | {r['host_name']} - {str(r['name'])[:45]}... ({r['neighbourhood_cleansed']} - Gain: +{r['potential_gain']:,.0f} €/an)"
                for _, r in df_opp_disp.head(40).iterrows()
            ]
            sel_choice = st.selectbox("Choisir une opportunité :", options=opp_choice_list, key="pitch_select")
            if sel_choice:
                p_id = int(sel_choice.split(" | ")[0])
                p_row = df_opp_disp[df_opp_disp['id'] == p_id].iloc[0]

                p_host = p_row.get('host_name', 'Propriétaire')
                p_name = p_row.get('name', 'votre bien')
                p_arr = p_row.get('neighbourhood_cleansed', 'Lyon')
                p_gain = p_row.get('potential_gain', 0)
                p_occ = p_row.get('estimated_occupancy_rate', 0) * 100
                p_clean = p_row.get('review_scores_cleanliness', 0)
                p_check = p_row.get('review_scores_checkin', 0)
                p_rev = p_row.get('estimated_annual_rev', 0)

                pitch_text = f"""Bonjour {p_host},

Je suis gestionnaire de conciergerie à Lyon. En analysant le marché locatif sur {p_arr}, j'ai particulièrement remarqué votre annonce « {p_name} ».

Votre bien possède un beau potentiel, mais présente un manque à gagner significatif :
- Votre taux d'occupation est estimé à {p_occ:.0f} % (contre plus de 55 % pour les biens optimisés du quartier)."""
                if p_clean < subscore_thresh:
                    pitch_text += f"\n- Votre note de propreté ({p_clean:.2f} ⭐) freine l'algorithme Airbnb et peut être relevée avec nos équipes de ménage hôtelier."
                if p_check < subscore_thresh:
                    pitch_text += f"\n- Votre logistique d'accueil ({p_check:.2f} ⭐) gagnerait à être automatisée 24/7."
                pitch_text += f"""
- En optimisant le pricing dynamique et la qualité, vous pourriez générer environ +{p_gain:,.0f} € net/an (revenu annuel potentiel de {p_rev + p_gain:,.0f} €).

Notre conciergerie prend en charge 100 % de l'exploitation (ménage, accueil, linge, assistance 7j/7).
Seriez-vous ouvert à un rapide échange de 5 minutes ?"""

                col_pt1, col_pt2 = st.columns([3, 1])
                with col_pt1:
                    st.text_area("Message d'accroche personnalisé (prêt à copier/coller) :", value=pitch_text, height=220)
                with col_pt2:
                    st.markdown(f"**Arrondissement :** {p_arr}")
                    st.markdown(f"**Gain estimé :** `+{p_gain:,.0f} €/an`")
                    st.markdown(f"**Diagnostic :** {p_row['diagnostic']}")
                    if st.button("🔍 Voir la fiche complète", key="btn_pitch_open"):
                        show_listing_modal(p_id)
    else:
        st.info("ℹ️ Aucune annonce ne correspond aux filtres de prospection sélectionnés. Essayez d'élargir les critères ou d'abaisser les seuils.")

# ==========================================================
# TAB: ÉQUIPEMENTS & PRESTATIONS
# ==========================================================
with tab_amenities:
    st.subheader("🛋️ Analyse des Équipements & Prestations")
    st.caption("Pénétration des équipements sur la sélection filtrée, surcote tarifaire (prime ADR) et leviers de valorisation pour vos prestations de conciergerie.")
    
    amenities_config = [
        ('Climatisation', 'has_air_conditioning', '❄️', 'Confort d\'été'),
        ('Parking', 'has_parking', '🅿️', 'Logistique'),
        ('Balcon / Terrasse', 'has_balcony', '🌿', 'Espace extérieur'),
        ('Ascenseur', 'has_elevator', '🛗', 'Accessibilité'),
        ('Lave-vaisselle', 'has_dishwasher', '🍽️', 'Confort cuisine'),
        ('Lave-linge', 'has_washer', '🧺', 'Long séjour'),
        ('Machine à café / Nespresso', 'has_coffee_machine', '☕', 'Prestation accueil'),
        ('Télévision', 'has_tv', '📺', 'Divertissement'),
        ('Arrivée autonome', 'has_self_checkin', '🔑', 'Flexibilité hôte'),
        ('Baignoire', 'has_bathtub', '🛁', 'Bien-être'),
        ('Espace de travail', 'has_workspace', '💻', 'Voyageurs pro'),
        ('Lit bébé', 'has_baby_crib', '👶', 'Familles'),
        ('Cuisine équipée', 'has_kitchen', '🍳', 'Indispensable'),
        ('Wifi', 'has_wifi', '📶', 'Indispensable')
    ]
    
    price_vals = df['price_clean'].values
    rating_vals = df['review_scores_rating'].values
    n_listings = len(df)
    
    am_rows = []
    amenity_cols_present = []
    for label, col, icon, category in amenities_config:
        if col in df.columns:
            amenity_cols_present.append(col)
            mask = (df[col].values == True)
            cnt = int(np.sum(mask))
            pct = (cnt / n_listings * 100) if n_listings > 0 else 0.0
            
            p_with = float(np.nanmedian(price_vals[mask])) if cnt > 0 and np.any(~np.isnan(price_vals[mask])) else 0.0
            p_without = float(np.nanmedian(price_vals[~mask])) if (n_listings - cnt) > 0 and np.any(~np.isnan(price_vals[~mask])) else 0.0
            premium = p_with - p_without if (p_with > 0 and p_without > 0) else 0.0
            
            r_with = float(np.nanmean(rating_vals[mask])) if cnt > 0 and np.any(~np.isnan(rating_vals[mask])) else 0.0
            
            if pct >= 80:
                recom = "✅ Standard indispensable"
            elif premium >= 25:
                recom = "💎 Pépite (Forte surcote)"
            elif premium >= 15:
                recom = "⭐ Différenciateur rentable"
            elif pct < 20:
                recom = "🔍 Niche recherchée"
            else:
                recom = "👍 Confort apprécié"
                
            am_rows.append({
                'label': label,
                'icon': icon,
                'name': f"{icon} {label}",
                'category': category,
                'count': cnt,
                'pct': round(pct, 1),
                'price_with': round(p_with, 1),
                'price_without': round(p_without, 1),
                'premium': round(premium, 1),
                'rating': round(r_with, 2),
                'recom': recom
            })
            
    df_am_stat = pd.DataFrame(am_rows)
    
    # Calculate equipment score per listing
    equip_scores = df[amenity_cols_present].sum(axis=1) if len(amenity_cols_present) > 0 else pd.Series(0, index=df.index)
    avg_score = equip_scores.mean() if n_listings > 0 else 0.0
    pct_premium_listings = (equip_scores >= 8).mean() * 100 if n_listings > 0 else 0.0
    
    top_premium_row = df_am_stat.loc[df_am_stat['premium'].idxmax()] if len(df_am_stat) > 0 else None
    rare_candidates = df_am_stat[df_am_stat['pct'] <= 25]
    top_rare_row = rare_candidates.loc[rare_candidates['premium'].idxmax()] if len(rare_candidates) > 0 else top_premium_row
    
    # --- Top KPIs Row ---
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Top Surcote Tarifaire</div>
            <div class="kpi-value">{top_premium_row['name'] if top_premium_row is not None else '-'}</div>
            <div class="kpi-sub">+{top_premium_row['premium']:.1f} € / nuitée</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Pépite Rare Différenciante</div>
            <div class="kpi-value">{top_rare_row['name'] if top_rare_row is not None else '-'}</div>
            <div class="kpi-sub">{top_rare_row['pct']:.1f}% présence • +{top_rare_row['premium']:.1f} €/nuit</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Équipements Moyens / Bien</div>
            <div class="kpi-value">{avg_score:.1f} / {len(amenity_cols_present)}</div>
            <div class="kpi-sub">Score d'équipement moyen</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Parc Bien Équipé (≥ 8)</div>
            <div class="kpi-value">{pct_premium_listings:.1f}%</div>
            <div class="kpi-sub">Biens à fort niveau de prestation</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    # --- Row 1: Charts (Taux d'Équipement & Surcote) ---
    c_am1, c_am2 = st.columns(2)
    
    with c_am1:
        df_sorted_pct = df_am_stat.sort_values('pct', ascending=True)
        colors_pct = [
            '#10B981' if p >= 75 else ('#3B82F6' if p >= 30 else '#FF5A5F') 
            for p in df_sorted_pct['pct']
        ]
        
        fig_pct = go.Figure(go.Bar(
            x=df_sorted_pct['pct'],
            y=df_sorted_pct['name'],
            orientation='h',
            marker=dict(color=colors_pct),
            text=[f"{p:.1f}%" for p in df_sorted_pct['pct']],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Taux de présence: <b>%{x:.1f}%</b><br>Nombre d\'annonces: %{customdata:,}<extra></extra>',
            customdata=df_sorted_pct['count']
        ))
        max_pct = max(df_am_stat['pct']) if len(df_am_stat) > 0 else 100
        fig_pct.update_layout(
            title="Taux d'Équipement sur la Sélection (%)",
            xaxis=dict(title="Taux de présence (%)", range=[0, min(100, max_pct * 1.15)]),
            yaxis=dict(title=""),
            template="plotly_white",
            height=460,
            margin=dict(l=10, r=40, t=45, b=25)
        )
        st.plotly_chart(fig_pct, width="stretch")
        
    with c_am2:
        df_sorted_prem = df_am_stat.sort_values('premium', ascending=True)
        colors_prem = ['#00A699' if p > 0 else '#94A3B8' for p in df_sorted_prem['premium']]
        
        fig_prem = go.Figure(go.Bar(
            x=df_sorted_prem['premium'],
            y=df_sorted_prem['name'],
            orientation='h',
            marker=dict(color=colors_prem),
            text=[f"+{p:.1f} €" if p > 0 else f"{p:.1f} €" for p in df_sorted_prem['premium']],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Prime tarifaire médiane: <b>+%{x:.1f} € / nuit</b><br>Prix médian avec: %{customdata[0]:.1f} €<br>Prix médian sans: %{customdata[1]:.1f} €<extra></extra>',
            customdata=df_sorted_prem[['price_with', 'price_without']]
        ))
        min_prem = min(df_am_stat['premium']) if len(df_am_stat) > 0 else 0
        max_prem = max(df_am_stat['premium']) if len(df_am_stat) > 0 else 50
        fig_prem.update_layout(
            title="Surcote Tarifaire Médiane par Équipement (€ / nuit)",
            xaxis=dict(title="Surcote par rapport aux biens non équipés (€)", range=[min(-10, min_prem - 5), max_prem * 1.18]),
            yaxis=dict(title=""),
            template="plotly_white",
            height=460,
            margin=dict(l=10, r=40, t=45, b=25)
        )
        st.plotly_chart(fig_prem, width="stretch")
        
    # --- Row 2: Strategic Matrix & Equipment Brackets ---
    c_m1, c_m2 = st.columns(2)
    
    with c_m1:
        fig_matrix = px.scatter(
            df_am_stat,
            x='pct',
            y='premium',
            size='count',
            color='category',
            text='name',
            title="Matrice Stratégique : Rareté vs Surcote Tarifaire",
            labels={
                'pct': 'Taux de présence (%)',
                'premium': 'Surcote médiane (€ / nuit)',
                'category': 'Catégorie'
            },
            custom_data=['count', 'price_with', 'price_without', 'rating']
        )
        fig_matrix.update_traces(
            textposition='top center',
            marker=dict(opacity=0.85, line=dict(width=1, color='#1E293B')),
            hovertemplate='<b>%{text}</b><br>Présence: %{x:.1f}% (%{customdata[0]:,} biens)<br>Surcote: +%{y:.1f} €/nuit<br>Prix médian avec: %{customdata[1]:.1f} €<br>Note moyenne: %{customdata[3]:.2f}/5<extra></extra>'
        )
        med_p = 35.0
        med_pr = 20.0
        fig_matrix.add_vline(x=med_p, line_dash="dash", line_color="#CBD5E1")
        fig_matrix.add_hline(y=med_pr, line_dash="dash", line_color="#CBD5E1")
        max_y_mat = max(df_am_stat['premium']) if len(df_am_stat) > 0 else 50
        fig_matrix.add_annotation(x=15, y=max_y_mat * 0.96, text="💎 PÉPITES (Rares & Fort gain)", showarrow=False, font=dict(color="#FF5A5F", size=10, family="sans-serif"))
        fig_matrix.add_annotation(x=78, y=max_y_mat * 0.96, text="⭐ STANDARDS HAUT DE GAMME", showarrow=False, font=dict(color="#00A699", size=10, family="sans-serif"))
        fig_matrix.add_annotation(x=80, y=min(5, min_prem + 4), text="📦 PRÉ-REQUIS OBLIGATOIRES", showarrow=False, font=dict(color="#64748B", size=10, family="sans-serif"))
        fig_matrix.update_layout(template="plotly_white", height=460, margin=dict(l=10, r=20, t=50, b=30))
        st.plotly_chart(fig_matrix, width="stretch")
        
    with c_m2:
        def get_bracket(s):
            if s <= 4:
                return '1. Essentiel (0-4)'
            elif s <= 7:
                return '2. Confort (5-7)'
            elif s <= 9:
                return '3. Premium (8-9)'
            else:
                return '4. Haut de Gamme (10+)'
                
        df_bracket = df.copy()
        df_bracket['bracket'] = equip_scores.apply(get_bracket)
        b_agg = df_bracket.groupby('bracket').agg(
            nb=('id', 'count'),
            adr_med=('price_clean', 'median'),
            rating=('review_scores_rating', 'mean')
        ).reset_index()
        
        fig_bracket = go.Figure()
        fig_bracket.add_trace(go.Bar(
            x=b_agg['bracket'],
            y=b_agg['adr_med'],
            name='Prix Médian (€ / nuit)',
            marker_color='#FF5A5F',
            text=[f"{p:.0f} €" if pd.notna(p) else "" for p in b_agg['adr_med']],
            textposition='outside',
            yaxis='y'
        ))
        fig_bracket.add_trace(go.Scatter(
            x=b_agg['bracket'],
            y=b_agg['rating'],
            name='Note Moyenne (/5)',
            mode='lines+markers',
            marker=dict(size=8, color='#0F172A'),
            line=dict(color='#0F172A', width=3),
            yaxis='y2'
        ))
        max_adr_b = b_agg['adr_med'].max() if len(b_agg) > 0 and pd.notna(b_agg['adr_med'].max()) else 150
        fig_bracket.update_layout(
            title="Impact du Niveau d'Équipement sur le Prix & la Note",
            xaxis=dict(title="Palier d'équipements dotés"),
            yaxis=dict(title="Prix Médian (€)", range=[0, max_adr_b * 1.25]),
            yaxis2=dict(title="Note Moyenne (/5)", overlaying='y', side='right', range=[4.5, 5.0]),
            template="plotly_white",
            height=460,
            margin=dict(l=10, r=40, t=50, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bracket, width="stretch")
        
    # --- Table & Strategic Guide ---
    st.markdown("### 📋 Tableau Détaillé des Prestations & Recommandations d'Intendance")
    
    display_df = df_am_stat.sort_values('premium', ascending=False)[[
        'name', 'category', 'pct', 'count', 'price_with', 'price_without', 'premium', 'rating', 'recom'
    ]].copy()
    display_df.columns = [
        'Équipement', 'Catégorie', 'Présence (%)', 'Logements', 'Prix Médian Avec (€)', 
        'Prix Médian Sans (€)', 'Surcote (€/nuit)', 'Note (/5)', 'Statut & Recommandation'
    ]
    
    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Présence (%)": st.column_config.ProgressColumn(
                "Taux de Présence",
                format="%.1f%%",
                min_value=0,
                max_value=100
            ),
            "Surcote (€/nuit)": st.column_config.NumberColumn(
                "Surcote (€/nuit)",
                format="+%.1f €"
            ),
            "Prix Médian Avec (€)": st.column_config.NumberColumn(
                "Prix Avec",
                format="%.0f €"
            ),
            "Prix Médian Sans (€)": st.column_config.NumberColumn(
                "Prix Sans",
                format="%.0f €"
            ),
            "Note (/5)": st.column_config.NumberColumn(
                "Note Moyenne",
                format="%.2f ⭐"
            )
        }
    )
    
    st.markdown("#### 💡 Conseils Stratégiques Conciergerie pour Valoriser le Bien du Propriétaire")
    st.info("""
    - **Climatisation & Rafraîchissement (+30 €/nuitée) :** Seulement ~15% des logements lyonnais sont climatisés. Proposer au propriétaire l'installation d'une climatisation ou a minima d'un ventilateur haut de gamme est l'argument n°1 pour doper le prix l'été et la rentabilité globale.
    - **Pack Famille & Lit Bébé (+50 €/nuitée) :** L'ajout d'un lit parapluie et d'une chaise haute (coût < 100 €) débloque immédiatement le segment familial et les séjours longue durée à fort panier moyen.
    - **Arrivée Autonome (+23 €/nuitée) :** L'installation d'une serrure connectée ou boîte à clés sécurisée améliore le confort voyageur tout en éliminant les coûts de check-in physique pour votre équipe.
    - **Machine à café & Prestation d'accueil (+26 €/nuitée) :** Mettre à disposition une machine à dosettes (Nespresso) et des capsules d'accueil est un investissement minime qui impacte directement la satisfaction et le taux de conversion.
    """)

# ==========================================================
# TAB 4: CALENDRIER & SAISONNALITÉ
# ==========================================================
with tab4:
    st.subheader("📅 Analyse Prévisionnelle des Réservations & Saisonnalité")
    st.caption("Données prévisionnelles calculées dynamiquement sur les annonces filtrées (Inside Airbnb, 12 prochains mois).")
    
    # Dynamic DuckDB query on the filtered listings
    filtered_ids = tuple(df['id'].tolist())
    df_calendar = query_calendar_forecast(filtered_ids)
    
    if len(df_calendar) > 0:
        is_filtered = len(df) < len(df_raw)
        
        # Summary KPIs for the filtered selection
        total_days = df_calendar['total_days'].sum()
        booked_days = df_calendar['booked_days'].sum()
        avg_occ_forecast = (booked_days / total_days * 100) if total_days > 0 else 0
        
        peak_row = df_calendar.loc[df_calendar['occupancy_rate'].idxmax()]
        low_row = df_calendar.loc[df_calendar['occupancy_rate'].idxmin()]
        
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Taux d'Occup. Prévisionnel</div>
                <div class="kpi-value">{avg_occ_forecast:.1f}%</div>
                <div class="kpi-sub">Moyenne 12 mois (Sélection)</div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Mois Pic de Demande</div>
                <div class="kpi-value">{peak_row['month']}</div>
                <div class="kpi-sub">{peak_row['occupancy_rate']:.1f}% d'occupation</div>
            </div>
            """, unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Mois Creux (Basse Saison)</div>
                <div class="kpi-value">{low_row['month']}</div>
                <div class="kpi-sub">{low_row['occupancy_rate']:.1f}% d'occupation</div>
            </div>
            """, unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Nuitées Réservées / Bloquées</div>
                <div class="kpi-value">{int(booked_days):,}</div>
                <div class="kpi-sub">Sur {len(df):,} annonces filtrées</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        col_cal1, col_cal2 = st.columns(2)
        
        with col_cal1:
            fig_occ_month = go.Figure()
            
            # Benchmark baseline if a filter is active
            if is_filtered and len(df_calendar_market) > 0:
                market_sub = df_calendar_market[df_calendar_market['month'] <= '2027-09']
                fig_occ_month.add_trace(go.Scatter(
                    x=market_sub['month'],
                    y=market_sub['occupancy_rate'],
                    mode='lines+markers',
                    name='Moyenne Grand Lyon (Total)',
                    line=dict(color='#94A3B8', width=2, dash='dash'),
                    marker=dict(size=5, color='#94A3B8'),
                    hovertemplate='<b>Lyon Global</b><br>Mois: %{x}<br>Taux: %{y:.1f}%<extra></extra>'
                ))
            
            sel_label = f"Sélection Filtrée ({len(df):,} annonces)" if is_filtered else "Ensemble du Marché"
            fig_occ_month.add_trace(go.Scatter(
                x=df_calendar['month'],
                y=df_calendar['occupancy_rate'],
                mode='lines+markers',
                name=sel_label,
                line=dict(color='#FF5A5F', width=3),
                marker=dict(size=7, color='#FF5A5F'),
                hovertemplate=f'<b>{sel_label}</b><br>Mois: %{{x}}<br>Taux: %{{y:.1f}}%<extra></extra>'
            ))
            
            min_y = max(30, int(df_calendar['occupancy_rate'].min() - 8))
            max_y = min(100, int(df_calendar['occupancy_rate'].max() + 8))
            
            fig_occ_month.update_layout(
                title=f"Taux d'Occupation Prévisionnel Mois par Mois (%)",
                xaxis_title="Mois",
                yaxis_title="Taux d'occupation (%)",
                template="plotly_white",
                yaxis=dict(range=[min_y, max_y]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_occ_month, width="stretch")
            
        with col_cal2:
            fig_days = go.Figure()
            fig_days.add_trace(go.Bar(
                x=df_calendar['month'],
                y=df_calendar['booked_days'],
                name='Jours Réservés / Bloqués',
                marker_color='#FF5A5F'
            ))
            fig_days.add_trace(go.Bar(
                x=df_calendar['month'],
                y=df_calendar['available_days'],
                name='Jours Disponibles à la vente',
                marker_color='#00A699'
            ))
            fig_days.update_layout(
                barmode='stack',
                title=f"Volume Jours Réservés vs Disponibles ({len(df):,} annonces)",
                xaxis_title="Mois",
                yaxis_title="Jours cumulés",
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_days, width="stretch")
            
        st.markdown("#### Conseils Stratégiques de Tarification Saisonnière pour Conciergerie à Lyon")
        st.info("""
        - **Pic de Décembre (Fête des Lumières) :** Explosion de la demande lors du premier week-end de décembre. Multiplier les tarifs par 2.0 à 3.0 et imposer une durée minimale de 3 nuits.
        - **Printemps & Automne (Tourisme d'affaires & Gastronomie) :** Forte activité MICE (salons Eurexpo, congrès à la Cité Internationale). Tarifs soutenus en semaine (mardi à jeudi).
        - **Été (Juillet - Août) :** Tourisme familial et étapes sur la route des vacances (A6/A7). Augmenter le tarif sur les logements 2 et 3 chambres avec climatisation et parking.
        """)
    else:
        st.info("Données de calendrier non disponibles pour la sélection active.")

# ==========================================================
# TAB 5: SIMULATEUR DE PRIX & RENTABILITÉ CONCIERGERIE
# ==========================================================
with tab5:
    st.subheader("💡 Simulateur d'Estimation & Devis de Prestations Conciergerie")
    
    # 1. Sélection directe des annonces comparables issues des Filtres Marché du volet latéral
    comp_df = df[(df['price_clean'].notna()) & (df['price_clean'] > 0)].copy()
    
    if len(comp_df) == 0:
        st.warning("⚠️ Aucune annonce ne correspond aux filtres sélectionnés dans le volet latéral gauche. Veuillez ajuster les filtres du marché pour lancer la simulation.")
    else:
        st.caption(f"🎯 Simulation basée sur l'échantillon des **{len(comp_df):,} annonces** sélectionnées via les filtres latéraux.")
        
        @st.fragment
        def render_simulator_fragment(comp_subset):
            # 2. Paramètres de Prestations & Exploitation
            st.markdown("##### ⚙️ Paramètres de Prestations & Exploitation")
            
            # Taux d'occupation moyen de référence calculé sur l'échantillon comparable (Modèle C)
            active_comps = comp_subset[comp_subset['is_active'] & (comp_subset['availability_365'] > 0)]
            if len(active_comps) > 0 and 'estimated_occupancy_rate' in active_comps.columns:
                market_occ_pct = int(round(active_comps['estimated_occupancy_rate'].mean() * 100))
                market_occ_pct = max(30, min(95, market_occ_pct))
            else:
                market_occ_pct = 65

            c_p1, c_p2, c_p3, c_p4 = st.columns(4)
            
            with c_p1:
                sim_occ = st.slider(
                    "Taux d'occupation estimé (%)",
                    min_value=30,
                    max_value=95,
                    value=market_occ_pct,
                    step=1,
                    help=f"Moyenne observée sur vos annonces comparables (Modèle C hybride) : {market_occ_pct} %. Ajustable selon vos hypothèses de remplissage."
                )
            with c_p2:
                sim_rotations = st.slider(
                    "Réservations moyennes / mois",
                    min_value=1,
                    max_value=15,
                    value=7,
                    step=1,
                    help="Nombre moyen de séjours (rotations de voyageurs) par mois."
                )
            with c_p3:
                sim_menage = st.number_input(
                    "Frais de ménage / rotation (€)",
                    min_value=0,
                    max_value=400,
                    value=40,
                    step=5,
                    help="Coût moyen par séjour pour le ménage et la blanchisserie."
                )
            with c_p4:
                sim_commission = st.number_input(
                    "Commission Conciergerie (%)",
                    min_value=5,
                    max_value=40,
                    value=20,
                    step=1
                )
                
            # 3. Calculs financiers
            base_median = float(comp_subset['price_clean'].median()) if len(comp_subset) > 0 and pd.notna(comp_subset['price_clean'].median()) else 95.0
            est_adr = base_median
            est_occ = sim_occ / 100.0
            
            ann_booked_days = int(365 * est_occ)
            brut_annuel = est_adr * ann_booked_days
            brut_mensuel = brut_annuel / 12
            
            # Étape 1 : Passer du brut au net de frais de plateforme (18,60 % TTC déduits)
            frais_airbnb = brut_annuel * 0.1860
            frais_airbnb_mensuel = frais_airbnb / 12
            net_plateforme = brut_annuel - frais_airbnb
            net_plat_mensuel = net_plateforme / 12
            
            # Étape 2 : Passer du net plateforme au Net de ménage (frais ménage * réservations/mois * 12)
            menage_mensuel = float(sim_menage * sim_rotations)
            menage_annuel = menage_mensuel * 12
            net_apres_menage = max(0.0, net_plateforme - menage_annuel)
            net_apres_menage_mensuel = net_apres_menage / 12
            
            # Étape 3 : Passer du net ménage au Net commission de conciergerie
            comm_annuelle = net_apres_menage * (sim_commission / 100)
            comm_mensuelle = comm_annuelle / 12
            
            # Revenu Net Final Propriétaire
            net_proprietaire = net_apres_menage - comm_annuelle
            net_prop_mensuel = net_proprietaire / 12
            pct_net_brut = (net_proprietaire / brut_annuel * 100) if brut_annuel > 0 else 0.0

            st.markdown("---")
            
            # 4. Indicateurs clés synthétiques
            kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
            kpi1.metric("Prix par Nuit (ADR)", f"{est_adr:.0f} €", "Médiane comparables")
            kpi2.metric("Taux d'Occupation", f"{sim_occ} %", f"~{ann_booked_days}j loués / an")
            kpi3.metric("CA Brut Voyageurs", f"{brut_annuel:,.0f} €".replace(',', ' '), f"{brut_mensuel:,.0f} € / mois")
            kpi4.metric(f"Honoraires ({sim_commission}%)", f"{comm_annuelle:,.0f} €".replace(',', ' '), f"{comm_mensuelle:,.0f} € / mois")
            kpi5.metric("👉 Net Propriétaire", f"{net_proprietaire:,.0f} €".replace(',', ' '), f"{net_prop_mensuel:,.0f} € / mois ({pct_net_brut:.1f}% brut)")
            
            # 5. Tableau récapitulatif financier cascade
            st.markdown(f"""
            | Étape Financière | Modalités / Assiette | Montant Annuel | Moyenne Mensuelle |
            | :--- | :---: | :---: | :---: |
            | **1. CA Brut Voyageurs (Volume d'affaires)** | {est_adr:.0f} €/nuit × {ann_booked_days}j ({sim_occ} % occ.) | **{brut_annuel:,.0f} €** | **{brut_mensuel:,.0f} €** |
            | Frais Plateforme Airbnb (18,60 % TTC) | - 18,6 % du Brut | - {frais_airbnb:,.0f} € | - {frais_airbnb_mensuel:,.0f} € |
            | **2. Net Plateforme (Versé par Airbnb)** | 81,4 % du Brut | **{net_plateforme:,.0f} €** | **{net_plat_mensuel:,.0f} €** |
            | Frais de Ménage & Blanchisserie | {sim_rotations} séjours/mois × {sim_menage:.0f} € | - {menage_annuel:,.0f} € | - {menage_mensuel:,.0f} € |
            | **3. Net après Ménage** | Assiette Commission | **{net_apres_menage:,.0f} €** | **{net_apres_menage_mensuel:,.0f} €** |
            | Honoraires Conciergerie ({sim_commission} % du Net Ménage) | Facturation de prestations | - {comm_annuelle:,.0f} € | - {comm_mensuelle:,.0f} € |
            | **👉 REVENU NET FINAL PROPRIÉTAIRE** | **{pct_net_brut:.1f} % du Brut** | **{net_proprietaire:,.0f} €** | **{net_prop_mensuel:,.0f} €** |
            """)
            
            # 6. Accordéons pour les détails
            with st.expander("📅 Fourchette tarifaire par saisonnalité"):
                f_col1, f_col2, f_col3 = st.columns(3)
                f_col1.metric("Basse Saison", f"{est_adr*0.8:.0f} €")
                f_col2.metric("Moyenne Saison", f"{est_adr:.0f} €")
                f_col3.metric("Haute Saison / Événements", f"{est_adr*1.6:.0f} €")
                
            with st.expander(f"🔎 Échantillon des annonces comparables du marché ({min(10, len(comp_subset))} sélectionnées)"):
                sort_cols = ['review_scores_rating']
                if 'number_of_reviews' in comp_subset.columns:
                    sort_cols.append('number_of_reviews')
                top_comps = comp_subset.sort_values(sort_cols, ascending=False).head(10)[[
                    'id', 'neighbourhood_cleansed', 'name', 'accommodates', 'bedrooms', 'bathrooms_clean', 'price_clean', 'review_scores_rating', 'listing_url'
                ]].copy().reset_index(drop=True)
                top_comps.insert(0, 'Fiche', '🔎 Ouvrir')
                
                st.dataframe(
                    top_comps.rename(columns={
                        'neighbourhood_cleansed': 'Secteur',
                        'name': 'Annonce concurrente',
                        'accommodates': 'Voyageurs',
                        'bedrooms': 'Chambres',
                        'bathrooms_clean': 'Salles de bain',
                        'price_clean': 'Prix (€)',
                        'review_scores_rating': 'Note',
                        'listing_url': 'Lien Airbnb'
                    }),
                    column_config={
                        'id': None,
                        'Fiche': st.column_config.ButtonColumn('Fiche', width='small', key='btn_click_sim_comps'),
                        'Lien Airbnb': st.column_config.LinkColumn('Lien Airbnb', display_text='Voir sur Airbnb')
                    },
                    hide_index=True,
                    width='stretch'
                )
                btn_sim = st.session_state.get('btn_click_sim_comps')
                if btn_sim:
                    row_idx = btn_sim.row if hasattr(btn_sim, 'row') else btn_sim.get('row')
                    if row_idx is not None and 0 <= row_idx < len(top_comps):
                        sel_id = top_comps.iloc[row_idx]['id']
                        show_listing_modal(sel_id)

            # --- 7. EXPORT DEVIS & FICHE D'ESTIMATION EN 1 CLIC ---
            st.markdown("---")
            st.markdown("### 📄 Fiche d'Estimation & Devis Conciergerie (Export en 1 Clic)")
            st.write(
                "Personnalisez l'identité de votre propriétaire prospect et exportez instantanément un **devis officiel & audit locatif** complet, "
                "avec projection de rentabilité sur 3 scénarios (Prudent, Recommandé, Optimiste), prêt pour vos rendez-vous de négociation."
            )

            # Client customization inputs
            col_cl1, col_cl2, col_cl3 = st.columns(3)
            with col_cl1:
                owner_name = st.text_input("Nom du Propriétaire Hôte :", value="M. / Mme Propriétaire", key="sim_owner_name")
            with col_cl2:
                default_addr = selected_arrs[0] if len(selected_arrs) == 1 else "Lyon (Métropole)"
                owner_address = st.text_input("Adresse ou Quartier du Bien :", value=default_addr, key="sim_owner_addr")
            with col_cl3:
                typology_options = ["Studio", "T1 (1 pièce)", "T2 (2 pièces)", "T3 (3 pièces)", "T4 (4 pièces)", "Maison / Villa"]
                owner_type = st.selectbox("Typologie du Logement :", options=typology_options, index=2, key="sim_owner_type")

            col_cl4, col_cl5 = st.columns([1, 2])
            with col_cl4:
                owner_cap = st.number_input(
                    "Capacité d'accueil (voyageurs) :",
                    min_value=1,
                    max_value=16,
                    value=min(4, max(1, int(selected_acc[1]))),
                    step=1,
                    key="sim_owner_cap"
                )
            with col_cl5:
                owner_note = st.text_input(
                    "Note ou Recommandation personnalisée pour le client :",
                    value="Emplacement stratégique, fort potentiel de valorisation en courte durée via Yield Management.",
                    key="sim_owner_notes"
                )

            # 3 Scenarios Computation
            # 1. Prudent (-10% ADR, -7% occ)
            adr_p = max(30.0, est_adr * 0.90)
            occ_p = max(0.35, est_occ - 0.07)
            days_p = int(365 * occ_p)
            brut_p = adr_p * days_p
            frais_plat_p = brut_p * 0.1860
            net_plat_p = brut_p - frais_plat_p
            menage_p = float(sim_menage * max(1, sim_rotations - 1) * 12)
            net_menage_p = max(0.0, net_plat_p - menage_p)
            comm_p = net_menage_p * (sim_commission / 100.0)
            net_p = net_menage_p - comm_p

            # 2. Median / Recommandé
            adr_m = est_adr
            occ_m = est_occ
            days_m = ann_booked_days
            brut_m = brut_annuel
            frais_plat_m = frais_airbnb
            net_plat_m = net_plateforme
            menage_m = menage_annuel
            comm_m = comm_annuelle
            net_m = net_proprietaire

            # 3. Optimiste (+10% ADR, +7% occ)
            adr_o = est_adr * 1.10
            occ_o = min(0.92, est_occ + 0.07)
            days_o = int(365 * occ_o)
            brut_o = adr_o * days_o
            frais_plat_o = brut_o * 0.1860
            net_plat_o = brut_o - frais_plat_o
            menage_o = float(sim_menage * (sim_rotations + 1) * 12)
            net_menage_o = max(0.0, net_plat_o - menage_o)
            comm_o = net_menage_o * (sim_commission / 100.0)
            net_o = net_menage_o - comm_o

            scenarios_data = {
                'prudent': {'adr': adr_p, 'occ': occ_p * 100, 'days': days_p, 'brut': brut_p, 'frais_airbnb': frais_plat_p, 'menage': menage_p, 'comm': comm_p, 'net': net_p},
                'median': {'adr': adr_m, 'occ': occ_m * 100, 'days': days_m, 'brut': brut_m, 'frais_airbnb': frais_plat_m, 'menage': menage_m, 'comm': comm_m, 'net': net_m},
                'optimist': {'adr': adr_o, 'occ': occ_o * 100, 'days': days_o, 'brut': brut_o, 'frais_airbnb': frais_plat_o, 'menage': menage_o, 'comm': comm_o, 'net': net_o}
            }

            market_stats = {
                'nb_comps': len(comp_subset),
                'adr_median': est_adr,
                'occ_moyen': float(comp_subset['estimated_occupancy_rate'].mean() * 100) if 'estimated_occupancy_rate' in comp_subset.columns else 65.0,
                'revpar_moyen': float(comp_subset['revpar'].mean()) if 'revpar' in comp_subset.columns else 55.0
            }

            client_info = {
                'name': owner_name,
                'address': owner_address,
                'type': owner_type,
                'capacity': int(owner_cap),
                'bedrooms': int(selected_bedrooms[0]) if selected_bedrooms[0] > 0 else 1,
                'sector': default_addr,
                'notes': owner_note
            }

            sim_params_dict = {
                'commission': sim_commission,
                'menage': sim_menage,
                'rotations': sim_rotations,
                'ref_id': f"{int(owner_cap)}{int(selected_bedrooms[0]) if selected_bedrooms[0] > 0 else 1}"
            }

            recommendations = [
                "☕ Machine à café / Nespresso (+12 €/nuit)",
                "🔑 Arrivée autonome 24/7 (+8 % occ)",
                "🍽️ Lave-vaisselle (+9 €/nuit)",
                "📶 Wifi haut débit & espace de travail"
            ]

            # Generate files
            pdf_bytes = generate_mandate_pdf(client_info, sim_params_dict, scenarios_data, market_stats, recommendations)
            html_str = generate_mandate_html(client_info, sim_params_dict, scenarios_data, market_stats, recommendations)

            # Download action buttons
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    label="📄 Télécharger le Devis Officiel en PDF (Prêt à signer)",
                    data=pdf_bytes,
                    file_name=f"Devis_Conciergerie_{owner_name.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key="btn_dl_mandate_pdf"
                )
            with col_dl2:
                st.download_button(
                    label="🌐 Télécharger la Fiche d'Estimation Imprimable (.HTML)",
                    data=html_str.encode('utf-8'),
                    file_name=f"Fiche_Estimation_Conciergerie_{owner_name.replace(' ', '_')}.html",
                    mime="text/html",
                    key="btn_dl_mandate_html"
                )

            # Visual preview expander
            with st.expander("👁️ Aperçu de la Proposition Financière & Engagements Conciergerie", expanded=True):
                col_sc1, col_sc2, col_sc3 = st.columns(3)
                with col_sc1:
                    st.markdown("##### 🛡️ Scénario Prudent")
                    st.caption("Hypothèse conservatrice basse saison")
                    st.metric("Net Annuel", f"{net_p:,.0f} €".replace(',', ' '), f"{net_p/12:,.0f} € / mois")
                    st.write(f"• ADR : **{adr_p:.0f} €** / nuit")
                    st.write(f"• Occupation : **{occ_p*100:.0f} %** ({days_p} nuits)")
                    st.write(f"• CA Brut : **{brut_p:,.0f} €**")
                with col_sc2:
                    st.markdown("##### ⭐ Scénario Recommandé")
                    st.caption("Médiane de marché & exploitation optimisée")
                    st.metric("Net Annuel", f"{net_m:,.0f} €".replace(',', ' '), f"{net_m/12:,.0f} € / mois")
                    st.write(f"• ADR : **{adr_m:.0f} €** / nuit")
                    st.write(f"• Occupation : **{occ_m*100:.0f} %** ({days_m} nuits)")
                    st.write(f"• CA Brut : **{brut_m:,.0f} €**")
                with col_sc3:
                    st.markdown("##### 🚀 Scénario Optimiste")
                    st.caption("Haute saison & Yield dynamique agressif")
                    st.metric("Net Annuel", f"{net_o:,.0f} €".replace(',', ' '), f"{net_o/12:,.0f} € / mois")
                    st.write(f"• ADR : **{adr_o:.0f} €** / nuit")
                    st.write(f"• Occupation : **{occ_o*100:.0f} %** ({days_o} nuits)")
                    st.write(f"• CA Brut : **{brut_o:,.0f} €**")

                st.markdown("---")
                st.markdown("##### 🤝 Synthèse des Engagements Inclus dans la Formule Conciergerie")
                col_srv1, col_srv2 = st.columns(2)
                with col_srv1:
                    st.markdown("""
                    * **📸 Shooting photo professionnel & Optimisation de l'annonce** (référencement SEO, multi-diffusion Airbnb / Booking / VRBO).
                    * **📈 Yield Management quotidien :** Tarification algorithmique dynamique selon événements lyonnais (Fête des Lumières, salons Eurexpo, etc.).
                    * **🔑 Accueil & Conciergerie 24/7 :** Sélection rigoureuse des voyageurs, boîte à clés ou accueil physique, assistance réactive 7j/7.
                    """)
                with col_srv2:
                    st.markdown(f"""
                    * **🧹 Ménage Hôtelier & Blanchisserie de qualité supérieure :** Frais de {sim_menage:.0f} € facturés directement aux voyageurs.
                    * **🛡️ Suivi des Cautions & Litiges :** Prise en charge intégrale des démarches et accompagnement AirCover.
                    * **💶 Transparence & Indépendance :** Le propriétaire encaisse directement ses revenus Airbnb, avec honoraires de **{sim_commission:.0f} %** facturés mensuellement.
                    """)

        render_simulator_fragment(comp_df)

# ==========================================================
# TAB 6: EXPLORATEUR D'ANNONCES
# ==========================================================
with tab6:
    st.subheader("📋 Explorateur Détaillé & Export des Annonces de Lyon")
    
    @st.fragment
    def render_explorer_fragment(df_source):
        # Keyword search
        search_query = st.text_input("🔍 Recherche par mot-clé dans le titre de l'annonce ou le nom de l'hôte :")
        df_table = df_source.copy()
        if search_query:
            df_table = df_table[
                df_table['name'].fillna('').str.contains(search_query, case=False) |
                df_table['host_name'].fillna('').str.contains(search_query, case=False)
            ]
            
        display_cols = [
            'id', 'name', 'neighbourhood_cleansed', 'room_type', 'accommodates',
            'bedrooms', 'price_clean', 'estimated_occupancy_rate',
            'estimated_monthly_rev', 'review_scores_rating',
            'number_of_reviews', 'is_superhost', 'host_name', 'host_segment',
            'listing_url'
        ]
        
        max_display = 500
        df_exp = df_table[display_cols].head(max_display).copy().reset_index(drop=True)
        df_exp['estimated_occupancy_rate'] = df_exp['estimated_occupancy_rate'].apply(
            lambda x: (x * 100) if pd.notna(x) and x <= 1.0 else x
        )
        df_exp.insert(0, 'Fiche', '🔎 Ouvrir')
        
        if len(df_table) > max_display:
            st.caption(f"⚡ Affichage optimisé des **{max_display} premières annonces** (sur **{len(df_table):,} annonces**). Le fichier CSV ci-dessous télécharge l'intégralité.")
        else:
            st.caption(f"Affichage de **{len(df_table):,} annonces**.")
            
        st.dataframe(
            df_exp.rename(columns={
                'name': 'Titre',
                'neighbourhood_cleansed': 'Arrondissement',
                'room_type': 'Type',
                'accommodates': 'Capacité',
                'bedrooms': 'Chambres',
                'price_clean': 'Prix / nuit (€)',
                'estimated_occupancy_rate': 'Taux Occ. Est. (%)',
                'estimated_monthly_rev': 'Rev. Mensuel Est. (€)',
                'review_scores_rating': 'Note',
                'number_of_reviews': 'Nb Avis',
                'is_superhost': 'Superhost',
                'host_name': 'Hôte',
                'host_segment': 'Profil Hôte',
                'listing_url': 'Lien Airbnb'
            }),
            column_config={
                'id': None,
                'Fiche': st.column_config.ButtonColumn('Fiche', width='small', key='btn_click_explorer'),
                'Lien Airbnb': st.column_config.LinkColumn('Lien Airbnb', display_text='Voir sur Airbnb'),
                'Taux Occ. Est. (%)': st.column_config.NumberColumn(format="%.1f %%"),
                'Prix / nuit (€)': st.column_config.NumberColumn(format="%d €"),
                'Rev. Mensuel Est. (€)': st.column_config.NumberColumn(format="%d €"),
                'Note': st.column_config.NumberColumn(format="%.2f / 5")
            },
            hide_index=True,
            width="stretch",
            height=520
        )
        btn_exp = st.session_state.get('btn_click_explorer')
        if btn_exp:
            row_idx = btn_exp.row if hasattr(btn_exp, 'row') else btn_exp.get('row')
            if row_idx is not None and 0 <= row_idx < len(df_exp):
                sel_id = df_exp.iloc[row_idx]['id']
                show_listing_modal(sel_id)

        # CSV download button (100% of data)
        csv_data = df_table[display_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Télécharger la sélection complète en CSV ({len(df_table):,} annonces)",
            data=csv_data,
            file_name="airbnb_lyon_conciergerie_data.csv",
            mime="text/csv"
        )

    render_explorer_fragment(df)

# --- FOOTER ---
st.markdown("---")
st.caption("Application développée pour société de conciergerie locative | Source des données brutes : Inside Airbnb (scraped pour Lyon, Auvergne-Rhône-Alpes, France).")
