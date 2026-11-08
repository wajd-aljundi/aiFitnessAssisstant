from ollama import Client
from recipe import *
import json
import re

client = Client(host="http://132.199.136.239:11434", timeout=500)


recipe_prompt = """
                You are Telefood, a friendly food assistant.

                If this is the first interaction and the user starts with a greeting like "Hey Telefood":
                - Greet back starting with: "Howdy Mate!"
                - Ask how you can assist today.

                Do NOT generate recipes, ingredients, instructions, or macro info yourself.
                Only follow up with questions to clarify the user's intent (like dietary preferences or ingredients) — structured information must be handled as specified above.
               """




other_prompt = """You are a helpful and focused assistant specialized in calorie and nutrition tracking, 
                healthy recipe suggestions, and physical activity planning. Your purpose is to 
                support the user in maintaining a healthy lifestyle through nutrition and exercise guidance. 
                If the user starts to discuss unrelated topics, gently but clearly steer the conversation back 
                to calorie tracking, recipes, or physical activity. Politely remind them of your role and encourage 
                them to ask questions or share updates related to their health goals.
                If the user goes off-topic, respond like this:
                'That sounds interesting, but just a quick reminder—I’m here to help you with calorie tracking, 
                recipe ideas, and planning physical activities. Would you like to log a meal, get a healthy recipe, 
                or plan your next workout?'
                Your only task is to lead the conversation back to the named topics, no exceptions!"""
    



calorie_tracking_prompt =  """You just got the nutrients fetched from the database. 
                            Your Job is to only return the following as it is without any Explanation or Regard to previous messages: 
                             
                              "We updated your profile:
                                - Calories: {cals}
                                - Protein: {protein}
                                - Carbs: {carbs}
                                - Fat: {fat}" """


def getPrompt(prompt_class: str) -> str:
    
    if "conversation" in prompt_class.lower() or "start" in prompt_class.lower():
        return recipe_prompt# needs to be changed to startPrompt in future
    elif "physical" in prompt_class.lower() or "acitivity" in prompt_class.lower():
        return physical_prompt1
    elif "recipe" in prompt_class.lower() or "request" in prompt_class.lower():
        return recipe_prompt
    elif "calorie" in prompt_class.lower() or "tracking" in prompt_class.lower():
        return calorie_tracking_prompt
    elif "other" in prompt_class.lower():
        return other_prompt


def activitiyPrompt(message_array, username, user_info=None):
    # get the last recipe that has been recommended
    recommended_recipes = getRecommendedRecipes(f"{username}")
    last_recipe = recommended_recipes[-1] if recommended_recipes else None
    last_recipe_prompt = f"This is the last recipe recommended to the user: {last_recipe}"
    # depending on the user message, the llm classifies it into different categories
    dietary_info = f"""
        Your job for this message is to understand the user's intent and only return structured data as instructed.
        Do not recommend a recipe or genrate anything not related to the structure below at any time.
        No quotes. No conversation.
        Only use the format specified above. Do NOT make up nutrients or recipes. Return a JSON object as specified above including the spcified information above
        Your response should be **ONLY** a single JSON object using one of the following structures, depending on the user request:

        1. If the intent is unclear or no task should be performed or the user is just greeting:
            - Return:
                {{"task": ""}}

        2. If the user wants to EAT something but doesn't say a specific food/recipe name (for example says: give me a recipe, or: recommend a recipe for me):
                {{"task": "eating", "recipe": "", "wanted_ingredients": wanted ingredients if given by the user else "", "unwanted_ingredients": unwanted ingredients if given by the user else ""}}
            

        3. If the user wants to EAT a recipe and mentions the specific recipe name:
            - Return:
                {{"task": "eating", "recipe": "recipe name"}}
            
        4. If the user asks for the ingredients of a specific recipe (for example says: i want to see the ingredient list, or: show me the ingredients):
            - Return:
                {{"task": "ingredients", "recipe": "recipe name"}}

        5. If the user asks for instructions for a specific recipe (for example says: give me the cooking instructions, or: show me the cooking instructions):
            - Return: 
                {{"task": "instructions", "recipe": "recipe name"}}
    """
    if last_recipe:
        dietary_info = last_recipe_prompt + dietary_info
    prompt_entry = {"role": "system", "content": dietary_info}
    msg = []
    for i in reversed(message_array): #only pass the last user message to the llm
        if i["role"] == "user":
                msg.append(i)
                break
    if msg:
        messages = [prompt_entry] + msg
    else: 
        messages = [prompt_entry] + message_array
    response = client.chat(model='gemma3:27b', messages= messages)
    content = json.loads(re.search(r'(\{.*\})', response["message"]["content"], re.DOTALL).group(1))
    # get the bot message containing data from the db
    task = content["task"]
    bot_reply=None
    recipe_name = ""
    wanted = ""
    unwanted = ""
    if "recipe" in content.keys():
        if content["recipe"] != "":
            recipe_name = content["recipe"]
    if "wanted_ingredients" in content.keys():
        wanted = content["wanted_ingredients"]
    if "unwanted_ingredients" in content.keys():
        unwanted = content["unwanted_ingredients"]
    bot_reply = getBotReplyWithData(task, wanted, unwanted, username, user_info, recipe_name)
    return bot_reply

# builds the main prompt for the llm 
def promptBuilder(current_prompt, bot_message, user_info):
    user_info_prompt =f"""
    this is a message containing Information that you should return to the user
    The Only important vlaues for your next reply are in this message.
    Only if macros are not given or the message tells to estimate the macros, then estimate them:
    {bot_message}
    """
    prompt = """
    You must strictly follow every line and rule below:

    Estimate the Macros ONLY if they are not provided in the message, that is, the message only has the recipe name of the message tells you to estimate them.
    1. If the message includes any of: calories, protein, carbohydrates, fat, return the following sentence and the Macros as follows:
        I recommend you try **recipe name from the message** with the macros:
        calories = value from the message
        protein = value from the message
        carbs = value from the message
        fat = value from the message 

    2. If the task equals eating, then return:
        Here are the macros of what you have eaten:
        task = eating
        recipe = (recipe name from the message)
        calories = (value from the message)
        protein = (value from the message)
        carbs = (value from the message)
        fat = (value from the message)
        
    3. If the macros are not given in the message or the message tells you to estimate the macros, say:
      "these are the macros for the recipe **recipe name from the message**: " and estimate the macros then return them in the same format in 2.

    4. If the message contains a list of ingredients, extract and reformat them as:
       Here are the ingredients for <recipe name>:
       ingredients = (one per line, formatted as bullet points)

    5. If the message includes cooking instructions, return the following sentence and the instructions as follows:
        Here are the instructions for **recipe name from the message**:
        instructions = cooking instructions from the message (reformat them as steps)

    Always include the recipe in the message if a recipe is given, even if it does not match with user preferences
    If the information needed is already in the message, then do not estimate anything and only include the information from the message
    Only include values explicitly present in the message. Do not guess or generate anything.
    """

    #if the botmessage is empty, s.t. the message was not about a recipe
    final_prompt = current_prompt
    if bot_message == "" or bot_message == None:
        if current_prompt == calorie_tracking_prompt and user_info:
            #set values in the prompt
            final_prompt = current_prompt.format(cals = user_info[7], protein = user_info[8], carbs = user_info[9], fat = user_info[10])
        return final_prompt
    else:
        return user_info_prompt + "\n" + prompt


def askLlm(message_array, current_prompt, bot_message = "", user_info=None):
           

    full_prompt = promptBuilder(current_prompt, bot_message, user_info)
    prompt_entry = {"role": "system", "content": full_prompt}
    shortend_message_array = message_array[-3:]
    shortend_message_array.insert(0, prompt_entry)
    response = client.chat(model='gemma3:27b', messages=shortend_message_array)
    
    return response['message']['content']



classifier_model_prompt = f"""You are a conversation monitor for a conversation between a user and a LLM.
                            Your task is to ONLY categorize the user message in an ongoing chat between a user and an assistant.
                            You will receive an user message.
                            If the message is 'hey telefood' or some sort of greeting respond with 'conversation start'.
                            Strictly follow the following rules:
                            FIRST: Your job is to only categorize! Do not return anything else.
                            SECOND: Take the context into account when classifying
                            THIRD: Never recommend a recipe or food by yourself
                            FOURTH: There are only five possible categories:
                            1. 'Recipe Request' (when the user says he Wants to eat something, he is hungry or asks for a recommendation)
                            2. 'Physical activity' (for example sports, fitness, only activities with the goal to burn calories)
                            3. 'Recipe calorie tracking' (the user told you he ate, already eaten a certain recipe or dish)
                            4. 'Calorie tracking' (the user told you that he ate, already eaten something that is not considered recipe)
                            5. 'Other'

                            FIFTH: Only respond with one of the category names above in this format: <name of category> . No exceptions, only the name of the category"""




def classifyConvo(message_array) -> str:
    message_array1 = message_array.copy()[-5:]
    message_array1.insert(0, {"role": "system", "content": classifier_model_prompt})
    response = client.chat(model='gemma3:27b', messages=message_array1)
    return response['message']['content']



# For food extraction to get the array of food
extractor_prompt = """
You are a food item extractor. Your task is to analyze a user's message and extract all mentioned food items along with their estimated or calculated amounts in GRAMS.

Follow these rules VERY CAREFULLY:

1. Identify all food items — both **natural foods** (e.g. fruits, vegetables) and **processed foods** (e.g. snacks, dairy products, supermarket items).
2. For every item, output the amount in **grams**.
3. If the quantity is mentioned (e.g. "2 bananas"), calculate the **total weight**. Example: 2 bananas = 2 × 120g = 240g.
4. If no amount is given, **estimate** a realistic average amount based on common knowledge. NEVER leave the amount blank.
5. NEVER list the same item more than once.
6. Return your answer in the **exact format** below — no extra comments or explanations.

Output Format:
Natural food:
- [item name]: [amount]g
Other food:
- [item name]: [amount]g

Definitions:
- **Natural food**: Raw, unprocessed items like fruits and vegetables.
  Examples: apple, banana, tomato, cucumber, cherry, spinach
Raw, unprocessed, single-ingredient plant-based items — typically fresh and not altered by cooking or packaging. These are foods you could pick, harvest, or eat without processing.

This includes:
- Fresh fruits: apple, banana, cherry, peach, grape, orange
- Fresh vegetables: tomato, cucumber, carrot, spinach, lettuce
- Raw herbs: parsley, basil, mint
- Berries: strawberry, blueberry, raspberry

Does NOT include:
- Cooked or baked foods: apple pie, grilled vegetables, dried fruit
- Packaged or cut versions: frozen spinach, pre-cut salad bags
- Dairy, meat, grains, or mixed items: cheese, bread, yogurt, nuts, cereal

**Other food**: Processed or composite items typically found in supermarkets.
  Examples: bread roll, cheese, yogurt, chocolate bar, pizza, Snickers
  Natural food:
EXAMPLES:

Example 1:
Input: I ate two bananas and an apple, then had a Snickers bar.
Output:
Natural food:
- banana: 240g
- apple: 150g
Other food:
- Snickers: 50g

Example 2:
Input: For breakfast, I had a bread roll with cheese, and later a salad with tomato and cucumber.
Output:
Natural food:
- tomato: 200g
- cucumber: 300g
Other food:
- bread roll: 70g
- cheese: 30g

Example 3:
Input: I had a slice of apple pie and three cherries.
Output:
Natural food:
- cherry: 30g
Other food:
- apple pie: 150g

Now your task: Analyze the following input and return ALL identified foods and their amounts in the format above.

"""

extraction_structure_prompt = """
You must convert the extracted food list into two strict JSON-style arrays.

Rules:
- NEVER return anything except the arrays in the format shown below.
- DO NOT add explanations, titles, or comments — only return the two arrays.
- The arrays must be separated by a single ampersand character: &
- The first array is for raw, natural food (e.g. fruits, vegetables) — key: "raw-food"
- The second array is for all other (processed) food — key: "food"
- If one array is empty, return it as an empty array: []
- DO NOT return "null", "none", or similar placeholders — only use []
- Each item must appear only once — no duplicates
- Each object must contain:
  - the correct key: "raw-food" or "food"
  - an integer value for "amount" (in grams), no quotes, no units

Examples:

Case with both natural and processed foods:
[
  {"raw-food": "apple", "amount": 150},
  {"raw-food": "banana", "amount": 240}
]
&
[
  {"food": "Snickers", "amount": 50}
]

Case with only processed foods:
[]
&
[
  {"food": "bread roll", "amount": 70}
]

Case with only natural foods:
[
  {"raw-food": "tomato", "amount": 100}
]
&
[]

Invalid outputs to avoid:
- Do not include "type", "category", or any other key
- Do not include "g", "grams", or any string in the amount field
- Do not modify key names ("raw", "natural", etc. are invalid — only use "raw-food")
- Do not surround arrays with explanation text

Now convert the extracted list into exactly this structure.
"""

# this function uses the prompt above to collect all given food from the conversation
# with name and amount, so that the nutrients can be requested by the API
def extractFood(user_message: str):
    food_extraction_array = [
        {"role": "system", "content": extractor_prompt},
        {"role": "user", "content": user_message}
    ]
    response = client.chat(model='gemma3:27b', messages=food_extraction_array)
    return response['message']['content']


def getExtractedFoodArray(user_message: str):
    content = extractFood(user_message)
    food_extraction_array = [
        {"role": "system", "content": extraction_structure_prompt},
        {"role": "user", "content": content}
    ]
    response = client.chat(model='gemma3:27b', messages=food_extraction_array)
    return response['message']['content']



physical_prompt1 = """
You are talking to a user. The user will say something like what physical activity they did today.

Your task is:
1. Wait for the user to say what physcial activity they did (e.g., "basketball", "running", "cooking").
2. Also wait until you know how many minutes they did the activity.
3. If the user message does not clearly contain the activity name, ask them what activity they did.
4. If the activity is clear, but the duration is missing, ask for how many minutes the user did this activity.
5. Do not guess. Only ask about the missing part.
6. As soon as you have both the activity and the number of minutes, return this Python dictionary and nothing else:

{
    "activity": "<activity name>",
    "duration_minutes": <number of minutes as integer>
}

Be strict: Only return the dictionary once you are 100 percent sure you have both values.
If you already returned a pyhton dictionary and the user comes up with another activity he did, 
repeat the whole process from the beginning.
"""

