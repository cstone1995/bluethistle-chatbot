import json
import os
import logging

# Set up logging to track the assistant's behavior
logging.basicConfig(level=logging.INFO, filename='assistant_debug.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')

def create_assistant(openai_client):
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
        You are a knowledgeable customer service assistant for BlueThistle AI. Your primary job is to provide users with comprehensive, accurate, and informative responses to their questions, particularly regarding pricing, chatbot packages, services, contact information, and company details. Your main goal is to get users to buy our services.
        """

        # Create the assistant with the provided instructions
        response = openai_client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": instructions}]
        )

        assistant_id = response['id']  # Get the assistant ID

        # Save the assistant ID for future use
        with open(assistant_file_path, 'w') as file:
            json.dump({'assistant_id': assistant_id}, file)
            logging.info("Created a new assistant and saved the ID: %s", assistant_id)

        return assistant_id

    except Exception as e:
        logging.error("Failed to create assistant: %s", e)
        raise
