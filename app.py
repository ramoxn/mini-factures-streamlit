import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

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
# SHEET LOTISSEMENTS
# -------------------------



sheet_lotissements = client.open_by_key("1b23PKic-7lUbCslLSCh_r0C4H0hr08tKiGXcjdcrMWs").sheet1

def load_lotissements():
    return sheet_lotissements.get_all_records()

lotissements_data = load_lotissements()
lotissements_names = [l["nom_lotissement"] for l in lotissements_data]



# -------------------------
# LOAD CLIENTS
# -------------------------

sheet_clients = client.open_by_key("1FSOi1Eze6jyQaxEZAkbDUfBlXaJWUgAaFxLNNKyA43I").sheet1

def load_clients():
    data = sheet_clients.get_all_records()
    return data

clients_data = load_clients()
client_names = [c["nom"] for c in clients_data]

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

col1, col2 = st.columns(2)

with col1:
    nom = st.text_input("Nom du client", value=client_info.get("nom", ""))
    rue = st.text_input("Rue", value=client_info.get("rue", ""))
    ville = st.text_input("Ville", value=client_info.get("ville", ""))

with col2:
    telephone = st.text_input("Téléphone", value=client_info.get("téléphone", ""))
    email = st.text_input("Email", value=client_info.get("email", ""))

meme_lotissement = st.checkbox("Même adresse lotissement")

if meme_lotissement:
    lot_nom = nom
    lot_rue = rue
    lot_ville = ville

copie_avim = st.checkbox("copie Avim")

st.header("Lotissement")

selected_lotissement = st.selectbox(
    "Sélectionner un lotissement",
    [""] + lotissements_names
)

lot_info = {}

if selected_lotissement:
    lot_info = next(l for l in lotissements_data if l["nom_lotissement"] == selected_lotissement)

colL1, colL2 = st.columns(2)

with colL1:
    lot_nom = st.text_input("Nom lotissement", value=lot_info.get("nom_lotissement", ""))

with colL2:
    lot_rue = st.text_input("Rue lotissement", value=lot_info.get("rue", ""))
    lot_ville = st.text_input("Ville lotissement", value=lot_info.get("ville", ""))


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

