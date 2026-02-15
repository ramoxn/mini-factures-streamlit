import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import pagesizes
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# -------------------------
# CONFIG
# -------------------------

SHEET_CLIENTS = "clients"

# 🔐 Mot de passe via secrets
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Mot de passe", type="password")
    if pwd == st.secrets["APP_PASSWORD"]:
        st.session_state.auth = True
        st.cache_data.clear()
        st.rerun()
    st.stop()
# -------------------------
# AUTH GOOGLE
# -------------------------

creds_json = base64.b64decode(st.secrets["SERVICE_ACCOUNT_JSON"])
creds_dict = json.loads(creds_json)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(credentials)

# -------------------------
# DRIVE SERVICE
# -------------------------
drive_service = build("drive", "v3", credentials=credentials)

# -------------------------
# DRIVE CONFIG
# -------------------------
PARENT_FOLDER_ID = "1sIipC_Y0MV_rWfg-WbGVjF4QfJ5uayEx"
 
# -------------------------
# DRIVE FUNCTIONS
# -------------------------

def create_invoice_folder(numero_facture, nom_client):
    folder_name = f"{numero_facture}_{nom_client}"

    query = (
        f"'{PARENT_FOLDER_ID}' in parents and "
        f"name='{folder_name}' and "
        f"mimeType='application/vnd.google-apps.folder' and trashed=false"
    )

    results = drive_service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])
    if files:
        return files[0]["id"]

    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [PARENT_FOLDER_ID]
    }

    folder = drive_service.files().create(
        body=folder_metadata,
        fields="id"
    ).execute()

    return folder["id"]


def upload_pdf_to_drive(pdf_buffer, filename, folder_id):
    media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf")

    file_metadata = {
        "name": filename,
        "parents": [folder_id]
    }

    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    return file["id"]
# ----------------------------------------------------------------------

def generate_invoice_pdf(buffer, numero_facture, client_info, lot_info, sous_clients, total, mode_paiement, date_facture):

    doc = SimpleDocTemplate(buffer, pagesize=pagesizes.A4)
    elements = []

    style = ParagraphStyle(name="Normal", fontSize=11)

    elements.append(Paragraph(f"<b>FACTURE N° {numero_facture}</b>", style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Client : {client_info['nom']}", style))
    elements.append(Paragraph(f"{client_info['rue']} - {client_info['ville']}", style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Date : {date_facture}", style))
    elements.append(Paragraph(f"Lieu : {lot_info['nom_lotissement']}", style))
    elements.append(Paragraph(f"{lot_info['rue']} - {lot_info['ville']}", style))
    elements.append(Spacer(1, 20))

    data = [["Désignation", "Qté", "PU TTC", "Total TTC"]]

    for sc in sous_clients:
        designation = f"{sc['intervention']} - {sc['appartement']} - {sc['nom']}"
        data.append([designation, "1", f"{sc['prix']:.2f}", f"{sc['prix']:.2f}"])

    data.append(["", "", "TOTAL", f"{total:.2f} €"])

    table = Table(data, colWidths=[220, 40, 70, 70])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Mode de paiement : {mode_paiement}", style))

    doc.build(elements)
    
# -------------------------------------------------------------------------

def generate_attestation_pdf(buffer, numero_facture, lot_info, sc, date_intervention):

    doc = SimpleDocTemplate(buffer, pagesize=pagesizes.A4)
    elements = []
    style = ParagraphStyle(name="Normal", fontSize=11)

    elements.append(Paragraph("<b>CERTIFICAT DE RAMONAGE</b>", style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"N° {numero_facture}", style))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Nom : {sc['nom']}", style))
    elements.append(Paragraph(f"Résidence : {lot_info['nom_lotissement']} Lot {sc['appartement']}", style))
    elements.append(Paragraph(f"{lot_info['rue']} - {lot_info['ville']}", style))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Date intervention : {date_intervention}", style))
    elements.append(Paragraph(f"Nature : {sc['intervention']} cheminée bois", style))
    elements.append(Spacer(1, 40))

    elements.append(Paragraph("Fait à Puyvalador", style))

    doc.build(elements)
   
# -------------------------
# LOAD SHEETS (anti quota 429)
# -------------------------

PARENT_FOLDER_ID = "1sIipC_Y0MV_rWfg-WbGVjF4QfJ5uayEx"

@st.cache_resource
def get_sheets():
    sheet_clients = client.open_by_key("1FSOi1Eze6jyQaxEZAkbDUfBlXaJWUgAaFxLNNKyA43I").sheet1
    sheet_lotissements = client.open_by_key("1b23PKic-7lUbCslLSCh_r0C4H0hr08tKiGXcjdcrMWs").sheet1
    sheet_factures = client.open_by_key("1AvWHq-t30wgxryEJSm91TgK0dUZhuYP6-Oyb9xX9_DM").sheet1
    return sheet_clients, sheet_lotissements, sheet_factures


sheet_clients, sheet_lotissements, sheet_factures = get_sheets()


# -------------------------
# LOAD DATA (cache 60 sec)
# -------------------------

@st.cache_data(ttl=60)
def load_clients():
    return sheet_clients.get_all_records()

@st.cache_data(ttl=60)
def load_lotissements():
    return sheet_lotissements.get_all_records()

@st.cache_data(ttl=60)
def load_factures():
    return sheet_factures.get_all_records()


clients_data = load_clients()
client_names = [c["nom"] for c in clients_data]

lotissements_data = load_lotissements()
lotissements_names = [l["nom_lotissement"] for l in lotissements_data]

factures_data = load_factures()







# -------------------------
# UI
# -------------------------


    
st.title("Facturation RamoXN")

st.header("Client principal")

selected_client = st.selectbox(
    "Sélectionner un client",
    [""] + client_names
)

client_info = {}

if selected_client:
    client_info = next(c for c in clients_data if c["nom"] == selected_client)
else:
    client_info = {}

# Initialisation session_state
if "client_nom" not in st.session_state:
    st.session_state.client_nom = ""
if "client_rue" not in st.session_state:
    st.session_state.client_rue = ""
if "client_ville" not in st.session_state:
    st.session_state.client_ville = ""
if "client_tel" not in st.session_state:
    st.session_state.client_tel = ""
if "client_email" not in st.session_state:
    st.session_state.client_email = ""

# Si sélection client → remplir les champs
if selected_client:
    st.session_state.client_nom = client_info.get("nom", "")
    st.session_state.client_rue = client_info.get("rue", "")
    st.session_state.client_ville = client_info.get("ville", "")
    st.session_state.client_tel = client_info.get("téléphone", "")
    st.session_state.client_email = client_info.get("email", "")
    
meme_lotissement = st.checkbox("Même adresse lotissement")

if meme_lotissement:
    st.session_state.client_rue = st.session_state.lot_rue
    st.session_state.client_ville = st.session_state.lot_ville

col1, col2 = st.columns(2)

with col1:
    nom = st.text_input("Nom du client", key="client_nom")
    rue = st.text_input("Rue", key="client_rue")
    ville = st.text_input("Ville", key="client_ville")


with col2:
    telephone = st.text_input("Téléphone", key="client_tel")
    email = st.text_input("Email", key="client_email")

copie_avim = st.checkbox("copie Avim")


# -------------------------
# ACTIONS
# -------------------------

colA, colB, colC = st.columns(3)

with colA:
    if st.button("Ajouter client"):
        sheet_clients.append_row([nom, rue, ville, telephone, email])
        st.success("Client ajouté")
        st.cache_data.clear()
        st.rerun()

with colB:
    if st.button("Modifier client") and selected_client:
        cell = sheet_clients.find(selected_client)
        row = cell.row
        sheet_clients.update(f"A{row}:E{row}", [[nom, rue, ville, telephone, email]])
        st.success("Client modifié")
        st.cache_data.clear()
        st.rerun()

with colC:
    if st.button("Supprimer client") and selected_client:
        cell = sheet_clients.find(selected_client)
        sheet_clients.delete_rows(cell.row)
        st.warning("Client supprimé")
        st.cache_data.clear()
        st.rerun()

# -------------------------
# SHEET LOTISSEMENTS
# -------------------------


st.header("Lotissement")

selected_lotissement = st.selectbox(
    "Sélectionner un lotissement",
    [""] + lotissements_names,
    key="select_lot"
)

lot_info = {}

if selected_lotissement:
    lot_info = next(l for l in lotissements_data if l["nom_lotissement"] == selected_lotissement)

# Initialiser session_state
if "lot_nom" not in st.session_state:
    st.session_state.lot_nom = ""
if "lot_rue" not in st.session_state:
    st.session_state.lot_rue = ""
if "lot_ville" not in st.session_state:
    st.session_state.lot_ville = ""

# Si sélection, remplir
if selected_lotissement:
    st.session_state.lot_nom = lot_info.get("nom_lotissement", "")
    st.session_state.lot_rue = lot_info.get("rue", "")
    st.session_state.lot_ville = lot_info.get("ville", "")

meme_lotissement = st.checkbox("Même adresse que client principal")

if meme_lotissement:
    st.session_state.lot_rue = st.session_state.client_rue
    st.session_state.lot_ville = st.session_state.client_ville
   
colL1, colL2 = st.columns(2)

with colL1:
    lot_nom = st.text_input("Nom lotissement", key="lot_nom")

with colL2:
    lot_rue = st.text_input("Rue lotissement", key="lot_rue")
    lot_ville = st.text_input("Ville lotissement", key="lot_ville")
    
colLA, colLB, colLC = st.columns(3)

with colLA:
    if st.button("Ajouter lotissement"):
        sheet_lotissements.append_row([lot_nom, lot_rue, lot_ville])
        st.success("Lotissement ajouté")
        st.cache_data.clear()
        st.rerun()

with colLB:
    if st.button("Modifier lotissement") and selected_lotissement:
        cell = sheet_lotissements.find(selected_lotissement)
        row = cell.row
        sheet_lotissements.update(f"A{row}:C{row}", [[lot_nom, lot_rue, lot_ville]])
        st.success("Lotissement modifié")
        st.cache_data.clear()
        st.rerun()

with colLC:
    if st.button("Supprimer lotissement") and selected_lotissement:
        cell = sheet_lotissements.find(selected_lotissement)
        sheet_lotissements.delete_rows(cell.row)
        st.warning("Lotissement supprimé")
        st.cache_data.clear()
        st.rerun()




# --------------------
# date numéro fact. paiment
# -------------------- 


   
st.header("Détails de la facturation")

import datetime

today = datetime.date.today()

import re
import datetime
def generate_invoice_number():
    now = datetime.datetime.now()
    month = now.strftime("%m")
    year = now.strftime("%y")
    prefix = f"{month}-{year}"

    factures = sheet_factures.get_all_records()

    numeros = []

    for f in factures:
        num = f.get("num", "")
        if num.startswith(prefix):
            match = re.search(r"-(\d{3})$", num)
            if match:
                numeros.append(int(match.group(1)))

    if numeros:
        next_number = max(numeros) + 1
    else:
        next_number = 1

    return f"{prefix}-{next_number:03d}"

if "invoice_number" not in st.session_state:
    st.session_state.invoice_number = generate_invoice_number()
    
colF1, colF2 = st.columns(2)

with colF1:
    date_intervention = st.date_input(
        "Date d'intervention",
        value=today
    )

    numero_facture = st.text_input(
        "Numéro de facture",
        key="invoice_number"
    )

with colF2:
    mode_paiement = st.selectbox(
        "Mode de paiement",
        [ "Virement", "Espèces", "Chèque", "Carte bancaire", "Non payé"]
    )
    
# -----------------------
# sous client
# -----------------------

st.header("Sous-clients")

# -------------------------
# INITIALISATION LISTE
# -------------------------



if "sous_clients" not in st.session_state:
    st.session_state.sous_clients = []

# Champs temporaires
if "temp_nom" not in st.session_state:
    st.session_state.temp_nom = ""

if "temp_appartement" not in st.session_state:
    st.session_state.temp_appartement = ""

if "temp_intervention" not in st.session_state:
    st.session_state.temp_intervention = "Ramonage"

if "temp_prix" not in st.session_state:
    st.session_state.temp_prix = 66.00

colS1, colS2 = st.columns(2)

with colS1:
    st.text_input("Nom du sous-client", key="temp_nom")
    st.text_input("Appartement", key="temp_appartement")

with colS2:
    st.text_input("Type d'intervention", key="temp_intervention")
    st.number_input("Prix TTC", min_value=0.0, step=1.0, key="temp_prix")

# -------------------------
# BOUTON AJOUTER
# -------------------------

if st.button("Ajouter sous-client"):

    if st.session_state.temp_nom.strip() != "":

        st.session_state.sous_clients.append({
            "nom": st.session_state.temp_nom,
            "appartement": st.session_state.temp_appartement,
            "intervention": st.session_state.temp_intervention,
            "prix": st.session_state.temp_prix
        })

        # On supprime les clés avant rerun
        for key in ["temp_nom", "temp_appartement", "temp_intervention", "temp_prix"]:
            if key in st.session_state:
                del st.session_state[key]

        st.success("Sous-client ajouté")
        st.cache_data.clear()
        st.rerun()

    else:
        st.warning("Veuillez entrer un nom de sous-client")


# -------------------------
# BOUTON VISUALISER LISTE
# -------------------------

if st.button("Voir liste des sous-clients"):

    if st.session_state.sous_clients:

        st.subheader("Liste des sous-clients")

        total = 0

        for i, sc in enumerate(st.session_state.sous_clients, start=1):
            st.write(f"{i}. {sc['nom']} | {sc['appartement']} | {sc['intervention']} | {sc['prix']} €")
            total += sc["prix"]

        st.markdown(f"### Total facture : {total:.2f} €")

    else:
        st.info("Aucun sous-client ajouté")
        
# -------------------------------------------------------------------

st.divider()
st.subheader("Génération finale")

if st.button("Générer facture et attestations"):

    if not st.session_state.sous_clients:
        st.warning("Aucun sous-client ajouté")
        st.stop()

    total = sum(sc["prix"] for sc in st.session_state.sous_clients)

    statut = "Payée" if mode_paiement in ["Espèces", "Carte bancaire"] else "Non payée"

    folder_id = create_invoice_folder(numero_facture, nom)

    # ---------- FACTURE ----------
    invoice_buffer = io.BytesIO()
    generate_invoice_pdf(
        invoice_buffer,
        numero_facture,
        client_info,
        lot_info,
        st.session_state.sous_clients,
        total,
        mode_paiement,
        date_intervention
    )
    invoice_buffer.seek(0)

    invoice_filename = f"Facture_{numero_facture}_{nom}.pdf"
    upload_pdf_to_drive(invoice_buffer, invoice_filename, folder_id)

    # ---------- ATTESTATIONS ----------
    for sc in st.session_state.sous_clients:
        attestation_buffer = io.BytesIO()

        generate_attestation_pdf(
            attestation_buffer,
            numero_facture,
            lot_info,
            sc,
            date_intervention
        )

        attestation_buffer.seek(0)

        attestation_filename = f"Attestation_{numero_facture}_{sc['nom']}_Lot{sc['appartement']}.pdf"
        upload_pdf_to_drive(attestation_buffer, attestation_filename, folder_id)

    # ---------- GOOGLE SHEET ----------
    sheet_factures.append_row([
        numero_facture,
        str(date_intervention),
        total,
        statut,
        nom,
        mode_paiement
    ])

    st.success("Facture et attestations générées avec succès 🎉")


