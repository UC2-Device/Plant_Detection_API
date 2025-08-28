from flask import Flask, request, jsonify
import requests
import certifi
from PIL import Image
import io
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# PlantNet API key from .env
PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY")
if not PLANTNET_API_KEY:
    raise ValueError("PLANTNET_API_KEY not found in environment variables")

project = "all"
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/{project}?api-key={PLANTNET_API_KEY}"

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def post_with_retry(url, files, data, retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Send POST request with retries."""
    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] Attempt {attempt}/{retries} sending request to PlantNet...")
            response = requests.post(
                url,
                files=files,
                data=data,
                verify=certifi.where(),
                timeout=30
            )
            print(f"[INFO] Attempt {attempt} completed with status {response.status_code}")
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            last_exception = e
            print(f"[ERROR] Attempt {attempt} failed: {e}")
            if attempt < retries:
                print(f"[INFO] Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("[FATAL] All retries failed.")
                raise last_exception

@app.route("/identify", methods=["POST"])
def identify_plant():
    try:
        # Check for uploaded image
        if "images" not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        image_file = request.files["images"]

        # Determine extension
        ext = os.path.splitext(image_file.filename)[1].lower()
        img = Image.open(image_file)

        # Resize large images (max 1024px)
        img.thumbnail((1024, 1024))

        buf = io.BytesIO()

        # Save image correctly
        if ext in [".png"]:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buf, format="PNG")
            mime_type = "image/png"
            filename = "plant.png"
        else:  # default JPEG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=85)
            mime_type = "image/jpeg"
            filename = "plant.jpg"

        buf.seek(0)

        files = {
            "images": (filename, buf, mime_type)
        }

        data = {}
        if "organs" in request.form:
            data["organs"] = request.form["organs"]

        # Send request with retry
        response = post_with_retry(PLANTNET_URL, files, data)

        if response.status_code != 200:
            return jsonify({
                "error": "PlantNet API request failed",
                "status_code": response.status_code,
                "details": response.text
            }), response.status_code

        # Extract JSON and summarize
        data_json = response.json()
        if "results" not in data_json or len(data_json["results"]) == 0:
            return jsonify({"error": "No species detected"}), 404

        best_result = data_json["results"][0]["species"]
        summary = {
            "best_match": best_result.get("scientificName"),
            "common_names": best_result.get("commonNames", []),
            "family": best_result.get("family", {}).get("scientificName"),
            "genus": best_result.get("genus", {}).get("scientificName"),
            "score": data_json["results"][0].get("score")
        }

        return jsonify(summary["common_names"])

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
