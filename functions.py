import json
import os
import openai
import logging

# Set up logging to track the assistant's behavior
logging.basicConfig(level=logging.INFO, filename='assistant_debug.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')

def create_assistant(openai_client):
    """Create or retrieve an assistant ID."""
    assistant_file_path = 'assistant.json'

    # Check if an existing assistant ID is saved
    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data.get('assistant_id')
            logging.info("Loaded existing assistant ID: %s", assistant_id)
            return assistant_id

    try:
        # Comprehensive instructions for the assistant
        instructions = """
        You are a customer service assistant for BlueThistle AI. Answer all queries briefly but informatively. 
        Focus on services, pricing, and getting users to buy services. Do not fabricate answers.
        """

        # Create the assistant with the provided instructions
        assistant = openai_client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": instructions}]
        )

        assistant_id = assistant['id']  # Get the assistant ID

        # Save the assistant ID for future use
        with open(assistant_file_path, 'w') as file:
            json.dump({'assistant_id': assistant_id}, file)
            logging.info("Created a new assistant and saved the ID: %s", assistant_id)

        return assistant_id

    except Exception as e:
        logging.error("Failed to create assistant: %s", e)
        return None

