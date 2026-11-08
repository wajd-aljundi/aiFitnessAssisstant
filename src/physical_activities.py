import sqlite3
from pathlib import Path
from ollama import Client
import re
import ast
from db import updateAfterPhysicalActivity

current_path = Path(__file__)
met_value_db_path = current_path.parent.parent / "metValues.db"
client = Client(host="http://hcai.uni-regensburg.de:11434", timeout=500)

# bodyweight in kg
def calculateCalories(met_value, bodyweight, minutes):
    conn = sqlite3.connect(met_value_db_path)
    cursor = conn.cursor()
    calories_per_minute = (met_value * 3.5 * bodyweight) / 200
    total_calories = round(calories_per_minute * minutes)
    conn.close()
    # logacitivities
    return total_calories

def physicalActivityCategories():
    conn = sqlite3.connect(met_value_db_path)
    cursor = conn.cursor()
    query = "SELECT DISTINCT major_heading FROM met_values"
    cursor.execute(query)
    categories = cursor.fetchall()
    conn.close()
    return [row[0] for row in categories]

def activitiesPerCategory(category):
    conn = sqlite3.connect(met_value_db_path)
    cursor = conn.cursor()
    query = "SELECT activity_code, activity_description FROM met_values WHERE major_heading = ?"
    cursor.execute(query, (category,))
    sports = cursor.fetchall()
    conn.close()
    return sports

def getMetValueFromDb(activity_code):
    conn = sqlite3.connect(met_value_db_path)
    cursor = conn.cursor()
    query = 'SELECT met_value FROM met_values WHERE activity_code = ?'
    cursor.execute(query, (activity_code,))
    met_value = cursor.fetchone()
    conn.close()
    return met_value[0] if met_value else None


def extractDictFromText(text):
    pattern = r'({.*?})'
    matches = re.findall(pattern, text, re.DOTALL)

    for match in matches:
        try:
            result = ast.literal_eval(match)
            if isinstance(result, dict):
                return result
        except (SyntaxError, ValueError):
            continue

    return None  




def getPhysicalCategoryPrompt(): 
    return f"""
            You are given one specific sport or physical activity and you have a list of categories below.

            Your job is to assign the given activity to exactly one of the categories.

            Instructions:
            1. Use only the categories provided.
            2. Choose the most appropriate category based on the main physical focus of the activity.
            3. Return only the name of the category as a string. Do not explain.
            4. If there is no fitting category, return the string: "None"

            categories:
            {physicalActivityCategories()}

            Example 1:
            Input Activity: "basketball"
            Output:"Sports"

            Example 2:
            Input Activity: "hiking"
            Output: "Walking"

            Example 3:
            Input Activity: "fishing"
            Output: "Fishing & Hunting"

            Example 4:
            Input Activity: "swimming"
            Output: "Water Activities"

            Example 5:
            Input Activity: "skiing"
            Output: "Winter Activities"

            Example 6:
            Input Activity: "Cycling"
            Output: "Bicylcling
            """

def getIdOfActivityPrompt(category):
    return f"""
            You are given:

            - One input activity to match.
            - A list of valid physical activities with their id below.

            Your task:
            1. Compare the input activity with the list of valid activities.
            2. Find the best-matching activity from the list.
            3. Return only the exact id from the list.
            4. Do not explain. Just return one id from the list.
            5. Don't make something up, if there is no fitting activity in the list, return the string: "None".


            list of activities:
            {activitiesPerCategory(category)}

            """


def logPhysicalActivity(dictionary, user_info, username):
    prompt2_message_array = [{'role': 'system', 'content': getPhysicalCategoryPrompt()},
                                 {'role': 'user', 'content': dictionary['activity']}]
    prompt2_response = client.chat(model="gemma3:27b", messages=prompt2_message_array)
    activity_category = prompt2_response['message']['content']

    if not ('none' in activity_category.lower()):
        prompt3_message_array = [{'role': 'system', 'content': getIdOfActivityPrompt(activity_category.strip())},
                                    {'role': 'user', 'content': dictionary['activity']}]
        prompt3_response = client.chat(model="gemma3:27b", messages=prompt3_message_array)
        activity_id = prompt3_response['message']['content']

        if not ('none' in activity_id.lower()):
            met_value =  float(getMetValueFromDb(int(activity_id)))
            burned_calories = calculateCalories(met_value, float(user_info[6]), dictionary['duration_minutes'])
            data = {'calories_burnt': burned_calories, 'task': 'physical', 'duration': dictionary['duration_minutes']}
            updateAfterPhysicalActivity(username, data)

            return burned_calories
        
    return None    