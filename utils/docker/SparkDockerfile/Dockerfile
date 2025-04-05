FROM python:3.9-slim
WORKDIR /app
COPY spark_tuning_job.py /app/
COPY spark_inference_job.py /app/
RUN pip install pyspark torch torchvision Pillow boto3 sqlite3
CMD ["bash"]
