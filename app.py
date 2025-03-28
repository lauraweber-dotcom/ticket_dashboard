import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv


# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Exemple d'utilisation des variables d'environnement dans ton code
db_host = st.secret('DB_HOST')
db_user = st.secret('DB_USER')
db_password = st.secret('DB_PASSWORD')
db_name = st.secret('DB_NAME')

# --- IMPORTANT : CONFIGURER LA PAGE EN PREMIER ---
st.set_page_config(layout="wide")

# Créer la chaîne de connexion
connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"

# Créer l'engine de connexion
engine = create_engine(connection_string)

# Requête SQL
query = '''
    SELECT 
        d.*,  -- Toutes les colonnes de v3_tickets_distribution_by_group_and_agent
        t.sum_first_time_reply,
        t.mean_first_time_reply,
        t.sum_answer_time,
        t.mean_answer_time,
        t.sla_1st_response,
        t.perc_sla,
        a.agent,  -- Supposons que fd_agent_id a une colonne agent_name
        g.group as group_name   -- Supposons que fd_group_id a une colonne group_name
    FROM v3_tickets_distribution_by_group_and_agent d
    LEFT JOIN v3_tadiplus_tickets_distri t
        ON d.date = t.date 
        AND d.group_id = t.group_id 
        AND d.agent_id = t.agent_id
    LEFT JOIN fd_agent_id a 
        ON d.agent_id = a.agent_id
    LEFT JOIN fd_group_id g 
        ON d.group_id = g.group_id;
'''
df = pd.read_sql(query, engine)

# Convertir la colonne 'date' en type datetime
df['date'] = pd.to_datetime(df['date'], errors='coerce')
# Supprimer les heures pour que l'affichage daily n'affiche que la date
df['date'] = pd.to_datetime(df['date'])

# Liste des agents à afficher
agents_to_display = [
    "Lisette Hapke", "Kerstin Rosskamp", "Sebastian Grund", "David Priemer",
    "Daniela Kolb", "Mario Krieger", "Christopher Loehr", "Jochen Wittmann",
    "Marion Nebrich", "Andreas Hombergs", "Michael Doodt", "Gabi Tiedtke",
    "Kayleigh Perkins", "Jacqueline Forstner", "Samuel Siegle", "Barbara Habermann",
    "Sandra Bulka", "Holger Koepff", "Marcel Gruber", "Chantal Schloeßer"
]

# Filtrer les données pour n'afficher que ces agents
df = df[df['agent'].isin(agents_to_display)]

# Sélection des dates - Par défaut la semaine en cours
today = datetime.today()
start_date = today - timedelta(days=today.weekday())  # Lundi de la semaine en cours
end_date = start_date + timedelta(days=6)  # Dimanche de la semaine en cours

# Sélection des dates via Streamlit
start_date_input = st.sidebar.date_input('Start Date', start_date)
end_date_input = st.sidebar.date_input('End Date', end_date)

# Sélection des agents
select_all_agents = st.sidebar.button("Select All Agents")
if select_all_agents:
    selected_agents = df['agent'].unique()
else:
    selected_agents = st.sidebar.multiselect('Select Agents', options=df['agent'].unique(), default=df['agent'].unique())

# Sélection des groupes
select_all_groups = st.sidebar.button("Select All Groups")
if select_all_groups:
    selected_groups = df['group_name'].unique()
else:
    selected_groups = st.sidebar.multiselect('Select Groups', options=df['group_name'].unique(), default=df['group_name'].unique())

# Filtrer les données selon les sélections
df_filtered = df[
    (df['date'].dt.date >= start_date_input) & 
    (df['date'].dt.date <= end_date_input) & 
    (df['agent'].isin(selected_agents)) & 
    (df['group_name'].isin(selected_groups))  # ✅ Ajout du filtre sur les groupes ici !
]

df_filtered['date'] = pd.to_datetime(df_filtered['date'])

df_filtered = df_filtered[df_filtered['agent'].isin(selected_agents)]
df_filtered = df_filtered[df_filtered['group_name'].isin(selected_groups)]

# Calculer le total des tickets traités
total_tickets = df_filtered['occurrences'].sum()

# Affichage du total de tickets en haut du dashboard
#st.markdown(f"### Total Tickets Processed: {total_tickets:,}")

# Filtrer les données pour Total Tadiplus (agents totaux)
total_agents = [
    "Lisette Hapke", "Kerstin Rosskamp", "Sebastian Grund", "David Priemer",
    "Daniela Kolb", "Mario Krieger", "Christopher Loehr", "Jochen Wittmann",
    "Marion Nebrich", "Andreas Hombergs", "Michael Doodt", "Gabi Tiedtke",
    "Kayleigh Perkins", "Jacqueline Forstner", "Samuel Siegle", "Barbara Habermann",
    "Sandra Bulka", "Holger Koepff", "Marcel Gruber", "Chantal Schloeßer"
]

# Appliquer également le filtre de date sur Total Tadiplus
df_total_tadiplus = df[
    (df['agent'].isin(total_agents)) & 
    (df['date'] >= pd.to_datetime(start_date_input)) & 
    (df['date'] <= pd.to_datetime(end_date_input)) & 
    (df['group_name'].isin(selected_groups))  # ✅ Ajout du filtre ici !
]

df_total_tadiplus_group = df_total_tadiplus.groupby('group_name')['occurrences'].sum().reset_index()

# Graphique 1 : Tickets par groupe (Total Tadiplus)
group_data = df_filtered.groupby('group_name')['occurrences'].sum().reset_index()
group_data = group_data.sort_values(by='occurrences', ascending=False)  # Ordre décroissant

fig_group = px.bar(
    group_data, 
    x='group_name', 
    y='occurrences', 
    title="🎟️ Tickets by Group", 
    text='occurrences'
)
fig_group.update_traces(
    textposition='outside', 
    marker=dict(color='rgb(6, 47, 104)')  # Couleur Total Tadiplus
)
fig_group.update_layout(
    xaxis_title="Groups",
    yaxis_title="Number of Tickets",
    yaxis=dict(
        autorange=True,  # Permet d'ajuster automatiquement les limites de l'axe Y
        showgrid=True,
        showline=True,
        ticks='outside',
        tickangle=45
    ),
    height=600,  # Ajuste la hauteur du graphique
    margin=dict(l=50, r=50, t=50, b=100)  # Ajuste les marges pour les axes
)

# --- Créer la deuxième figure : Tickets par Agent et Groupe + Total Tadiplus ---
df_agents_group = df_filtered.groupby(['group_name', 'agent'])['occurrences'].sum().reset_index()
df_agents_group = df_agents_group.sort_values(by='occurrences', ascending=False)  # Tri par ordre décroissant

# Créer une couleur pour chaque agent
color_map = {agent: px.colors.qualitative.Set1[i % len(px.colors.qualitative.Set1)] for i, agent in enumerate(df_agents_group['agent'].unique())}

# Ajouter Total Tadiplus dans le graphique 2
df_total_tadiplus_group['agent'] = 'Total Tadiplus'
df_total_tadiplus_group['occurrences'] = df_total_tadiplus_group['occurrences']

# Fusionner Total Tadiplus avec les agents
df_combined = pd.concat([df_agents_group, df_total_tadiplus_group[['group_name', 'agent', 'occurrences']]])

# Forcer la couleur "Total Tadiplus" à être la couleur définie : rgb(6, 47, 104)
color_map['Total Tadiplus'] = 'rgb(6, 47, 104)'

# S'assurer que "Total Tadiplus" soit toujours en première position
df_combined['sort_order'] = df_combined['agent'].apply(lambda x: 0 if x == 'Total Tadiplus' else 1)
df_combined = df_combined.sort_values(by=['group_name', 'sort_order', 'occurrences'], ascending=[True, True, False])

# Triez les groupes en fonction des occurrences de Total Tadiplus
total_tadiplus_order = df_total_tadiplus_group.sort_values(by='occurrences', ascending=False)['group_name'].tolist()
df_combined['group_name'] = pd.Categorical(df_combined['group_name'], categories=total_tadiplus_order, ordered=True)
df_combined = df_combined.sort_values('group_name')

# Créer le graphique des tickets par agent et groupe avec Total Tadiplus
fig_agent = px.bar(
    df_combined,
    x='group_name',
    y='occurrences',
    color='agent',
    title="🎟️ Tickets by Agent and Group + Total Tadiplus",
    text='occurrences',
    barmode='group',  # Barres groupées (Total vs agents)
    color_discrete_map=color_map  # Appliquer la carte de couleurs
)
fig_agent.update_traces(textposition='outside')
fig_agent.update_layout(
    xaxis_title="Groups",
    yaxis_title="Number of Tickets",
    yaxis=dict(
        autorange=True,  # Permet d'ajuster automatiquement les limites de l'axe Y
        showgrid=True,
        showline=True,
        ticks='outside',
        tickangle=45
    ),
    height=600,  # Ajuste la hauteur du graphique
    margin=dict(l=50, r=50, t=50, b=100)  # Ajuste les marges pour les axes
)

# --- Affichage des graphiques indépendants dans Streamlit ---
#st.plotly_chart(fig_group, use_container_width=True)  # Afficher la première figure
#st.plotly_chart(fig_agent, use_container_width=True)  # Afficher la deuxième figure


# Transformer les dates en fonction de l'échelle sélectionnée
df_filtered["Week"] = df_filtered["date"].dt.strftime("%Y-W%U")  # Format année-semaine
df_filtered["Week_Range"] = df_filtered["date"].dt.to_period("W").astype(str)  # Format avec dates de début et fin de semaine
df_filtered["Month"] = df_filtered["date"].dt.strftime("%B %Y")  # Ex: "February 2025"
#df_filtered["Quarter"] = df_filtered["date"].dt.to_period("Q").astype(str)  # Format trimestre

# Sélection de l'échelle de temps
time_scale = st.sidebar.selectbox(
    "Select Time Scale", 
    ["Daily", "Weekly", "Monthly"],
    index=0  # Par défaut : Daily
)

# Adapter la colonne X en fonction de l'échelle choisie
if time_scale == "Daily":
    df_filtered["date"] = pd.to_datetime(df_filtered["date"]).dt.date
    x_column = "date"
elif time_scale == "Weekly":
    x_column = "Week_Range"  # Affiche la plage de dates des semaines
elif time_scale == "Monthly":
    x_column = "Month"
elif time_scale == "Quarterly":
    x_column = "Quarter"


# Grouper les données selon l'axe X choisi
df_time_series = df_filtered.groupby(x_column)['occurrences'].sum().reset_index()

# Création du graphique
fig_time_series = px.line(
    df_time_series,
    x=x_column,
    y="occurrences",
    title="📈 Evolution of Tickets Over Time",
    markers=True,  # Ajoute des points visibles
    text="occurrences",  # Affiche les valeurs des points
    line_shape="linear",  # Garde une courbe simple
    color_discrete_sequence=["rgb(6, 47, 104)"]  # Améliore la lisibilité avec une couleur contrastée
)

# Améliorer la visibilité des données
fig_time_series.update_traces(
    marker=dict(size=8, opacity=0.8, symbol="circle"),  # Points plus gros
    line=dict(width=3),  # Épaissir la ligne
    textposition="top center"  # Positionner les valeurs au-dessus des points
)

# Optimiser l'affichage des dates sur l'axe X
fig_time_series.update_layout(
    xaxis_title="Time Period",
    yaxis_title="Number of Tickets",
    xaxis=dict(
        tickangle=-45,  # Incliner les dates pour éviter le chevauchement
        showgrid=True
    ),
    yaxis=dict(showgrid=True),
    height=500,
    margin=dict(l=50, r=50, t=50, b=100)
)

#### Ajout graph tickets created by day

# Requête SQL pour récupérer les données de v3_ticket_created_count avec les groupes et la date
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

# Requête SQL pour récupérer les données de v3_ticket_created_count avec les groupes et la date
query_tickets = '''
    SELECT 
        t.date, 
        t.group_id, 
        t.time_slot, 
        t.ticket_count,
        g.group as group_name  
    FROM v3_ticket_created_counts t
    LEFT JOIN fd_group_id g ON t.group_id = g.group_id
'''
df_tickets = pd.read_sql(query_tickets, engine)

# Convertir 'date' en datetime, et normaliser à minuit (on supprime l'heure)
df_tickets['date'] = pd.to_datetime(df_tickets['date']).apply(lambda x: x.normalize())

# Convertir 'time_slot' en datetime et ajouter 1h
df_tickets['time_slot'] = pd.to_datetime(df_tickets['time_slot'], errors='coerce') + pd.Timedelta(hours=1)

# Extraire uniquement l'heure au format HH:MM
df_tickets['time_slot'] = df_tickets['time_slot'].dt.strftime('%H:%M')

# Filtrage des données selon les dates et groupes
start_date_input = pd.to_datetime(start_date_input).normalize()  # Normaliser à minuit
end_date_input = pd.to_datetime(end_date_input).normalize()  # Normaliser à minuit

# Filtrage des données selon les dates et groupes
df_filtered_tickets = df_tickets[
    (df_tickets['date'] >= start_date_input) & 
    (df_tickets['date'] <= end_date_input) & 
    (df_tickets['group_name'].isin(selected_groups))
].copy()

# Grouper par 'time_slot' et 'group_name'
df_grouped_time_slot = df_filtered_tickets.groupby(['time_slot', 'group_name'])['ticket_count'].sum().reset_index()

# Ajouter une ligne pour les valeurs totales
df_total = df_filtered_tickets.groupby('time_slot')['ticket_count'].sum().reset_index()
df_total['group_name'] = 'Total'  # On ajoute une colonne 'group_name' pour différencier

# Ajouter les totaux dans le dataset principal
df_grouped_time_slot = pd.concat([df_grouped_time_slot, df_total], ignore_index=True)

# Convertir 'time_slot' en minutes depuis minuit pour garantir un tri correct
def time_to_minutes(t):
    hour, minute = map(int, t.split(':'))
    return hour * 60 + minute

# Appliquer la fonction pour convertir 'time_slot' en minutes
df_grouped_time_slot['time_slot_minutes'] = df_grouped_time_slot['time_slot'].apply(time_to_minutes)

# Trier les données par 'time_slot_minutes' pour garantir l'ordre chronologique
df_grouped_time_slot = df_grouped_time_slot.sort_values(by='time_slot_minutes')

# Convertir de nouveau 'time_slot' en format 'HH:MM' pour l'affichage après tri
df_grouped_time_slot['time_slot'] = df_grouped_time_slot['time_slot'].apply(lambda x: f"{int(x.split(':')[0]):02}:{int(x.split(':')[1]):02}")

# 🎨 Création du graphique combinant courbe + histogramme
fig_time_slot = go.Figure()

# Ajouter d'abord la courbe pour le total
df_total_group = df_grouped_time_slot[df_grouped_time_slot['group_name'] == 'Total']
fig_time_slot.add_trace(go.Scatter(
    x=df_total_group['time_slot'], 
    y=df_total_group['ticket_count'],
    mode='lines+markers+text',
    text=df_total_group['ticket_count'],
    textposition='top center',  # Placer le texte au-dessus des points
    name='Total',
    line=dict(color="rgb(100, 120, 160)" , width=4, dash='solid'),  # Couleur modifiée et épaisseur du trait augmentée
    textfont=dict(color="rgb(100, 120, 160)" ),  # Couleur du texte
))

# Ajouter ensuite les barres pour chaque groupe
for group in df_grouped_time_slot['group_name'].unique():
    if group != "Total":
        df_group = df_grouped_time_slot[df_grouped_time_slot['group_name'] == group]
        fig_time_slot.add_trace(go.Bar(
            x=df_group['time_slot'], 
            y=df_group['ticket_count'], 
            name=group, 
            text=df_group['ticket_count'], 
            textposition='inside',  # Position du texte à l'intérieur des barres pour éviter le chevauchement
            textfont=dict(size=10),  # Taille de la police du texte
        ))

# 🔹 Personnalisation du graphique
fig_time_slot.update_layout(
    title="🎟️ Tickets Created per Time Slot by Group",
    xaxis_title="Time Slot",
    yaxis_title="Number of Tickets Created",
    barmode='stack',
    height=500,
    margin=dict(l=50, r=50, t=50, b=100),
    xaxis=dict(
        tickmode='array',  # Mode de tick personnalisé
        tickvals=df_grouped_time_slot['time_slot'],  # Mettre les ticks de manière appropriée
        ticktext=df_grouped_time_slot['time_slot']  # Texte des ticks
    ),
    xaxis_tickangle=-45  # Inclinaison des labels en X pour lisibilité
)


########## 
#### Graph actions des agents par time slot
# Requête SQL pour récupérer les données de v3_agent_action_counts avec les agents et la date
query_tickets = '''
    SELECT 
        t.date, 
        t.group_id, 
        t.time_slot, 
        t.action_count as ticket_count,
        g.group as group_name,
        a.agent
    FROM v3_agent_action_counts t
    LEFT JOIN fd_group_id g ON t.group_id = g.group_id
    LEFT JOIN fd_agent_id a ON t.agent_id = a.agent_id
'''

df_tickets = pd.read_sql(query_tickets, engine)

# Convertir 'date' en datetime, et normaliser à minuit (on supprime l'heure)
df_tickets['date'] = pd.to_datetime(df_tickets['date']).apply(lambda x: x.normalize())

# Convertir 'time_slot' en datetime et ajouter 1h
df_tickets['time_slot'] = pd.to_datetime(df_tickets['time_slot'], errors='coerce') + pd.Timedelta(hours=1)

# Extraire uniquement l'heure au format HH:MM
df_tickets['time_slot'] = df_tickets['time_slot'].dt.strftime('%H:%M')

# Filtrage des données selon les dates et groupes
start_date_input = pd.to_datetime(start_date_input).normalize()  # Normaliser à minuit
end_date_input = pd.to_datetime(end_date_input).normalize()  # Normaliser à minuit

# Filtrage des données selon les dates, groupes et agents
df_filtered_tickets = df_tickets[
    (df_tickets['date'] >= start_date_input) & 
    (df_tickets['date'] <= end_date_input) & 
    (df_tickets['group_name'].isin(selected_groups)) & 
    (df_tickets['agent'].isin(selected_agents))
].copy()

# Grouper par 'time_slot' et 'agent'
df_grouped_agent = df_filtered_tickets.groupby(['time_slot', 'agent'])['ticket_count'].sum().reset_index()

# Ajouter une ligne pour les valeurs totales si vous souhaitez les afficher en plus
df_total = df_filtered_tickets.groupby('time_slot')['ticket_count'].sum().reset_index()
df_total['agent'] = 'Total'  # On ajoute une colonne 'agent' pour différencier

# Ajouter les totaux dans le dataset principal
df_grouped_agent = pd.concat([df_grouped_agent, df_total], ignore_index=True)

# Convertir 'time_slot' en minutes depuis minuit pour garantir un tri correct
def time_to_minutes(t):
    hour, minute = map(int, t.split(':'))
    return hour * 60 + minute

# Appliquer la fonction pour convertir 'time_slot' en minutes
df_grouped_agent['time_slot_minutes'] = df_grouped_agent['time_slot'].apply(time_to_minutes)

# Trier les données par 'time_slot_minutes' pour garantir l'ordre chronologique
df_grouped_agent = df_grouped_agent.sort_values(by='time_slot_minutes')

# Convertir de nouveau 'time_slot' en format 'HH:MM' pour l'affichage après tri
df_grouped_agent['time_slot'] = df_grouped_agent['time_slot'].apply(lambda x: f"{int(x.split(':')[0]):02}:{int(x.split(':')[1]):02}")

# 🎨 Création du graphique combinant courbe + histogramme par agent
fig_agent_actions = go.Figure()

# Ajouter la courbe pour le total d'abord (afin que la courbe soit affichée en premier)
df_total_group = df_grouped_agent[df_grouped_agent['agent'] == 'Total']
fig_agent_actions.add_trace(go.Scatter(
    x=df_total_group['time_slot'], 
    y=df_total_group['ticket_count'],
    mode='lines+markers+text',
    text=df_total_group['ticket_count'],
    textposition='top center',  # Placer le texte au-dessus des points
    name='Total',
    line=dict(color="rgb(100, 120, 160)", width=4, dash='solid'),  # Couleur modifiée et épaisseur du trait augmentée
    textfont=dict(color="rgb(100, 120, 160)"),  # Couleur du texte
))

# Ajouter les barres pour chaque agent
for agent in df_grouped_agent['agent'].unique():
    if agent != "Total":
        df_agent = df_grouped_agent[df_grouped_agent['agent'] == agent]
        fig_agent_actions.add_trace(go.Bar(
            x=df_agent['time_slot'], 
            y=df_agent['ticket_count'], 
            name=f"{agent}",
            text=df_agent['ticket_count'], 
            textposition='inside',  # Position du texte à l'intérieur des barres
            textfont=dict(size=10),  # Taille de la police du texte
        ))

# 🔹 Personnalisation du graphique
fig_agent_actions.update_layout(
    title="🎯 Actions per Time Slot by Agent",
    xaxis_title="Time Slot",
    yaxis_title="Number of Actions",
    barmode='stack',
    height=500,
    margin=dict(l=50, r=50, t=50, b=100),
    xaxis=dict(
        tickmode='array',  # Mode de tick personnalisé
        tickvals=df_grouped_agent['time_slot'],  # Mettre les ticks de manière appropriée
        ticktext=df_grouped_agent['time_slot']  # Texte des ticks
    ),
    xaxis_tickangle=-45  # Inclinaison des labels en X pour lisibilité
)
####################### test group time et sla
# Fonction pour convertir les secondes en format hh:mm:ss
def seconds_to_hms(seconds):
    if pd.isna(seconds):  # Vérifier si la valeur est NaN
        return ""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"  # Format hh:mm:ss

# Requête SQL pour récupérer les données
query_group_kpis = '''
    SELECT 
        gk.date,
        gk.group_id,
        gk.mean_answer,
        gk.mean_first_answer,
        gk.sla_1st_perc,
        gk.sla_solution_perc,
        g.group as group_name,
        gk.nb_tickets  
    FROM v3_group_kpis gk
    LEFT JOIN fd_group_id g ON gk.group_id = g.group_id
'''

# Chargement des données depuis la base
df_group_kpis = pd.read_sql(query_group_kpis, engine)

# Convertir 'date' en datetime
df_group_kpis['date'] = pd.to_datetime(df_group_kpis['date'])

# Filtrer les données selon les dates et groupes sélectionnés
df_filtered_group_kpis = df_group_kpis[
    (df_group_kpis['date'] >= pd.to_datetime(start_date_input)) & 
    (df_group_kpis['date'] <= pd.to_datetime(end_date_input)) & 
    (df_group_kpis['group_name'].isin(selected_groups))
].copy()

# Ignorer les valeurs NaN pour le calcul des moyennes et des SLA
df_filtered_group_kpis = df_filtered_group_kpis.dropna(subset=['mean_answer', 'mean_first_answer', 'sla_1st_perc', 'sla_solution_perc'])

# **Graphique pour les temps de réponse (mean_answer et mean_first_answer)**
fig1 = go.Figure()

for group in df_filtered_group_kpis['group_name'].unique():
    df_group = df_filtered_group_kpis[df_filtered_group_kpis['group_name'] == group]

    # Mean Answer
    fig1.add_trace(go.Bar(
        x=[group], 
        y=df_group['mean_answer'],  
        name=f"Mean Answer - {group}",
        text=[f"<b>{seconds_to_hms(x)}</b>" for x in df_group['mean_answer']],  # Labels en hh:mm:ss et en gras
        textposition='inside',
        texttemplate="%{text}",  # Force le formatage HTML
    ))
    
    # Mean First Answer
    fig1.add_trace(go.Bar(
        x=[group], 
        y=df_group['mean_first_answer'],  
        name=f"Mean First Answer - {group}",
        text=[f"<b>{seconds_to_hms(x)}</b>" for x in df_group['mean_first_answer']],  # Labels en hh:mm:ss et en gras
        textposition='inside',
        texttemplate="%{text}",
    ))

fig1.update_layout(
    title="Mean Answer & Mean First Answer by Group",
    xaxis_title="Group",
    yaxis_title="Time (in seconds)",  # Axe Y reste en secondes
    barmode='group',  
    height=500,
)

# **Graphique pour les SLA (sla_1st_perc et sla_solution_perc)**
fig2 = go.Figure()

for group in df_filtered_group_kpis['group_name'].unique():
    df_group = df_filtered_group_kpis[df_filtered_group_kpis['group_name'] == group]
    
    # SLA 1st Percent
    fig2.add_trace(go.Bar(
        x=[group], 
        y=df_group['sla_1st_perc'],  
        name=f"SLA 1st Response % - {group}",
        text=[f"<b>{int(x)}%</b>" for x in df_group['sla_1st_perc']],  # Labels en gras et sans virgule
        textposition='inside',
        texttemplate="%{text}",
    ))

    # SLA Solution Percent
    fig2.add_trace(go.Bar(
        x=[group], 
        y=df_group['sla_solution_perc'],  
        name=f"SLA Solution % - {group}",
        text=[f"<b>{int(x)}%</b>" for x in df_group['sla_solution_perc']],  # Labels en gras et sans virgule
        textposition='inside',
        texttemplate="%{text}",
    ))

fig2.update_layout(
    title="SLA 1st Response % & SLA Solution % by Group",
    xaxis_title="Group",
    yaxis_title="Percentage",
    barmode='group',
    height=500,
)


##############Temps et sla 
query_tadiplus = '''
    SELECT 
        t.date,
        a.agent,  
        g.group as group_name,  
        t.occurrences,
        t.mean_answer_time
    FROM v3_tadiplus_tickets_distri t
    LEFT JOIN fd_group_id g ON t.group_id = g.group_id
    LEFT JOIN fd_agent_id a ON t.agent_id = a.agent_id
'''

df_tadiplus = pd.read_sql(query_tadiplus, engine)
df_tadiplus['date'] = pd.to_datetime(df_tadiplus['date'])

# --- FILTRAGE DES DONNÉES ---
df_filtered = df_tadiplus[
    (df_tadiplus['date'] >= pd.to_datetime(start_date_input)) &
    (df_tadiplus['date'] <= pd.to_datetime(end_date_input)) &
    (df_tadiplus['group_name'].isin(selected_groups)) &
    (df_tadiplus['agent'].isin(selected_agents))
].copy()

# --- SUPPRIMER LES NAN UNIQUEMENT POUR mean_answer_time ---
df_filtered = df_filtered.dropna(subset=['mean_answer_time'])

# --- CALCUL DE LA MOYENNE PONDÉRÉE PAR AGENT ET GROUPE ---
df_grouped = df_filtered.groupby(['agent', 'group_name'], as_index=False).agg({
    'occurrences': 'sum',
    'mean_answer_time': lambda x: (x * df_filtered.loc[x.index, 'occurrences']).sum() / df_filtered.loc[x.index, 'occurrences'].sum(),
})

# --- CALCUL DU TEMPS MOYEN TOTAL PAR AGENT ---
df_total = df_filtered.groupby('agent', as_index=False).agg({
    'occurrences': 'sum',
    'mean_answer_time': lambda x: (x * df_filtered.loc[x.index, 'occurrences']).sum() / df_filtered.loc[x.index, 'occurrences'].sum(),
})

df_total['group_name'] = 'TOTAL'

# Fusionner les données
df_final = pd.concat([df_grouped, df_total])

# --- CONVERSION SECONDES → HH:MM ---
def seconds_to_hms(seconds):
    if pd.isna(seconds):
        return None
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{int(hours):02}:{int(minutes):02}"

df_final['mean_answer_time_display'] = df_final['mean_answer_time'].apply(seconds_to_hms)

# Trier les agents par temps total (pour un affichage ordonné sur l'axe Y)
df_final['sort_order'] = df_final.groupby('agent')['mean_answer_time'].transform('mean')
df_final = df_final.sort_values(by='sort_order', ascending=False)

# --- CRÉATION DU GRAPHIQUE ---
fig = go.Figure()

for group in df_final['group_name'].unique():
    df_group = df_final[df_final['group_name'] == group]
    fig.add_trace(go.Bar(
        x=df_group['agent'],
        y=df_group['mean_answer_time'],  # Valeur en secondes pour un axe bien ordonné
        name=f"{group}",
        text=df_group['mean_answer_time_display'],  # Affichage en HH:MM
        textposition='inside',
    ))

fig.update_layout(
    title="Average Response Time by Agent and Group",
    xaxis_title="Agents",
    yaxis_title="Average Response Time (Seconds)",  # Mettre en "Seconds" pour l'axe
    barmode='group',
    height=500,
)

# Afficher le graphique
#st.plotly_chart(fig, use_container_width=True) #Average reponse time by Agent and Group

###### essaie affichage par date 
#######################


##########################
#########################
#test heatmap
###########################
#
import plotly.express as px
import plotly.graph_objects as go

# --- CONVERSION SECONDES → HH:MM:SS ---
def seconds_to_hms(seconds):
    if pd.isna(seconds):
        return ""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{sec:02}"

# --- CRÉATION D'UNE TABLE PIVOT POUR LA HEATMAP ---
df_pivot = df_filtered.pivot_table(index="agent", columns="group_name", values="mean_answer_time", aggfunc="mean")

# Appliquer la conversion HH:MM:SS pour l'affichage des valeurs
df_pivot_display = df_pivot.applymap(seconds_to_hms)

# --- CRÉATION DE LA HEATMAP AVEC GO.HEATMAP (POUR SUPPORTER LES TEXTES) ---
fig_heatmap = go.Figure(data=go.Heatmap(
    z=df_pivot.values,  
    x=df_pivot.columns,  
    y=df_pivot.index,  
    colorscale="RdYlBu_r",  # Rouge = mauvais, Bleu = bon
    text=df_pivot_display.values,  # Affichage en HH:MM:SS
    hoverinfo="text",  # Afficher les valeurs sur hover
    showscale=True
))

# --- AJOUT DES VALEURS DIRECTEMENT DANS LA HEATMAP ---
annotations = []
for i, row in enumerate(df_pivot.index):
    for j, col in enumerate(df_pivot.columns):
        value = df_pivot_display.iloc[i, j]
        annotations.append(
            go.layout.Annotation(
                text=value,
                x=col,
                y=row,
                showarrow=False,
                font=dict(color="black" if df_pivot.iloc[i, j] < df_pivot.values.mean() else "white")  # Texte lisible
            )
        )

fig_heatmap.update_layout(
    title="⏳ Heatmap of Average Response Time by Agent and Group",
    xaxis_title="Groups",
    yaxis_title="Agents",
    height=500,
    annotations=annotations
)

# --- AFFICHAGE SUR STREAMLIT ---
#st.plotly_chart(fig_heatmap, use_container_width=True) #Heatmap Average Response Time
######## ok
############ autres heatmap - pour sla 
###############
# --- REQUÊTE SQL : Récupération des données SLA ---
query_sla = '''
    SELECT 
        t.date,
        a.agent,  
        g.group as group_name,  
        t.occurrences,
        t.mean_answer_time,
        t.sla_1st_response,  -- SLA 1st Response Compliance
        t.perc_sla  -- Percentage SLA Compliance
    FROM v3_tadiplus_tickets_distri t
    LEFT JOIN fd_group_id g ON t.group_id = g.group_id
    LEFT JOIN fd_agent_id a ON t.agent_id = a.agent_id
'''

df_sla = pd.read_sql(query_sla, engine)
df_sla['date'] = pd.to_datetime(df_sla['date'])

# --- FILTRAGE DES DONNÉES ---
df_sla_filtered = df_sla[
    (df_sla['date'] >= pd.to_datetime(start_date_input)) &
    (df_sla['date'] <= pd.to_datetime(end_date_input)) &
    (df_sla['group_name'].isin(selected_groups)) &
    (df_sla['agent'].isin(selected_agents))
].copy()

# --- SUPPRESSION DES NaN UNIQUEMENT POUR SLA ---
df_sla_filtered = df_sla_filtered.dropna(subset=['sla_1st_response', 'perc_sla'])

# --- FONCTION DE CRÉATION DE HEATMAP ---
def create_heatmap(df, value_col, title, colorscale):
    df_pivot = df.pivot_table(index="agent", columns="group_name", values=value_col, aggfunc="mean")

    fig = px.imshow(
        df_pivot,
        labels=dict(x="Group", y="Agent", color=value_col),
        x=df_pivot.columns,
        y=df_pivot.index,
        color_continuous_scale=colorscale,
        text_auto=".1f"  # Affichage des valeurs avec 1 décimale
    )

    fig.update_layout(
        title=title,
        xaxis_title="Groups",
        yaxis_title="Agents",
        coloraxis_colorbar=dict(title=value_col),
        height=600,
    )

    return fig

# --- CRÉATION DES HEATMAPS ---
fig_sla_1st_response = create_heatmap(
    df_sla_filtered,
    "sla_1st_response",
    "🚀 SLA 1st Response Compliance by Agent & Group",
    "RdYlBu"  # Bleu pour 100 (bon), rouge pour 0 (mauvais)
)

fig_perc_sla = create_heatmap(
    df_sla_filtered,
    "perc_sla",
    "📊 Percentage SLA Compliance by Agent & Group",
    "RdYlBu"
)

# --- AFFICHAGE DES HEATMAPS DANS STREAMLIT ---
#st.plotly_chart(fig_sla_1st_response, use_container_width=True) #Heatmap SLA 1er
#st.plotly_chart(fig_perc_sla, use_container_width=True) # Hetmap SLA tot


###########################
############################
#### Essai KPIS Agent Group au cours du temps 
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Fonction pour convertir les secondes en HH:MM:SS
def seconds_to_hms(seconds):
    return str(pd.to_datetime(seconds, unit='s').strftime('%H:%M:%S'))

# --- REQUÊTE SQL : Récupérer les données pour sla_1st_response, perc_sla, et mean_answer_time ---
# --- Requête SQL pour obtenir les données ---
query_sla_and_answer = '''
    SELECT 
        t.date,
        a.agent,  
        g.group as group_name,  
        t.occurrences,
        t.mean_answer_time,
        t.sla_1st_response,  -- SLA 1st Response Compliance
        t.perc_sla  -- Percentage SLA Compliance
    FROM v3_tadiplus_tickets_distri t
    LEFT JOIN fd_group_id g ON t.group_id = g.group_id
    LEFT JOIN fd_agent_id a ON t.agent_id = a.agent_id
'''

# Charger les données
df_sla_answer = pd.read_sql(query_sla_and_answer, engine)
df_sla_answer['date'] = pd.to_datetime(df_sla_answer['date'])

# --- FILTRAGE DES DONNÉES ---
df_filtered_sla_answer = df_sla_answer[
    (df_sla_answer['date'] >= pd.to_datetime(start_date_input)) & 
    (df_sla_answer['date'] <= pd.to_datetime(end_date_input)) & 
    (df_sla_answer['group_name'].isin(selected_groups)) & 
    (df_sla_answer['agent'].isin(selected_agents))
].copy()

# --- SUPPRESSION DES NaN UNIQUEMENT POUR LES COLONNES D'INTERÊT ---
df_filtered_sla_answer = df_filtered_sla_answer.dropna(subset=['sla_1st_response', 'perc_sla', 'mean_answer_time'])

# --- CALCUL DES MOYENNES PONDÉRÉES PAR DATE, GROUPE ET AGENT ---
df_grouped = df_filtered_sla_answer.groupby(['date', 'group_name', 'agent'], as_index=False).agg({
    'occurrences': 'sum',
    'mean_answer_time': lambda x: (x * df_filtered_sla_answer.loc[x.index, 'occurrences']).sum() / df_filtered_sla_answer.loc[x.index, 'occurrences'].sum(),
    'sla_1st_response': lambda x: (x * df_filtered_sla_answer.loc[x.index, 'occurrences']).sum() / df_filtered_sla_answer.loc[x.index, 'occurrences'].sum(),
    'perc_sla': lambda x: (x * df_filtered_sla_answer.loc[x.index, 'occurrences']).sum() / df_filtered_sla_answer.loc[x.index, 'occurrences'].sum(),
})

# --- AJOUTER UN WIDGET POUR CHOISIR LA MÉTRIQUE À AFFICHER ---
#metric_option = st.radio(
#    "Select the metric to visualize:",
#    ("Mean Answer Time", "SLA 1st Response", "Percentage SLA")
#)

# --- AFFICHAGE DES DONNÉES PAR GROUPE AU FIL DU TEMPS ---
#fig = go.Figure()

# Ajouter la courbe pour chaque agent et chaque métrique sélectionnée
#for group in df_grouped['group_name'].unique():
#    df_group = df_grouped[df_grouped['group_name'] == group]
    
#    for agent in df_group['agent'].unique():
#        df_agent = df_group[df_group['agent'] == agent]
        
        # Choisir la métrique en fonction de la sélection de l'utilisateur#
#        if metric_option == "Mean Answer Time":
#            metric_col = "mean_answer_time"
#            metric_label = "Mean Answer Time"
#        elif metric_option == "SLA 1st Response":
#            metric_col = "sla_1st_response"
#            metric_label = "SLA 1st Response"
#        elif metric_option == "Percentage SLA":
#            metric_col = "perc_sla"
#            metric_label = "Percentage SLA"
        
        # Ajouter la courbe
#        fig.add_trace(go.Scatter(
#            x=df_agent['date'],
#            y=df_agent[metric_col],
#            mode='lines+markers',
#            name=f"{group} - {agent} - {metric_label}",
#            text=df_agent[metric_col].apply(lambda x: f"{x:.1f}%") if metric_col != "mean_answer_time" else df_agent[metric_col].apply(seconds_to_hms),
#            textposition='top center',
#            line=dict(width=2)
#        ))

        # Ajouter les annotations pour chaque agent
#        for i, row in df_agent.iterrows():
#            agent_value = row[metric_col]
#            agent_name = row['agent']
#            date = row['date']
            
#            fig.add_annotation(
#                x=date,
#                y=agent_value,
#                text=f"{agent_name}: {seconds_to_hms(agent_value) if metric_col == 'mean_answer_time' else f'{agent_value:.1f}%'}",
#                showarrow=True,
#                arrowhead=2,
#                ax=0,
#                ay=-50,
#                font=dict(size=10, color="black"),
#                bgcolor="white",
#                opacity=0.7
#            )

# Personnalisation du graphique
#fig.update_layout(
#    title=f"{metric_label} over Time by Group with Agent Values",
#    xaxis_title="Date",
#    yaxis_title="Values",
#    height=600,
#    showlegend=True,
#)

# --- AFFICHAGE DU GRAPHIQUE ET DU BOUTON À CÔTÉ ---
#col1, col2 = st.columns([4, 1])

#with col1:
#    st.plotly_chart(fig, use_container_width=True)

#with col2:
#    st.write("**Select a metric to view**")
#    st.write("Choose the metric (Mean Answer Time, SLA 1st Response, or Percentage SLA) using the radio button above.")

#########################
#######################################################
#Graphs + ou - valides 


# Afficher le graphique avec un key unique pour éviter le conflit d'ID
#st.plotly_chart(fig_agent_actions, use_container_width=True, key="agent_actions_graph_unique")  # Actions per Time Slot by Agent


# Affichage des graphiques !!!!


# Affichage des graphiques
import streamlit as st



# --- PAGE TITLE ---
st.title("📊 Ticket Analysis Dashboard")

# --- SECTION 1: GENERAL OVERVIEW ---
st.subheader("General Overview")
st.markdown("This section provides a high-level view of ticket distribution and trends.")

# Display total tickets processed
st.markdown(f"### ✅ Total Tickets Processed: **{total_tickets:,}**")

st.divider()  # Adds a visual separation

# Layout: Two columns to maximize space
col1, col2 = st.columns([1, 1])

with col1:
    st.plotly_chart(fig_group, use_container_width=True)  # Tickets by Group

with col2:
    st.plotly_chart(fig_time_series, use_container_width=True)  # Evolution of Tickets Over Time

st.plotly_chart(fig_time_slot, use_container_width=True)  # Full-width: Tickets Created per Time Slot by Group

st.markdown("---")  # Horizontal separator

# --- SECTION 2: GROUP PERFORMANCE ---
st.subheader("Performance by Group")
st.markdown("Analyze response times, SLA compliance, and performance metrics at the group level.")

col1, col2 = st.columns([1, 1])

with col1: 
    st.plotly_chart(fig1, use_container_width=True)  # Mean Answer & Mean First Answer by Group

with col2:
    st.plotly_chart(fig2, use_container_width=True)  # SLA 1st Response % & SLA Solution % by Group

st.empty().write("")  # Adds some extra spacing

# --- Dynamic Metric Selection (Full Width) ---
st.markdown("#### 📊 Compare Metrics Across Groups")

# Full-width section
#######################################################################
# --- AJOUTER UN WIDGET POUR CHOISIR LA MÉTRIQUE À AFFICHER ---
metric_option = st.radio(
    "Select the metric to visualize:",
    ("Mean Answer Time", "SLA 1st Response", "Percentage SLA")
)

# --- AFFICHAGE DES DONNÉES PAR GROUPE AU FIL DU TEMPS ---
fig = go.Figure()

# Ajouter la courbe pour chaque agent et chaque métrique sélectionnée
for group in df_grouped['group_name'].unique():
    df_group = df_grouped[df_grouped['group_name'] == group]
    
    for agent in df_group['agent'].unique():
        df_agent = df_group[df_group['agent'] == agent]
        
        # Choisir la métrique en fonction de la sélection de l'utilisateur
        if metric_option == "Mean Answer Time":
            metric_col = "mean_answer_time"
            metric_label = "Mean Answer Time"
        elif metric_option == "SLA 1st Response":
            metric_col = "sla_1st_response"
            metric_label = "SLA 1st Response"
        elif metric_option == "Percentage SLA":
            metric_col = "perc_sla"
            metric_label = "Percentage SLA"
        
        # Ajouter la courbe
        fig.add_trace(go.Scatter(
            x=df_agent['date'],
            y=df_agent[metric_col],
            mode='lines+markers',
            name=f"{group} - {agent} - {metric_label}",
            text=df_agent[metric_col].apply(lambda x: f"{x:.1f}%") if metric_col != "mean_answer_time" else df_agent[metric_col].apply(seconds_to_hms),
            textposition='top center',
            line=dict(width=2)
        ))

        # Ajouter les annotations pour chaque agent
        for i, row in df_agent.iterrows():
            agent_value = row[metric_col]
            agent_name = row['agent']
            date = row['date']
            
            fig.add_annotation(
                x=date,
                y=agent_value,
                text=f"{agent_name}: {seconds_to_hms(agent_value) if metric_col == 'mean_answer_time' else f'{agent_value:.1f}%'}",
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-50,
                font=dict(size=10, color="black"),
                bgcolor="white",
                opacity=0.7
            )

# Personnalisation du graphique
fig.update_layout(
    title=f"{metric_label} over Time by Group with Agent Values",
    xaxis_title="Date",
    yaxis_title="Values",
    height=600,
    showlegend=True,
)
st.plotly_chart(fig, use_container_width=True)  
########################################################
st.markdown("---")

# --- SECTION 3: AGENT ANALYSIS ---
st.subheader("Agent Performance Analysis")
st.markdown("This section focuses on individual agent performance across different metrics.")

# Full-width chart
st.plotly_chart(fig_agent, use_container_width=True)  # Tickets by Agent and Group

st.empty().write("")  # Adds spacing

# Full-width charts
st.plotly_chart(fig_heatmap, use_container_width=True)

# Two-column heatmaps
col1, col2 = st.columns([1, 1])

with col1:
    st.plotly_chart(fig_sla_1st_response, use_container_width=True)  # Heatmap SLA 1st Response

with col2:
    st.plotly_chart(fig_perc_sla, use_container_width=True)  # Heatmap SLA Compliance

# Full-width charts
st.plotly_chart(fig_agent_actions, use_container_width=True, key="agent_actions_graph_unique")  # Actions per Time Slot by Agent

st.markdown("---")

# --- END OF DASHBOARD ---
st.markdown("🚀 **End of Dashboard**")
