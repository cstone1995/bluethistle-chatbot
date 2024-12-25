import os
from time import sleep, time
from flask import Flask, request, jsonify
import openai
from openai import OpenAI
import functions
import datetime
import json

# Check if the OpenAI version is correct
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

if current_version < required_version:
    raise ValueError(f"Error: OpenAI version {openai.__version__} is less than the required version 1.1.1")
else:
    print("OpenAI version is compatible.")

# Start Flask app
app = Flask(__name__)

VERIFY_TOKEN = 'bluethistle'

client = OpenAI(
    api_key=OPENAI_API_KEY,
    default_headers={
        "OpenAI-Beta": "assistants=v2"
    }
)

assistant_id = functions.create_assistant(client)

conversation_progress = {}
conversation_expiry = {}
conversation_transcripts = {}
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

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    token_sent = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if token_sent == VERIFY_TOKEN:
        return challenge
    else:
        return 'Invalid verification token', 403

@app.route('/start', methods=['GET', 'POST'])
def start_conversation():
    try:
        if request.method == 'POST' and request.content_type != 'application/json':
            return jsonify({"error": "Content-Type must be 'application/json'"}), 415

        thread = client.beta.threads.create()
        thread_id = thread.id

        conversation_expiry[thread_id] = time() + 7 * 24 * 60 * 60
        conversation_transcripts[thread_id] = []
        metrics["total_conversations"] += 1
        save_metrics()

        return jsonify({"thread_id": thread_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    if request.content_type != 'application/json':
        return jsonify({"error": "Content-Type must be 'application/json'"}), 415

    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        thread_id = data.get('thread_id')
        user_input = data.get('message', '')

        if not thread_id or not user_input:
            return jsonify({"error": "Missing 'thread_id' or 'message' in request"}), 400

        if thread_id in conversation_expiry:
            if time() > conversation_expiry[thread_id]:
                del conversation_expiry[thread_id]
                del conversation_progress[thread_id]
                del conversation_transcripts[thread_id]
                return jsonify({"error": "Conversation has expired."}), 400

        conversation_transcripts[thread_id].append({"role": "user", "content": user_input})
        start_time = time()

        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input
        )

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            tools=[
                {"type": "file_search"},
                {"type": "code_interpreter"}
            ]
        )

        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == 'completed':
                break
            sleep(1)

        end_time = time()
        response_time = end_time - start_time
        metrics["total_messages"] += 1
        metrics["average_response_time"] = (
            (metrics["average_response_time"] * (metrics["total_messages"] - 1)) + response_time
        ) / metrics["total_messages"]
        save_metrics()

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        response = messages.data[0].content[0].text.value

        if "I couldn't find" in response and "document" in response:
            response = "I'm currently unable to find specific details on that. However, here are some related details that might help."

        conversation_transcripts[thread_id].append({"role": "assistant", "content": response})

        with open(f'transcripts/{thread_id}.json', 'w') as transcript_file:
            json.dump(conversation_transcripts[thread_id], transcript_file)

        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ping', methods=['GET'])
def keep_alive():
    return "I am alive!", 200

@app.route('/metrics', methods=['GET'])
def get_metrics():
    return jsonify(metrics)

@app.route('/link_click', methods=['POST'])
def track_link_click():
    data = request.json
    link = data.get('link')

    if link:
        metrics["links_clicked"].setdefault(link, 0)
        metrics["links_clicked"][link] += 1
        save_metrics()
        return jsonify({"message": "Link click recorded"}), 200
    else:
        return jsonify({"error": "Missing link data"}), 400

def save_metrics():
    with open(metrics_file_path, 'w') as metrics_file:
        json.dump(metrics, metrics_file)

if __name__ == '__main__':
    if not os.path.exists('transcripts'):
        os.makedirs('transcripts')
    app.run(host='0.0.0.0', port=8080)

