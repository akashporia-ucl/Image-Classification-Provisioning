from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

# Define the Python function that prints "Hello World"
def print_hello():
    print("Hello")

def print_world():
    print("World")

def print_zephyr():
    print("Zephyr")

# Define the default_args for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 4, 7),
    'retries': 1,
}

# Initialize the DAG
with DAG(
    'zephyr',
    default_args=default_args,
    description='A simple Hello World DAG',
    schedule_interval=None,  # Set to None for one-time run
) as dag:

    # Create a PythonOperator to run the print_hello_world function
    hello_task = PythonOperator(
        task_id='hello_task',
        python_callable=print_hello,
    )

    world_task = PythonOperator(
        task_id='world_task',
        python_callable=print_world,
    )
    zephyr_task = PythonOperator(
        task_id='zephyr_task',
        python_callable=print_zephyr,
    )

    [hello_task, world_task] >> zephyr_task # Set the task to be executed