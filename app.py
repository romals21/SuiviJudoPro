import streamlit as st
import pandas as pd
import os
import plotly.express as px  # N'oublie pas d'ajouter cette ligne en haut de ton fichier
import datetime  # Ajoute cet import en haut du fichier avec les autres
import json  # <--- AJOUTE CETTE LIGNE ICI
import sheets_utils as sh  # <-- Accès aux données via Google Sheets (remplace les fichiers Excel/JSON locaux)

# Colonnes de référence des deux tableaux de suivi (utilisées à la création
# d'un nouveau judoka et pour vérifier qu'une feuille Google Sheets a bien
# la bonne structure)
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


def get_categorie_auto(annee_naissance, date_combat):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # On accepte les deux noms possibles du fichier (certains PC Windows
    # cachent l'extension .json et l'affichent avec un .txt en plus)
    json_path = os.path.join(BASE_DIR, "categories_age.json")
    if not os.path.exists(json_path):
        json_path = os.path.join(BASE_DIR, "categories_age.json.txt")

    if not os.path.exists(json_path):
        st.error(f"Fichier introuvable : categories_age.json")
        return "Erreur JSON"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Déterminer la clé de saison
    annee_c = pd.to_datetime(date_combat).year
    mois_c = pd.to_datetime(date_combat).month

    # Logique de sélection de la clé saison
    if annee_c == 2018:
        saison_key = "2018_P2" if mois_c >= 1 else "2018_P1"
    else:
        saison_debut = annee_c if mois_c >= 9 else annee_c - 1
        saison_key = f"{saison_debut}_{saison_debut + 1}"

    # Chercher la catégorie correspondante
    if saison_key in data:
        for cat, bornes in data[saison_key].items():
            if cat == "desc":
                continue
            if bornes["min"] == 0:
                if annee_naissance <= bornes["max"]:
                    return cat
            else:
                if bornes["min"] <= annee_naissance <= bornes["max"]:
                    return cat
    return "Inconnue"


def get_saison(date_str):
    date = pd.to_datetime(date_str)
    # Si le mois est >= 9, la saison commence cette année-là
    # Sinon, elle a commencé l'année précédente
    annee_debut = date.year if date.month >= 9 else date.year - 1
    return f"{annee_debut}/{annee_debut + 1}"


# Configuration de la page (doit être tout au début)
st.set_page_config(page_title="Suivi Judo Pro", layout="wide")

# --- LOGIQUE D'ACCUEIL ---
# On liste les judokas existants (une feuille Google Sheets = un judoka)
liste_judokas = sh.lister_judokas()

# Si on n'a pas encore de sélection en session_state, on va sur l'accueil
if "JUDOKA_ACTIF" not in st.session_state:
    st.title("🥋 Bienvenue sur Suivi Judo Pro")
    accueil_tab1, accueil_tab2, accueil_tab3 = st.tabs(
        ["Choisir un profil", "Créer un nouveau profil", "Modifier Profil"]
    )

    with accueil_tab1:
        if not liste_judokas:
            st.info(
                "Aucun judoka trouvé pour l'instant. Crée un profil dans l'onglet suivant."
            )
        else:
            choix = st.selectbox("Sélectionner un judoka existant :", liste_judokas)
            if st.button("Charger ce profil"):
                st.session_state.JUDOKA_ACTIF = choix
                st.rerun()

    with accueil_tab2:
        nouveau_nom = st.text_input("Prénom Nom du nouveau judoka :")
        if st.button("Créer"):
            if nouveau_nom:
                if nouveau_nom not in liste_judokas:
                    with st.spinner("Création de la feuille Google Sheets..."):
                        sh.creer_judoka(
                            nouveau_nom, COLONNES_COMPETITIONS, COLONNES_COMBATS
                        )
                    st.success(f"Profil {nouveau_nom} créé avec succès !")
                    st.rerun()
                else:
                    st.error("Ce profil existe déjà.")
            else:
                st.warning("Veuillez entrer un nom.")

    with accueil_tab3:
        if not liste_judokas:
            st.info("Aucun judoka à modifier pour l'instant.")
        else:
            cible = st.selectbox(
                "Quel profil modifier ?", liste_judokas, key="mod_select"
            )
            profil = sh.charger_profil(cible)

            with st.form("form_profil"):
                nom = st.text_input("Nom / Prénom", value=profil.get("nom", ""))
                dob = st.date_input(
                    "Date de naissance",
                    value=pd.to_datetime(profil.get("dob", "2000-01-01")),
                )
                grados = [
                    "Blanche",
                    "Jaune",
                    "Orange",
                    "Verte",
                    "Bleue",
                    "Marron",
                    "Noire 1D",
                    "Noire 2D",
                    "Noire 3D",
                ]
                grade = st.selectbox(
                    "Grade", grados, index=grados.index(profil.get("grade", "Blanche"))
                )
                poids = st.text_input(
                    "Catégorie de poids actuelle", value=profil.get("poids", "-60")
                )

                if st.form_submit_button("Enregistrer"):
                    data = {"nom": nom, "dob": str(dob), "grade": grade, "poids": poids}
                    sh.sauver_profil(cible, data)
                    st.success("Profil mis à jour !")
                    st.rerun()
    st.stop()

# On a forcément un judoka en session_state ici (sinon st.stop() plus haut)
JUDOKA_ACTIF = st.session_state.JUDOKA_ACTIF

# On s'assure que les 3 onglets (Profil / Competitions / Combats) existent
# bien sur la feuille Google Sheets de ce judoka
sh.assurer_structure(JUDOKA_ACTIF, COLONNES_COMPETITIONS, COLONNES_COMBATS)

# Constantes utilisées partout dans le script à la place des anciens
# chemins de fichiers Excel (DATA_FILE / COMBATS_FILE)
ONGLET_COMPETITIONS = "Competitions"
ONGLET_COMBATS = "Combats"

profil = sh.charger_profil(JUDOKA_ACTIF)

# Calcul de la date de naissance pour le reste du script
annee_naiss = pd.to_datetime(profil.get("dob", "2000-01-01")).year

liste_judokas = sh.lister_judokas()


# --- Définition des constantes ---
POIDS_COMPLETS = {
    "Seniors": [
        "-48",
        "-52",
        "-55",
        "-57",
        "-60",
        "-63",
        "-66",
        "-70",
        "-73",
        "-78",
        "-81",
        "-90",
        "-100",
        "+78",
        "+100",
    ],
    "Juniors": [
        "-44",
        "-48",
        "-52",
        "-55",
        "-57",
        "-60",
        "-63",
        "-66",
        "-70",
        "-73",
        "-78",
        "-81",
        "-90",
        "-100",
        "+78",
        "+100",
    ],
    "Cadets": [
        "-40",
        "-44",
        "-46",
        "-48",
        "-50",
        "-52",
        "-55",
        "-57",
        "-60",
        "-63",
        "-70",
        "-73",
        "-81",
        "-90",
        "+70",
        "+90",
    ],
    "Minimes": [
        "-34",
        "-36",
        "-38",
        "-40",
        "-42",
        "-44",
        "-46",
        "-48",
        "-50",
        "-52",
        "-57",
        "-60",
        "-63",
        "-66",
        "-70",
        "-73",
        "+70",
        "+73",
    ],
    "Benjamins": [
        "-26",
        "-28",
        "-30",
        "-32",
        "-34",
        "-36",
        "-38",
        "-40",
        "-42",
        "-44",
        "-46",
        "-48",
        "-50",
        "-52",
        "-55",
        "-57",
        "-60",
        "-63",
        "-66",
        "+63",
        "+66",
    ],
}


# (L'initialisation des onglets Google Sheets est déjà faite plus haut
# par sh.assurer_structure())

# --- NAVIGATION ---
c1, c2 = st.columns([1, 5])
with c1:
    if st.button("⬅️ Retour"):
        del st.session_state.JUDOKA_ACTIF
        st.rerun()

st.title("🥋 Dashboard Performance Judo")
tab1, tab2, tab3 = st.tabs(
    ["📊 Dashboard", "➕ Ajouter Compétition", "⚔️ Gestion des Combats"]
)

# --- Système de points ---
BAR_POINTS = {
    "WSC": 20,
    "JO": 20,
    "ECC": 10,
    "GS": 8,
    "CF1D": 5,
    "GP": 5,
    "CO": 2.4,
    "EC": 1.6,
    "TL SE": 1.6,
    "CF2D": 1.3,
    "TL E": 1.2,
    "CF3D": 0.6,
    "TL A": 0.6,
    "1/2F": 0.6,
    "REG": 0.45,
    "DEP": 0.1,
    "SUI": 0.1,
    "UNI": 0.1,
}
# Multiplicateurs selon le résultat
MULT_RES = {"Or": 1.0, "Argent": 0.7, "Bronze": 0.5, "5": 0.3, "7": 0.2, "NC": 0.0}


def calculer_points(niveau, resultat):
    pts_base = BAR_POINTS.get(niveau, 0.1)
    return pts_base * MULT_RES.get(resultat, 0)


with tab1:
    # --- PROFIL ET CATÉGORIE DYNAMIQUE ---
    st.header(f"📈 Bilan de Saison : {profil.get('nom', JUDOKA_ACTIF)}")

    # On calcule la catégorie basée sur la date actuelle pour le profil
    cat_actuelle = get_categorie_auto(annee_naiss, datetime.date.today())

    c1, c2, c3, c4 = st.columns(4)  # Passage à 4 colonnes
    c1.metric(
        "Âge",
        f"{(datetime.date.today() - pd.to_datetime(profil.get('dob')).date()).days // 365} ans",
    )
    c2.metric("Grade", profil.get("grade", "Non défini"))
    c3.metric("Poids", profil.get("poids", "-"))
    c4.metric("Catégorie (Auto)", cat_actuelle)  # Affichage de la catégorie calculée
    st.divider()

    if True:  # Les onglets existent forcément (créés par assurer_structure())
        # 1. Chargement et Calcul des saisons
        df_c_raw = sh.charger_df(JUDOKA_ACTIF, ONGLET_COMBATS)
        df_comp_raw = sh.charger_df(JUDOKA_ACTIF, ONGLET_COMPETITIONS)

        # Calcul de la catégorie automatique pour chaque compétition
        df_comp_raw["Categorie_Auto"] = df_comp_raw["Date"].apply(
            lambda x: get_categorie_auto(annee_naiss, x)
        )

        # Identification du surclassement
        df_comp_raw["Surclassement"] = (
            df_comp_raw["Âge"] != df_comp_raw["Categorie_Auto"]
        )

        df_comp_raw["Saison"] = df_comp_raw["Date"].apply(get_saison)

        df_comp_raw["Saison"] = df_comp_raw["Date"].apply(get_saison)
        df_c_raw["Date_Extracted"] = df_c_raw["Compétition"].apply(
            lambda x: str(x).split(" - ")[0]
        )
        df_c_raw["Saison"] = df_c_raw["Date_Extracted"].apply(get_saison)

        # 2. FILTRE MULTI-SAISONS
        saisons_dispo = sorted(df_comp_raw["Saison"].unique(), reverse=True)
        saisons_choisies = st.multiselect(
            "Filtrer par saison(s) :", options=saisons_dispo, default=saisons_dispo[0]
        )

        df_comp_raw = df_comp_raw[df_comp_raw["Saison"].isin(saisons_choisies)]
        df_c_raw = df_c_raw[df_c_raw["Saison"].isin(saisons_choisies)]

        # 3. FILTRE RLN
        LISTE_RLN = [
            "TL A",
            "TL E",
            "EC",
            "CO",
            "CF1D",
            "GP",
            "GS",
            "MAS",
            "ECC",
            "WSC",
            "JO",
        ]
        filtre_rln = st.radio(
            "Affichage des statistiques :",
            ["Toute la saison", "Compétitions RLN uniquement"],
            horizontal=True,
            key="mon_filtre_rln",
        )

        # 4. Filtrage final
        df_comp_raw["Date_Clean"] = pd.to_datetime(df_comp_raw["Date"]).dt.strftime(
            "%Y-%m-%d"
        )
        df_comp = df_comp_raw.copy()

        if filtre_rln == "Compétitions RLN uniquement":
            df_comp = df_comp[df_comp["Niveau"].isin(LISTE_RLN)]

        liste_cles = [
            f"{d} - {l}" for d, l in zip(df_comp["Date_Clean"], df_comp["Lieu"])
        ]
        df = df_c_raw[df_c_raw["Compétition"].isin(liste_cles)]

        # 5. Calcul des points et Performance
        df_comp["Points"] = df_comp.apply(
            lambda x: calculer_points(x["Niveau"], x["Résultat"]), axis=1
        )

        # On compte le nombre de combats par compétition dans df_c_raw
        # On suppose que 'Compétition' dans df_c_raw contient le lieu/date
        nb_combats = df_c_raw["Compétition"].value_counts()

        # On ajoute cette info dans df_comp pour pouvoir trier dessus
        # Il faut que le format soit compatible (ex: "Date - Lieu")
        df_comp["Nb_Combats"] = df_comp.apply(
            lambda x: nb_combats.get(f"{x['Date_Clean']} - {x['Lieu']}", 0), axis=1
        )

        # On trie : d'abord Points (desc), puis Nb_Combats (desc)
        if not df_comp.empty:
            df_sorted = df_comp.sort_values(
                by=["Points", "Nb_Combats"], ascending=[False, False]
            )
            meilleure = df_sorted.iloc[0]
        else:
            meilleure = None

        if meilleure is not None:
            st.subheader("🏆 Performance de la saison")
            col_m1, col_m2 = st.columns([1, 2])
            col_m1.metric(
                "Top Compétition", meilleure["Lieu"], f"{meilleure['Points']:.1f} pts"
            )
            col_m2.info(
                f"Ta meilleure performance est **{meilleure['Lieu']}** ({meilleure['Niveau']}) "
                f"où tu as fini **{meilleure['Résultat']}**."
            )

        # 6. Combats et Graphiques (TOUT EST DÉSORMAIS BIEN INDENTÉ SOUS LE IF NOT DF.EMPTY)
        if not df.empty:
            cols_scores = [
                "Notre_I",
                "Notre_W",
                "Notre_Y",
                "Notre_S",
                "Adv_I",
                "Adv_W",
                "Adv_Y",
                "Adv_S",
            ]
            for col in cols_scores:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

            def get_type_fin(row):
                res = row["Resultat"]
                if res == "Victoire":
                    i, w, y, s_adv = (
                        row["Notre_I"],
                        row["Notre_W"],
                        row["Notre_Y"],
                        row["Adv_S"],
                    )
                else:  # Défaite
                    i, w, y, s_adv = (
                        row["Adv_I"],
                        row["Adv_W"],
                        row["Adv_Y"],
                        row["Notre_S"],
                    )
                if i >= 1:
                    return "Ippon"
                if s_adv >= 3:
                    return "Shidos"
                if w == 2:
                    return "Waza-ari Awasete Ippon"
                if w == 1:
                    return "Waza-ari"
                if y >= 1:
                    return "Yuko"
                return "Aucun"

            df["Type_Fin"] = df.apply(get_type_fin, axis=1)

            # KPIs
            vics = len(df[df["Resultat"] == "Victoire"])
            total = len(df)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Combats", total)
            c2.metric("Victoires", vics)
            c3.metric(
                "Taux de Victoire", f"{(vics/total)*100:.1f}%" if total > 0 else "0%"
            )

            # Graphiques
            col_g1, col_g2 = st.columns(2)
            color_map = {
                "Ippon": "#FF4B4B",
                "Waza-ari Awasete Ippon": "#FFA500",
                "Waza-ari": "#FFD700",
                "Yuko": "#87CEFA",
                "Shidos": "#90EE90",
            }

            def draw_pie(container, df_filtered, title):
                with container:
                    st.subheader(title)
                    d = df_filtered[df_filtered["Type_Fin"] != "Aucun"]
                    if not d.empty:
                        fig = px.pie(
                            d,
                            names="Type_Fin",
                            color="Type_Fin",
                            color_discrete_map=color_map,
                        )
                        fig.update_traces(
                            texttemplate="%{percent:.2%}",
                            textinfo="percent",
                            hoverinfo="label+percent",
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.write("Pas assez de données.")

            draw_pie(
                col_g1, df[df["Resultat"] == "Victoire"], "Répartition des Victoires"
            )
            draw_pie(
                col_g2, df[df["Resultat"] == "Défaite"], "Répartition des Défaites"
            )

            # 1. On prépare les données de surclassement
            info_surclassement = df_comp_raw[
                ["Date_Clean", "Lieu", "Surclassement"]
            ].copy()

            # 2. On crée la colonne "Compétition" pour qu'elle corresponde exactement au format du fichier combats
            info_surclassement["Compétition"] = (
                info_surclassement["Date_Clean"].astype(str)
                + " - "
                + info_surclassement["Lieu"].astype(str)
            )

            # 3. Maintenant, le merge fonctionnera avec la colonne "Compétition" présente des deux côtés
            df = df.merge(
                info_surclassement[["Compétition", "Surclassement"]],
                on="Compétition",
                how="left",
            )

            with st.expander("Historique détaillé"):
                # Fonction pour colorer
                def style_surclassement(row):
                    # Le contenu ici doit être décalé de 4 espaces par rapport au "def"
                    if row.get("Surclassement") == True:
                        return ["background-color: #ff9999"] * len(row)
                    return [""] * len(row)

                # Affichage avec le style appliqué
                st.dataframe(
                    df.style.apply(style_surclassement, axis=1),
                    use_container_width=True,
                )

with tab2:
    st.header("Gestion des Compétitions")

    # Listes de référence pour la structure
    LISTE_NIVEAU = [
        "SUI",
        "DEP",
        "REG",
        "1/2F",
        "TL A",
        "CF3D",
        "TL E",
        "CF2D",
        "TL SE",
        "EC",
        "CO",
        "CF1D",
        "GP",
        "GS",
        "ECC",
        "WSC",
        "JO",
        "UNI",
    ]
    LISTE_RESULTAT = ["Or", "Argent", "Bronze", "5", "7", "NC"]

    action = st.radio(
        "Mode :",
        ["Ajouter une compétition", "Modifier / Supprimer une compétition"],
        horizontal=True,
    )

    if action == "Ajouter une compétition":
        age_sel = st.selectbox(
            "Sélectionnez l'Âge d'abord :", list(POIDS_COMPLETS.keys())
        )
        with st.form("form_comp_add"):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date")
                lieu = st.text_input("Lieu")
            with col2:
                niveau = st.selectbox("Niveau", LISTE_NIVEAU)
                poids = st.selectbox("Catégorie de poids", POIDS_COMPLETS[age_sel])
                resultat = st.selectbox("Résultat", LISTE_RESULTAT)

            if st.form_submit_button("Enregistrer la compétition"):
                df = sh.charger_df(JUDOKA_ACTIF, ONGLET_COMPETITIONS)
                nouvelle = pd.DataFrame(
                    [
                        {
                            "Date": date,
                            "Lieu": lieu,
                            "Niveau": niveau,
                            "Âge": age_sel,
                            "Poids": poids,
                            "Résultat": resultat,
                        }
                    ]
                )
                df = pd.concat([df, nouvelle], ignore_index=True)
                sh.sauver_df(JUDOKA_ACTIF, ONGLET_COMPETITIONS, df)
                st.success(f"Compétition {lieu} enregistrée !")
                st.rerun()

    else:  # Mode Modifier / Supprimer
        df_comp = sh.charger_df(JUDOKA_ACTIF, ONGLET_COMPETITIONS)
        if not df_comp.empty:
            df_comp["Label"] = df_comp["Date"].astype(str) + " - " + df_comp["Lieu"]
            selected_comp = st.selectbox(
                "Choisir la compétition :", df_comp["Label"].tolist()
            )
            idx = df_comp[df_comp["Label"] == selected_comp].index[0]
            row = df_comp.loc[idx]

            # Sélection âge
            age_sel = st.selectbox(
                "Sélectionnez l'Âge d'abord :",
                list(POIDS_COMPLETS.keys()),
                index=list(POIDS_COMPLETS.keys()).index(row["Âge"]),
                key=f"age_{idx}",
            )

            with st.form("form_comp_edit"):
                col1, col2 = st.columns(2)
                with col1:
                    date = st.date_input("Date", value=pd.to_datetime(row["Date"]))
                    lieu = st.text_input("Lieu", value=row["Lieu"])
                with col2:
                    # Niveau sécurisé
                    niveau = st.selectbox(
                        "Niveau",
                        LISTE_NIVEAU,
                        index=(
                            LISTE_NIVEAU.index(row["Niveau"])
                            if row["Niveau"] in LISTE_NIVEAU
                            else 0
                        ),
                    )

                    # Poids sécurisé : on cherche la valeur correspondante dans la liste des poids de l'âge sélectionné
                    options_poids = POIDS_COMPLETS[age_sel]
                    poids_cible = str(row["Poids"])
                    poids_idx = next(
                        (
                            i
                            for i, x in enumerate(options_poids)
                            if str(x) == poids_cible
                        ),
                        0,
                    )
                    poids = st.selectbox(
                        "Catégorie de poids", options_poids, index=poids_idx
                    )

                    # Résultat sécurisé
                    res_cible = str(row["Résultat"])
                    res_idx = next(
                        (
                            i
                            for i, x in enumerate(LISTE_RESULTAT)
                            if str(x) == res_cible
                        ),
                        0,
                    )
                    resultat = st.selectbox("Résultat", LISTE_RESULTAT, index=res_idx)

                if st.form_submit_button("Appliquer les modifications"):
                    date_dt = pd.to_datetime(date)
                    poids_propre = int(str(poids).replace("-", "").strip())

                    df_comp.loc[
                        idx, ["Date", "Lieu", "Niveau", "Âge", "Poids", "Résultat"]
                    ] = [date_dt, lieu, niveau, age_sel, poids_propre, resultat]

                    sh.sauver_df(JUDOKA_ACTIF, ONGLET_COMPETITIONS, df_comp)
                    st.success("Compétition mise à jour !")
                    st.rerun()

with tab3:
    st.header("⚔️ Gestion des Combats")

    # Lecture des fichiers
    df_comp = sh.charger_df(JUDOKA_ACTIF, ONGLET_COMPETITIONS)
    df_combats = sh.charger_df(JUDOKA_ACTIF, ONGLET_COMBATS)

    action = st.radio(
        "Mode :",
        ["Ajouter un combat", "Modifier / Supprimer un combat"],
        horizontal=True,
    )

    if action == "Ajouter un combat":
        if not df_comp.empty:
            df_comp["Label"] = (
                df_comp["Date"].astype(str) + " - " + df_comp["Lieu"].astype(str)
            )
            comp_choisie = st.selectbox(
                "Choisir la compétition", df_comp["Label"].tolist()
            )

            with st.form("form_combat_add"):
                col1, col2 = st.columns(2)
                with col1:
                    tour = st.selectbox(
                        "Tour",
                        [
                            "1/64",
                            "1/32",
                            "1/16",
                            "1/8",
                            "1/4",
                            "1/2",
                            "Finale",
                            "Repêchages T1",
                            "Repêchages T2",
                            "Repêchages T3",
                            "Repêchages T4",
                            "Repêchages T5",
                            "1/2 Repêchages",
                            "Finale Repêchages",
                            "Poules",
                        ],
                    )
                    adversaire = st.text_input("Adversaire")
                    garde = st.selectbox(
                        "Garde", ["Gauche", "Droite", "Ambidextre", "NSP"]
                    )
                    res = st.selectbox("Résultat", ["Victoire", "Défaite"])
                    temps = st.text_input("Temps final (ex: 2:30)")
                with col2:
                    st.subheader("Score (I-W-Y-S)")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**NOUS**")
                        ni = st.number_input("Ippon", 0, 1, key="add_ni")
                        nw = st.number_input("Waza", 0, 2, key="add_nw")
                        ny = st.number_input("Yuko", 0, 5, key="add_ny")
                        ns = st.number_input("Shido", 0, 3, key="add_ns")
                    with c2:
                        st.write("**ADV**")
                        ai = st.number_input("Ippon", 0, 1, key="add_ai")
                        aw = st.number_input("Waza", 0, 2, key="add_aw")
                        ay = st.number_input("Yuko", 0, 5, key="add_ay")
                        as_ = st.number_input("Shido", 0, 3, key="add_as")

                if st.form_submit_button("Enregistrer Combat"):
                    new_data = pd.DataFrame(
                        [
                            {
                                "Compétition": comp_choisie,
                                "Tour": tour,
                                "Adversaire": adversaire,
                                "Garde": garde,
                                "Resultat": res,
                                "Notre_I": ni,
                                "Notre_W": nw,
                                "Notre_Y": ny,
                                "Notre_S": ns,
                                "Adv_I": ai,
                                "Adv_W": aw,
                                "Adv_Y": ay,
                                "Adv_S": as_,
                                "Temps": temps,
                            }
                        ]
                    )
                    df_combats = pd.concat([df_combats, new_data], ignore_index=True)
                    sh.sauver_df(JUDOKA_ACTIF, ONGLET_COMBATS, df_combats)
                    st.success("Combat ajouté !")
                    st.rerun()

    else:  # Mode Modifier / Supprimer
        df_edit = sh.charger_df(JUDOKA_ACTIF, ONGLET_COMBATS)
        # On force chaque colonne en string pour éviter les erreurs de type
        df_edit["Search_Key"] = (
            df_edit["Compétition"].astype(str)
            + " | "
            + df_edit["Tour"].astype(str)
            + " vs "
            + df_edit["Adversaire"].astype(str)
        )

        selected_key = st.selectbox(
            "Sélectionner le combat :", df_edit["Search_Key"].tolist()
        )
        idx = df_edit[df_edit["Search_Key"] == selected_key].index[0]
        row = df_edit.loc[idx]

        with st.form("form_combat_edit"):
            col1, col2 = st.columns(2)
            with col1:
                tours = [
                    "1/64",
                    "1/32",
                    "1/16",
                    "1/8",
                    "1/4",
                    "1/2",
                    "Finale",
                    "Repêchages T1",
                    "Repêchages T2",
                    "Repêchages T3",
                    "Repêchages T4",
                    "Repêchages T5",
                    "1/2 Repêchages",
                    "Finale Repêchages",
                ]
                tour = st.selectbox(
                    "Tour",
                    tours,
                    index=tours.index(row["Tour"]) if row["Tour"] in tours else 0,
                )
                adversaire = st.text_input("Adversaire", value=row["Adversaire"])
                gardes = ["Gauche", "Droite", "Ambidextre", "NSP"]
                garde = st.selectbox(
                    "Garde",
                    gardes,
                    index=gardes.index(row["Garde"]) if row["Garde"] in gardes else 0,
                )
                results = ["Victoire", "Défaite"]
                res = st.selectbox(
                    "Résultat",
                    results,
                    index=(
                        results.index(row["Resultat"])
                        if row["Resultat"] in results
                        else 0
                    ),
                )
                temps = st.text_input("Temps final", value=str(row["Temps"]))

            with col2:
                st.subheader("Score (I-W-Y-S)")
                sub_c1, sub_c2 = st.columns(2)
                with sub_c1:
                    st.write("**NOUS**")
                    ni = st.number_input(
                        "Ippon",
                        0,
                        1,
                        value=int(float(row["Notre_I"])),
                        key=f"mod_ni_{idx}",
                    )
                    nw = st.number_input(
                        "Waza",
                        0,
                        2,
                        value=int(float(row["Notre_W"])),
                        key=f"mod_nw_{idx}",
                    )
                    ny = st.number_input(
                        "Yuko",
                        0,
                        5,
                        value=int(float(row["Notre_Y"])),
                        key=f"mod_ny_{idx}",
                    )
                    ns = st.number_input(
                        "Shido",
                        0,
                        3,
                        value=int(float(row["Notre_S"])),
                        key=f"mod_ns_{idx}",
                    )
                with sub_c2:
                    st.write("**ADV**")
                    ai = st.number_input(
                        "Ippon",
                        0,
                        1,
                        value=int(float(row["Adv_I"])),
                        key=f"mod_ai_{idx}",
                    )
                    aw = st.number_input(
                        "Waza",
                        0,
                        2,
                        value=int(float(row["Adv_W"])),
                        key=f"mod_aw_{idx}",
                    )
                    ay = st.number_input(
                        "Yuko",
                        0,
                        5,
                        value=int(float(row["Adv_Y"])),
                        key=f"mod_ay_{idx}",
                    )
                    as_ = st.number_input(
                        "Shido",
                        0,
                        3,
                        value=int(float(row["Adv_S"])),
                        key=f"mod_as_{idx}",
                    )

            # Un seul bouton de soumission
            if st.form_submit_button("Appliquer les modifications"):
                df_edit.loc[
                    idx,
                    [
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
                    ],
                ] = [
                    tour,
                    adversaire,
                    garde,
                    res,
                    ni,
                    nw,
                    ny,
                    ns,
                    ai,
                    aw,
                    ay,
                    as_,
                    temps,
                ]
                sh.sauver_df(
                    JUDOKA_ACTIF,
                    ONGLET_COMBATS,
                    df_edit.drop(columns=["Search_Key"]),
                )
                st.success("Combat mis à jour !")
                st.rerun()

        # Bouton supprimer en dehors du formulaire
        if st.button("Supprimer ce combat"):
            sh.sauver_df(
                JUDOKA_ACTIF,
                ONGLET_COMBATS,
                df_edit.drop(idx).drop(columns=["Search_Key"], errors="ignore"),
            )
            st.warning("Combat supprimé.")
            st.rerun()
