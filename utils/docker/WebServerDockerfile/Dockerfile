FROM python:3.9-slim
WORKDIR /app
COPY app.py /app/
RUN pip install flask flask-jwt-extended pika boto3
EXPOSE 5000
CMD ["python", "app.py"]
