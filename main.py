iimport os
from time import sleep, time
from packaging import version
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import functions
import json

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Start Flask app
app = Flask(__name__)

# Enable CORS for the entire app
CORS(app, resources={r"/*": {"origins": "*"}})

# Store customer information and conversation progress
conversation_expiry = {}  # Dictionary to store conversation expiry timestamps
conversation_transcripts = {}  # Dictionary to store conversation transcripts
metrics = {
    "total_conversations": 0,
    "total_messages": 0,
    "average_response_time": 0,
}

# Save metrics to a file for persistent storage
metrics_file_path = 'metrics.json'
if os.path.exists(metrics_file_path):
    with open(metrics_file_path, 'r') as metrics_file:
        metrics = json.load(metrics_file)

@app.route('/start', methods=['GET'])
def start_conversation():
    """Start a new conversation."""
    print("Starting a new conversation...")  # Debugging line
    try:
        thread_id = f"thread-{int(time())}"  # Generate a unique thread ID
        conversation_expiry[thread_id] = time() + 7 * 24 * 60 * 60  # Expire after 7 days
        conversation_transcripts[thread_id] = []  # Initialize an empty transcript
        metrics["total_conversations"] += 1  # Increment metrics
        save_metrics()
        return jsonify({"thread_id": thread_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle a chat message from the user."""
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
            messages=[
                {"role": "user", "content": user_input}
            ]
        )
        assistant_response = response.choices[0].message['content']
        conversation_transcripts[thread_id].append({"role": "assistant", "content": assistant_response})
        response_time = time() - start_time
        metrics["total_messages"] += 1
        metrics["average_response_time"] = ((metrics["average_response_time"] * (metrics["total_messages"] - 1)) + response_time) / metrics["total_messages"]
        save_metrics()
        return jsonify({"response": assistant_response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ping', methods=['GET'])
def keep_alive():
    """Keep-alive endpoint."""
    return "I am alive!", 200

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Return bot metrics."""
    return jsonify(metrics), 200

def save_metrics():
    """Save metrics to a JSON file."""
    with open(metrics_file_path, 'w') as metrics_file:
        json.dump(metrics, metrics_file)

if __name__ == '__main__':
    if not os.path.exists('transcripts'):
        os.makedirs('transcripts')
    app.run(host='0.0.0.0', port=8080)
