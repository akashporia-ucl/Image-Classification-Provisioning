from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from datetime import datetime, timedelta

default_args = {
    'owner': 'admin',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'max_active_runs': 1,
}

with DAG(
    dag_id='spark_dag',
    default_args=default_args,
    description='A simple Spark DAG',
    schedule_interval='@once',
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    tune_resnet = SparkSubmitOperator(
        task_id='tune_resnet',
        application='resnet50.py',
        name="Tune Inception Model",
        application_args=['.1'],  # match your CLI argument
        executor_memory='4G',
        executor_cores=2,
        num_executors=4,
        conf={'spark.master': 'spark://management:7077'},
        deploy_mode='client'
    )

    tune_resnet