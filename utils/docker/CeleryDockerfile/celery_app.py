from celery import Celery
import subprocess

app = Celery('tasks', broker='amqp://guest:guest@rabbitmq//')

@app.task
def run_tuning():
    cmd = [
        "spark-submit",
        "--master", "spark://spark-master:7077",
        "spark_tuning_job.py"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else result.stderr

@app.task
def run_inference(message):
    bucket, filename = message.split("|")
    cmd = [
        "spark-submit",
        "--master", "spark://spark-master:7077",
        "spark_inference_job.py",
        "--bucket", bucket,
        "--filename", filename
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else result.stderr
