import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Définir le thème de l'application
st.set_page_config(page_title="Gestion des Tickets", layout="wide")

# Titre de l'application
st.title("🔧 Gestion des Tickets")

# Charger le fichier CSV
uploaded_file = st.file_uploader("📁 Choisir un fichier CSV", type="csv")

if uploaded_file is not None:
    try:
        # Lire le fichier CSV avec l'encodage spécifié
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig', delimiter=',')

        # Sélectionner les colonnes nécessaires
        selected_columns = [
            'ID du ticket', 
            'Type', 
            'Organisation',
            'Date - Création (Europe/Paris)', 
            'Date - Clôture (Europe/Paris)', 
            'SLA - Clôture - Statut',
            'Priorité'
        ]
        
        # Vérifier que toutes les colonnes sont présentes dans le dataframe
        if all(col in df.columns for col in selected_columns):
            df = df[selected_columns]
            
            # Convertir les colonnes de date en datetime
            df['Date - Création (Europe/Paris)'] = pd.to_datetime(df['Date - Création (Europe/Paris)'], errors='coerce')
            df['Date - Clôture (Europe/Paris)'] = pd.to_datetime(df['Date - Clôture (Europe/Paris)'], errors='coerce')
            
            # Section pour les données
            st.sidebar.header("Filtres")
            
            # Filtres pour l'utilisateur : Type de ticket
            type_filtre = st.sidebar.multiselect(
                "🔍 Filtrer par type de ticket", 
                options=df['Type'].unique(),
                default=df['Type'].unique()
            )
            
            # Filtres pour l'utilisateur : Organisation
            organisation_filtre = st.sidebar.multiselect(
                "🏢 Filtrer par organisation", 
                options=df['Organisation'].unique(),
                default=df['Organisation'].unique()
            )

            # Filtre pour la période
            date_debut, date_fin = st.sidebar.date_input(
                "📅 Filtrer par période", 
                value=[pd.to_datetime('2024-01-01').date(), pd.to_datetime('2024-01-31').date()],
                min_value=pd.to_datetime('2020-01-01').date(),
                max_value=pd.to_datetime('2024-12-31').date()
            )
            
            # Appliquer les filtres
            if type_filtre:
                df = df[df['Type'].isin(type_filtre)]
                
            if organisation_filtre:
                df = df[df['Organisation'].isin(organisation_filtre)]
                
            if date_debut and date_fin:
                # Convertir les dates de date_debut et date_fin en datetime pour la comparaison
                date_debut = pd.to_datetime(date_debut)
                date_fin = pd.to_datetime(date_fin)
                
                df = df[(df['Date - Création (Europe/Paris)'] >= date_debut) & 
                        (df['Date - Création (Europe/Paris)'] <= date_fin)]
            
            # Calculer les métriques pour le graphique
            ouvertures = df[df['Date - Création (Europe/Paris)'].between(date_debut, date_fin)]
            ouvertures = ouvertures.groupby(ouvertures['Date - Création (Europe/Paris)'].dt.date).size().reset_index(name='Ouvertures')
            
            clotures = df[df['Date - Clôture (Europe/Paris)'].between(date_debut, date_fin)]
            clotures = clotures.groupby(clotures['Date - Clôture (Europe/Paris)'].dt.date).size().reset_index(name='Clotures')
            
            backlog = df[((df['Date - Création (Europe/Paris)'] <= date_fin) & 
                          ((df['Date - Clôture (Europe/Paris)'] > date_fin) | (df['Date - Clôture (Europe/Paris)'].isna())))]
            backlog = backlog.groupby(backlog['Date - Création (Europe/Paris)'].dt.date).size().reset_index(name='Backlog')

            # Fusionner les données pour le graphique sur la colonne Date
            df_graph = pd.merge(ouvertures, clotures, left_on='Date - Création (Europe/Paris)', right_on='Date - Clôture (Europe/Paris)', how='outer', suffixes=('_Ouvertures', '_Clotures')).fillna(0)
            df_graph = pd.merge(df_graph, backlog, left_on='Date - Création (Europe/Paris)', right_on='Date - Création (Europe/Paris)', how='outer').fillna(0)

            # Créer la colonne Date pour le graphique
            df_graph['Date'] = df_graph['Date - Création (Europe/Paris)'].combine_first(df_graph['Date - Clôture (Europe/Paris)'])
            
            # Remplacer les dates invalides ou égales à 1970-01-01
            df_graph['Date'] = df_graph['Date'].apply(
                lambda x: x if pd.notna(x) and x != pd.Timestamp(0) else pd.NaT
            )
            
            # Supprimer les lignes avec des dates invalides
            df_graph = df_graph.dropna(subset=['Date'])
            df_graph = df_graph[df_graph['Date'] != 0 ]
            
            # Afficher les données du graphique pour vérifier
            st.subheader("📊 Données pour le graphique")
            st.write(df_graph)
            
            # Créer le graphique interactif avec Plotly
            fig = go.Figure()

            # Ajouter les barres pour Ouvertures et Clôtures
            fig.add_trace(go.Bar(x=df_graph['Date'], y=df_graph['Ouvertures'], name='Ouvertures', marker_color='skyblue'))
            fig.add_trace(go.Bar(x=df_graph['Date'], y=df_graph['Clotures'], name='Clôtures', marker_color='lightgreen'))

            # Ajouter la courbe pour le Backlog
            fig.add_trace(go.Scatter(x=df_graph['Date'], y=df_graph['Backlog'], mode='lines+markers', name='Backlog', line=dict(color='red')))

            # Mettre à jour la disposition du graphique
            fig.update_layout(
                title='Nombre de tickets par jour (Ouvertures, Clôtures, Backlog)',
                xaxis_title='Date',
                yaxis_title='Nombre de tickets',
                barmode='group',  # Important pour les barres groupées
                xaxis=dict(
                    title='Date',
                    tickangle=-45,
                    range=[date_debut, date_fin],  # Définir l'intervalle de dates
                    tickformat='%d-%m-%Y'  # Format des dates
                ),
                yaxis=dict(
                    title='Nombre de tickets',
                    rangemode='tozero'  # Assurer que l'axe Y commence à zéro
                ),
                legend_title='Statut',
                plot_bgcolor='rgba(0,0,0,0)'  # Fond du graphique transparent
            )

            st.plotly_chart(fig)

            # Calculer les métriques pour le tableau Priorités/SLA
            tableau_priorite_sla = df.groupby(['Priorité', 'SLA - Clôture - Statut']).size().reset_index(name='Nombre de tickets')
            
            # Calculer le total des tickets pour les pourcentages
            total_tickets = tableau_priorite_sla['Nombre de tickets'].sum()
            
            # Ajouter une colonne pourcentage
            tableau_priorite_sla['Pourcentage (%)'] = (tableau_priorite_sla['Nombre de tickets'] / total_tickets * 100).round(2)
            
            # Afficher le tableau des priorités/SLA avec les pourcentages
            st.subheader("📊 Tableau Priorités/SLA")
            st.write(tableau_priorite_sla)

        else:
            st.error("❌ Les colonnes nécessaires ne sont pas toutes présentes dans le fichier CSV.")
    
    except Exception as e:
        st.error(f"⚠️ Erreur lors de la lecture du fichier CSV : {e}")
