"""
sheets_utils.py
----------------
Toutes les fonctions qui parlent à Google Sheets à la place des anciens
fichiers Excel/JSON locaux.

Organisation choisie :
- Une feuille de calcul Google Sheets = un judoka.
- Son titre est toujours "SuiviJudoPro - <Nom du judoka>".
- Elle contient 3 onglets : "Profil", "Competitions", "Combats".

Pour lister les judokas existants, on demande simplement à Google Sheets
la liste des feuilles auxquelles le compte de service a accès (gc.openall())
et on garde celles qui commencent par le bon préfixe.
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

PREFIXE = "SuiviJudoPro - "

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_client():
    """Ouvre la connexion à Google Sheets à partir des identifiants du
    compte de service stockés dans les Secrets de Streamlit
    (voir secrets.toml.example)."""
    infos_compte = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(infos_compte, scopes=SCOPES)
    return gspread.authorize(creds)


def lister_judokas():
    """Renvoie la liste triée des noms de judokas déjà suivis."""
    gc = get_client()
    feuilles = gc.openall()
    noms = [f.title[len(PREFIXE):] for f in feuilles if f.title.startswith(PREFIXE)]
    return sorted(noms)


def _ouvrir(nom_judoka):
    gc = get_client()
    return gc.open(f"{PREFIXE}{nom_judoka}")


def _ouvrir_onglet(nom_judoka, onglet):
    return _ouvrir(nom_judoka).worksheet(onglet)


def charger_profil(nom_judoka):
    """Renvoie le profil du judoka sous forme de dict (comme l'ancien
    profil.json)."""
    ws = _ouvrir_onglet(nom_judoka, "Profil")
    lignes = ws.get_all_values()
    if len(lignes) >= 2:
        entetes, valeurs = lignes[0], lignes[1]
        return dict(zip(entetes, valeurs))
    return {"nom": nom_judoka, "dob": "2000-01-01", "grade": "Blanche", "poids": "-60"}


def sauver_profil(nom_judoka, data):
    """Écrase l'onglet Profil avec les nouvelles infos (dict)."""
    ws = _ouvrir_onglet(nom_judoka, "Profil")
    cles = list(data.keys())
    ws.clear()
    ws.update(values=[cles, [str(data[c]) for c in cles]])


def charger_df(nom_judoka, onglet):
    """Renvoie le contenu d'un onglet (Competitions ou Combats) sous
    forme de DataFrame pandas, comme le faisait pd.read_excel()."""
    ws = _ouvrir_onglet(nom_judoka, onglet)
    lignes = ws.get_all_values()
    if not lignes:
        return pd.DataFrame()
    entetes = lignes[0]
    if len(lignes) == 1:
        return pd.DataFrame(columns=entetes)
    return pd.DataFrame(lignes[1:], columns=entetes)


def sauver_df(nom_judoka, onglet, df):
    """Écrase un onglet avec le contenu du DataFrame, comme le faisait
    df.to_excel(..., index=False)."""
    ws = _ouvrir_onglet(nom_judoka, onglet)
    df_txt = df.fillna("").astype(str)
    valeurs = [df_txt.columns.tolist()] + df_txt.values.tolist()
    ws.clear()
    ws.update(values=valeurs)


def _partager_avec_moi(spreadsheet):
    """Partage une feuille nouvellement créée avec ton adresse Google,
    pour que tu puisses aussi la consulter/l'éditer directement dans
    Google Sheets si besoin. Configure MON_EMAIL dans les Secrets."""
    mon_email = st.secrets.get("MON_EMAIL")
    if mon_email:
        spreadsheet.share(mon_email, perm_type="user", role="writer")


def creer_judoka(nom_judoka, colonnes_competitions, colonnes_combats):
    """Crée la feuille Google Sheets d'un nouveau judoka avec ses 3 onglets."""
    gc = get_client()
    sh_new = gc.create(f"{PREFIXE}{nom_judoka}")
    _partager_avec_moi(sh_new)

    ws_profil = sh_new.sheet1
    ws_profil.update_title("Profil")
    profil_init = {
        "nom": nom_judoka,
        "dob": "2000-01-01",
        "grade": "Blanche",
        "poids": "-60",
    }
    ws_profil.update(
        values=[list(profil_init.keys()), [str(v) for v in profil_init.values()]]
    )

    ws_comp = sh_new.add_worksheet(
        title="Competitions", rows=200, cols=max(len(colonnes_competitions), 10)
    )
    ws_comp.update(values=[colonnes_competitions])

    ws_combats = sh_new.add_worksheet(
        title="Combats", rows=500, cols=max(len(colonnes_combats), 20)
    )
    ws_combats.update(values=[colonnes_combats])

    return sh_new


def assurer_structure(nom_judoka, colonnes_competitions, colonnes_combats):
    """Vérifie que les 3 onglets existent bien pour ce judoka et les crée
    s'ils manquent (utile après une migration ou une création manuelle
    dans Google Sheets)."""
    spreadsheet = _ouvrir(nom_judoka)
    titres = [ws.title for ws in spreadsheet.worksheets()]

    if "Profil" not in titres:
        ws = spreadsheet.add_worksheet(title="Profil", rows=5, cols=5)
        profil_init = {
            "nom": nom_judoka,
            "dob": "2000-01-01",
            "grade": "Blanche",
            "poids": "-60",
        }
        ws.update(
            values=[list(profil_init.keys()), [str(v) for v in profil_init.values()]]
        )

    if "Competitions" not in titres:
        ws = spreadsheet.add_worksheet(
            title="Competitions", rows=200, cols=max(len(colonnes_competitions), 10)
        )
        ws.update(values=[colonnes_competitions])

    if "Combats" not in titres:
        ws = spreadsheet.add_worksheet(
            title="Combats", rows=500, cols=max(len(colonnes_combats), 20)
        )
        ws.update(values=[colonnes_combats])
