import argparse, io, os, boto3
from pyspark.sql import SparkSession
from PIL import Image
import torch
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as transforms

s3_client = boto3.client('s3',
    endpoint_url="http://minio:9000",
    aws_access_key_id="minioaccesskey",
    aws_secret_access_key="miniosecretkey",
)
BUCKET_NAME = "images"

def load_tuned_model():
    model = models.resnet50(pretrained=False)
    model.fc = torch.nn.Linear(model.fc.in_features, 2)
    s3_client.download_file(BUCKET_NAME, "tuned_model.pt", "tuned_model.pt")
    model.load_state_dict(torch.load("tuned_model.pt", map_location=torch.device('cpu')))
    model.eval()
    return model

def get_transforms():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
    ])

def classify(bucket, filename):
    s3_client.download_file(bucket, filename, filename)
    image = Image.open(filename).convert("RGB")
    input_tensor = get_transforms()(image).unsqueeze(0)
    model = load_tuned_model()
    with torch.no_grad():
        output = model(input_tensor)
    probs = F.softmax(output, dim=1)
    confidence, pred = torch.topk(probs, 1)
    return f"Prediction: {pred.item()}, Confidence: {confidence.item():.4f}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--filename", required=True)
    args = parser.parse_args()
    result = classify(args.bucket, args.filename)
    print(result)

if __name__ == "__main__":
    main()
