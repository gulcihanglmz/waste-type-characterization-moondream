# Waste Type Characterization

This project is an application that detects waste items in images and classifies them into predefined waste categories using the **Moondream API**.

## Categories
The application classifies waste into four main categories:

- **Cardboard**: cardboard boxes, pizza boxes, juice and milk cartons, etc.
  
- **Glass**: glass bottles, glass jars, glass beverage bottles, etc.
  
- **Metal**: aluminum cans, beverage cans, metal containers, etc.
  
- **Plastic**: plastic bottles, plastic bags, plastic containers, plastic cups, etc.

Each category contains specific subcategories as defined in the script.

## Setup

1. Clone or download this repository.

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   
## Set your Moondream API key in the .env file:
Open the .env file.
Update the MOONDREAM_API_KEY variable with your own Moondream API key:
```bash
MOONDREAM_API_KEY="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## Features
* Uses powerful image understanding models from the Moondream API.
* Automatically detects waste items in images and categorizes them.
* Classifies waste into categories like plastic, glass, metal, cardboard.
* Processes multiple response formats.
* If no exact matches are found, defaults to category-based keywords.
* Provides detailed counts for each waste category and subcategory.

## Example Output
Here is an example of what the output might look like:
```bash
📦 Waste Type Detection Result:
🔹 Plastic: 93 items
🔹 Cardboard: 10 items
🔹 Glass: 5 items
🔹 Metal: 2 items

AI Response:
 plastic bottle, plastic bottle, plastic bottle, plastic bag, cardboard box, cardboard box, plastic bottle, ...
```
