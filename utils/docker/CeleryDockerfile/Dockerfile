FROM python:3.9-slim
WORKDIR /app
COPY celery_app.py /app/
RUN pip install celery pika
CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
