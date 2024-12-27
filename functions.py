import json
import os
import openai
import logging

# Set up logging to track the assistant's behavior
logging.basicConfig(level=logging.INFO, filename='assistant_debug.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')

def create_assistant(client):
    """Create or retrieve an assistant with a knowledge file and instructions."""
    assistant_file_path = 'assistant.json'

    # Check if an existing assistant ID is saved
    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data.get('assistant_id')
            logging.info("Loaded existing assistant ID: %s", assistant_id)
            return assistant_id

    try:
        # Upload the knowledge file to the vector store
        vector_store = client.beta.vector_stores.create()
        file = client.files.create(
            file=open("knowledge.docx", "rb"),
            purpose="assistants"
        )
        logging.info("Knowledge file uploaded successfully with ID: %s", file.id)

        client.beta.vector_stores.add_files(
            vector_store_id=vector_store.id,
            file_ids=[file.id]
        )

        # Comprehensive instructions for the assistant
        instructions = """
You are a knowledgeable customer service assistant for Bluethistle AI. Your role is to provide users with accurate, concise, and informative responses to their questions. Always use the knowledge file for retrieval when relevant.

### Key Responsibilities:
1. Provide accurate responses about:
   - Services and Pricing (e.g., Basic AI Package: £500 setup, £750 monthly).
   - Contact details (Email: team@bluethistleai.co.uk, Phone: +44 7305712251).
   - Social media links.
2. Guide users effectively, e.g., "Visit our Get Started page for more details: https://bluethistleai.co.uk/get-started/."

### Communication Guidelines:
- Always use concise answers (2 sentences max) unless asked for more details.
- If information is not in the knowledge file, say: "I’m currently unable to find specific details, but here’s what I know."
"""

        # Create the assistant with vector store for knowledge retrieval
        assistant = client.beta.assistants.create(
            name="Bluethistle AI Assistant",
            instructions=instructions,
            model="gpt-3.5-turbo",
            tools=[
                {"type": "file_search"},
                {"type": "code_interpreter"}
            ],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id]
                }
            }
        )

        assistant_id = assistant["id"]

        # Save the assistant ID for future use
        with open(assistant_file_path, 'w') as file:
            json.dump({'assistant_id': assistant_id}, file)
            logging.info("Created a new assistant and saved the ID: %s", assistant_id)

        return assistant_id

    except Exception as e:
        logging.error("Failed to create assistant or upload knowledge file: %s", e)
        raise e

