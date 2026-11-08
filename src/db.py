import sqlite3
from uuid import uuid4
from datetime import datetime
from typing import Any

#constructs the userDb if not existing
def userDb():
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute('''CREATE TABLE IF NOT EXISTS users(
        userID INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        calories INTEGER,
        protein INTEGER,
        carbs INTEGER,
        fat INTEGER,
        allergies TEXT,
        height FLOAT,
        weight FLOAT,
        remaining_calories INT,
        remaining_protein INT,
        remaining_carbs INT,
        remaining_fat INT,
        unwanted TEXT)''')
    con.commit()
    con.close()

# verfies if the user has entered the correct pw and username
def verifyUser(username, password):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("""SELECT * FROM users 
               WHERE username = ? AND password = ?""", 
               (username, password))
    
    user = cr.fetchone()
    con.close()
    return user

#fetches user information
def getUserInfo(username):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("""SELECT calories, protein, carbs, fat, allergies, height, weight,
              remaining_calories, remaining_protein, remaining_carbs, remaining_fat, unwanted
              FROM users 
              WHERE username = ?""", (username,))
    row = cr.fetchone()
    # if remaining cals, protein, carbs and fats are none, set them to the daily consumption data
    if row[7] == None or row[8] == None or row[9] == None or row[10] == None:
        vals = row[:4]
        cr.execute("""
            UPDATE users SET
              remaining_calories=?, remaining_protein=?,
              remaining_carbs=?, remaining_fat=?
            WHERE username=?
        """, (vals[0],
              vals[1],
              vals[2],
              vals[3],
              username))
        con.commit()
        cr.execute("""SELECT calories, protein, carbs, fat, allergies, height, weight,
                  remaining_calories, remaining_protein, remaining_carbs, remaining_fat, unwanted
                  FROM users 
                  WHERE username = ?""", (username,))        
        row = cr.fetchone()
    con.close()
    return row


def getUserIdByName(username):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("""
      SELECT UserID
      FROM users WHERE username=?
    """, (username,))
    user_id = cr.fetchone()
    con.close()
    if user_id:
        return user_id[0]
    else:
        raise Exception("username doesn't exist")

# updates user stats in the db when he inputs new stats in the profile
def updateUserStats(username, data):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("""
      SELECT calories, protein, carbs, fat,
            remaining_calories, remaining_protein,
            remaining_carbs, remaining_fat,
            height, weight, unwanted
      FROM users WHERE username=?
    """, (username,))
    old = cr.fetchone()
    cal_old, prot_old, carb_old, fat_old = old[:4]
    remains = list(old[4:8])
    height_old, weight_old = old[8], old[9]

    hated_ingredients = data["hated_ingredients"]
    # calc the difference between old and new vals
    diffs = [
      data["calories"] - int(cal_old),
      data["protein"] - int(prot_old),
      data["carbs"] - int(carb_old),
      data["fat"] - int(fat_old)
    ]
    #set the new vals
    for i in range(4):
        remains[i] = max(remains[i] + diffs[i], 0)
    
    new_height = float(data.get("height", height_old))
    new_weight = float(data.get("weight", weight_old))

    cr.execute("""
        UPDATE users SET
          calories=?, protein=?, carbs=?, fat=?,
          remaining_calories=?, remaining_protein=?,
          remaining_carbs=?, remaining_fat=?,
          height=?, weight=?, unwanted = ?
        WHERE username=?
    """, (
        data["calories"], data["protein"], data["carbs"], data["fat"],
        remains[0], remains[1], remains[2], remains[3],
        new_height, new_weight, hated_ingredients, username
    ))

    con.commit()
    con.close()
# reset user remaining variables
def reset():
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("""
        UPDATE users SET
            remaining_calories = calories,
            remaining_protein = protein,
            remaining_carbs = carbs,
            remaining_fat = fat
    """)
    con.commit()
    con.close()
# if the user does a physical acitivity, update it in the DB
def updateAfterPhysicalActivity(username, data):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("""
      SELECT remaining_calories
      FROM users WHERE username=?
    """, (username,))
    remaining_calories = cr.fetchone()[0]
    #update remaining cals after a workout
    new_remaining_calories = remaining_calories + data['calories_burnt']
    
    cr.execute("""
        UPDATE users SET
            remaining_calories = ?
        WHERE username = ?
    """, (
        new_remaining_calories,
        username
    ))
    
    con.commit()
    #log physical activity
    cr.execute("""
        INSERT INTO physicalActivities (username, activity, calories_burnt)
        VALUES (?, ?, ?)
    """, (username, data["task"], data["calories_burnt"]))
    
    con.commit()
    con.close()
    logActivities(data["task"], username, data)

#updates user remaining cals, fats etc. after eating something
def updateFoodTracking(username, data):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("""
      SELECT remaining_calories, remaining_protein,
             remaining_carbs, remaining_fat
      FROM users WHERE username=?
    """, (username,))
    remains = cr.fetchone()

    if remains:
        new_remains = [
            max(remains[0] - data["calories"], 0),
            max(remains[1] - data["protein"], 0),
            max(remains[2] - data["carbs"], 0),
            max(remains[3] - data["fat"], 0)
        ]
        cr.execute("""
            UPDATE users SET
              remaining_calories=?, remaining_protein=?,
              remaining_carbs=?, remaining_fat=?
            WHERE username=?
        """, (*new_remains, username))
    #log eating activity
    con.commit()
    cr.execute("""
        INSERT INTO dailyFoodConsumed (username, activity, calories, protein, carbs, fat)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, data["task"], data["calories"], data["protein"], data["carbs"], data["fat"]))
    con.commit()
    con.close()
    logActivities(data["task"], username, data)

# logs the activity into a logging table that logs all daily acitivites 
def logActivities(task, username, data):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    details = ""
    if task == "eating": 
        details = f"Calories: {data["calories"]}, Protein: {data["protein"]}, Carbs: {data["carbs"]}, Fat: {data["fat"]}"
        cr.execute("""
            INSERT INTO userActivityLog (username, activityType, details)
            VALUES (?, 'eating', ?)
        """, (username, details))
    elif task == "physical":
        details = f"Calories Burnt: {data['calories_burnt']}, duration: {data["duration"]}"
        cr.execute("""
        INSERT INTO userActivityLog (username, activityType, details)
        VALUES (?, 'physical', ?)
    """, (username, details))
    con.commit()
    con.close()

# add new chat in the DB
def newChatToDb(user_id: int) -> int:
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("INSERT INTO chats (user_id) VALUES (?)", (user_id,))
    chat_id = cr.lastrowid
    con.commit()
    con.close()
    return chat_id

#add a message to a chat
def messageToDb(content: str, role: str, chat_id: int) -> str:
    con = sqlite3.connect("user.db")
    cr = con.cursor()

    if role != "assistant" and role != "user":
        raise Exception("role needs to be 'assistant' or 'user'")
    
    message_uuid = str(uuid4())
    cr.execute("INSERT INTO messages (id, chat_id, role, content) VALUES (?, ?, ?, ?)", 
               (message_uuid, chat_id, role, content))
    con.commit()
    con.close()
    return message_uuid

# get message array of a chat   
def getMessageArray(chat_id: int, user_id:int) -> list[dict[str, str]]:
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("SELECT id FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id))
    if not cr.fetchone():
        con.close()
        return None
    cr.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY timestamp ASC", (chat_id,))
    rows = cr.fetchall()
    message_array = []
    for row in rows:
        entry = {}
        entry["role"] = row[0]
        entry["content"] = row[1]
        message_array.append(entry)
    
    con.close()
    return message_array

# get all chats a user has ever started
def getAllChatsByUserId(user_id):
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("SELECT id, timestamp FROM chats WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    desc = cr.description
    column_names = [col[0] for col in desc]
    data = [dict(zip(column_names, row)) for row in cr.fetchall()]
    con.close()
    return data
# get the chat the user started today
def getTodayChatByUserID(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    con = sqlite3.connect("user.db")
    cr = con.cursor()
    cr.execute("""SELECT id FROM chats WHERE user_id = ? AND DATE(timestamp) = ? ORDER BY timestamp DESC LIMIT 1""", (user_id, today))
    row = cr.fetchone()
    if row:
        chat_id = row[0]
        cr.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY timestamp ASC", (chat_id,))
        messages = cr.fetchall()
    else:
        chat_id = newChatToDb(user_id)
        messages = []
    
    con.close()
    return chat_id, messages