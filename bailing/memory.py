import json
import os
import glob
import logging
import re

# Update the import statement
from langchain_ollama import ChatOllama as Ollama

from bailing.utils import read_json_file, write_json_file

logger = logging.getLogger(__name__)

memory_prompt_template = """
You are a dialogue recorder responsible for extracting and recording the dialogue information between the user and the assistant. Please generate the latest and most complete dialogue summary based on the following content, highlighting the useful information related to the user, and ensure that the summary does not exceed 800 characters. The historical dialogue summary contains the previously recorded dialogue summaries, involving the user's needs, preferences, and key issues. The most recent dialogue history is the latest dialogue record, containing the specific communication content between the user and the assistant.

# Historical Dialogue Summary
${dialogue_abstract}

# Most Recent Dialogue History
${dialogue_history}

# Output Requirements
- Synthesize the historical dialogue summary and the most recent dialogue history to form a structured dialogue summary, taking into account the user's dialogue style.
- Ensure that the extracted information is of practical value and helps understand the user's needs and background.
- The summary should be clear, concise, and easy for subsequent reference and analysis.
- Output the dialogue summary, the user's dialogue preferences, the user's dialogue style, and the dialogue strategy to be adopted next time.
"""

class Memory:
    def __init__(self, config):
        file_path = config.get("dialogue_history_path")
        self.memory_file = config.get("memory_file")
        if os.path.isfile(self.memory_file):
            self.memory = read_json_file(self.memory_file)
        else:
            self.memory = {"history_memory_file": [], "memory": ""}

        self.model_name = config.get("model_name")
        self.base_url = config.get("url", "http://localhost:11434")  # Default Ollama service address
        # Use the new Ollama class
        self.client = Ollama(
            model=self.model_name,
            base_url=self.base_url
        )

        self.read_dialogues_in_order(file_path)

        write_json_file(self.memory_file, self.memory)

    def get_memory(self):
        return self.memory["memory"]

    def update_memory(self, file_name, dialogue_history):
        memory_prompt = memory_prompt_template.replace("${dialogue_abstract}", self.memory["memory"])\
            .replace("${dialogue_history}", dialogue_history).strip()
        new_memory = None
        try:
            # Adjust the invocation method to fit Ollama
            responses = self.client.invoke([{
                "role": "user",
                "content": memory_prompt
            }])
            new_memory = responses.content
        except Exception as e:
            logger.error(f"Error in response generation: {e}")
        if new_memory is not None:
            self.memory["history_memory_file"].append(file_name)
            self.memory["memory"] = new_memory

    @staticmethod
    def extract_time_from_filename(filename):
        """Extract time information from the file name."""
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', filename)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def read_dialogue_file(file_path):
        """Read the JSON dialogue file and return the dialogue list."""
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                dialogues = json.load(file)
                return dialogues
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON: {e}")
                return []

    @staticmethod
    def dialogues_history(dialogues):
        """Print the dialogue content."""
        dialogues_str = list()
        for dialogue in dialogues:
            role = dialogue.get('role', 'Unknown Role')
            content = dialogue.get('content', '')
            logger.debug(f"{role}: {content}")
            dialogues_str.append(role + ": " + content)
        return "\n".join(dialogues_str)

    def read_dialogues_in_order(self, directory):
        """Read all dialogue files in the specified directory and sort them by time."""
        # Get the paths of all files that match the naming rule
        pattern = os.path.join(directory, 'dialogue-*-*-*.json')
        files = glob.glob(pattern)

        # Sort by time
        # files.sort(key=lambda x: x.split('-')[1:4])  # Sort according to the time part
        files.sort(key=lambda x: self.extract_time_from_filename(os.path.basename(x)))

        # Read and print all dialogues
        for file_path in files:
            if file_path in self.memory["history_memory_file"]:
                logger.info(f"{file_path} dialogue history has already formed memory")
                continue
            logger.info(f"Processing: {file_path}")
            dialogues = self.read_dialogue_file(file_path)
            dialogue_history = self.dialogues_history(dialogues)
            self.update_memory(file_path, dialogue_history)
