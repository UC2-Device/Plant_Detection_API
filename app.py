from flask import Flask, request, jsonify
import requests
import certifi
from PIL import Image
import io
import os

app = Flask(__name__)

# 🔑 Replace with your real PlantNet API key
PLANTNET_API_KEY = ""
project = 'all'
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/{project}?api-key={PLANTNET_API_KEY}"

@app.route("/identify", methods=["POST"])
def identify_plant():
    try:
        # ✅ Check file
        if "images" not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        image_file = request.files["images"]

        # ✅ Resize large images (max 1024px)
        img = Image.open(image_file)
        img.thumbnail((1024, 1024))  
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)

        files = {
            "images": ("plant.jpg", buf, "images/jpeg")
        }

        data = {}
        if "organs" in request.form:
            data["organs"] = request.form["organs"]

        response = requests.post(
            PLANTNET_URL,
            files=files,
            data=data,
            verify=certifi.where(),  # secure SSL
            timeout=30
        )

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
