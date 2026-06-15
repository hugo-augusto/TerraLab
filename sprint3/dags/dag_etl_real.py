from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import geopandas as gpd
import psycopg2
from shapely.geometry import Point


def extrair(**context):
    df = pd.read_csv('/opt/airflow/data/dados_processo_seletivo.csv')
    print(f"Total de registros extraidos: {len(df)}")
    context['ti'].xcom_push(key='total_extraido', value=len(df))
    return len(df)


def transformar(**context):
    df = pd.read_csv('/opt/airflow/data/dados_processo_seletivo.csv')
    total_inicial = len(df)

    # Remover OpenRouteService
    df = df[df['geoapi_id'] != 'OpenRouteService']
    print(f"Apos remover OpenRouteService: {len(df)} registros")

    # Ler shapefile local do IBGE
    estados = gpd.read_file('/opt/airflow/data/sprint3/BR_UF_2022.zip')
    estados = estados.to_crs(epsg=4326)

    # Verificar se cada ponto esta dentro da UF declarada
    def ponto_dentro_uf(row):
        try:
            ponto = Point(row['longitude'], row['latitude'])
            uf = estados[estados['SIGLA_UF'] == row['state']]
            if uf.empty:
                return False
            return uf.geometry.contains(ponto).any()
        except Exception:
            return False

    df['dentro_uf'] = df.apply(ponto_dentro_uf, axis=1)
    df = df[df['dentro_uf'] == True].drop(columns=['dentro_uf'])
    print(f"Apos remover pontos fora da UF: {len(df)} registros")
    print(f"Total removido: {total_inicial - len(df)} registros")

    df.to_csv('/opt/airflow/data/sprint3/dados_tratados.csv', index=False)
    return len(df)


def carregar():
    df = pd.read_csv('/opt/airflow/data/sprint3/dados_tratados.csv')

    conn = psycopg2.connect(
        host="postgres",
        database="airflow",
        user="airflow",
        password="airflow"
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dados_tratados (
            id SERIAL PRIMARY KEY,
            city VARCHAR(100),
            state VARCHAR(10),
            latitude FLOAT,
            longitude FLOAT,
            accuracy FLOAT,
            geoapi_id VARCHAR(100),
            date VARCHAR(20)
        )
    """)

    cursor.execute("DELETE FROM dados_tratados")

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO dados_tratados (city, state, latitude, longitude, accuracy, geoapi_id, date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            row['city'],
            row['state'],
            row['latitude'],
            row['longitude'],
            row['accuracy'],
            row['geoapi_id'],
            row['date']
        ))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Total de registros carregados no Postgres: {len(df)}")


with DAG(
    'dag_etl_real',
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    description='ETL real: extrai CSV, transforma e carrega no Postgres'
) as dag:

    tarefa_extrair = PythonOperator(
        task_id='extrair',
        python_callable=extrair
    )

    tarefa_transformar = PythonOperator(
        task_id='transformar',
        python_callable=transformar,
        provide_context=True
    )

    tarefa_carregar = PythonOperator(
        task_id='carregar',
        python_callable=carregar
    )

    tarefa_extrair >> tarefa_transformar >> tarefa_carregar