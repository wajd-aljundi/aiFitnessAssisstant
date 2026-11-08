import {fetchUserChats} from './chatLoader.js'
import {loadChat} from './chatLoader.js'

const sendButton = document.getElementById('sendButton');
const userInput = document.getElementById('userInput');
const chatLayout = document.getElementById('chatLayout');

//creates a message div and adds it to the conversation
function addMessageToConversation(content, sender) {
  const message = document.createElement("div");
  message.classList.add('message', sender);
  message.innerHTML = marked.parse(content);
  chatLayout.appendChild(message);
  chatLayout.scrollTop = chatLayout.scrollHeight;
}

// send user input to the backend and get a response
async function getBotReply(user_text) {
  const response = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: user_text })
  });

  const data = await response.json();
  return data.reply;
}

function getActivityInfo(text) {
  const lines = text.split('\n');
  let task = "";
  let calories = 0, protein = 0, carbs = 0, fat = 0;
  let calories_burnt = 0, duration = 0;
  let found_task_block = false;

  for (const line of lines) {
    const lower = line.toLowerCase();
    const parts = line.split('=');
    if (parts.length < 2) continue;

    const key = parts[0].replace(/[*_~`]+/g, '').trim().toLowerCase();
    const value = parts[1].replace(/[*_~`]+/g, '').trim().split(" ")[0];

    if (key === 'task' && !found_task_block) {
      task = value.toLowerCase();
      found_task_block = true;
      continue;
    }
    if (!found_task_block) continue;
    else if (key.includes('calories') && !key.includes('burnt') && key!=null) calories = Number(value);
    else if (key.includes('protein') && key!=null) protein = Number(value);
    else if (key.includes('carbs') && key!=null) carbs = Number(value);
    else if (key.includes('fat') && key!=null) fat = Number(value);
    console.log(task, calories, protein, carbs, fat)
  }
  if (task === "eating" && calories > 0 && protein >= 0 && carbs >= 0 && fat >= 0) {
    return { task, calories, protein, carbs, fat };
  } else {
    return { task: "" };
  }
}


// handles user input and disables input until a reply is received
async function handleMessageSending() {
  const text = userInput.value.trim();
  if (!text) return;

  sendButton.style.pointerEvents = 'none';
  userInput.disabled = true;

  addMessageToConversation(text, 'user');
  userInput.value = '';

  const reply = await getBotReply(text);
  const nutrition = getActivityInfo(reply);
  addMessageToConversation(reply, 'bot');
  console.log("LLM raw reply:", reply);
  
  if (nutrition.task.includes('eating')) {
    await fetch("/applyActivities", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: 'same-origin',
      body: JSON.stringify(nutrition)
    });
  }

  sendButton.style.pointerEvents = 'auto';
  userInput.disabled = false;
  userInput.focus();
}

document.addEventListener('DOMContentLoaded', () => {

  fetch('/chat/getTodayChat')
    .then(res => res.json())
    .then(data => {
      if (data.messages) {
        data.messages.forEach(msg => {
          addMessageToConversation(msg.content, msg.role === 'user' ? 'user' : 'bot');
        });
      }
    });
});



//run handleMessage sending when clicking on the send button
sendButton.addEventListener('click', handleMessageSending);

//same but with "Enter"
userInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') handleMessageSending();
});