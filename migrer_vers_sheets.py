"""
migrer_vers_sheets.py
----------------------
À LANCER UNE SEULE FOIS, en local, depuis le dossier du projet
(là où se trouvent data_judokas/, categories_age.json, etc.)

Ce script :
1. Parcourt chaque dossier judoka dans data_judokas/
2. Ouvre la feuille Google Sheets "SuiviJudoPro - <Nom>" préalablement créée sur le Drive
3. Copie dedans son profil.json, son suivi_competitions et son suivi_combats

Utilisation (dans un terminal, à la racine du projet) :
    python migrer_vers_sheets.py
"""

import os
import glob
import json

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---------------------------------------------------
FICHIER_CLE = "suivijudopro-a5ee1916d1ad.json"
MON_EMAIL = "romainalonso21@gmail.com"

ROOT_DATA = "data_judokas"
PREFIXE = "SuiviJudoPro - "

COLONNES_COMPETITIONS = ["Date", "Lieu", "Niveau", "Âge", "Poids", "Résultat"]
COLONNES_COMBATS = [
    "Compétition",
    "Tour",
    "Adversaire",
    "Garde",
    "Resultat",
    "Notre_I",
    "Notre_W",
    "Notre_Y",
    "Notre_S",
    "Adv_I",
    "Adv_W",
    "Adv_Y",
    "Adv_S",
    "Temps",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
# ----------------------------------------------------------------------


def get_client():
    creds = Credentials.from_service_account_file(FICHIER_CLE, scopes=SCOPES)
    return gspread.authorize(creds)


def trouver_fichier(dossier, base_name):
    """Cherche un fichier base_name.* (xls, xlsx...) dans le dossier."""
    candidats = glob.glob(os.path.join(dossier, f"{base_name}.*"))
    return candidats[0] if candidats else None


def df_vers_valeurs(df):
    df_txt = df.fillna("").astype(str)
    return [df_txt.columns.tolist()] + df_txt.values.tolist()


def migrer():
    if not os.path.exists(ROOT_DATA):
        print(f"Dossier introuvable : {ROOT_DATA}")
        return

    gc = get_client()
    noms = sorted(
        d for d in os.listdir(ROOT_DATA) if os.path.isdir(os.path.join(ROOT_DATA, d))
    )
    print(f"{len(noms)} judoka(s) trouvé(s) : {noms}\n")

    for nom in noms:
        titre = f"{PREFIXE}{nom}"
        dossier = os.path.join(ROOT_DATA, nom)

        print(f"- Migration de '{nom}'...")
        
        # On ouvre directement la feuille existante sur le Drive
        try:
            spreadsheet = gc.open(titre)
        except gspread.SpreadsheetNotFound:
            print(f"  -> ERREUR : Impossible de trouver la feuille '{titre}' sur ton Drive. Vérifie qu'elle est bien partagée avec le bot.")
            continue

        # --- Profil ---
        profil_path = os.path.join(dossier, "profil.json")
        if os.path.exists(profil_path):
            with open(profil_path, "r", encoding="utf-8") as f:
                profil = json.load(f)
        else:
            profil = {
                "nom": nom,
                "dob": "2000-01-01",
                "grade": "Blanche",
                "poids": "-60",
            }
            
        # Gestion de l'onglet Profil (création s'il n'existe pas ou utilisation de sheet1)
        try:
            ws_profil = spreadsheet.worksheet("Profil")
        except gspread.WorksheetNotFound:
            ws_profil = spreadsheet.sheet1
            ws_profil.update_title("Profil")
            
        ws_profil.update(
            values=[list(profil.keys()), [str(v) for v in profil.values()]]
        )

        # --- Compétitions ---
        fichier_comp = trouver_fichier(dossier, "suivi_competitions")
        if fichier_comp:
            df_comp = pd.read_excel(fichier_comp)
        else:
            df_comp = pd.DataFrame(columns=COLONNES_COMPETITIONS)
            print("  (aucun fichier suivi_competitions trouvé, onglet vide créé)")

        try:
            ws_comp = spreadsheet.worksheet("Competitions")
        except gspread.WorksheetNotFound:
            ws_comp = spreadsheet.add_worksheet(
                title="Competitions",
                rows=max(len(df_comp) + 10, 100),
                cols=max(len(df_comp.columns), 10),
            )
        ws_comp.update(values=df_vers_valeurs(df_comp))

        # --- Combats ---
        fichier_combats = trouver_fichier(dossier, "suivi_combats")
        if fichier_combats:
            df_combats = pd.read_excel(fichier_combats)
        else:
            df_combats = pd.DataFrame(columns=COLONNES_COMBATS)
            print("  (aucun fichier suivi_combats trouvé, onglet vide créé)")

        try:
            ws_combats = spreadsheet.worksheet("Combats")
        except gspread.WorksheetNotFound:
            ws_combats = spreadsheet.add_worksheet(
                title="Combats",
                rows=max(len(df_combats) + 10, 100),
                cols=max(len(df_combats.columns), 20),
            )
        ws_combats.update(values=df_vers_valeurs(df_combats))

        print(f"  -> OK : {len(df_comp)} compétition(s), {len(df_combats)} combat(s)\n")

    print("Migration terminée !")


if __name__ == "__main__":
    migrer()