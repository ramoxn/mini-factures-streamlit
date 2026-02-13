import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
from datetime import datetime

st.title("Mini Gestion Factures")

# 🔐 Mot de passe via secrets
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Mot de passe", type="password")
    if pwd == st.secrets["APP_PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# 🔑 Connexion Google via secrets
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_json = base64.b64decode(st.secrets["SERVICE_ACCOUNT_JSON"])
creds_dict = json.loads(creds_json)

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

sheet = client.open("factures_test").sheet1

st.subheader("Ajouter une facture")

client_nom = st.text_input("Client")
montant = st.number_input("Montant", min_value=0.0)

if st.button("Enregistrer"):
    if client_nom == "":
        st.error("Veuillez entrer un nom client")
    else:
        date = datetime.now().strftime("%d/%m/%Y")
        sheet.append_row([date, client_nom, montant])
        st.success("Facture ajoutée !")
        st.rerun()

st.subheader("Historique")
data = sheet.get_all_values()
st.table(data)

if len(data) > 1:
    total = sum(float(row[2]) for row in data[1:] if row[2])
    st.subheader(f"Total facturé : {total} €")
