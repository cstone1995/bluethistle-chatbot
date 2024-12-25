let threadId = null; // Store the thread ID for the conversation

async function startConversation() {
    try {
        const response = await fetch('https://bluethistle-chatbot.onrender.com/start', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        threadId = data.thread_id; // Save the thread ID for future interactions
        displayMessage("Chatbot", "Hello! How can I assist you today?");
    } catch (error) {
        console.error("Error starting conversation:", error);
        displayMessage("Chatbot", "Sorry, I couldn't start the chat. Please try again later.");
    }
}

async function sendMessage() {
    const inputField = document.getElementById('chat-input');
    const message = inputField.value.trim();

    if (!message) return;

    displayMessage("You", message); // Display the user's message
    inputField.value = ""; // Clear the input field

    try {
        const response = await fetch('https://bluethistle-chatbot.onrender.com/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_id: threadId, message: message })
        });
        const data = await response.json();
        displayMessage("Chatbot", data.response); // Display the chatbot's response
    } catch (error) {
        console.error("Error sending message:", error);
        displayMessage("Chatbot", "Sorry, something went wrong. Please try again.");
    }
}

function displayMessage(sender, message) {
    const chatWindow = document.getElementById('chat-window');
    const messageElement = document.createElement('div');
    messageElement.textContent = `${sender}: ${message}`;
    chatWindow.appendChild(messageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight; // Scroll to the bottom
}

document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('chat-input').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') sendMessage();
});

startConversation(); // Start the conversation when the page loads
