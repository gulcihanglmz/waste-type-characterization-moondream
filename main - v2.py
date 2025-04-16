from collections import defaultdict
import re
import requests
import base64
from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()

# Category definitions
categories = {
    # Paper/Cardboard category
    "cardboard": "Paper",
    "paper": "Paper",
    "carton": "Paper",
    "box": "Paper",
    "tetra pak": "Paper",
    "milk carton": "Paper",
    "juice carton": "Paper",
    "food packaging": "Paper",
    "magazine": "Paper",
    "book": "Paper",
    "newspaper": "Paper",
    "paper cup": "Paper",
    "paper bag": "Paper",
    "paper wrapper": "Paper",
    "paper tray": "Paper",
    "paper container": "Paper",

    # Glass category
    "glass": "Glass",
    "bottle": "Glass",
    "jar": "Glass",
    "container": "Glass",
    "window": "Glass",
    "mirror": "Glass",
    "vase": "Glass",

    # Metal category
    "metal": "Metal",
    "aluminum": "Metal",
    "tin": "Metal",
    "can": "Metal",
    "steel": "Metal",
    "foil": "Metal",

    # Plastic category
    "plastic": "Plastic",
    "pet": "Plastic",
    "bottle": "Plastic",
    "container": "Plastic",
    "bag": "Plastic",
    "foam": "Plastic",
    "lid": "Plastic",
    "wrapper": "Plastic",
    "tray": "Plastic",
    "cup": "Plastic",
    "dish": "Plastic",
    "bucket": "Plastic",
    "hose": "Plastic",
    "crate": "Plastic",
}

# Resize image and convert to base64
def encode_image(image_path, max_size=(800, 800)):
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        image = Image.open(image_path).convert("RGB")
        image.thumbnail(max_size)
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=95)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Image processing error: {str(e)}")
        return None

# Analyze with Moondream API
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

    # Use a single effective prompt
    prompt = """
            You are a waste classification assistant.
            Categories:
            - Paper
            - Glass
            - Metal
            - Plastic
            Instructions:
            - Look at the image and list visible, clearly identifiable waste items under each category.
            - If no items for a category, write "None".
            - Use this exact format:
            paper: item1, item2
            glass: item1, item2
            metal: item1, item2
            plastic: item1, item2
            Do not include explanations.
            """

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
                        "text": prompt
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
            print("ERROR: 403 - API access denied. Please check your Moondream API key.")
            return None
        elif response.status_code != 200:
            print(f"ERROR: {response.status_code} - {response.text}")
            return None

        result = response.json()
        message_content = result["choices"][0]["message"]["content"]

        return message_content
    except requests.exceptions.RequestException as e:
        print(f"API request error: {str(e)}")
        return None
    except ValueError as e:
        print(f"JSON parsing error: {str(e)}")
        return None

def classify_waste_items(response_text):
    response_text = response_text.lower()
    waste_count = defaultdict(int)

    # Find category headers
    categories_found = []
    for category in ["paper/cardboard", "glass", "metal", "plastic"]:
        if category in response_text:
            categories_found.append(category)

    # Find items for each category
    for category in categories_found:
        # Find the category section
        try:
            category_section = response_text.split(category)[1].split("\n\n")[0]

            # Find items and quantities
            items = re.findall(r'[-•]\s*(\d+)\s*([^,\n]+)', category_section)

            for quantity, item in items:
                quantity = int(quantity)
                item = item.strip().lower()

                # Category matching
                matched_category = None
                for keyword, cat in categories.items():
                    if keyword in item:
                        matched_category = cat
                        break

                if matched_category:
                    waste_count[matched_category] += quantity
                    print(f"Found: {quantity}x {item} → {matched_category}")
                else:
                    print(f"Skipped: {item} (no category)")
        except Exception as e:
            print(f"Category processing error ({category}): {str(e)}")
            continue

    # If no categories found, search directly in the text
    if not categories_found:
        print("No category headers found, searching directly in text...")

        # Find all numbers and words next to them
        items = re.findall(r'(\d+)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)', response_text)

        for quantity, item in items:
            quantity = int(quantity)
            item = item.strip().lower()

            # Category matching
            matched_category = None
            for keyword, cat in categories.items():
                if keyword in item:
                    matched_category = cat
                    break

            if matched_category:
                waste_count[matched_category] += quantity
                print(f"Found (direct): {quantity}x {item} → {matched_category}")
            else:
                print(f"Skipped (direct): {item} (no category)")

    # JSON output
    return json.dumps({
        "paper": waste_count.get("Paper", 0),
        "plastic": waste_count.get("Plastic", 0),
        "metal": waste_count.get("Metal", 0),
        "glass": waste_count.get("Glass", 0)
    }, indent=4)

def process_image(image_path):
    print(f"Analyzing image: {image_path}")
    result_text = analyze_image_with_moondream(image_path)
    if result_text:
        print("\nAPI Response:")
        print(result_text)
        json_output = classify_waste_items(result_text)
        print("\nJSON Output:")
        print(json_output)
        return json_output
    else:
        return None

def process_folder(folder_path):
    start_time = time.time()

    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    total_images = len(image_files)
    print(f"\nFound {total_images} images.\n")

    all_results = {}
    total_counts = {
        "paper": 0,
        "plastic": 0,
        "metal": 0,
        "glass": 0
    }

    for idx, image_file in enumerate(image_files, 1):
        image_path = os.path.join(folder_path, image_file)
        print(f"\n[{idx}/{total_images}] Processing {image_file}...")

        result_json_str = process_image(image_path)
        if result_json_str:
            result_dict = json.loads(result_json_str)
            all_results[image_file] = result_dict

            # Add to totals
            for category in total_counts:
                total_counts[category] += result_dict.get(category, 0)

    # Save results
    output_file = os.path.join(folder_path, "waste_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)

    # Save total result
    total_output_file = os.path.join(folder_path, "waste_results_total.json")
    with open(total_output_file, "w", encoding="utf-8") as f:
        json.dump(total_counts, f, indent=4, ensure_ascii=False)

    end_time = time.time()
    total_seconds = end_time - start_time
    total_minutes = total_seconds / 60

    print(f"\nAll processing completed.")
    print(f"Total time: {total_seconds:.2f} seconds ({total_minutes:.2f} minutes)")
    print(f"Results saved to: {output_file}")
    print(f"Total results saved to: {total_output_file}")


if __name__ == "__main__":
    folder_path = r"D:\inegol_images"
    process_folder(folder_path)

