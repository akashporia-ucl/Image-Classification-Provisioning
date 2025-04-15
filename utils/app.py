import secrets
import time
import json
import subprocess
import os
import sys
import logging
import pika
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_socketio import SocketIO

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Load Environment Variables and Setup CORS
# -----------------------------------------------------------------------------
load_dotenv(dotenv_path='/home/almalinux/Image Classification/backend/.env')
cors_origins = os.getenv(
    'REACT_APP_CORS_ORIGINS',
    'https://react-ucabpor.comp0235.condenser.arc.ucl.ac.uk,http://localhost:3501'
).split(',')
if 'http://localhost:3501' not in cors_origins:
    cors_origins.append('http://localhost:3501')
logger.info(f"CORS origins: {cors_origins}")

app = Flask(__name__)
CORS(app, origins=cors_origins)
socketio = SocketIO(app, cors_allowed_origins=cors_origins)

# -----------------------------------------------------------------------------
# App Configuration
# -----------------------------------------------------------------------------
app.config['JWT_SECRET_KEY'] = secrets.token_urlsafe(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

jwt = JWTManager(app)
db = SQLAlchemy(app)

# -----------------------------------------------------------------------------
# File Upload Setup
# -----------------------------------------------------------------------------
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -----------------------------------------------------------------------------
# RabbitMQ Configuration
# -----------------------------------------------------------------------------
RABBITMQ_HOST = 'worker1'
credentials = pika.PlainCredentials('myuser', 'mypassword')
EXCHANGE_NAME = 'direct_logs'
REQUEST_QUEUE = 'request_queue'
REQUEST_ROUTING_KEY = 'request_key'
RESPONSE_QUEUE = 'response_queue'
RESPONSE_ROUTING_KEY = 'response_key'

# -----------------------------------------------------------------------------
# Database Model
# -----------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='testuser').first():
        hashed_pw = generate_password_hash('testpass')
        test_user = User(username='testuser', password=hashed_pw)
        db.session.add(test_user)
        db.session.commit()
        logger.info("Test user 'testuser' created with password 'testpass'")

# -----------------------------------------------------------------------------
# RabbitMQ Publisher
# -----------------------------------------------------------------------------
def request_publisher(message):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
        )
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct')
        channel.queue_declare(queue=REQUEST_QUEUE, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=REQUEST_QUEUE, routing_key=REQUEST_ROUTING_KEY)
        channel.basic_publish(exchange=EXCHANGE_NAME, routing_key=REQUEST_ROUTING_KEY, body=message)
        logger.info("Message sent to RabbitMQ: %s", message)
        connection.close()
    except Exception as e:
        logger.error("Error in request_publisher: %s", e)

# -----------------------------------------------------------------------------
# RabbitMQ Response Consumer with Timed-Polling
# -----------------------------------------------------------------------------
def response_consumer(timeout=10):
    """
    Polls the RabbitMQ response queue for a specified time limit.
    Returns the first message received or None if the timeout expires.
    """
    result = None
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
        )
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct')
        channel.queue_declare(queue=RESPONSE_QUEUE, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=RESPONSE_QUEUE, routing_key=RESPONSE_ROUTING_KEY)

        start_time = time.time()
        logger.info("Started polling the response queue with a timeout of %s seconds", timeout)
        while time.time() - start_time < timeout:
            method_frame, header_frame, body = channel.basic_get(queue=RESPONSE_QUEUE, auto_ack=True)
            if method_frame:
                result = body.decode('utf-8')
                logger.info("Received response: %s", result)
                break
            time.sleep(0.5)
        connection.close()
        if result is None:
            logger.warning("Response not received within timeout (%s seconds)", timeout)
        return result
    except Exception as e:
        logger.error("Error in response_consumer: %s", e)
        return None

# -----------------------------------------------------------------------------
# HDFS Utility Functions
# -----------------------------------------------------------------------------
def put_image_to_hdfs(local_file, hdfs_path):
    try:
        logger.info("Uploading %s to HDFS at %s", local_file, hdfs_path)
        result = subprocess.run(
            ['hdfs', 'dfs', '-put', local_file, hdfs_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info("HDFS upload output: %s", result.stdout.decode())
        logger.info("Successfully uploaded %s to HDFS at %s", local_file, hdfs_path)
    except subprocess.CalledProcessError as e:
        logger.error("Error uploading file to HDFS: %s", e.stderr.decode())

def cleanup_upload_folder(local_file):
    try:
        os.remove(local_file)
        logger.info("Removed local file: %s", local_file)
    except Exception as e:
        logger.error("Error removing local file: %s", e)

# -----------------------------------------------------------------------------
# Flask Endpoints
# -----------------------------------------------------------------------------
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    logger.info("Register request received: %s", data)
    
    if User.query.filter_by(username=data['username']).first():
        logger.info("Username already exists")
        return jsonify({"msg": "Username already exists"}), 400
    
    hashed_pw = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    logger.info("User '%s' registered successfully", data['username'])
    
    token = create_access_token(identity=data['username'])
    return jsonify({"msg": "User registered successfully", "access_token": token}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    logger.info("Login attempt: %s", data['username'])
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        token = create_access_token(identity=user.username)
        logger.info("Login successful for user: %s", data['username'])
        return jsonify(access_token=token)
    logger.warning("Login failed for user: %s", data['username'])
    return jsonify({"msg": "Invalid credentials"}), 401

@app.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    current_user = get_jwt_identity()
    logger.info("Protected route accessed by user: %s", current_user)

    if 'file' not in request.files:
        logger.error("No file part in the request")
        return jsonify(msg="No file part"), 400

    file = request.files['file']
    if file.filename == '':
        logger.error("No selected file")
        return jsonify(msg="No selected file"), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    logger.info("File saved at: %s", file_path)

    try:
        # Upload the image file to HDFS
        put_image_to_hdfs(file_path, "/data/images/")
        # Clean up the local file
        cleanup_upload_folder(file_path)

        message_data = {
            'filename': filename,
            'hdfs_path': "/data/images/" + filename
        }
        message = json.dumps(message_data)
        request_publisher(message)
        logger.info("Request sent to RabbitMQ. Waiting for prediction result...")

        # Poll for response from RabbitMQ using timed polling
        response = response_consumer(timeout=10)
        if response is None:
            return jsonify(msg="Prediction result not received within timeout"), 504
        
        result = {"Result": response}
        return jsonify(result), 200

    except Exception as e:
        logger.error("Prediction process failed: %s", e)
        return jsonify(msg="Prediction process failed"), 500

@app.route('/test_socket')
def test_socket():
    socketio.emit('rabbitmq_message', {'message': 'Test message from server'})
    return 'Test event sent!'

@app.route('/csv_<string:mode>', methods=['GET'])
@jwt_required()
def get_csv(mode):
    current_user = get_jwt_identity()
    logger.info("CSV download requested by user: %s", current_user)

    if mode == 'train':
        hdfs_file_path = '/data/distributed_evaluation_results.csv'
    elif mode == 'test':
        hdfs_file_path = '/data/distributed_evaluation_test_results.csv'
    else:
        logger.error("Invalid CSV mode requested: %s", mode)
        return jsonify(msg="Invalid CSV mode requested"), 400
    try:
        result = subprocess.run(
            ['hdfs', 'dfs', '-cat', hdfs_file_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        csv_content = result.stdout
        logger.info("Fetched CSV content from HDFS (%s bytes)", len(csv_content))
        response = app.response_class(
            response=csv_content,
            status=200,
            mimetype='text/csv'
        )
        response.headers['Content-Disposition'] = 'attachment; filename=test_results_inception.csv'
        logger.info("CSV file sent successfully")
        return response
    except subprocess.CalledProcessError as e:
        logger.error("Error fetching CSV file from HDFS: %s", e.stderr.decode())
        return jsonify(msg="CSV file not found or error fetching from HDFS"), 500

# -----------------------------------------------------------------------------
# SocketIO and Background Task for Model Tuning Messages
# -----------------------------------------------------------------------------
def model_tuning_consumer():
    def callback(ch, method, properties, body):
        message = body.decode('utf-8')
        logger.info("Received RabbitMQ message: %s", message)
        if message == "Model tuning completed":
            socketio.emit('rabbitmq_message', {'message': message})
        else:
            socketio.emit('update_message', {'message': message})
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='management', credentials=credentials))
        channel = connection.channel()
        channel.queue_declare(queue='model_queue', durable=True)
        channel.exchange_declare(exchange='direct_logs', exchange_type='direct')
        channel.queue_bind(exchange='direct_logs', queue='model_queue', routing_key='model_key')
        logger.info("RabbitMQ consumer started, waiting for messages.")
        channel.basic_consume(queue='model_queue', on_message_callback=callback, auto_ack=True)
        channel.start_consuming()
    except Exception as e:
        logger.error("Error in RabbitMQ consumer: %s", e)

socketio.start_background_task(model_tuning_consumer)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=3500)
