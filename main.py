import os
import logging
from time import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import functions
import json

# Logging configuration
logging.basicConfig(level=logging.DEBUG)

# OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in environment variables.")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Start Flask app
app = Flask(__name__)

# Enable CORS
CORS(app, resources={r"/*": {"origins": "https://bluethistleai.co.uk"}})

# Metrics and conversation management
conversation_expiry = {}
conversation_transcripts = {}
metrics = {
    "total_conversations": 0,
    "total_messages": 0,
    "average_response_time": 0,
}
metrics_file_path = 'metrics.json'

# Load metrics from file
if os.path.exists(metrics_file_path):
    with open(metrics_file_path, 'r') as metrics_file:
        metrics = json.load(metrics_file)

# Save metrics to file
def save_metrics():
    with open(metrics_file_path, 'w') as metrics_file:
        json.dump(metrics, metrics_file)

# Create assistant instance
client = openai.OpenAI(default_headers={"OpenAI-Beta": "assistants=v2"})
assistant_id = functions.create_assistant(client)

@app.route('/start', methods=['GET'])
def start_conversation():
    """Start a new conversation."""
    try:
        logging.debug("Starting a new conversation...")
        thread_id = str(int(time()))  # Generate a unique thread ID
        conversation_expiry[thread_id] = time() + 7 * 24 * 60 * 60  # Expire in 7 days
        conversation_transcripts[thread_id] = [{"role": "system", "content": "You are a helpful assistant."}]
        metrics["total_conversations"] += 1
        save_metrics()
        logging.debug(f"Thread created: {thread_id}")
        return jsonify({"thread_id": thread_id}), 200
    except Exception as e:
        logging.exception("Error starting conversation.")
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests."""
    try:
        data = request.json
        thread_id = data.get('thread_id')
        user_input = data.get('message', '')

        if not thread_id or not user_input:
            logging.error("Missing thread_id or message.")
            return jsonify({"error": "Missing thread_id or message"}), 400

        # Validate thread ID and expiry
        if thread_id not in conversation_expiry or time() > conversation_expiry[thread_id]:
            logging.error("Invalid or expired thread_id.")
            return jsonify({"error": "Conversation has expired."}), 400

        # Add user input to transcript
        conversation_transcripts[thread_id].append({"role": "user", "content": user_input})

        # Call OpenAI API
        start_time = time()
        response = client.beta.threads.messages.create(
            thread_id=thread_id,
            content=user_input,
            role="user"
        )
        end_time = time()

        # Get assistant response
        assistant_response = response['choices'][0]['message']['content']
        conversation_transcripts[thread_id].append({"role": "assistant", "content": assistant_response})

        # Update metrics and transcripts
        metrics["total_messages"] += 1
        response_time = end_time - start_time
        metrics["average_response_time"] = ((metrics["average_response_time"] * (metrics["total_messages"] - 1)) + response_time) / metrics["total_messages"]
        save_metrics()

        return jsonify({"response": assistant_response}), 200
    except Exception as e:
        logging.exception("Error in /chat endpoint.")
        return jsonify({"error": str(e)}), 500

@app.route('/ping', methods=['GET'])
def keep_alive():
    """Health check."""
    return "I am alive!", 200

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get chatbot metrics."""
    return jsonify(metrics), 200

if __name__ == '__main__':
    if not os.path.exists('transcripts'):
        os.makedirs('transcripts')
    app.run(host='0.0.0.0', port=8080)
