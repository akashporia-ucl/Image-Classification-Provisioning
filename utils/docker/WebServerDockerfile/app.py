from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import pika, os, secrets, boto3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = secrets.token_urlsafe(32)
jwt = JWTManager(app)

# In-memory user store (replace with persistent storage as needed)
USERS = {"demo": "password"}

# Configure boto3 client for MinIO (S3-compatible)
s3_client = boto3.client('s3',
    endpoint_url="http://minio:9000",
    aws_access_key_id="minioaccesskey",
    aws_secret_access_key="miniosecretkey",
)

BUCKET_NAME = "images"

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if data.get("username") in USERS and USERS[data.get("username")] == data.get("password"):
        token = create_access_token(identity=data.get("username"))
        return jsonify(access_token=token), 200
    return jsonify({"msg": "Bad credentials"}), 401

@app.route('/upload', methods=['POST'])
@jwt_required()
def upload():
    if 'file' not in request.files:
        return jsonify({"msg": "No file uploaded"}), 400
    file = request.files['file']
    filename = secure_filename(file.filename)
    local_path = os.path.join("/tmp", filename)
    file.save(local_path)
    # Upload file to MinIO
    s3_client.upload_file(local_path, BUCKET_NAME, filename)
    # Enqueue a task for inference
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='image_tasks', durable=True)
    message = f"{BUCKET_NAME}|{filename}"
    channel.basic_publish(exchange='',
                          routing_key='image_tasks',
                          body=message,
                          properties=pika.BasicProperties(delivery_mode=2))
    connection.close()
    return jsonify({"msg": "File uploaded and task queued"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
