import os
import folium
import osmnx as ox
import streamlit as st
from rapidfuzz import process
from streamlit_folium import st_folium
import pandas as pd

# 📁 Configuration des dossiers
base_dir = "D:/projet_cartographie"
os.makedirs(base_dir, exist_ok=True)

# ⚙️ Paramètres OSMnx
ox.settings.cache_folder = os.path.join(base_dir, "osmnx_cache")
ox.settings.use_cache = True

# 🌍 Lieu à cartographier
place_name = "Cazouls-lès-Béziers, France"
graph = ox.graph_from_place(place_name, network_type="drive")
edges = ox.graph_to_gdfs(graph, nodes=False)

# 🚫 / 🔏️ Rues à statut connu
rues_interdites = {"rue de la république", "rue condorcet", "rue ampère", "rue hoche", "rue louis blanc", "rue alfred musset", "rue villaret de joyeuse",
"rue pascal", "rue lamartine", "rue arago", "impasse lavoisier", "rue camille desmoulins", "rue lapérouse", "rue championnet", "boulevard sadi carnot", "rue geoffre", "rue fabre d'églantine", 
"rue surcouf", "impasse berryer", "rue du docteur cot", "rue boissy d'anglas", "place des cent quarante", "rue alexandre cabanel", "rue vergniaud", "impasse achille guilhem", "rue balzac", 
"place émile zola", "rue rouget de lisle", "rue lafontaine", "rue barbaroux", "rue bayard", "chemin de montmajou", "rue des mimosas"}
rues_sans_cs = {"rue barbes", "rue kléber", "rue aubert", "rue villebois-mareuil", "rue du 22 septembre", "rue xavier landes", "rue barbès", "rue jean bart", "rue maréchal bugeaud",""}

# 🔎 Préparation des noms de rues détectés
noms_detectes = set()
for _, row in edges.iterrows():
    noms = row.get("name", "")
    if isinstance(noms, list):
        noms_detectes.update([str(n).lower() for n in noms])
    elif pd.notna(noms):
        noms_detectes.add(str(noms).lower())

# 🔼️ Interface Streamlit
st.title("🔼️ Carte des rues de livraison – Cazouls-lès-Béziers")
recherche = st.text_input("🔎 Rechercher une rue :", "")

# ✅ Filtres dans la barre latérale
st.sidebar.title("🧹 Filtres d'affichage")
afficher_rues_interdites = st.sidebar.checkbox("Afficher les rues interdites", value=True)
afficher_rues_sans_cs = st.sidebar.checkbox("Afficher les rues sans CS", value=True)
afficher_om = st.sidebar.checkbox("Afficher les poubelles OM", value=True)
afficher_verre = st.sidebar.checkbox("Afficher les poubelles Verre", value=True)
afficher_recyclage = st.sidebar.checkbox("Afficher les poubelles Recyclage", value=True)
afficher_papier = st.sidebar.checkbox("Afficher les poubelles Papier", value=True)

# 🔎 Traitement de la recherche floue
resultat = None
if recherche.strip():
    match, score, _ = process.extractOne(recherche.lower(), noms_detectes)
    if score >= 60:
        resultat = match
        st.success(f"Résultat le plus proche : **{match}** ({score}%)")
    else:
        st.warning("Aucune rue correspondante trouvée.")

# 🔧 Fonction pour extraire les noms
def extraire_noms(n):
    if isinstance(n, list):
        return [str(x).lower() for x in n]
    elif pd.notna(n):
        return [str(n).lower()]
    return []

# 📍 Création de la carte
center = ox.geocode(place_name)
m = folium.Map(location=center, zoom_start=15)

# 📂 Ajout des rues avec couleur
for _, row in edges.iterrows():
    noms_rue = extraire_noms(row.get("name", ""))
    coords = [(lat, lon) for lon, lat in row["geometry"].coords]

    if resultat and resultat in noms_rue:
        color = "green"
        statut = "🔍 Rue recherchée"
        weight = 8
    elif any(n in rues_interdites for n in noms_rue) and afficher_rues_interdites:
        color = "red"
        statut = "🚫 Interdite à la livraison"
        weight = 4
    elif any(n in rues_sans_cs for n in noms_rue) and afficher_rues_sans_cs:
        color = "orange"
        statut = "🔇️ Rue sans CS"
        weight = 4
    else:
        continue

    nom_affiche = row.get("name", "Rue sans nom")
    popup = f"<b>{nom_affiche}</b><br>{statut}"
    folium.PolyLine(coords, color=color, weight=weight, popup=folium.Popup(popup)).add_to(m)

fichier_collecte = os.path.join(base_dir, "points_collecte.csv")
if os.path.exists(fichier_collecte):
    df_points = pd.read_csv(fichier_collecte)
    for _, point in df_points.iterrows():
        type_poubelle = point["type"].lower()

        if type_poubelle == "papier" and afficher_papier:
            icon = folium.Icon(color="blue")
        elif type_poubelle == "recyclage" and afficher_recyclage:
            icon = folium.Icon(color="orange")
        elif type_poubelle == "verre" and afficher_verre:
            icon = folium.Icon(color="green")
        elif type_poubelle == "ordures" and afficher_om:
            icon = folium.Icon(color="black")
        else:
            continue

        folium.Marker(
            location=[point["lat"], point["lon"]],
            popup=f'{point["nom"]} ({point["type"]})',
            icon=icon,
        ).add_to(m)

# 📂 Export HTML et GeoJSON
export_html = os.path.join(base_dir, "carte_export.html")
export_geojson = os.path.join(base_dir, "carte_export.geojson")

if st.button("📂 Exporter cette carte"):
    m.save(export_html)
    edges.to_file(export_geojson, driver="GeoJSON")
    st.success(f"Carte HTML : {export_html}\nDonnées vectorielles : {export_geojson}")

# 🌐 Affichage Streamlit
st_data = st_folium(m, width=800, height=800)

# 🔀 Coordonnées du clic + formulaire d’ajout
if st_data and st_data.get("last_clicked"):
    coords = st_data["last_clicked"]
    st.info(f"📱 Coordonnées cliquées : **{coords['lat']}, {coords['lng']}**")

    with st.form("formulaire_poubelle"):
        nom = st.text_input("📝 Nom du point (ex : OM 4)")
        type_ = st.selectbox("🥒️ Type de poubelle", ["ordures", "verre", "recyclage", "papier"])
        valider = st.form_submit_button("✅ Ajouter au CSV")

        if valider and nom.strip():
            new_row = pd.DataFrame([{
                "nom": nom.strip(),
                "type": type_,
                "lat": coords["lat"],
                "lon": coords["lng"]
            }])

            if os.path.exists(fichier_collecte):
                df_points = pd.read_csv(fichier_collecte)
                df_points = pd.concat([df_points, new_row], ignore_index=True)
            else:
                df_points = new_row

            df_points.to_csv(fichier_collecte, index=False)
            st.success(f"✅ Point « {nom} » ajouté à `points_collecte.csv` !")
