import os
from time import sleep, time
from packaging import version
from flask import Flask, request, jsonify
import openai
import functions
import datetime
import json
import pkg_resources
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Check if the OpenAI version is correct
required_version = version.parse("1.1.1")  # Define the minimum required version of OpenAI
try:
    current_version = version.parse(pkg_resources.get_distribution("openai").version)  # Get the current version of OpenAI
except pkg_resources.DistributionNotFound:
    raise ImportError("The 'openai' library is not installed. Please install it with 'pip install openai'.")

# Validate the OpenAI version
if current_version < required_version:
    raise ValueError(f"Error: OpenAI version {current_version} is less than the required version {required_version}")
else:
    print("OpenAI version is compatible.")

# Start Flask app
app = Flask(__name__)

# Verification token for Facebook webhook
VERIFY_TOKEN = 'bluethistle'  # Replace with your custom verification token

# Initialize the OpenAI client with v2 beta header
client = openai

# Create new assistant or load existing one
assistant_id = functions.create_assistant()  # Create or load the assistant using a custom function

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

# Webhook verification route for Facebook
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    # Facebook webhook verification
    token_sent = request.args.get('hub.verify_token')  # Get the token sent by Facebook
    challenge = request.args.get('hub.challenge')  # Get the challenge code sent by Facebook

    # Verify the token
    if token_sent == VERIFY_TOKEN:
        return challenge  # Return the challenge code to verify successfully
    else:
        return 'Invalid verification token', 403  # Return an error if the token is invalid

# Start a new conversation thread
@app.route('/start', methods=['GET'])
def start_conversation():
    print("Starting a new conversation...")  # Debugging line to indicate conversation start
    thread = client.beta.threads.create()  # Create a new conversation thread using OpenAI API
    thread_id = thread.id  # Extract the thread ID
    conversation_expiry[thread_id] = time() + 7 * 24 * 60 * 60  # Set expiry time to 7 days from now
    conversation_transcripts[thread_id] = []  # Initialize an empty transcript for the new conversation
    metrics["total_conversations"] += 1  # Increment the total conversation count
    save_metrics()  # Save updated metrics to the file
    print(f"New thread created with ID: {thread.id}")  # Debugging line to show thread ID
    return jsonify({"thread_id": thread.id})  # Return the thread ID as a JSON response

# Generate a response to user input
@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Parse and validate the JSON payload
        data = request.json
        if not data or 'thread_id' not in data or 'message' not in data:
            app.logger.error("Invalid request payload")
            return jsonify({"error": "Invalid request payload"}), 400

        thread_id = data['thread_id']
        user_input = data['message']

        # Check if thread_id is valid
        if thread_id not in conversation_expiry:
            app.logger.error(f"Invalid thread_id: {thread_id}")
            return jsonify({"error": "Invalid thread_id"}), 400

        current_time = time()
        if current_time > conversation_expiry[thread_id]:
            app.logger.error(f"Conversation expired for thread_id: {thread_id}")
            return jsonify({"error": "Conversation has expired."}), 400

        # Record the user input
        conversation_transcripts[thread_id].append({"role": "user", "content": user_input})
        start_time = time()

        # Simulate OpenAI API response for testing
        response = {"content": "This is a simulated response"}  # Replace with real OpenAI call

        # Calculate response time
        end_time = time()
        response_time = end_time - start_time
        metrics["total_messages"] += 1
        metrics["average_response_time"] = (
            (metrics["average_response_time"] * (metrics["total_messages"] - 1)) + response_time
        ) / metrics["total_messages"]

        # Record assistant response
        conversation_transcripts[thread_id].append({"role": "assistant", "content": response["content"]})

        return jsonify({"response": response["content"]})

    except Exception as e:
        app.logger.error(f"Error in /chat route: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

# Keep-alive endpoint
@app.route('/ping', methods=['GET'])
def keep_alive():
    return "I am alive!", 200

# Endpoint to get performance metrics
@app.route('/metrics', methods=['GET'])
def get_metrics():
    return jsonify(metrics)  # Return the performance metrics as a JSON response

# Endpoint to track link clicks
@app.route('/link_click', methods=['POST'])
def track_link_click():
    data = request.json
    link = data.get('link')

    if link:
        if link not in metrics["links_clicked"]:
            metrics["links_clicked"][link] = 0
        metrics["links_clicked"][link] += 1  # Increment the click count for the link
        save_metrics()  # Save updated metrics to the file
        return jsonify({"message": "Link click recorded"}), 200
    else:
        return jsonify({"error": "Missing link data"}), 400

# Save metrics to a file
def save_metrics():
    with open(metrics_file_path, 'w') as metrics_file:
        json.dump(metrics, metrics_file)  # Save metrics to a JSON file

# Run the server
if __name__ == '__main__':
    if not os.path.exists('transcripts'):
        os.makedirs('transcripts')  # Create the transcripts directory if it doesn't exist
    app.run(host='0.0.0.0', port=8080)  # Run the Flask app on port 8080 and listen on all IP addresses

