import json
import logging
import docx  # For parsing .docx files

# Logging configuration
logging.basicConfig(level=logging.DEBUG)

def extract_knowledge_from_docx(file_path):
    """Extract text content from the provided .docx file."""
    try:
        doc = docx.Document(file_path)
        content = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():  # Ignore empty paragraphs
                content.append(paragraph.text.strip())
        logging.debug("Extracted content from knowledge.docx successfully.")
        return "\n".join(content)
    except Exception as e:
        logging.error(f"Failed to extract knowledge from docx: {e}")
        raise

def generate_system_instructions(content):
    """Generate dynamic system instructions based on the extracted content."""
    return (
        "You are a knowledgeable customer service assistant for BlueThistle AI. "
        "Your job is to provide accurate, concise, and helpful responses based on the following details:\n\n"
        f"{content}\n\n"
        "Ensure all responses are brief, helpful, and focus on providing actionable insights. Avoid fabricating answers."
    )
