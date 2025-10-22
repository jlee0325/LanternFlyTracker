import os
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient, ContentSettings

# Environment variables
CONTAINER_NAME = os.getenv("IMAGES_CONTAINER", "lanternfly-images")
CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")

# Connect to Azure Blob
bsc = BlobServiceClient.from_connection_string(CONNECTION_STRING)
cc = bsc.get_container_client(CONTAINER_NAME)
app = Flask(__name__)

# Ensure container exists
try:
    cc.create_container()
    print(f"✅ Created container {CONTAINER_NAME}")
except Exception:
    print(f"ℹ️ Container {CONTAINER_NAME} already exists")

# Helper: sanitize filename
def sanitize_filename(name):
    base = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    return base.lower()

@app.post("/api/v1/upload")
def upload():
    """Upload endpoint for images."""
    if "file" not in request.files:
        return jsonify(ok=False, error="Missing file field"), 400

    f = request.files["file"]
    if not f or f.filename == "":
        return jsonify(ok=False, error="No file selected"), 400
    if not f.mimetype.startswith("image/"):
        return jsonify(ok=False, error="Only image/* types allowed"), 415
    if request.content_length and request.content_length > 10 * 1024 * 1024:
        return jsonify(ok=False, error="File too large (max 10 MB)"), 413

    clean = sanitize_filename(f.filename)
    blob_name = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}-{clean}"
    try:
        cc.upload_blob(
            blob_name,
            f.read(),
            overwrite=True,
            content_settings=ContentSettings(content_type=f.mimetype),
        )
        blob_url = f"{ACCOUNT_URL}/{CONTAINER_NAME}/{blob_name}"
        print(f"✅ Uploaded {blob_name}")
        return jsonify(ok=True, url=blob_url)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.get("/api/v1/gallery")
def gallery():
    """Return list of public blob URLs."""
    try:
        urls = [
            f"{ACCOUNT_URL}/{CONTAINER_NAME}/{b.name}"
            for b in cc.list_blobs()
        ]
        return jsonify(ok=True, gallery=urls)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.get("/api/v1/health")
def health():
    return jsonify(ok=True), 200


@app.get("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)