import os
from time import sleep, time
from packaging import version
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import functions
import json
import logging

# Logging configuration
logging.basicConfig(level=logging.DEBUG)

# Check if the OpenAI version is compatible
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in environment variables.")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Start Flask app
app = Flask(__name__)

# Enable CORS for the entire app
CORS(app, resources={r"/*": {"origins": "https://bluethistleai.co.uk"}})

# Initialize metrics and conversation data
conversation_expiry = {}
conversation_transcripts = {}
metrics = {
    "total_conversations": 0,
    "total_messages": 0,
    "average_response_time": 0,
}
metrics_file_path = 'metrics.json'

# Load existing metrics if available
if os.path.exists(metrics_file_path):
    with open(metrics_file_path, 'r') as metrics_file:
        metrics = json.load(metrics_file)

# Helper function to save metrics
def save_metrics():
    with open(metrics_file_path, 'w') as metrics_file:
        json.dump(metrics, metrics_file)

@app.route('/start', methods=['GET'])
def start_conversation():
    """Start a new conversation and return a thread_id."""
    logging.debug("Starting a new conversation...")
    thread_id = str(int(time()))  # Generate a unique thread ID based on timestamp
    conversation_expiry[thread_id] = time() + 7 * 24 * 60 * 60  # Expiry in 7 days
    conversation_transcripts[thread_id] = []  # Initialize transcript
    metrics["total_conversations"] += 1
    save_metrics()
    logging.debug(f"Thread created: {thread_id}")
    return jsonify({"thread_id": thread_id}), 200

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages from users."""
    try:
        data = request.json
        thread_id = data.get('thread_id')
        user_input = data.get('message', '')

        if not thread_id or not user_input:
            logging.error("Missing thread_id or message in request.")
            return jsonify({"error": "Missing thread_id or message"}), 400

        # Check if the thread ID is valid and not expired
        current_time = time()
        if thread_id not in conversation_expiry or current_time > conversation_expiry[thread_id]:
            logging.error("Invalid or expired thread_id.")
            return jsonify({"error": "Conversation has expired."}), 400

        # Append user message to transcript
        conversation_transcripts[thread_id].append({"role": "user", "content": user_input})

        # Call OpenAI API to generate a response
        start_time = time()
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation_transcripts[thread_id]
        )
        assistant_response = response['choices'][0]['message']['content']
        end_time = time()

        # Update metrics
        conversation_transcripts[thread_id].append({"role": "assistant", "content": assistant_response})
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
    """Health check endpoint."""
    return "I am alive!", 200

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Return chatbot performance metrics."""
    return jsonify(metrics), 200

if __name__ == '__main__':
    if not os.path.exists('transcripts'):
        os.makedirs('transcripts')
    app.run(host='0.0.0.0', port=8080)
