import sqlite3

#this is a file that resets everything in user.db and fills them with a default user "alw"

con = sqlite3.connect("user.db")
cr = con.cursor()
cr.execute("""DELETE FROM users""")
cr.execute("""DELETE FROM dailyFoodConsumed""")
cr.execute("""DELETE FROM physicalActivities""")
cr.execute("""DELETE FROM userActivityLog""")
cr.execute("""DELETE FROM chats""")
cr.execute("""DELETE FROM messages""")
cr.execute("DELETE FROM RecipeRecommendations")

unwanted = "bread, spaghetti"


cr.execute("""
    CREATE TABLE IF NOT EXISTS users(
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
        unwanted TEXT)""")
con.commit()
cr.execute("""
    CREATE TABLE IF NOT EXISTS RecipeRecommendations(
        userID INT,
        recipe TEXT,
        FOREIGN KEY (userID) REFERENCES users(userID)
           )
    """)
con.commit()
cr.execute("""                
    INSERT INTO users 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, "alw", "1234", 0, 0, 0, 0, "none", 0, 0, 0, 0, 0, 0, unwanted))

con.commit()


cr.execute("""
    CREATE TABLE IF NOT EXISTS userActivityLog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    activityType TEXT, 
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")
cr.execute("""DELETE FROM userActivityLog""")

cr.execute("""
    CREATE TABLE IF NOT EXISTS dailyFoodConsumed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        activity TEXT,
        calories INT,
        protein INT,
        carbs INT, 
        fat INT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
con.commit()

cr.execute("""
    CREATE TABLE IF NOT EXISTS physicalActivities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        activity TEXT,
        calories_burnt INT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")


