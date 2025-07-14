
import uuid
import json
import os
from datetime import datetime
from flask import current_app
import logging

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
                if conditional.get('depends_on') and conditional.get('show_if'):
                    processed_question['conditional'] = {
                        'depends_on': conditional['depends_on'],
                        'show_if': conditional['show_if']
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
