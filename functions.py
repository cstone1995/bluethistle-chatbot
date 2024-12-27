import json
import os
import openai
import logging

# Set up logging to track the assistant's behavior
logging.basicConfig(level=logging.INFO, filename='assistant_debug.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')

def create_assistant():
    # Check if the environment variable for the OpenAI API key is set
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        raise ValueError("The 'OPENAI_API_KEY' environment variable is not set.")
    
    openai.api_key = OPENAI_API_KEY
    
    assistant_file_path = 'assistant.json'

    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data['assistant_id']
            logging.info("Loaded existing assistant ID: %s", assistant_id)
    else:
        try:
            # Upload the file to create an assistant
            file = openai.File.create(
                file=open("knowledge.docx", "rb"),
                purpose='answers'
            )
            logging.info("Knowledge file uploaded successfully with ID: %s", file.id)

            # Modularized instructions for the assistant
            general_info = """
You are a knowledgeable customer service assistant for BlueThistle AI. Your primary job is to provide users with comprehensive, accurate, and informative responses to their questions, particularly regarding pricing, chatbot packages, services, contact information, and company details your main goal is to get users to buy our services.

You have access to a document that contains detailed information about BlueThistle AI's offerings, including service packages, pricing, office hours, social media links, policies, and more. Always prioritize using the document's content to provide concise, accurate, and helpful responses. Keep answers very brief, aiming for a maximum of 2 sentences unless the user explicitly asks for more details.
"""

            # Create the assistant with modular instructions
            assistant = openai.Answer.create(
                name="BlueThistle AI Customer Support Assistant",
                instructions=general_info,
                file_ids=[file.id],
                search_model="davinci",
                model="curie",
                max_tokens=1000,
                stop=["\n", "User:"],
            )

            # Save the assistant ID for future use
            with open(assistant_file_path, 'w') as file:
                json.dump({'assistant_id': assistant['id']}, file)
                logging.info("Created a new assistant and saved the ID: %s", assistant['id'])

            assistant_id = assistant['id']
        except Exception as e:
            logging.error("Failed to create assistant or upload knowledge file: %s", str(e))
            raise e

    return assistant_id

