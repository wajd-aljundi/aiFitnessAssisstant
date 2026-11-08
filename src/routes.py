from flask import render_template, request, redirect, url_for, session, jsonify
from flask import request, jsonify, render_template, session

from nutrientAPIs import trackFood
from db import verifyUser, getUserInfo, updateUserStats, updateAfterPhysicalActivity, updateFoodTracking, getUserIdByName, newChatToDb, messageToDb, getMessageArray, getAllChatsByUserId, getTodayChatByUserID
from llm import askLlm, classifyConvo, getPrompt, activitiyPrompt
from physical_activities import extractDictFromText, logPhysicalActivity
import sqlite3
from datetime import date


def setup_routes(app):

    @app.route('/')
    def index():
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template("index.html")
    
    @app.route('/chats')
    def chats():
        return render_template("chats.html")

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if verifyUser(username, password):
                session['user'] = username
                session['user_id'] = getUserIdByName(session['user'])
                return redirect(url_for('profile'))
            return render_template('login.html', error="Invalid login")
        return render_template('login.html')

    @app.route('/profile', methods = ['GET', 'POST'])
    def profile():
        if 'user' not in session:
            return redirect(url_for('login'))
        user_data = getUserInfo(session['user'])
        return render_template('profile.html', username=session['user'], data=user_data)
    

    @app.route('/getAllChats', methods=['GET', 'POST'])
    def getAllChats():
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not logged in'}), 401
        chat_sessions = getAllChatsByUserId(user_id)
        return jsonify(chat_sessions)
    

    @app.route('/chat/<int:chat_id>', methods=['GET'])
    def getChatMessages(chat_id):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not logged in'}), 401
        messages = getMessageArray(chat_id, user_id)
        return jsonify(messages)
    
    @app.route('/chat/getTodayChat', methods=['Get'])
    def getTodayChat():
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not logged in'}), 401
        chat_id, messages = getTodayChatByUserID(user_id)
        session["chat_id"] = chat_id
        return jsonify({'chat_id': chat_id, 'messages': [{'role': m[0], 'content': m[1]} for m in messages]})



    @app.route('/updateUserStats', methods=['POST'])    
    def update_profile():
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401

        username = session['user']
        data = request.get_json()

        updateUserStats(username, data)

        return jsonify({"success": True})
    
    #when an activity is done by the user, this function is used to update the profile and log the acitivties
    @app.route('/applyActivities', methods=['POST'])
    def applyActivities():
        Activity = request.get_json()
        username = session['user']
        user_data = getUserInfo(username)
        task = Activity.get('task')
        recipe_vals = {
            'task': task,
            'calories': Activity.get('calories', 0), 
            'protein': Activity.get('protein', 0), 
            'carbs': Activity.get('carbs', 0), 
            'fat': Activity.get('fat', 0)
            }
        if task.lower() == "eating":
            updateFoodTracking(username, recipe_vals)
        else:
            return jsonify({"error": "Unknown task type"}), 400

        return jsonify({"success": True, "userData": user_data})


    @app.route('/chat', methods=['GET', 'POST'])
    def chat():
        if 'chat_id' not in session:
            session['chat_id'] = newChatToDb(session['user_id'])
        
        user_input = request.json.get('message', '') #get user input 

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not logged in'}), 401
        
        messageToDb(user_input, 'user', session['chat_id'])
        message_array = getMessageArray(session['chat_id'], user_id) # message Array after user input but no {"role": "system"} entry at index 0!!!
        
        conversation_class = classifyConvo(message_array)
        current_prompt = getPrompt(conversation_class)
        username = session['user']
        # get userdata from DB
        user_info = None
        # tell user to fill all fields in his profile
        if 'user' in session:
            user_info = getUserInfo(session['user'])
            if any(metric == 0 for metric in user_info[:4]):
                reply = "please fill all the values in your profile"
                messageToDb(reply, 'assistant', session['chat_id'])
                return jsonify({'reply': reply}) 
            
        # API request for nutriments
        if ('calorie' in conversation_class.lower() or 'tracking' in conversation_class.lower()) and "recipe" not in conversation_class.lower():
            # array with all nutrients added up
            tracked_food = trackFood(user_input)
            task = "eating"
            food_vals = {
                'task': task,
                'calories': tracked_food.get('calories', 0), 
                'protein': tracked_food.get('protein', 0), 
                'carbs': tracked_food.get('carbs', 0), 
                'fat': tracked_food.get('fats', 0)
            }
            updateFoodTracking(username, food_vals)
            user_info = getUserInfo(session['user'])
        # sets the bot message if the message is classified as a recipe request
        bot_message = ""
        if "Recipe" in conversation_class or "Request" in conversation_class:
            if user_info != None:
                bot_message = activitiyPrompt(message_array, username, user_info)
                if bot_message == None:
                    bot_message = ""

        # main communication with the llm
        reply = askLlm(message_array, current_prompt, bot_message, user_info)

        if "physical" in conversation_class.lower():
            activity_min_dict = extractDictFromText(reply)
            if activity_min_dict:
                burned_calories = logPhysicalActivity(activity_min_dict, user_info, username)
                if burned_calories:
                    reply = f"""Your activity, "{activity_min_dict['activity']}", has been successfully logged. You burned a total of {burned_calories} calories."""

                else:
                    reply = f"""The activity '{activity_min_dict['activity']}' is not supported for tracking."""
                
                

        messageToDb(reply, 'assistant', session['chat_id'])

        return jsonify({'reply': reply}) 
    

    @app.route('/tracker')
    def tracker():
        username = session.get('user')
        if not username:
            return redirect('/login')

        con = sqlite3.connect('user.db')
        cur = con.cursor()

        # 1. ÜBRIGE NÄHRWERTE
        cur.execute("""
            SELECT 
                remaining_calories, 
                remaining_protein, 
                remaining_carbs, 
                remaining_fat 
            FROM users 
            WHERE username=?
        """, (username,))
        remaining_row = cur.fetchone()
        remaining = {
            'calories': remaining_row[0],
            'protein': remaining_row[1],
            'carbs': remaining_row[2],
            'fat': remaining_row[3]
        }

        today = date.today().isoformat()
        cur.execute("""
            SELECT 
                COALESCE(SUM(calories), 0),
                COALESCE(SUM(protein), 0),
                COALESCE(SUM(carbs), 0),
                COALESCE(SUM(fat), 0)
            FROM dailyFoodConsumed
            WHERE username=? AND date(timestamp)=?
        """, (username, today))
        food_row = cur.fetchone()
        eaten = {
            'calories': food_row[0],
            'protein': food_row[1],
            'carbs': food_row[2],
            'fat': food_row[3]
        }

        remaining_after_food = {
            'calories': remaining['calories'] - eaten['calories'],
            'protein': remaining['protein'] - eaten['protein'],
            'carbs': remaining['carbs'] - eaten['carbs'],
            'fat': remaining['fat'] - eaten['fat']
        }

        # 2. HEUTIGE AKTIVITÄTEN
        today = date.today().isoformat()
        cur.execute("""
            SELECT activity, calories_burnt
            FROM physicalActivities
            WHERE username=? AND date(timestamp)=?
        """, (username, today))
        activities = [
            {'activity': row[0], 'calories_burned': row[1]}
            for row in cur.fetchall()
        ]

        con.close()


        return render_template(
            'tracker.html',
            remaining=remaining_after_food,
            activities=activities
        )