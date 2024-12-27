import json
import os
import openai
import logging

# Set up logging to track the assistant's behavior
logging.basicConfig(level=logging.INFO, filename='assistant_debug.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')

def create_assistant(client):
    # Ensure client has correct headers
    if "OpenAI-Beta" not in client.default_headers:
        client.default_headers.update({
            "OpenAI-Beta": "assistants=v2"
        })
    
    assistant_file_path = 'assistant.json'

    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data['assistant_id']
            logging.info("Loaded existing assistant ID: %s", assistant_id)
    else:
        try:
            # Upload the knowledge document
            file = client.files.create(
                file=open("knowledge.docx", "rb"),
                purpose='assistants'
            )
            logging.info("Knowledge file uploaded successfully with ID: %s", file.id)

            # Attempt vector store creation
            try:
                vector_store = client.beta.vector_stores.create()
                client.beta.vector_stores.add_files(
                    vector_store_id=vector_store.id,
                    file_ids=[file.id]
                )
                logging.info("Vector store created with ID: %s", vector_store.id)
            except Exception as e:
                logging.error(f"Vector store creation failed: {e}")
                vector_store = None  # Fallback for assistant creation without vector store

            # Create the assistant
            assistant = client.beta.assistants.create(
                name="BlueThistle AI Customer Support Assistant",
                instructions="""
You are a knowledgeable customer service assistant for BlueThistle AI. Your primary job is to provide users with comprehensive, accurate, and informative responses to their questions, particularly regarding pricing, chatbot packages, services, contact information, and company details. Your main goal is to get users to buy our services.
""",
                model="gpt-3.5-turbo",
                tools=[{"type": "code_interpreter"}, {"type": "file_search"}] if vector_store else [{"type": "code_interpreter"}],
                tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}} if vector_store else None
            )

            # Save the assistant ID for future use
            with open(assistant_file_path, 'w') as file:
                json.dump({'assistant_id': assistant.id}, file)
                logging.info("Created a new assistant and saved the ID: %s", assistant.id)

            assistant_id = assistant.id
        except Exception as e:
            logging.error("Failed to create assistant or upload knowledge file: %s", str(e))
            raise e

    return assistant_id
