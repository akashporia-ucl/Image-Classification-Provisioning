import argparse, io, os, sqlite3, boto3
from pyspark.sql import SparkSession
from PIL import Image
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.models as models
import torchvision.transforms as transforms

# Connect to MinIO
s3_client = boto3.client('s3',
    endpoint_url="http://minio:9000",
    aws_access_key_id="minioaccesskey",
    aws_secret_access_key="miniosecretkey",
)
BUCKET_NAME = "images"

def load_model():
    model = models.resnet50(pretrained=True)
    # For fine-tuning, replace the final layer (example for 2 classes)
    model.fc = nn.Linear(model.fc.in_features, 2)
    return model

def get_transforms():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
    ])

def fetch_image_from_s3(key):
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    return Image.open(io.BytesIO(response['Body'].read())).convert("RGB")

def main():
    spark = SparkSession.builder.appName("TuningJob").getOrCreate()
    sc = spark.sparkContext
    # For demo purposes, assume these image keys are available in MinIO
    image_keys = ["img1.jpg", "img2.jpg", "img3.jpg"]
    rdd = sc.parallelize(image_keys)
    transform = get_transforms()
    def preprocess(key):
        try:
            image = fetch_image_from_s3(key)
            tensor = transform(image)
            return (key, tensor.numpy().tolist())
        except Exception as e:
            return (key, None)
    processed = rdd.map(preprocess).collect()
    model = load_model()
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    for epoch in range(2):  # demo: 2 epochs
        for key, data in processed:
            if data is None:
                continue
            input_tensor = torch.tensor(data).unsqueeze(0)
            target = torch.tensor([1])
            optimizer.zero_grad()
            output = model(input_tensor)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
    # Save tuned model and upload to MinIO
    torch.save(model.state_dict(), "tuned_model.pt")
    s3_client.upload_file("tuned_model.pt", BUCKET_NAME, "tuned_model.pt")
    # Log training metrics to a SQLite DB
    conn = sqlite3.connect("tuning_metrics.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS metrics (epoch INTEGER, loss REAL)")
    c.execute("INSERT INTO metrics VALUES (?, ?)", (epoch, loss.item()))
    conn.commit()
    conn.close()
    spark.stop()
    print("Tuning complete. Model saved to MinIO and metrics logged.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    main()
