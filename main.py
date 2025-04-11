from collections import defaultdict
import re
import requests
import base64
from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv
import json

load_dotenv()

categories = {
    # Paper/Cardboard category
    "cardboard cup": "Paper",
    "piece of brown cardboard": "Paper",
    "piece of paper": "Paper",
    "brown cartoon": "Paper",
    "egg carton": "Paper",
    "cardboard": "Paper",
    "paper": "Paper",
    "cardboard box": "Paper",
    "cardboard packaging": "Paper",
    "corrugated board": "Paper",
    "paperboard": "Paper",
    "cereal box": "Paper",
    "milk carton": "Paper",
    "juice carton": "Paper",
    "pizza box": "Paper",
    "food packaging": "Paper",
    "magazine": "Paper",
    "book": "Paper",
    "envelope": "Paper",
    "newspaper": "Paper",
    "carton": "Paper",
    "tetra pak": "Paper",
    "paper cup": "Paper",
    "paper bag": "Paper",
    "paper wrapper": "Paper",
    "paper tray": "Paper",
    "paper container": "Paper",

    # Glass category
    "glass": "Glass",
    "glass bottle": "Glass",
    "glass jar": "Glass",
    "beverage bottle": "Glass",
    "jar": "Glass",
    "glass container": "Glass",
    "sauce jar": "Glass",
    "jam jar": "Glass",
    "cosmetic jar": "Glass",
    "window pane": "Glass",
    "glass pane": "Glass",
    "glass cup": "Glass",
    "glass dish": "Glass",
    "glass vase": "Glass",
    "glass mirror": "Glass",

    # Metal category
    "aluminum": "Metal",
    "aluminum can": "Metal",
    "tin can": "Metal",
    "scrap metal": "Metal",
    "aluminum foil": "Metal",
    "beverage can": "Metal",
    "soda can": "Metal",
    "steel can": "Metal",
    "food can": "Metal",
    "paint can": "Metal",
    "oil can": "Metal",

    # Plastic category
    "plastic bottle": "Plastic",
    "plastic bottles": "Plastic",
    "plastic": "Plastic",  # Added a more general 'plastic' keyword to catch everything
    "blue pet bottle": "Plastic",
    "pet bottle": "Plastic",
    "water bottle": "Plastic",
    "white foam": "Plastic",
    "piece of fabric": "Plastic",
    "aquarium": "Plastic",
    "bucket": "Plastic",
    "hose": "Plastic",
    "piece of milk carton": "Plastic",
    "plastic lid": "Plastic",
    "vegetable fruit crate": "Plastic",
    "food container": "Plastic",
}


# Görseli küçültüp base64'e çevir
def encode_image(image_path, max_size=(512, 512)):
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Görsel dosyası bulunamadı: {image_path}")

        image = Image.open(image_path).convert("RGB")
        image.thumbnail(max_size)
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Görsel işleme hatası: {str(e)}")
        return None


# Moondream API analiz
def analyze_image_with_moondream(image_path):
    api_key = os.getenv('MOONDREAM_API_KEY')
    if not api_key:
        print("ERROR: MOONDREAM_API_KEY NOT FOUND.")
        return None

    image_b64 = encode_image(image_path)
    if not image_b64:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "moondream-2B",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "This is a waste/trash image. Please list *unique* waste items with their *estimated quantity* only if they are clearly visible. Avoid repeating the same item multiple times. Focus on: paper, cardboard, plastic, metal, glass."
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            "https://api.moondream.ai/v1/chat/completions",
            headers=headers,
            json=payload
        )

        if response.status_code == 403:
            print("ERROR: 403 - API erişim izniniz yok. Lütfen Moondream API anahtarınızı kontrol edin.")
            return None
        elif response.status_code != 200:
            print(f"ERROR: {response.status_code} - {response.text}")
            return None

        result = response.json()
        message_content = result["choices"][0]["message"]["content"]

        return message_content
    except requests.exceptions.RequestException as e:
        print(f"API isteği hatası: {str(e)}")
        return None
    except ValueError as e:
        print(f"JSON ayrıştırma hatası: {str(e)}")
        return None


def classify_waste_items(response_text):
    response_text = response_text.lower()
    waste_count = defaultdict(int)

    # "item: quantity" formatını yakala (örnek: "plastic bottles: 20")
    items = re.findall(r'([^:,\n]+):\s*(\d+)', response_text)

    for label, quantity in items:
        label = label.strip()
        quantity = int(quantity)

        # Kategori eşleştirme
        matched_category = None
        for keyword, category in categories.items():
            if keyword in label:
                matched_category = category
                break

        if matched_category:
            waste_count[matched_category] += quantity
            print(f"Bulundu: {quantity}x {label} → {matched_category}")
        else:
            print(f"Atlandı: {label} (kategori yok)")

    # JSON çıktısı
    return json.dumps({
        "paper": waste_count.get("Paper", 0),
        "plastic": waste_count.get("Plastic", 0),
        "metal": waste_count.get("Metal", 0),
        "glass": waste_count.get("Glass", 0)
    }, indent=4)


# Örnek kullanım:
def process_image(image_path):
    print(f"Görsel analiz ediliyor: {image_path}")
    result_text = analyze_image_with_moondream(image_path)
    if result_text:
        print("\nAPI'dan Gelen Yanıt:")
        print(result_text)
        json_output = classify_waste_items(result_text)
        print("\nJSON Çıktısı:")
        print(json_output)


if __name__ == "__main__":
    image_path = r"D:\inegol_images\IMG-20250410-WA0016.jpg"
    process_image(image_path)
