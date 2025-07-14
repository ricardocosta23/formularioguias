import uuid
import json
import os
from datetime import datetime
from flask import current_app
import logging
from utils.monday_api import MondayAPI

class FormGenerator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.forms_dir = 'Forms'
        # Ensure Forms directory exists
        os.makedirs(self.forms_dir, exist_ok=True)

    def generate_form(self, form_data):
        """Generate a new form and store it persistently"""
        form_id = str(uuid.uuid4())

        # Process questions to ensure conditional questions are properly formatted
        processed_questions = self._process_questions(form_data.get("questions", []))

        # Create complete form data structure
        complete_form_data = {
            "id": form_id,
            "type": form_data.get("type"),
            "title": form_data.get("title"),
            "subtitle": form_data.get("subtitle"),
            "questions": processed_questions,
            "webhook_data": form_data.get("webhook_data", {}),
            "header_data": form_data.get("header_data", {}),
            "created_at": datetime.now().isoformat()
        }

        # Save to file
        self._save_form_to_file(form_id, complete_form_data)

        # Also store in memory for immediate access
        if hasattr(current_app, 'store_form_data'):
            current_app.store_form_data(form_id, complete_form_data)

        self.logger.info(f"Generated form {form_id} for type {form_data.get('type')}")
        return form_id

    def _process_questions(self, questions):
        """Process questions to ensure conditional questions are properly formatted"""
        processed_questions = []

        for question in questions:
            # Copy the question
            processed_question = question.copy()

            # Handle conditional questions
            if 'conditional' in question and question['conditional']:
                # Ensure the conditional structure is correct
                conditional = question['conditional']
                if conditional.get('depends_on'):
                    processed_question['conditional'] = {
                        'depends_on': conditional['depends_on'],
                        'show_if': conditional.get('show_if', '')  # Allow empty show_if
                    }
                    processed_question['is_conditional'] = True
                else:
                    # Remove invalid conditional
                    processed_question.pop('conditional', None)
                    processed_question['is_conditional'] = False
            else:
                processed_question['is_conditional'] = False

            processed_questions.append(processed_question)

        return processed_questions

    def _save_form_to_file(self, form_id, form_data):
        """Save form data to a JSON file"""
        try:
            file_path = os.path.join(self.forms_dir, f"{form_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(form_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Form {form_id} saved to file")
        except Exception as e:
            self.logger.error(f"Error saving form to file: {str(e)}")

    def _load_form_from_file(self, form_id):
        """Load form data from a JSON file"""
        try:
            file_path = os.path.join(self.forms_dir, f"{form_id}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading form from file: {str(e)}")
        return None

    def get_form_data(self, form_id):
        """Get form data from memory or file"""
        # First try memory
        if hasattr(current_app, 'get_form_data'):
            form_data = current_app.get_form_data(form_id)
            if form_data:
                return form_data

        # If not in memory, try loading from file
        form_data = self._load_form_from_file(form_id)
        if form_data and hasattr(current_app, 'store_form_data'):
            # Store back in memory for future access
            current_app.store_form_data(form_id, form_data)

        return form_data

    def list_all_forms(self):
        """List all forms from both memory and files"""
        forms = []
        form_ids = set()

        # Get forms from memory
        if hasattr(current_app, 'FORMS_STORAGE'):
            for form_id, form_data in current_app.FORMS_STORAGE.items():
                forms.append({
                    'id': form_id,
                    'type': form_data.get('type', 'unknown'),
                    'created_at': form_data.get('created_at', ''),
                    'header_data': form_data.get('header_data', {})
                })
                form_ids.add(form_id)

        # Get forms from files that aren't already in memory
        try:
            if os.path.exists(self.forms_dir):
                for filename in os.listdir(self.forms_dir):
                    if filename.endswith('.json'):
                        form_id = filename[:-5]  # Remove .json extension
                        if form_id not in form_ids:
                            form_data = self._load_form_from_file(form_id)
                            if form_data:
                                forms.append({
                                    'id': form_id,
                                    'type': form_data.get('type', 'unknown'),
                                    'created_at': form_data.get('created_at', ''),
                                    'header_data': form_data.get('header_data', {})
                                })
        except Exception as e:
            self.logger.error(f"Error listing forms from files: {str(e)}")

        return forms

    def delete_form(self, form_id):
        """Delete a form from memory and file"""
        deleted = False

        # Delete from memory
        if hasattr(current_app, 'FORMS_STORAGE') and form_id in current_app.FORMS_STORAGE:
            del current_app.FORMS_STORAGE[form_id]
            deleted = True

        # Delete from file
        try:
            file_path = os.path.join(self.forms_dir, f"{form_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted = True
                self.logger.info(f"Form file {form_id}.json deleted")
        except Exception as e:
            self.logger.error(f"Error deleting form file: {str(e)}")

        return deleted

    def process_form_submission(self, form_id, submission_data):
        """Process form submission and save to Monday.com"""
        try:
            # Get form data
            form_data = self.get_form_data(form_id)
            if not form_data:
                logging.error(f"Form {form_id} not found")
                return False

            # Load configuration
            with open('setup/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

            form_type = form_data.get('type')
            if not form_type or form_type not in config:
                logging.error(f"Form type {form_type} not found in config")
                return False

            form_config = config[form_type]

            # Get destination board (board_b)
            destination_board = form_config.get('board_b')
            if not destination_board:
                logging.error(f"No destination board configured for {form_type}")
                return False

            # Initialize Monday API
            monday_api = MondayAPI()

            # Prepare column values for Monday.com
            column_values = {}

            # Process each question and its submission
            for question in form_data.get('questions', []):
                question_id = question.get('id')
                destination_column = question.get('destination_column')
                question_type = question.get('type', '')

                # Skip questions without ID
                if not question_id:
                    continue

                # Handle Monday column questions (Coluna do Monday)
                if question_type == 'monday_column':
                    # Handle text destination column (for the fetched text value)
                    text_destination = question.get('text_destination_column') or question.get('destination_column')
                    column_value = question.get('column_value', '')
                    
                    if column_value and text_destination:
                        column_values[text_destination] = str(column_value)
                        logging.info(f"Monday column question {question_id}: saving text '{column_value}' to text destination '{text_destination}'")
                    
                    # Handle rating destination column (for user's numeric rating)
                    rating_destination = question.get('rating_destination_column')
                    submitted_rating = submission_data.get(question_id, "")
                    
                    if submitted_rating and rating_destination:
                        try:
                            rating_value = int(submitted_rating)
                            if 1 <= rating_value <= 10:
                                column_values[rating_destination] = rating_value
                                logging.info(f"Monday column question {question_id}: saving rating {rating_value} to rating destination '{rating_destination}'")
                            else:
                                logging.warning(f"Rating value {rating_value} outside valid range (1-10) for question {question_id}")
                        except ValueError:
                            logging.warning(f"Invalid rating value '{submitted_rating}' for question {question_id}")
                    
                    # Log if missing destination columns
                    if not text_destination and not rating_destination:
                        logging.warning(f"Monday column question {question_id} has no destination columns configured")
                else:
                    # For other question types, use submitted value
                    submitted_value = submission_data.get(question_id, "")

                    if submitted_value and destination_column:
                        # Format value based on question type
                        if question_type == 'rating':
                            # Handle rating questions (1-5 scale)
                            try:
                                rating_value = int(submitted_value)
                                column_values[destination_column] = str(rating_value)
                            except ValueError:
                                column_values[destination_column] = submitted_value
                        elif question_type == 'yesno':
                            # Handle yes/no questions
                            column_values[destination_column] = submitted_value
                        else:
                            # Handle text, longtext, dropdown questions
                            column_values[destination_column] = str(submitted_value)
                    elif submitted_value and not destination_column:
                        logging.warning(f"Question {question_id} ({question_type}) has submitted value but no destination_column")

            # Create item name from header data
            header_data = form_data.get('header_data', {})
            item_name = f"Avaliação - {header_data.get('Viagem', 'Formulário')}"

            logging.info(f"Creating Monday.com item with values: {column_values}")

            # Create item with all column values at once
            if column_values:
                result = monday_api.create_item_with_values(
                    board_id=destination_board,
                    item_name=item_name,
                    column_values=column_values
                )

                if result and result.get('data', {}).get('create_item'):
                    item_id = result['data']['create_item']['id']
                    logging.info(f"Successfully created Monday.com item {item_id} with values")
                    return True
                else:
                    logging.error(f"Failed to create Monday.com item: {result}")
                    return False
            else:
                # Create item without values if no columns to update
                result = monday_api.create_item(destination_board, item_name)
                if result:
                    logging.info(f"Created Monday.com item without column values")
                    return True
                else:
                    logging.error("Failed to create Monday.com item")
                    return False

        except Exception as e:
            logging.error(f"Error processing form submission: {str(e)}")
            return False
