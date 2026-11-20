"""
Module de génération de Devis & Fiche d'Estimation de Prestations de Conciergerie.
Conformité stricte Loi Hoguet (conciergerie sans carte G) :
- Zéro mention du terme 'mandat'
- Zéro mention du terme 'gestion'
- Encaissement direct des loyers par le propriétaire hôte
"""

import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_mandate_pdf(client_info, sim_params, scenarios, market_stats, recommendations=None):
    """Génère un document PDF d'estimation et devis de conciergerie au format A4."""
    if recommendations is None:
        recommendations = []

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor('#1E293B')
    brand_red = colors.HexColor('#FF5A5F')
    gray_bg = colors.HexColor('#F8FAFC')
    card_bg = colors.HexColor('#F1F5F9')

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#64748B')
    )
    sec_style = ParagraphStyle(
        'SecTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=brand_red,
        spaceBefore=6,
        spaceAfter=3
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.2,
        textColor=colors.HexColor('#334155')
    )
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    th_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9.2,
        textColor=colors.white,
        alignment=1
    )
    td_style = ParagraphStyle(
        'TD',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.2,
        alignment=1
    )
    td_bold = ParagraphStyle(
        'TDBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9.2,
        alignment=1
    )
    td_left = ParagraphStyle(
        'TDLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.2,
        alignment=0
    )
    td_left_bold = ParagraphStyle(
        'TDLeftBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9.2,
        alignment=0
    )
    legal_style = ParagraphStyle(
        'LegalNote',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor('#64748B'),
        alignment=1
    )

    story = []

    # 1. En-tête officiel
    story.append(Paragraph('ÉTUDE DE POTENTIEL LOCATIF & PROPOSITION DE CONCIERGERIE', title_style))
    today_str = datetime.date.today().strftime('%d/%m/%Y')
    ref_str = f"ESTIM-{datetime.date.today().strftime('%Y%m%d')}-{sim_params.get('ref_id', '01')}"
    story.append(Paragraph(f"Services de Conciergerie & Intendance Locative Lyon • Document Confidentiel • Réf : {ref_str}", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width='100%', thickness=2, color=brand_red, spaceBefore=0, spaceAfter=5))

    # 2. Coordonnées Client & Caractéristiques du Bien
    client_data = [
        [
            Paragraph('<b>PROPRIÉTAIRE HÔTE :</b>', body_style),
            Paragraph(client_info.get('name', 'M. / Mme Propriétaire'), body_bold),
            Paragraph('<b>DATE DU DEVIS :</b>', body_style),
            Paragraph(today_str, body_style)
        ],
        [
            Paragraph('<b>ADRESSE / SECTEUR :</b>', body_style),
            Paragraph(client_info.get('address', 'Lyon'), body_bold),
            Paragraph('<b>HONORAIRES CONCIERGERIE :</b>', body_style),
            Paragraph(f"<b>{sim_params.get('commission', 20)} %</b> sur chiffre d'affaires net", body_bold)
        ],
        [
            Paragraph('<b>LOGEMENT CONCERNÉ :</b>', body_style),
            Paragraph(f"{client_info.get('type', 'Appartement')} • {client_info.get('capacity', 4)} pers. • {client_info.get('bedrooms', 1)} ch.", body_style),
            Paragraph('<b>FRAIS MÉNAGE / SÉJOUR :</b>', body_style),
            Paragraph(f"{sim_params.get('menage', 40)} € (répercutés voyageurs)", body_style)
        ]
    ]
    t_client = Table(client_data, colWidths=[110, 160, 110, 140])
    t_client.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), gray_bg),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(t_client)
    story.append(Spacer(1, 5))

    # 3. Synthèse du Marché Comparable
    story.append(Paragraph('1. SYNTHÈSE DU MARCHÉ COMPARABLE (SECTEUR & TYPOLOGIE)', sec_style))
    mkt_data = [
        [
            Paragraph(f"<b>Biens comparables :</b><br/>{market_stats.get('nb_comps', 0):,} annonces", body_style),
            Paragraph(f"<b>Prix Médian Constaté :</b><br/>{market_stats.get('adr_median', 0):.0f} € / nuit", body_style),
            Paragraph(f"<b>Taux d'Occupation :</b><br/>{market_stats.get('occ_moyen', 0):.0f} % (Modèle C)", body_style),
            Paragraph(f"<b>RevPAR Moyen Secteur :</b><br/>{market_stats.get('revpar_moyen', 0):.0f} € / nuit", body_style)
        ]
    ]
    t_mkt = Table(mkt_data, colWidths=[130, 130, 130, 130])
    t_mkt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), card_bg),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t_mkt)
    story.append(Spacer(1, 5))

    # 4. Tableau Financier des 3 Scénarios d'Exploitation
    story.append(Paragraph('2. PROJECTION FINANCIÈRE EN 3 SCÉNARIOS D\'EXPLOITATION ANNUELLE', sec_style))

    headers = [
        Paragraph('Flux Financiers', th_style),
        Paragraph('Scénario Prudent<br/>(Basse Saison)', th_style),
        Paragraph('Scénario Recommandé<br/>(Médian / Cible)', th_style),
        Paragraph('Scénario Optimiste<br/>(Yield Dynamique)', th_style)
    ]

    sc_rows = [
        [Paragraph('Prix Moyen par Nuit (ADR)', td_left),
         Paragraph(f"{scenarios['prudent']['adr']:.0f} €", td_style),
         Paragraph(f"{scenarios['median']['adr']:.0f} €", td_bold),
         Paragraph(f"{scenarios['optimist']['adr']:.0f} €", td_style)],
        [Paragraph('Taux d\'Occupation Estimé', td_left),
         Paragraph(f"{scenarios['prudent']['occ']:.0f} %", td_style),
         Paragraph(f"{scenarios['median']['occ']:.0f} %", td_bold),
         Paragraph(f"{scenarios['optimist']['occ']:.0f} %", td_style)],
        [Paragraph('Nuitées Louées Estimées', td_left),
         Paragraph(f"{scenarios['prudent']['days']} j/an", td_style),
         Paragraph(f"{scenarios['median']['days']} j/an", td_bold),
         Paragraph(f"{scenarios['optimist']['days']} j/an", td_style)],
        [Paragraph('<b>1. CA Brut Voyageurs (Total)</b>', td_left_bold),
         Paragraph(f"{scenarios['prudent']['brut']:,.0f} €", td_bold),
         Paragraph(f"{scenarios['median']['brut']:,.0f} €", td_bold),
         Paragraph(f"{scenarios['optimist']['brut']:,.0f} €", td_bold)],
        [Paragraph('Frais Plateforme Airbnb (18,60 % TTC)', td_left),
         Paragraph(f"- {scenarios['prudent']['frais_airbnb']:,.0f} €", td_style),
         Paragraph(f"- {scenarios['median']['frais_airbnb']:,.0f} €", td_style),
         Paragraph(f"- {scenarios['optimist']['frais_airbnb']:,.0f} €", td_style)],
        [Paragraph('Frais Ménage & Blanchisserie', td_left),
         Paragraph(f"- {scenarios['prudent']['menage']:,.0f} €", td_style),
         Paragraph(f"- {scenarios['median']['menage']:,.0f} €", td_style),
         Paragraph(f"- {scenarios['optimist']['menage']:,.0f} €", td_style)],
        [Paragraph(f"Honoraires Conciergerie ({sim_params.get('commission', 20)} %)", td_left),
         Paragraph(f"- {scenarios['prudent']['comm']:,.0f} €", td_style),
         Paragraph(f"- {scenarios['median']['comm']:,.0f} €", td_style),
         Paragraph(f"- {scenarios['optimist']['comm']:,.0f} €", td_style)],
        [Paragraph('<b>👉 REVENU NET PROPRIÉTAIRE (AN)</b>', td_left_bold),
         Paragraph(f"<b>{scenarios['prudent']['net']:,.0f} €</b>", td_bold),
         Paragraph(f"<b>{scenarios['median']['net']:,.0f} €</b>", td_bold),
         Paragraph(f"<b>{scenarios['optimist']['net']:,.0f} €</b>", td_bold)],
        [Paragraph('<b>👉 MOYENNE MENSUELLE NETTE</b>', td_left_bold),
         Paragraph(f"<b>{scenarios['prudent']['net']/12:,.0f} €/mois</b>", td_bold),
         Paragraph(f"<b>{scenarios['median']['net']/12:,.0f} €/mois</b>", td_bold),
         Paragraph(f"<b>{scenarios['optimist']['net']/12:,.0f} €/mois</b>", td_bold)],
    ]

    t_fin = Table([headers] + sc_rows, colWidths=[170, 115, 120, 115])
    t_fin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (2,1), (2,-1), colors.HexColor('#EFF6FF')),
        ('BACKGROUND', (0,-2), (-1,-1), colors.HexColor('#DCFCE7')),
        ('TEXTCOLOR', (0,-2), (-1,-1), colors.HexColor('#166534')),
    ]))
    story.append(t_fin)
    story.append(Spacer(1, 5))

    # 5. Prestations de Conciergerie Incluses
    story.append(Paragraph('3. PRESTATIONS INCLUSES DANS NOTRE FORMULE DE CONCIERGERIE', sec_style))
    services_text = (
        '• <b>Mise en valeur & Référencement :</b> Annonce optimisée (titre, descriptif pro, multi-diffusion Airbnb, Booking.com, VRBO).<br/>'
        '• <b>Yield Management :</b> Tarification algorithmique dynamique ajustée chaque jour selon les événements lyonnais.<br/>'
        '• <b>Accueil & Expérience Voyageurs :</b> Organisation des arrivées autonomes ou physiques, assistance et conciergerie 7j/7.<br/>'
        '• <b>Ménage Hôtelier & Blanchisserie :</b> Nettoyage professionnel après chaque séjour, linge de lit & de bain de qualité hôtelière.<br/>'
        '• <b>Transparence & Indépendance :</b> Vous encaissez 100 % de vos revenus Airbnb sur votre compte bancaire. Facturation mensuelle de nos prestations.'
    )
    story.append(Paragraph(services_text, body_style))
    story.append(Spacer(1, 5))

    # 6. Préconisations d'Équipements
    story.append(Paragraph('4. PRÉCONISATIONS ÉQUIPEMENTS & VALEUR AJOUTÉE', sec_style))
    recom_text = ' • '.join([f'<b>{rec}</b>' for rec in recommendations]) if recommendations else 'Machine Nespresso • Arrivée autonome • Wifi haut débit'
    story.append(Paragraph(f"Pour maximiser la note et le prix moyen de votre bien, nous recommandons : {recom_text}.", body_style))
    story.append(Spacer(1, 6))

    # 7. Bloc Signatures
    sig_data = [
        [
            Paragraph('<b>POUR LE PROPRIÉTAIRE HÔTE :</b><br/>Date :<br/>Mention manuscrite <i>« Lu et approuvé, bon pour accord »</i> :<br/><br/><br/>Signature :', body_style),
            Paragraph('<b>POUR LA CONCIERGERIE PRESTATAIRE :</b><br/>Date :<br/>Cachet & Signature du représentant :<br/><br/><br/>Signature :', body_style)
        ]
    ]
    t_sig = Table(sig_data, colWidths=[260, 260])
    t_sig.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
        ('BACKGROUND', (0,0), (-1,-1), gray_bg),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_sig)
    story.append(Spacer(1, 4))

    # 8. Mention de conformité Loi Hoguet
    story.append(Paragraph(
        '<i>Cadre réglementaire (Loi Hoguet) : Ce document présente une estimation prévisionnelle et une proposition de prestations de conciergerie et intendance (contrat de prestations de services). '
        'La conciergerie n\'exerce pas d\'activité d\'entremise immobilière. Le propriétaire hôte conserve la pleine maîtrise de son annonce et encaisse directement les paiements voyageurs sur son compte personnel.</i>',
        legal_style
    ))

    doc.build(story)
    return buf.getvalue()


def generate_mandate_html(client_info, sim_params, scenarios, market_stats, recommendations=None):
    """Génère un document HTML complet d'estimation et devis de conciergerie stylisé pour l'impression directe."""
    if recommendations is None:
        recommendations = []

    today_str = datetime.date.today().strftime('%d/%m/%Y')
    ref_str = f"ESTIM-{datetime.date.today().strftime('%Y%m%d')}-{sim_params.get('ref_id', '01')}"
    recom_badges = ' '.join([
        f'<span style="background:#e0f2fe;color:#0369a1;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-right:6px;">{r}</span>'
        for r in recommendations
    ])

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Étude de Potentiel Locatif & Devis Conciergerie - {client_info.get('name', 'Propriétaire')}</title>
<style>
  @page {{ size: A4; margin: 10mm; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; margin: 0; padding: 18px; font-size: 12.5px; line-height: 1.38; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #ff5a5f; padding-bottom: 8px; margin-bottom: 10px; }}
  .title {{ font-size: 17px; font-weight: bold; color: #0f172a; margin: 0; }}
  .subtitle {{ color: #64748b; font-size: 11px; margin-top: 3px; }}
  .badge {{ background: #fee2e2; color: #ef4444; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: bold; }}
  .box-client {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin-bottom: 10px; font-size: 11.5px; }}
  .section-title {{ font-size: 11.5px; font-weight: bold; color: #ff5a5f; text-transform: uppercase; margin: 12px 0 5px 0; letter-spacing: 0.5px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 7px; margin-bottom: 10px; }}
  .kpi-card {{ background: #f1f5f9; padding: 7px; border-radius: 6px; text-align: center; border: 1px solid #cbd5e1; }}
  .kpi-title {{ font-size: 10.5px; color: #64748b; }}
  .kpi-val {{ font-size: 14.5px; font-weight: bold; color: #0f172a; margin-top: 2px; }}
  .table-fin {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 11.5px; }}
  .table-fin th, .table-fin td {{ border: 1px solid #cbd5e1; padding: 5px 8px; text-align: right; }}
  .table-fin th:first-child, .table-fin td:first-child {{ text-align: left; }}
  .table-fin th {{ background: #1e293b; color: white; }}
  .highlight-rec {{ background: #eff6ff; font-weight: bold; }}
  .highlight-net {{ background: #dcfce7; color: #166534; font-weight: bold; }}
  .services-list {{ background: #f8fafc; border-left: 3px solid #ff5a5f; padding: 7px 11px; border-radius: 0 6px 6px 0; margin-bottom: 10px; font-size: 11px; }}
  .sig-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }}
  .sig-box {{ border: 1px solid #94a3b8; background: #f8fafc; border-radius: 6px; padding: 8px; height: 85px; font-size: 10.5px; }}
  .btn-print {{ background: #ff5a5f; color: white; border: none; padding: 7px 14px; border-radius: 6px; font-weight: bold; cursor: pointer; }}
  .legal-footer {{ font-size: 9.5px; color: #64748b; font-style: italic; margin-top: 8px; text-align: center; }}
  @media print {{
    body {{ padding: 0; }}
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="no-print" style="text-align: right; margin-bottom: 8px;">
  <button class="btn-print" onclick="window.print()">🖨️ Imprimer ou Enregistrer en PDF</button>
</div>
<div class="header">
  <div>
    <div class="title">ÉTUDE DE POTENTIEL LOCATIF & PROPOSITION DE CONCIERGERIE</div>
    <div class="subtitle">Services de Conciergerie & Intendance Locative Lyon • Réf : {ref_str}</div>
  </div>
  <div class="badge">DEVIS ESTIMATIF</div>
</div>

<div class="box-client">
  <div><b>Propriétaire Hôte :</b> {client_info.get('name', 'M. / Mme Propriétaire')}</div>
  <div><b>Date du devis :</b> {today_str} (Valable 30 jours)</div>
  <div><b>Adresse du bien :</b> {client_info.get('address', 'Lyon')}</div>
  <div><b>Honoraires de conciergerie :</b> <b>{sim_params.get('commission', 20)} %</b> sur chiffre d'affaires net</div>
  <div><b>Typologie :</b> {client_info.get('type', 'T2')} • {client_info.get('capacity', 4)} voyageurs ({client_info.get('bedrooms', 1)} ch.)</div>
  <div><b>Frais de ménage :</b> {sim_params.get('menage', 40)} € / séjour (facturés aux voyageurs)</div>
</div>

<div class="section-title">1. Synthèse du Marché Comparable (Secteur & Typologie)</div>
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-title">Biens comparables</div><div class="kpi-val">{market_stats.get('nb_comps', 0):,} annonces</div></div>
  <div class="kpi-card"><div class="kpi-title">Prix Médian Constaté</div><div class="kpi-val">{market_stats.get('adr_median', 0):.0f} € / nuit</div></div>
  <div class="kpi-card"><div class="kpi-title">Taux d'occupation</div><div class="kpi-val">{market_stats.get('occ_moyen', 0):.0f} %</div></div>
  <div class="kpi-card"><div class="kpi-title">RevPAR Moyen</div><div class="kpi-val">{market_stats.get('revpar_moyen', 0):.0f} € / nuit</div></div>
</div>

<div class="section-title">2. Projection Financière en 3 Scénarios d'Exploitation Annuelle</div>
<table class="table-fin">
  <thead>
    <tr>
      <th>Flux Financiers</th>
      <th>Scénario Prudent</th>
      <th class="highlight-rec">Scénario Recommandé</th>
      <th>Scénario Optimiste</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>Prix Moyen par Nuit (ADR)</td><td>{scenarios['prudent']['adr']:.0f} €</td><td class="highlight-rec">{scenarios['median']['adr']:.0f} €</td><td>{scenarios['optimist']['adr']:.0f} €</td></tr>
    <tr><td>Taux d'Occupation Annuel</td><td>{scenarios['prudent']['occ']:.0f} %</td><td class="highlight-rec">{scenarios['median']['occ']:.0f} %</td><td>{scenarios['optimist']['occ']:.0f} %</td></tr>
    <tr><td>Nuitées Louées Estimées</td><td>{scenarios['prudent']['days']} nuits</td><td class="highlight-rec">{scenarios['median']['days']} nuits</td><td>{scenarios['optimist']['days']} nuits</td></tr>
    <tr style="background:#f8fafc;font-weight:600;"><td>1. CA Brut Voyageurs (Total)</td><td>{scenarios['prudent']['brut']:,.0f} €</td><td class="highlight-rec">{scenarios['median']['brut']:,.0f} €</td><td>{scenarios['optimist']['brut']:,.0f} €</td></tr>
    <tr><td>Frais Plateforme Airbnb (18,60 % TTC)</td><td>- {scenarios['prudent']['frais_airbnb']:,.0f} €</td><td class="highlight-rec">- {scenarios['median']['frais_airbnb']:,.0f} €</td><td>- {scenarios['optimist']['frais_airbnb']:,.0f} €</td></tr>
    <tr><td>Frais de Ménage & Blanchisserie</td><td>- {scenarios['prudent']['menage']:,.0f} €</td><td class="highlight-rec">- {scenarios['median']['menage']:,.0f} €</td><td>- {scenarios['optimist']['menage']:,.0f} €</td></tr>
    <tr><td>Honoraires Conciergerie ({sim_params.get('commission', 20)} %)</td><td>- {scenarios['prudent']['comm']:,.0f} €</td><td class="highlight-rec">- {scenarios['median']['comm']:,.0f} €</td><td>- {scenarios['optimist']['comm']:,.0f} €</td></tr>
    <tr class="highlight-net"><td style="font-size:12px;">👉 REVENU NET ANNUEL PROPRIÉTAIRE</td><td>{scenarios['prudent']['net']:,.0f} €</td><td class="highlight-rec" style="color:#166534;font-size:13px;">{scenarios['median']['net']:,.0f} €</td><td>{scenarios['optimist']['net']:,.0f} €</td></tr>
    <tr class="highlight-net"><td>👉 REVENU NET MENSUEL MOYEN</td><td>{scenarios['prudent']['net']/12:,.0f} € / mois</td><td class="highlight-rec" style="color:#166534;font-size:12.5px;">{scenarios['median']['net']/12:,.0f} € / mois</td><td>{scenarios['optimist']['net']/12:,.0f} € / mois</td></tr>
  </tbody>
</table>

<div class="section-title">3. Prestations de Conciergerie Incluses</div>
<div class="services-list">
  <b>• Optimisation de l'Annonce :</b> Shooting photo professionnel, rédaction soignée SEO, multi-diffusion (Airbnb, Booking.com, VRBO).<br/>
  <b>• Yield Management Quotidien :</b> Tarification algorithmique dynamique ajustée chaque jour selon les salons, congrès et événements lyonnais.<br/>
  <b>• Accueil & Conciergerie 24/7 :</b> Sélection des voyageurs, accueil autonome ou personnalisé, conciergerie et assistance 7j/7.<br/>
  <b>• Ménage Hôtelier & Linge :</b> Nettoyage professionnel après chaque séjour, blanchisserie de gamme supérieure, réassort des consommables.<br/>
  <b>• Transparence & Indépendance :</b> Vous encaissez 100 % de vos revenus Airbnb sur votre compte bancaire. Facturation mensuelle de nos prestations.
</div>

<div class="section-title">4. Préconisations d'Équipements & Valeur Ajoutée</div>
<div style="margin-bottom:8px;">{recom_badges}</div>

<div class="sig-grid">
  <div class="sig-box">
    <b>Pour le Propriétaire Hôte :</b><br/>
    Date :<br/>
    Mention manuscrite <i>« Lu et approuvé, bon pour accord »</i> :<br/><br/>
    Signature :
  </div>
  <div class="sig-box">
    <b>Pour la Conciergerie Prestataire :</b><br/>
    Date :<br/>
    Cachet & Signature du représentant :<br/><br/>
    Signature :
  </div>
</div>

<div class="legal-footer">
  Cadre réglementaire (Loi Hoguet) : Ce document présente une estimation prévisionnelle et une proposition de prestations de conciergerie et intendance (contrat de prestations de services).
  La conciergerie n'exerce pas d'activité d'entremise immobilière. Le propriétaire hôte conserve la pleine maîtrise de son annonce et encaisse directement les paiements voyageurs sur son compte personnel.
</div>
</body>
</html>"""
    return html
