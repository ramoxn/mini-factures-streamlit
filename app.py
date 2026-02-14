import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials


if "invoice_number" not in st.session_state:
    st.session_state.invoice_number = generate_invoice_number()

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
# LOAD SHEET
# -------------------------

sheet_lotissements = client.open_by_key("1b23PKic-7lUbCslLSCh_r0C4H0hr08tKiGXcjdcrMWs").sheet1

def load_lotissements():
    return sheet_lotissements.get_all_records()

lotissements_data = load_lotissements()
lotissements_names = [l["nom_lotissement"] for l in lotissements_data]


sheet_clients = client.open_by_key("1FSOi1Eze6jyQaxEZAkbDUfBlXaJWUgAaFxLNNKyA43I").sheet1

def load_clients():
    data = sheet_clients.get_all_records()
    return data

clients_data = load_clients()
client_names = [c["nom"] for c in clients_data]

sheet_factures = client.open_by_key("1AvWHq-t30wgxryEJSm91TgK0dUZhuYP6-Oyb9xX9_DM").sheet1

def load_factures():
    return sheet_factures.get_all_records()

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
        st.rerun()

with colB:
    if st.button("Modifier client") and selected_client:
        cell = sheet_clients.find(selected_client)
        row = cell.row
        sheet_clients.update(f"A{row}:E{row}", [[nom, rue, ville, telephone, email]])
        st.success("Client modifié")
        st.rerun()

with colC:
    if st.button("Supprimer client") and selected_client:
        cell = sheet_clients.find(selected_client)
        sheet_clients.delete_rows(cell.row)
        st.warning("Client supprimé")
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
        st.rerun()

with colLB:
    if st.button("Modifier lotissement") and selected_lotissement:
        cell = sheet_lotissements.find(selected_lotissement)
        row = cell.row
        sheet_lotissements.update(f"A{row}:C{row}", [[lot_nom, lot_rue, lot_ville]])
        st.success("Lotissement modifié")
        st.rerun()

with colLC:
    if st.button("Supprimer lotissement") and selected_lotissement:
        cell = sheet_lotissements.find(selected_lotissement)
        sheet_lotissements.delete_rows(cell.row)
        st.warning("Lotissement supprimé")
        st.rerun()
    
st.header("Détails de la facturation")

import datetime

today = datetime.date.today()

# Génération numéro 
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

