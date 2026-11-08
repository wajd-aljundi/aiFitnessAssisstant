import requests
import json
import re
from dotenv import load_dotenv
import os
from llm import getExtractedFoodArray

load_dotenv()
API_KEY = os.getenv("API_KEY")

### requests to OpenFoodFacts API for "processed supermarket-food"
def getNutrientsOff(food_array):
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    results = []

    for food_item in food_array:
        product_name = food_item['food']
        product_amount = food_item['amount']

        params = {
            'search_terms': product_name,
            'search_simple': 1,
            'action': 'process',
            'json': 1
        }

        response = requests.get(url, params=params)
        data = response.json()

        products = data.get('products', [])
        if not products:
            results.append({
                "food": product_name,
                "error": "No products found."
            })
            continue

        product = products[0]
        nutrients = product.get('nutriments', {})

        def getValue(nutrient_key):
            value_per_100g = nutrients.get(nutrient_key)
            if value_per_100g is not None:
                return round(value_per_100g * (product_amount / 100), 2)
            else:
                return None

        result = {
            "food": product_name,
            "product_name": product.get('product_name', 'Unbekannt'),
            "barcode": product.get('code'),
            "amount_in_grams": product_amount,
            "nutriments": {
                "energy_kcal": getValue('energy-kcal_100g'),
                "fat_g": getValue('fat_100g'),
                "sugars_g": getValue('sugars_100g'),
                "proteins_g": getValue('proteins_100g'),
                "salt_g": getValue('salt_100g')
            }
        }

        results.append(result)

    return results

## function to restructure the output of the OpenFoodFacts API request
def extractMakrosOff(nutrient_array):
    total_calories = 0
    total_proteins = 0
    total_fats = 0
    total_carbs = 0

    if nutrient_array:
        for item in nutrient_array:
            nutriments = item['nutriments']
            total_calories += nutriments.get('energy_kcal', 0)
            total_proteins += nutriments.get('proteins_g', 0)
            total_fats += nutriments.get('fat_g', 0)
            total_carbs += nutriments.get('sugars_g', 0)
    return {
        'calories': total_calories,
        'protein': total_proteins,
        'fat': total_fats,
        'carbs': total_carbs
    }


### requests to USDA database API for natural food
def getNutrientsUsda(natural_food_array):
    if not natural_food_array:
        return {
            'calories': 0,
            'protein': 0,
            'fats': 0,
            'carbs': 0
        }

    search_url = 'https://api.nal.usda.gov/fdc/v1/foods/search'
    nutrients_structure = {
        'Protein': 'protein',
        'Carbohydrate, by difference': 'carbs',
        'Total lipid (fat)': 'fats'
    }

    total_nutrients = {
        'calories': 0.0,
        'protein': 0.0,
        'fats': 0.0,
        'carbs': 0.0
    }

    for item in natural_food_array:
        query = item['raw-food']
        amount_in_grams = item['amount']

        # 1. Search the food
        search_params = {
            'query': query,
            'dataType': 'Foundation',
            'pageSize': 1,
            'api_key': API_KEY
        }
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()
        search_results = search_response.json()

        foods = search_results.get('foods')
        if not foods:
            continue

        fdcID = foods[0]['fdcId']

        # 2. Get nutrient details
        fdcID_url = f'https://api.nal.usda.gov/fdc/v1/food/{fdcID}'
        fdcID_response = requests.get(fdcID_url, params={'api_key': API_KEY})
        fdcID_response.raise_for_status()
        detail = fdcID_response.json()

        # 3. Extract and accumulate nutrients per food
        nutrients = {
            'calories': None,
            'protein': None,
            'fats': None,
            'carbs': None
        }

        for nutrient_item in detail.get('foodNutrients', []):
            nutrient_name = nutrient_item.get('nutrient', {}).get('name')
            nutrient_value = nutrient_item.get('amount')
            nutrient_unit = nutrient_item.get('nutrient', {}).get('unitName')

            if nutrient_name:
                if 'Energy' in nutrient_name and nutrient_unit == 'kcal':
                    if nutrients['calories'] is None or nutrient_name == 'Energy (Atwater Specific Factors)':
                        nutrients['calories'] = nutrient_value

                elif nutrient_name in nutrients_structure:
                    nutrients[nutrients_structure[nutrient_name]] = nutrient_value

        # 4. Scale by amount in grams (nutrients are per 100g)
        for key in total_nutrients:
            value_per_100g = nutrients[key]
            if value_per_100g is not None:
                total_nutrients[key] += (value_per_100g * amount_in_grams / 100)

    # 5. Round result to 2 decimal places
    for key in total_nutrients:
        total_nutrients[key] = round(total_nutrients[key], 2)
    return total_nutrients


## function to merge all nutrients from both API outputs
def mergeNutrientDicts(dict1, dict2):
    key_mapping = {
        'fat': 'fats',
        'fats': 'fats',
        'protein': 'protein',
        'carbs': 'carbs',
        'calories': 'calories'
    }

    merged = {
        'calories': 0.0,
        'protein': 0.0,
        'carbs': 0.0,
        'fats': 0.0
    }

    for d in [dict1, dict2]:
        for key, value in d.items():
            normalized_key = key_mapping.get(key)
            if normalized_key and value is not None:
                merged[normalized_key] += value

    for key in merged:
        merged[key] = round(merged[key], 0)

    return merged



def validateFoodString(s):

    parts = s.strip().split("&")
    if len(parts) != 2:
        return False

    def validJsonArray(part):
        part = part.strip()
        if re.search(r",\s*\]", part):
            return False
        try:
            data = json.loads(part)
            if isinstance(data, list):
                return True
        except json.JSONDecodeError:
            return False
        return False

    return validJsonArray(parts[0]) and validJsonArray(parts[1])



def trackFood(user_input):
     # uses functions 'extract_food' and 'get_extracted_food_array' to scan the conversation for food that was eaten. 
    # This is structured in a string made of two arrays chained by '&'. 
    # One for natural and one for processed food, because those are requested by different APIs  
    # It checks if the structure of the returned Arrays is correct, if not it will create them again     
    valid = False
    while not valid:
        tracked_food = getExtractedFoodArray(user_input) # string with food arrays chained by '&'
        valid = validateFoodString(tracked_food)
    
    # separate the string and turn it into working array for API requests
    raw_food_string, processed_food_string = tracked_food.split('&')
    raw_food = json.loads(raw_food_string.strip())
    processed_food = json.loads(processed_food_string.strip())

    # request food from the 'processed_food array' at OpenFoodFacts
    nutrients_processed = getNutrientsOff(processed_food)
    # restructure the output for further processing
    nutrients_off = extractMakrosOff(nutrients_processed) # output array from OpenFoodFacts

    # request food from the 'raw_food array' at USDA database
    nutrients_usda = getNutrientsUsda(raw_food) # output array from USDA

    # merge all collected nutriments in one array
    merged_nutrients = mergeNutrientDicts(nutrients_off, nutrients_usda)
    
    # update the userprofile with the new information
    return merged_nutrients# all nutrients added up
