export function fetchUserChats() {
  fetch('/getAllChats')
    .then(res => res.json())
    .then(chats => {
      const list = document.getElementById('chat-list');
      list.innerHTML = '';

      chats.forEach(chat => {
        const li = document.createElement('li');
        const link = document.createElement('a');
        link.href = '#';
        const date = new Date(chat.timestamp).toISOString().split('T')[0];
        link.textContent = date;
        link.onclick = () => loadChat(chat.id);

        li.appendChild(link);
        list.appendChild(li);
      });
    });
}

export function loadChat(chat_id) {
  fetch(`/chat/${chat_id}`)
  .then(res => res.json())
  .then(messages => {
    const history = document.getElementById('chat-history');
    history.innerHTML = '';
    console.log("fetched")
    console.log(messages)
    messages.forEach(msg => {
      const msgDiv = document.createElement('div');
      msgDiv.className = msg.role === 'user' ? 'user-msg' : 'bot-msg';
      msgDiv.textContent = msg.content;
      history.appendChild(msgDiv);
    });
  });
}

fetchUserChats();