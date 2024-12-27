import json
import os
import openai
import logging

# Set up logging to track the assistant's behavior
logging.basicConfig(level=logging.INFO, filename='assistant_debug.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')

def create_assistant(client):
    # Ensure client has correct headers for v2 API
    if "OpenAI-Beta" not in client.default_headers:
        client.default_headers.update({
            "OpenAI-Beta": "assistants=v2"
        })
    
    assistant_file_path = 'assistant.json'

    # Check if an existing assistant ID is saved
    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data['assistant_id']
            logging.info("Loaded existing assistant ID: %s", assistant_id)
            return assistant_id

    try:
        # Upload the knowledge file
        file = client.files.create(
            file=open("knowledge.docx", "rb"),
            purpose='assistants'
        )
        logging.info("Knowledge file uploaded successfully with ID: %s", file.id)

        # Modularized instructions
        general_info = "You are a knowledgeable customer service assistant for BlueThistle AI..."
        key_responsibilities = "### Key Responsibilities...\n1. Use Document for Retrieval..."
        communication_guidelines = "### Communication Guidelines...\n1. Avoid repetitive greetings..."
        additional_guidelines = "### Additional Guidelines...\n1. Website Links..."
        important_guidelines = "### Important...\nDo not mention the document directly..."

        # Create vector store for file search
        vector_store = client.beta.vector_stores.create()
        client.beta.vector_stores.add_files(
            vector_store_id=vector_store.id,
            file_ids=[file.id]
        )

        # Create the assistant
        assistant = client.beta.assistants.create(
            name="BlueThistle AI Customer Support Assistant",
            instructions=f"{general_info}{key_responsibilities}{communication_guidelines}{additional_guidelines}{important_guidelines}",
            model="gpt-4-turbo",
            tools=[
                {"type": "code_interpreter"},
                {"type": "file_search"}
            ],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id]
                }
            }
        )

        # Save the assistant ID for future use
        with open(assistant_file_path, 'w') as file:
            json.dump({'assistant_id': assistant.id}, file)
            logging.info("Created a new assistant and saved the ID: %s", assistant.id)

        return assistant.id
    except Exception as e:
        logging.error("Failed to create assistant: %s", str(e))
        raise e
