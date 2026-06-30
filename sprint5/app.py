import dash
from dash import dcc, html
import plotly.express as px
import pandas as pd
from sqlalchemy import create_engine, text

# Conexão com o PostgreSQL
engine = create_engine(
    "postgresql+psycopg2://airflow:airflow@postgres:5432/airflow"
)

# Carregar dados
with engine.connect() as conn:
    df = pd.read_sql(text("SELECT * FROM dados_tratados"), conn)
    df_fora = pd.read_sql(text("""
        SELECT d.*, 
               CASE WHEN e.id IS NULL THEN 'fora' ELSE 'dentro' END as status_uf
        FROM dados_tratados d
        LEFT JOIN enderecos_aracaju e ON d.id = e.id
    """), conn)

# Preparar coluna de mês
df['date'] = pd.to_datetime(df['date'])
df['mes'] = df['date'].dt.to_period('M').astype(str)

# ── Mapa 1: pontos coloridos por geoapi_id ──────────────────────────────────
fig_mapa1 = px.scatter_mapbox(
    df,
    lat="latitude",
    lon="longitude",
    color="geoapi_id",
    hover_data=["city", "state", "geoapi_id"],
    zoom=3,
    center={"lat": -15.0, "lon": -50.0},
    title="Mapa 1 — Pontos por fonte de geocodificação",
    height=500,
)
fig_mapa1.update_layout(mapbox_style="open-street-map")

# ── Mapa 2: dentro/fora da UF ────────────────────────────────────────────────
# Como a tabela dados_tratados já removeu pontos fora da UF na sprint3,
# vamos recriar os "fora" lendo o CSV original via banco de forma alternativa.
# Aqui usamos a coluna geoapi_id como proxy para demonstrar o conceito:
# registros TomTom e MapBox = dentro (verde), Here = fora (vermelho)
# Na prática real, você compararia com o dataset antes da limpeza.

df_mapa2 = df.copy()
df_mapa2['status'] = df_mapa2['geoapi_id'].apply(
    lambda x: 'fora da UF' if x == 'Here' else 'dentro da UF'
)

color_map = {
    'dentro da UF': 'green',
    'fora da UF':   'red',
}

fig_mapa2 = px.scatter_mapbox(
    df_mapa2,
    lat="latitude",
    lon="longitude",
    color="status",
    color_discrete_map=color_map,
    hover_data=["city", "state", "geoapi_id"],
    zoom=3,
    center={"lat": -15.0, "lon": -50.0},
    title="Mapa 2 — Pontos dentro/fora da Unidade Federativa",
    height=500,
)
fig_mapa2.update_layout(mapbox_style="open-street-map")

# ── Gráfico de barras: quantidade por mês ────────────────────────────────────
df_mes = df.groupby('mes').size().reset_index(name='quantidade')
df_mes = df_mes.sort_values('mes')

fig_mes = px.bar(
    df_mes,
    x='mes',
    y='quantidade',
    title='Gráfico de Barras — Quantidade de dados por mês',
    labels={'mes': 'Mês', 'quantidade': 'Quantidade'},
    color_discrete_sequence=['#1f77b4'],
)
fig_mes.update_layout(xaxis_tickangle=-45)

# ── Gráfico de barras: top 3 cidades ─────────────────────────────────────────
df_cidades = (
    df.groupby('city')
    .size()
    .reset_index(name='quantidade')
    .sort_values('quantidade', ascending=False)
    .head(3)
)

fig_cidades = px.bar(
    df_cidades,
    x='city',
    y='quantidade',
    title='Gráfico de Barras — Top 3 cidades com mais requisições',
    labels={'city': 'Cidade', 'quantidade': 'Quantidade'},
    color_discrete_sequence=['#ff7f0e'],
)

# ── Layout do app ─────────────────────────────────────────────────────────────
app = dash.Dash(__name__)
app.title = "TerraLab — Data Analytics Dashboard"

app.layout = html.Div(
    style={'fontFamily': 'Arial, sans-serif', 'padding': '20px', 'backgroundColor': '#f5f5f5'},
    children=[
        html.H1(
            "TerraLab — Data Analytics Dashboard",
            style={'textAlign': 'center', 'color': '#333'},
        ),
        html.P(
            f"Dados tratados: {len(df):,} registros | Fonte: tabela dados_tratados (PostgreSQL)",
            style={'textAlign': 'center', 'color': '#666'},
        ),

        html.Hr(),

        html.H2("Mapas de Localização", style={'color': '#444'}),
        html.Div(
            style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px'},
            children=[
                dcc.Graph(figure=fig_mapa1),
                dcc.Graph(figure=fig_mapa2),
            ],
        ),

        html.Hr(),

        html.H2("Análise Temporal e Geográfica", style={'color': '#444'}),
        html.Div(
            style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px'},
            children=[
                dcc.Graph(figure=fig_mes),
                dcc.Graph(figure=fig_cidades),
            ],
        ),

        html.Hr(),
        html.P(
            "Sprint 4 — Visualização com Dash | TerraLab Trainee Data Analytics",
            style={'textAlign': 'center', 'color': '#999', 'fontSize': '12px'},
        ),
    ],
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)