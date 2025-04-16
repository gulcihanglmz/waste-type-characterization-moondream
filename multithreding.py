from collections import defaultdict
import re
from difflib import get_close_matches
import requests
import base64
from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

API_KEY = os.getenv("MOONDREAM_API_KEY")
PROMPT_TEXT = "List the visible waste items grouped by material: paper, plastic, metal, and glass."

categories = {
    # Paper/Cardboard category
    "cardboard": "Paper", "paper": "Paper", "carton": "Paper", "box": "Paper", "tetra pak": "Paper",
    "milk carton": "Paper", "juice carton": "Paper", "food packaging": "Paper", "magazine": "Paper",
    "book": "Paper", "newspaper": "Paper", "paper cup": "Paper", "paper bag": "Paper",
    "paper wrapper": "Paper", "paper tray": "Paper", "paper container": "Paper",

    # Glass category
    "glass": "Glass", "bottle": "Glass", "jar": "Glass", "container": "Glass",
    "window": "Glass", "mirror": "Glass", "vase": "Glass",

    # Metal category
    "metal": "Metal", "aluminum": "Metal", "tin": "Metal", "can": "Metal",
    "steel": "Metal", "foil": "Metal",

    # Plastic category
    "plastic": "Plastic", "pet": "Plastic", "bottle": "Plastic", "container": "Plastic",
    "bag": "Plastic", "foam": "Plastic", "lid": "Plastic", "wrapper": "Plastic",
    "tray": "Plastic", "cup": "Plastic", "dish": "Plastic", "bucket": "Plastic",
    "hose": "Plastic", "crate": "Plastic",
}

def encode_image(image_path, max_size=(512, 512)):
    try:
        image = Image.open(image_path).convert("RGB")
        image.thumbnail(max_size)
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[Moondream] Image processing error: {str(e)}")
        return None

def analyze_image(image_path):
    if not API_KEY:
        print("[Moondream] API key not found.")
        return None

    image_b64 = encode_image(image_path)
    if not image_b64:
        return None

    headers = {
        "Authorization": f"Bearer {API_KEY}",
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
                        "text": PROMPT_TEXT
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post("https://api.moondream.ai/v1/chat/completions", headers=headers, json=payload)
        if response.status_code != 200:
            print(f"[Moondream] API Error: {response.status_code} - {response.text}")
            return None

        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Moondream] Request error: {str(e)}")
        return None

def classify_items(caption_text):
    caption_text = caption_text.lower()
    waste_count = defaultdict(int)

    category_lines = re.findall(r'(paper|glass|metal|plastic):\s*(.*)', caption_text)

    for category, items_text in category_lines:
        if "none" in items_text:
            continue

        items = [item.strip() for item in items_text.split(",")]

        for item in items:
            match = get_close_matches(item, [key.lower() for key in categories.keys()], n=1, cutoff=0.3)
            if match:
                matched_key = [key for key in categories if key.lower() == match[0]][0]
                matched_category = categories[matched_key]
                waste_count[matched_category] += 1
            else:
                found = False
                for key in categories:
                    if key.lower() in item:
                        matched_category = categories[key]
                        waste_count[matched_category] += 1
                        found = True
                        break
                if not found:
                    print(f"[Moondream] Unmatched label: {item}")

    return waste_count

def detect_and_classify(image_path):
    try:
        caption = analyze_image(image_path)
        print(f"--- API CAPTION: {caption} ---")

        if not caption:
            return {"error": "Moondream analysis failed."}

        category_counts = classify_items(caption)

        return {
            "caption": caption,
            "paper": category_counts.get("Paper", 0),
            "plastic": category_counts.get("Plastic", 0),
            "metal": category_counts.get("Metal", 0),
            "glass": category_counts.get("Glass", 0)
        }
    except Exception as e:
        print(f"[Moondream] Error during detection: {str(e)}")
        return {"error": str(e)}

def process_folder_parallel(folder_path, max_workers=100):
    start_time = time.time()

    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    total_images = len(image_files)
    print(f"\nFound {total_images} images.\n")

    all_results = {}
    total_counts = {"paper": 0, "plastic": 0, "metal": 0, "glass": 0}

    def worker(image_file):
        image_path = os.path.join(folder_path, image_file)
        print(f"Processing {image_file}...")
        result = detect_and_classify(image_path)
        return (image_file, result)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, image_file): image_file for image_file in image_files}

        for idx, future in enumerate(as_completed(futures), 1):
            image_file = futures[future]
            try:
                image_file, result_dict = future.result()
                all_results[image_file] = result_dict

                for category in total_counts:
                    total_counts[category] += result_dict.get(category, 0)
            except Exception as e:
                print(f"Error processing {image_file}: {str(e)}")

    with open(os.path.join(folder_path, "waste_results_parallel.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)

    with open(os.path.join(folder_path, "waste_results_total_parallel.json"), "w", encoding="utf-8") as f:
        json.dump(total_counts, f, indent=4, ensure_ascii=False)

    end_time = time.time()
    print(f"\nCompleted in {end_time - start_time:.2f} seconds.")

# Main
if __name__ == "__main__":
    folder_path = r"D:\images-inegol"
    process_folder_parallel(folder_path, max_workers=100)
