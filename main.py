import os
from time import sleep, time
from packaging import version
from flask import Flask, request, jsonify
from flask_cors import CORS  # Import for handling CORS
import openai
import functions
import datetime
import json

# Check if the OpenAI version is correct
required_version = version.parse("1.1.1")  # Define the minimum required version of OpenAI
current_version = version.parse(openai.__version__)  # Get the current version of OpenAI
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')  # Get the OpenAI API key from environment variables

# Validate the OpenAI version
if current_version < required_version:
    raise ValueError(f"Error: OpenAI version {openai.__version__} is less than the required version 1.1.1")
else:
    print("OpenAI version is compatible.")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Start Flask app
app = Flask(__name__)

# Enable CORS for the entire app
CORS(app, resources={r"/*": {"origins": "https://bluethistleai.co.uk"}})

# Create new assistant or load existing one
assistant_id = functions.create_assistant(openai)  # Pass `openai` directly to the helper function

# Store customer information and conversation progress
conversation_progress = {}  # Dictionary to store conversation progress
conversation_expiry = {}  # Dictionary to store conversation expiry timestamps
conversation_transcripts = {}  # Dictionary to store conversation transcripts
metrics = {
    "total_conversations": 0,
    "total_messages": 0,
    "average_response_time": 0,
    "links_clicked": {}  # Metrics to track link clicks for each link
}  # Metrics to track bot performance

# Save metrics to a file for persistent storage
metrics_file_path = 'metrics.json'
if os.path.exists(metrics_file_path):
    with open(metrics_file_path, 'r') as metrics_file:
        metrics = json.load(metrics_file)  # Load existing metrics from file

@app.route('/start', methods=['GET'])
def start_conversation():
    print("Starting a new conversation...")  # Debugging line
    try:
        thread = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[])  # Simulate thread creation
        thread_id = thread['id']  # Extract a mock thread ID
        conversation_expiry[thread_id] = time() + 7 * 24 * 60 * 60  # Expire after 7 days
        conversation_transcripts[thread_id] = []  # Initialize an empty transcript
        metrics["total_conversations"] += 1  # Increment metrics
        save_metrics()
        return jsonify({"thread_id": thread_id}), 200
    except Exception as e:
        print(f"Error in /start: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    thread_id = data.get('thread_id')
    user_input = data.get('message', '')

    if not thread_id:
        return jsonify({"error": "Missing thread_id"}), 400

    if thread_id not in conversation_expiry or time() > conversation_expiry[thread_id]:
        return jsonify({"error": "Conversation has expired."}), 400

    conversation_transcripts[thread_id].append({"role": "user", "content": user_input})
    try:
        start_time = time()
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation_transcripts[thread_id]
        )
        assistant_response = response.choices[0].message['content']
        conversation_transcripts[thread_id].append({"role": "assistant", "content": assistant_response})
        response_time = time() - start_time
        metrics["total_messages"] += 1
        metrics["average_response_time"] = ((metrics["average_response_time"] * (metrics["total_messages"] - 1)) + response_time) / metrics["total_messages"]
        save_metrics()
        return jsonify({"response": assistant_response}), 200
    except Exception as e:
        print(f"Error in /chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/ping', methods=['GET'])
def keep_alive():
    return "I am alive!", 200

@app.route('/metrics', methods=['GET'])
def get_metrics():
    return jsonify(metrics), 200

def save_metrics():
    with open(metrics_file_path, 'w') as metrics_file:
        json.dump(metrics, metrics_file)

if __name__ == '__main__':
    if not os.path.exists('transcripts'):
        os.makedirs('transcripts')
    app.run(host='0.0.0.0', port=8080)

