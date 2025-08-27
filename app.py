from flask import Flask, request, jsonify
import requests
import certifi
from PIL import Image
import io
import time
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# 🔑 Replace with your real PlantNet API key
PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY")
project = "all"
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/{project}?api-key={PLANTNET_API_KEY}"


def post_with_retry(url, files, data, retries=3, delay=2):
    """Try sending a POST request with retries."""
    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] Attempt {attempt}/{retries} sending request to PlantNet...")
            response = requests.post(
                url,
                files=files,
                data=data,
                verify=certifi.where(),
                timeout=30,
            )
            print(f"[INFO] Attempt {attempt} completed with status {response.status_code}")
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
        # ✅ Check file
        if "images" not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        image_file = request.files["images"]

        # Detect extension
        ext = os.path.splitext(image_file.filename)[1].lower()
        img = Image.open(image_file)

        # ✅ Resize large images (max 1024px)
        img.thumbnail((1024, 1024))

        buf = io.BytesIO()

        # ✅ Handle PNG or JPEG correctly
        if ext in [".png"]:
            if img.mode in ("RGBA", "P"):  # Convert if has alpha channel
                img = img.convert("RGB")
            img.save(buf, format="PNG")
            mime_type = "image/png"
            filename = "plant.png"
        else:  # default → JPEG
            if img.mode in ("RGBA", "P"):  # Convert for JPEG compatibility
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

        # 🔄 Retry-enabled request
        response = post_with_retry(PLANTNET_URL, files, data, retries=3, delay=2)

        if response.status_code != 200:
            return jsonify({
                "error": "PlantNet API request failed",
                "status_code": response.status_code,
                "details": response.text
            }), response.status_code

        return jsonify(response.json())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
