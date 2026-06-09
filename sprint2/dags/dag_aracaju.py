from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import psycopg2


def ler_csv():
    df = pd.read_csv('/opt/airflow/data/dados_processo_seletivo.csv')
    print(f"CSV carregado com sucesso! Total de linhas: {len(df)}")
    print(f"Colunas: {list(df.columns)}")
    return len(df)


def filtrar_e_salvar():
    df = pd.read_csv('/opt/airflow/data/dados_processo_seletivo.csv')

    df_aracaju = df[df['city'] == 'ARACAJU'].copy()
    print(f"Total de registros de Aracaju: {len(df_aracaju)}")

    conn = psycopg2.connect(
        host="postgres",
        database="airflow",
        user="airflow",
        password="airflow"
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS enderecos_aracaju (
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

    cursor.execute("DELETE FROM enderecos_aracaju")

    for _, row in df_aracaju.iterrows():
        cursor.execute("""
            INSERT INTO enderecos_aracaju (city, state, latitude, longitude, accuracy, geoapi_id, date)
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
    print("Dados salvos no Postgres com sucesso!")


with DAG(
    'dag_aracaju_etl',
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    description='ETL: filtra enderecos de Aracaju do CSV e salva no Postgres'
) as dag:

    tarefa_ler_csv = PythonOperator(
        task_id='ler_csv',
        python_callable=ler_csv
    )

    tarefa_filtrar_salvar = PythonOperator(
        task_id='filtrar_e_salvar_aracaju',
        python_callable=filtrar_e_salvar
    )

    tarefa_ler_csv >> tarefa_filtrar_salvar