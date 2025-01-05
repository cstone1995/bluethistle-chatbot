import os
from time import sleep, time
from packaging import version
from flask import Flask, request, jsonify
import openai
from openai import OpenAI
import functions
import json
import requests
from flask_cors import CORS
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, filename='assistant_debug.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')

# OpenAI and Facebook setup
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
VERIFY_TOKEN = 'bluethistle'
FB_PAGE_ACCESS_TOKEN = os.environ.get('FB_PAGE_ACCESS_TOKEN')

if not FB_PAGE_ACCESS_TOKEN:
    raise ValueError("Facebook Page Access Token is not set in environment variables.")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    default_headers={
        "OpenAI-Beta": "assistants=v2"
    }
)

# Create new assistant or load existing one
assistant_id = functions.create_assistant(client)

# Flask app setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://bluethistleai.co.uk"}})

# Metrics and conversation tracking
metrics = {
    "total_conversations": 0,
    "total_messages": 0,
    "average_response_time": 0,
    "links_clicked": {}
}
metrics_file_path = 'metrics.json'

if os.path.exists(metrics_file_path):
    with open(metrics_file_path, 'r') as metrics_file:
        metrics = json.load(metrics_file)

def save_metrics():
    with open(metrics_file_path, 'w') as metrics_file:
        json.dump(metrics, metrics_file)

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    token_sent = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if token_sent == VERIFY_TOKEN:
        return challenge
    else:
        return 'Invalid verification token', 403

@app.route('/webhook', methods=['POST'])
def receive_facebook_message():
    data = request.json
    if 'object' in data and data['object'] == 'page':
        for entry in data.get('entry', []):
            for event in entry.get('messaging', []):
                sender_id = event['sender']['id']
                if 'message' in event:
                    user_message = event['message'].get('text', '')
                    logging.info(f"Received message from {sender_id}: {user_message}")

                    # Generate a response using process_message
                    try:
                        response_message = process_message(user_message)
                        send_message_to_facebook(sender_id, response_message)
                    except Exception as e:
                        logging.error(f"Error in processing message: {e}")
                        send_message_to_facebook(sender_id, "Sorry, something went wrong.")

                    # Update metrics
                    metrics["total_messages"] += 1
                    save_metrics()
        return "EVENT_RECEIVED", 200
    else:
        return "ERROR", 404

def send_message_to_facebook(recipient_id, message):
    url = f"https://graph.facebook.com/v12.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logging.info(f"Message sent to {recipient_id}: {message}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending message to Facebook: {e}")

def process_message(user_message):
    try:
        # Create a thread (access the `id` attribute directly)
        thread = client.beta.threads.create()
        thread_id = thread.id  # Correctly access the thread ID

        # Send the user message to the thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # Process the assistant's response
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,  # Use the assistant_id here
            tools=[
                {"type": "file_search"},
                {"type": "code_interpreter"}
            ]
        )

        # Wait for the response
        timeout = 30  # Timeout in seconds
        start_time = time()
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == "completed":
                break
            if time() - start_time > timeout:
                return "Sorry, the response took too long. Please try again later."
            sleep(2)

        # Retrieve the assistant's response
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        # Extract the response text from TextContentBlock
        response_content = messages.data[0].content[0].text.value
        logging.info(f"Assistant response: {response_content}")
        return response_content

    except Exception as e:
        logging.error(f"Error querying assistant: {e}")
        return "Sorry, I couldn't process your request. Please try again later."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

