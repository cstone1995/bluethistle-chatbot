import json
import os
import openai
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, filename='assistant_debug.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

def create_assistant(client):
    """Create or retrieve an assistant ID linked to a knowledge file."""
    assistant_file_path = 'assistant.json'

    # Check if an existing assistant ID is saved
    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data.get('assistant_id')
            logging.info("Loaded existing assistant ID: %s", assistant_id)
            return assistant_id

    try:
        # Upload the knowledge file
        knowledge_file = client.files.create(
            file=open("knowledge.docx", "rb"),
            purpose="assistants"
        )
        logging.info("Knowledge file uploaded with ID: %s", knowledge_file["id"])

        # Create a vector store for the knowledge file
        vector_store = client.beta.vector_stores.create()
        client.beta.vector_stores.add_files(
            vector_store_id=vector_store.id,
            file_ids=[knowledge_file["id"]]
        )
        logging.info("Vector store created and file associated with vector store ID: %s", vector_store.id)

        # Modular instructions for the assistant
        instructions = """
        You are a customer service assistant for Bluethistle AI. Always use the provided knowledge file for answering questions.
        Your responsibilities include:
        - Responding to queries about services, pricing, contact information, and other details provided in the file.
        - Avoiding speculation or fabrication of answers; always rely on the uploaded knowledge file.
        """

        # Create the assistant with the vector store
        assistant = client.beta.assistants.create(
            name="Bluethistle AI Assistant",
            instructions=instructions,
            model="gpt-3.5-turbo",
            tools=[
                {"type": "file_search"}
            ],
            tool_resources={
                "file_search": {"vector_store_ids": [vector_store.id]}
            }
        )
        logging.info("Assistant created with ID: %s", assistant["id"])

        # Save the assistant ID
        with open(assistant_file_path, 'w') as file:
            json.dump({"assistant_id": assistant["id"]}, file)

        return assistant["id"]
    except Exception as e:
        logging.error("Failed to create assistant: %s", e)
        raise e

