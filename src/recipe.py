import sqlite3
from datetime import datetime
import time
import random
from dbConfig import mysql_pool


def recommendRecipeWithPreferences(username, wanted, unwanted):
    recommended_recipes = getRecommendedRecipes(username)
    wanted = [w.strip().lower() for w in wanted.strip().split(",") if w.strip()]  # preferred ingredients
    unwanted = [u.strip().lower() for u in unwanted.strip().split(",") if u.strip()]  # unwanted ingredients

    con = mysql_pool.get_connection()
    cr = con.cursor(dictionary=True)

    # Fetch all (recipe_id, ingredient) pairs
    cr.execute("SELECT recipe_id, LOWER(ingredient_name) as ingredient FROM ingredients LIMIT 5000")
    rows = cr.fetchall()

    # Build a map: recipe_id -> list of ingredients
    recipe_map = {}
    for row in rows:
        rid = row['recipe_id']
        ing = row['ingredient']
        if rid not in recipe_map:
            recipe_map[rid] = []
        recipe_map[rid].append(ing)

    result = []
    for recipe_id, ingredients in recipe_map.items():
        # Skip already recommended recipes
        if recipe_id in recommended_recipes:
            continue

        # Skip if unwanted ingredients are present
        if unwanted and any(u in ingredients for u in unwanted):
            continue

        # Skip if none of the wanted ingredients are present
        if wanted and not any(w in ingredients for w in wanted):
            continue

        match_score = countMatches(ingredients, wanted)
        result.append([recipe_id, match_score])

    cr.close()
    con.close()

    if not result:
        return None

    # Choose one of the top 20 recipe matches
    result.sort(key=lambda x: x[1], reverse=True)
    top_results = result[:20] if len(result) >= 20 else result
    recommended_recipe = random.choice(top_results)[0]
    appendRecommendedRecipe(recommended_recipe)
    return recommended_recipe


def countMatches(ingredient_string, wanted):
    ingredient_lower = [ing.lower() for ing in ingredient_string]
    return sum(ing.lower() in ingredient_lower for ing in wanted)

#fetches the recipes that have already been recommended that have already been recommended
def getRecommendedRecipes(user_id):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("SELECT recipe FROM RecipeRecommendations where userID = ?", (user_id,))
    recommended_recipes = [row[0] for row in cr.fetchall()]
    cr.close()
    con.close()
    return recommended_recipes
#adds a recommended recipe to the recipes that have already been recommended
def appendRecommendedRecipe(recommended_recipe):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("INSERT INTO RecipeRecommendations VALUES (?, ?)", ("alw", recommended_recipe))
    con.commit()
    cr.close()
    con.close()
    
#gets a recipe name and searches for the recipe that matches it
def filterByRecipeName(recipe_name):
    recipe_name = recipe_name.strip().lower().replace(" ", "-")
    con = mysql_pool.get_connection()
    cr = con.cursor()
    cr.execute("""
        SELECT DISTINCT recipe_id
        FROM recipe_profiles 
        WHERE recipe_id LIKE %s
    """, (f'%{recipe_name}%',))
    result = cr.fetchall()
    if result is None:
        cr.close()
        con.close()
        return []
    matched_href = result[0][0]
    cr.close()
    con.close()
    return matched_href
#given a recipe name it extracts its ingredients
def extractRecipeIngredients(matched_href):
    con = mysql_pool.get_connection()
    cr = con.cursor()
    cr.execute("""
        SELECT ingredient_name FROM ingredients WHERE recipe_id = %s
    """, (matched_href,))

    ings = [row[0] for row in cr.fetchall()]
    cr.close()
    con.close()
    return ings

# given a recipe href from the table recipe_profiles, searches for a recipe with the highest number of matches from the table recipe_profiles_analysis
def matchAnalysisRecipeId(recipe_href):
    parts = recipe_href.split('/')
    if not parts:
        return None

    recipe_part = parts[-2]
    keyword = recipe_part.lower().replace("--", "-").strip()

    con = mysql_pool.get_connection()
    cr = con.cursor()

    cr.execute("""
        SELECT recipe_id
        FROM recipe_profiles_analysis
        WHERE LOWER(recipe_id) LIKE %s
        LIMIT 1
    """, (f'%{keyword}%',))

    result = cr.fetchone()
    cr.close()
    con.close()

    if result:
        return result[0]
    return recipe_href

# given a recipe href it returns the recipe nutrients
def getRecipeNutrients(matched_href):
    # search for a match for the href in recipe_profiles_analysis
    recipe_href = matchAnalysisRecipeId(matched_href)
    con = mysql_pool.get_connection()
    cr = con.cursor()
    #fetch nutrients
    cr.execute("""
        SELECT kcal, protein, carbohydrates, fat FROM recipe_profiles_analysis WHERE recipe_id = %s
    """, (recipe_href,))
    vals = cr.fetchone()
    cr.close()
    con.close()
    return vals
# given a recipe href it extracts the cooking instructions
def extractCookingInstructions(matched_href):
    con = mysql_pool.get_connection()
    cr = con.cursor()
    cr.execute("""
        SELECT recipe_directions FROM recipe_profiles WHERE recipe_id = %s
    """, (matched_href,))

    instructions = [row[0] for row in cr.fetchall()]
    cr.close()
    con.close()
    return instructions

# returns the botmessage conatining a recipe with its nutrients when the user says he ate a recipe
def returnFoundRecipe(activity_data, recipe_name, user_stats):
    matched_href = filterByRecipeName(recipe_name)
    #default message if no match is found in recipe_profiles_analysis
    bot_message = f"you must estimate the macros for this recipe: {recipe_name}"
    if matched_href:
        nutrients = getRecipeNutrients(matched_href)
        if nutrients:           
            activity_data.update({"calories": nutrients[0], "protein": nutrients[1], "fat": nutrients[2], "carbs": nutrients[3]})
            exceeding_nutritional_values = [key for key in ["calories", "protein", "fat", "carbs"] if activity_data[key] > user_stats[key]]
            #warn the user if it exceeds his daily consumption goals
            if exceeding_nutritional_values:
                bot_message = f"warning! this recipe {recipe_name} exceeds your limits for {', '.join(exceeding_nutritional_values)}.\n It contains:\n- {nutrients[0]} kcal\n- {nutrients[1]}g protein\n- {nutrients[2]}g fat\n- {nutrients[3]}g carbs"
            else:
                bot_message = f"I recommend trying **{recipe_name}**. It contains:\n- {nutrients[0]} kcal\n- {nutrients[1]}g protein\n- {nutrients[2]}g fat\n- {nutrients[3]}g carbs"  
    return bot_message

# returns the botmessage conatining a recipe with its nutrients when the user asks for a recipe recommendation
def returnRecommendedRecipe(username, activity_data, wanted, unwanted, user_stats):

    bad_recipe = True
    # recommend nothing if the user has already achieved his goals
    if all(val==0 for val in user_stats.values()):
        return {"message": "You have already met your nutritional goals for today", "activity_data": {"task": ""}}
    # return a recipe the does not exceed the daily limit
    while bad_recipe:
        matched_href = recommendRecipeWithPreferences(username, wanted, unwanted)
        # if no match found for the given preferences
        if not matched_href:
            return {"message": "Sorry, no matching recipe found.", "activity_data": {"task": ""}}
        recipe_name = matched_href.split("/")[-2].replace("-", " ")
        nutrients = getRecipeNutrients(matched_href)
        if nutrients:
            activity_data.update({"calories": nutrients[0], "protein": nutrients[1], "fat": nutrients[2], "carbs": nutrients[3]})
            for key in ["calories", "protein", "fat", "carbs"]:
                if activity_data[key] > user_stats[key]:
                    continue
            activity_data["recipe"] = recipe_name
            bot_message = f"I recommend trying **{recipe_name}**. It contains:\n- {nutrients[0]} kcal\n- {nutrients[1]}g protein\n- {nutrients[2]}g fat\n- {nutrients[3]}g carbs"
            bad_recipe = False
        else:
            bot_message = f"I recommend trying **{recipe_name}**" #if no match is found for the nutrients in recipe_profiles_analysis, it will let the llm estimate the values
            bad_recipe = False
    return bot_message

# given a task: instruction, ingredients, eating it returns the correct botmessage accordingly
def getBotReplyWithData(task, wanted_ingredients, unwanted_ingredients, username, user_info, recipe_name = None):

    activity_data = {
        "task": task,
        "recipe": recipe_name,
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0
    }

    bot_message = ""
    if task == "eating":
        user_stats = {
            "calories": user_info[7],
            "protein": user_info[8],
            "carbs": user_info[9], 
            "fat": user_info[10]
            }
        if recipe_name != "" and recipe_name != None: #if the user says he ate a recipe
            bot_message = returnFoundRecipe(activity_data, recipe_name, user_stats)
        else: # if the user asks for a recipe recommendation, s.t. no recipe name is given
            wanted = wanted_ingredients 
            unwanted = user_info[-1] + unwanted_ingredients
            bot_message = returnRecommendedRecipe(username, activity_data, wanted, unwanted, user_stats)

    elif task == "ingredients":
        matched_href = filterByRecipeName(recipe_name)
        if matched_href:
            ingredient_text = extractRecipeIngredients(matched_href)
            bot_message = f"Here are the ingredients for **{recipe_name}**:\n- {ingredient_text}"
        else:
            bot_message = f"Couldn't find ingredients for **{recipe_name}**."
            activity_data["task"] = ""

    elif task == "instructions":
        matched_href = filterByRecipeName(recipe_name)
        if matched_href:
            instructions = extractCookingInstructions(matched_href)
            bot_message = f"Here are the cooking instructions for **{recipe_name}**:\n\n{instructions[0]}"
        else:
            bot_message = f"Couldn't find instructions for **{recipe_name}**."
            activity_data["task"] = ""
    else:
        bot_message = "Got it. Let me know what you'd like to do."
    return {"message": bot_message}