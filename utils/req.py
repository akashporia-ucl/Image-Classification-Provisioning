import os
import subprocess
import json
import logging
import time
from PIL import Image
import pika
import torch
import torchvision.models as models
import torchvision.transforms as transforms

# -----------------------------------------------------------------------------
# Configuration and Constants
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RabbitMQ configuration
RABBITMQ_HOST = 'worker1'
RABBITMQ_USERNAME = 'myuser'
RABBITMQ_PASSWORD = 'mypassword'
credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)

# Exchange and queue settings
EXCHANGE_NAME = 'direct_logs'
REQUEST_QUEUE = 'request_queue'
REQUEST_ROUTING_KEY = 'request_key'
RESPONSE_QUEUE = 'response_queue'
RESPONSE_ROUTING_KEY = 'response_key'

# HDFS configuration for the model and images
MODEL_HDFS_PATH = '/data/model_collated'
# (No hardcoding of local filename; it is chosen dynamically from HDFS)

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------
def find_model_file_in_hdfs(hdfs_dir):
    try:
        output = subprocess.check_output(["hdfs", "dfs", "-ls", hdfs_dir]).decode("utf-8")
    except subprocess.CalledProcessError as e:
        logger.error("Error listing HDFS directory '%s': %s", hdfs_dir, e)
        return None
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) >= 8:
            file_path = parts[-1]
            if file_path.endswith(".pt"):
                return file_path
    return None

def load_pretrained_model():
    model_file_in_hdfs = find_model_file_in_hdfs(MODEL_HDFS_PATH)
    if model_file_in_hdfs is None:
        logger.error("No .pt model file found in HDFS directory '%s'", MODEL_HDFS_PATH)
        raise FileNotFoundError("No model file found in HDFS directory.")
    
    local_model_filename = os.path.basename(model_file_in_hdfs)
    if not os.path.exists(local_model_filename):
        logger.info("Local model file '%s' not found. Downloading from HDFS: %s", 
                    local_model_filename, model_file_in_hdfs)
        subprocess.run(['hdfs', 'dfs', '-get', model_file_in_hdfs, local_model_filename], check=True)
    
    try:
        loaded_obj = torch.load(local_model_filename, map_location=torch.device('cpu'))
    except Exception as e:
        logger.error("Error loading model file '%s': %s", local_model_filename, e)
        raise e

    filename_lower = local_model_filename.lower()
    if "resnet" in filename_lower:
        logger.info("Detected architecture: ResNet50")
        model = models.resnet50(pretrained=False, num_classes=2)
        arch = "resnet"
    elif "vgg" in filename_lower:
        logger.info("Detected architecture: VGG16")
        model = models.vgg16(pretrained=False, num_classes=2)
        arch = "vgg"
    elif "inception" in filename_lower:
        logger.info("Detected architecture: InceptionV3")
        model = models.inception_v3(pretrained=False, num_classes=2, aux_logits=False)
        arch = "inception"
    else:
        logger.warning("Unknown model architecture in filename '%s'. Defaulting to ResNet50.", local_model_filename)
        model = models.resnet50(pretrained=False, num_classes=2)
        arch = "resnet"

    if isinstance(loaded_obj, dict):
        model.load_state_dict(loaded_obj)
    else:
        model = loaded_obj

    model.eval()
    logger.info("Pretrained model loaded successfully from '%s'", local_model_filename)
    return model, arch

def download_image_from_hdfs(hdfs_path, local_path):
    logger.info("Downloading image from HDFS: '%s' to local file: '%s'", hdfs_path, local_path)
    subprocess.run(['hdfs', 'dfs', '-get', hdfs_path, local_path], check=True)

def preprocess_image(image_path, arch):
    """
    Preprocess the input image in the same way as during training.
    For InceptionV3, use a 299x299 crop; for other architectures (e.g., ResNet50), use 224x224.
    """
    image = Image.open(image_path).convert('RGB')
    target_size = (299, 299) if arch == "inception" else (224, 224)
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(target_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])
    image = transform(image)
    image = image.unsqueeze(0)
    return image

def publish_response(classification):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
        )
        channel = connection.channel()
        # Declare the exchange without durable flag (or set durable=False to match existing exchange)
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct')
        channel.queue_declare(queue=RESPONSE_QUEUE, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=RESPONSE_QUEUE, routing_key=RESPONSE_ROUTING_KEY)
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=RESPONSE_ROUTING_KEY,
            body=str(classification),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        logger.info("Published classification result: '%s'", classification)
        time.sleep(0.2)
        connection.close()
    except Exception as e:
        logger.error("Error publishing response: %s", e)

def process_message(body, model, arch):
    logger.info("Processing message: %s", body)
    try:
        message_data = json.loads(body.decode('utf-8'))
    except Exception as e:
        logger.error("Failed to parse message: %s", e)
        return

    filename = message_data.get('filename')
    hdfs_image_path = message_data.get('hdfs_path')
    if not filename or not hdfs_image_path:
        logger.error("Invalid message data: %s", message_data)
        return

    local_image_path = filename
    try:
        download_image_from_hdfs(hdfs_image_path, local_image_path)
        # Use the updated preprocessing for consistency with training
        input_tensor = preprocess_image(local_image_path, arch)
        with torch.no_grad():
            output = model(input_tensor)
        classification = output.argmax(dim=1).item()
        publish_response(classification)
    except Exception as e:
        logger.error("Error during image processing/classification: %s", e)
    finally:
        if os.path.exists(local_image_path):
            try:
                os.remove(local_image_path)
            except Exception as e:
                logger.error("Error cleaning up image file: %s", e)

def on_message(ch, method, properties, body, model, arch):
    logger.info("Received message: %s", body)
    process_message(body, model, arch)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    model, arch = load_pretrained_model()
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    )
    channel = connection.channel()
    # Declare the exchange without a durable flag.
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct')
    channel.queue_declare(queue=REQUEST_QUEUE, durable=True)
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=REQUEST_QUEUE, routing_key=REQUEST_ROUTING_KEY)

    logger.info("Waiting for messages in queue '%s'. To exit press CTRL+C", REQUEST_QUEUE)

    def callback(ch, method, properties, body):
        on_message(ch, method, properties, body, model, arch)

    channel.basic_consume(queue=REQUEST_QUEUE, on_message_callback=callback, auto_ack=False)
    channel.start_consuming()

if __name__ == '__main__':
    main()
