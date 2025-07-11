import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import tempfile
import uuid
from datetime import datetime
import threading

# Import API modules
from api.formguias import formguias_bp
from api.formclientes import formclientes_bp  
from api.formfornecedores import formfornecedores_bp

# Configure logging for Vercel
logging.basicConfig(level=logging.INFO)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback-secret-key-for-development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# In-memory storage for forms (since Vercel is read-only)
FORMS_STORAGE = {}
CONFIG_STORAGE = {
    "guias": {
        "board_a": "",
        "board_b": "",
        "link_column": "",
        "questions": []
    },
    "clientes": {
        "board_a": "",
        "board_b": "",
        "link_column": "",
        "questions": []
    },
    "fornecedores": {
        "board_a": "",
        "board_b": "",
        "link_column": "",
        "questions": []
    }
}

def load_config():
    """Load configuration from file or environment"""
    try:
        if os.path.exists('setup/config.json'):
            with open('setup/config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass

    # Try to load from environment variable for Vercel
    config_env = os.environ.get('FORMS_CONFIG')
    if config_env:
        try:
            return json.loads(config_env)
        except:
            pass

    return CONFIG_STORAGE

def save_config(config):
    """Save configuration (in development only)"""
    try:
        if not os.environ.get('VERCEL'):  # Only save in development
            os.makedirs('setup', exist_ok=True)
            with open('setup/config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        else:
            # In production, log that config should be set via environment
            app.logger.info("Production environment: Configuration should be set via FORMS_CONFIG environment variable")
    except Exception as e:
        app.logger.error(f"Error saving configuration: {str(e)}")

# Register blueprints
app.register_blueprint(formguias_bp)
app.register_blueprint(formclientes_bp)
app.register_blueprint(formfornecedores_bp)

@app.route('/')
def index():
    """Home page with navigation to admin interface"""
    return render_template('base.html')

@app.route('/admin')
def admin():
    """Admin interface for managing form configurations"""
    config = load_config()
    return render_template('admin.html', config=config)

@app.route('/api/config', methods=['GET', 'POST'])
def config_api():
    """API endpoint for managing configurations"""
    if request.method == 'GET':
        config = load_config()
        return jsonify(config)

    elif request.method == 'POST':
        try:
            config = request.get_json()
            save_config(config)
            return jsonify({"message": "Configuration saved successfully"})
        except Exception as e:
            app.logger.error(f"Error saving configuration: {str(e)}")
            return jsonify({"error": "Failed to save configuration"}), 500

@app.route('/api/forms', methods=['GET'])
def list_forms():
    """API endpoint to list all forms"""
    try:
        forms = []
        for form_id, form_data in FORMS_STORAGE.items():
            forms.append({
                'id': form_id,
                'type': form_data.get('type', 'unknown'),
                'created_at': form_data.get('created_at', ''),
                'header_data': form_data.get('header_data', {})
            })
        return jsonify(forms)
    except Exception as e:
        app.logger.error(f"Error listing forms: {str(e)}")
        return jsonify({"error": "Failed to list forms"}), 500

@app.route('/api/forms/<form_id>', methods=['DELETE'])
def delete_form(form_id):
    """API endpoint to delete a form"""
    try:
        if form_id in FORMS_STORAGE:
            del FORMS_STORAGE[form_id]
            return jsonify({"message": "Form deleted successfully"})
        else:
            return jsonify({"error": "Form not found"}), 404
    except Exception as e:
        app.logger.error(f"Error deleting form {form_id}: {str(e)}")
        return jsonify({"error": "Failed to delete form"}), 500

@app.route('/form/<form_id>')
def display_form(form_id):
    """Display generated form"""
    try:
        form_data = FORMS_STORAGE.get(form_id)
        if not form_data:
            return "Form not found", 404

        return render_template('form_template.html', form_data=form_data, form_id=form_id)
    except Exception as e:
        app.logger.error(f"Error displaying form {form_id}: {str(e)}")
        return "Form not found", 404

def process_form_background(form_id, submission_data, stored_form_data):
    """Background processing function for form submission"""
    try:
        app.logger.info(f"Background processing started for form {form_id}")

        # Load configuration
        config = load_config()
        form_type = stored_form_data.get('type')
        form_config = config.get(form_type, {})

        app.logger.info(f"Processing - Form type: {form_type}, Config: {form_config}")

        if form_config.get('board_b'):
            from utils.monday_api import MondayAPI
            monday_api = MondayAPI()

            # Get the item ID from webhook data
            webhook_data = stored_form_data.get('webhook_data', {})
            item_id = webhook_data.get('event', {}).get('pulseId')
            board_b = form_config['board_b']

            app.logger.info(f"Processing - Saving responses to Board B: {board_b}, Item ID: {item_id}")

            if item_id and board_b:
                # Always create a new item in Board B for each form response
                header_data = stored_form_data.get('header_data', {})
                item_name = header_data.get('Viagem') or webhook_data.get('event', {}).get('pulseName', 'Resposta do Formulário')
                app.logger.info(f"Processing - Creating new item in Board B: {item_name}")

                create_result = monday_api.create_item(board_b, item_name)
                if create_result and create_result.get('create_item', {}).get('id'):
                    new_item_id = create_result['create_item']['id']
                    app.logger.info(f"Processing - Created new item with ID: {new_item_id}")

                    # Prepare all updates in a batch
                    updates_to_process = []

                    # Add header data to destination board
                    header_data = stored_form_data.get('header_data', {})

                    # Add other header fields to specific columns
                    if header_data.get('Destino'):
                        updates_to_process.append({
                            'column_id': 'text_mkrb17ct',
                            'value': header_data['Destino'],
                            'description': f"Destino from header data"
                        })

                    if header_data.get('Data'):
                        updates_to_process.append({
                            'column_id': 'text_mksq2j87',
                            'value': header_data['Data'],
                            'description': f"Data from header data"
                        })

                    if header_data.get('Cliente'):
                        updates_to_process.append({
                            'column_id': 'text_mkrjdnry',
                            'value': header_data['Cliente'],
                            'description': f"Cliente from header data"
                        })

                    # Debug submission data
                    app.logger.info(f"Form submission data keys: {list(submission_data.keys())}")
                    app.logger.info(f"Form submission data: {submission_data}")

                    # Collect all updates from questions
                    for question in stored_form_data.get('questions', []):
                        question_id = question.get('id')
                        destination_column = question.get('destination_column')
                        question_destination_column = question.get('question_destination_column')
                        question_type = question.get('type')
                        question_text = question.get('text', '')[:50] + "..." if len(question.get('text', '')) > 50 else question.get('text', '')

                        app.logger.info(f"Processing question {question_id}: type={question_type}")
                        app.logger.info(f"  Text: {question_text}")
                        app.logger.info(f"  Destination column: '{destination_column}'")
                        app.logger.info(f"  Question destination column: '{question_destination_column}'")

                        # Skip divider questions
                        if question_type == 'divider':
                            app.logger.info(f"Skipping divider question {question_id}")
                            continue

                        # For Monday column questions, save both the response and the column value
                        if question_type == 'monday_column':
                            # First, save the user's response (rating)
                            response_value = submission_data.get(question_id)
                            if response_value is not None and str(response_value).strip():
                                response_str = str(response_value).strip()
                                
                                # Convert English to Portuguese
                                if response_str.lower() == "yes":
                                    response_str = "Sim"
                                elif response_str.lower() == "no":
                                    response_str = "Não"

                                if destination_column and destination_column.strip():
                                    updates_to_process.append({
                                        'column_id': destination_column.strip(),
                                        'value': response_str,
                                        'description': f"Monday column question {question_id} response: {response_str}"
                                    })
                                    app.logger.info(f"✅ Added Monday column response: {question_id} -> {destination_column} = '{response_str}'")

                            # Second, save the column value (question text) if configured
                            if question_destination_column and question_destination_column.strip():
                                column_value = question.get('column_value', '')
                                if column_value and column_value not in ['', 'Dados não encontrados', 'Erro ao carregar dados', 'Dados não disponíveis', 'Configuração incompleta']:
                                    updates_to_process.append({
                                        'column_id': question_destination_column.strip(),
                                        'value': column_value,
                                        'description': f"Monday column question {question_id} text: {column_value}"
                                    })
                                    app.logger.info(f"✅ Added Monday column text: {question_id} -> {question_destination_column} = '{column_value}'")

                        else:
                            # For regular questions (yesno, rating, text, longtext, dropdown)
                            response_value = submission_data.get(question_id)
                            
                            if response_value is not None:
                                response_str = str(response_value).strip()
                                
                                if response_str:
                                    # Convert English to Portuguese
                                    if response_str.lower() == "yes":
                                        response_str = "Sim"
                                    elif response_str.lower() == "no":
                                        response_str = "Não"

                                    if destination_column and destination_column.strip():
                                        updates_to_process.append({
                                            'column_id': destination_column.strip(),
                                            'value': response_str,
                                            'description': f"Question {question_id} ({question_type}) response: {question_text}"
                                        })
                                        app.logger.info(f"✅ Added regular question: {question_id} -> {destination_column} = '{response_str}'")
                                    else:
                                        app.logger.warning(f"⚠️  Question {question_id} has no destination column configured")
                                else:
                                    app.logger.warning(f"Question {question_id} has empty response value")
                            else:
                                app.logger.warning(f"❌ Question {question_id} was not answered in form submission")
                                app.logger.info(f"Available form fields: {list(submission_data.keys())}")

                    # Process all updates
                    app.logger.info(f"Processing - Processing {len(updates_to_process)} column updates")
                    successful_updates = 0
                    failed_updates = 0

                    for update in updates_to_process:
                        try:
                            app.logger.info(f"Processing - {update['description']}: column={update['column_id']}, value={update['value']}")

                            # Skip empty values
                            if not update['value'] or str(update['value']).strip() == '':
                                app.logger.warning(f"Skipping empty value for column {update['column_id']}")
                                continue

                            monday_api.update_item_column(
                                board_id=board_b,
                                item_id=new_item_id,
                                column_id=update['column_id'],
                                value=update['value']
                            )
                            app.logger.info(f"Processing - Successfully updated column {update['column_id']}")
                            successful_updates += 1
                        except Exception as e:
                            app.logger.error(f"Processing - Failed to update column {update['column_id']}: {str(e)}")
                            failed_updates += 1

                    app.logger.info(f"Processing - Completed: {successful_updates} successful, {failed_updates} failed updates")
                    app.logger.info(f"Processing - Completed all updates for form {form_id}")
                else:
                    app.logger.error("Processing - Failed to create item in Board B")
            else:
                app.logger.error("Processing - Missing item_id or board_b configuration")
        else:
            app.logger.warning(f"Processing - No board_b configured for form type: {form_type}")

    except Exception as e:
        app.logger.error(f"Background processing error for form {form_id}: {str(e)}")


@app.route('/submit_form/<form_id>', methods=['POST'])
def submit_form(form_id):
    """Handle form submission with background processing"""
    try:
        # Get form data
        stored_form_data = FORMS_STORAGE.get(form_id)
        if not stored_form_data:
            return "Form not found", 404

        # Process form submission
        submission_data = request.form.to_dict()
        app.logger.info(f"=== FORM SUBMISSION START ===")
        app.logger.info(f"Form {form_id} submitted with {len(submission_data)} fields")
        app.logger.info(f"Form type: {stored_form_data.get('type')}")
        app.logger.info(f"Header data: {stored_form_data.get('header_data')}")
        app.logger.info(f"Total questions in form: {len(stored_form_data.get('questions', []))}")

        # Log all submission data
        app.logger.info(f"Submission data:")
        for key, value in submission_data.items():
            app.logger.info(f"  {key}: '{value}'")

        # Log all questions and their destination columns
        app.logger.info(f"Questions with destination columns:")
        for i, question in enumerate(stored_form_data.get('questions', [])):
            if question.get('type') != 'divider':
                app.logger.info(f"  Q{i+1}: ID={question.get('id')}, Type={question.get('type')}, DestCol='{question.get('destination_column', '')}', Text='{question.get('text', '')[:50]}...'")

        # Start background processing
        background_thread = threading.Thread(
            target=process_form_background,
            args=(form_id, submission_data, stored_form_data)
        )
        background_thread.daemon = True
        background_thread.start()

        app.logger.info(f"Form {form_id} submitted successfully, processing in background")
        app.logger.info(f"=== FORM SUBMISSION END ===")

        # Return success page immediately
        return render_template('success.html')

    except Exception as e:
        app.logger.error(f"Error submitting form {form_id}: {str(e)}")
        return "Error submitting form", 500

@app.errorhandler(404)
def not_found(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return "Internal server error", 500

# Store form data function for use by API modules
def store_form_data(form_id, form_data):
    """Store form data in memory"""
    FORMS_STORAGE[form_id] = form_data
    return True

def get_form_data(form_id):
    """Get form data from memory"""
    return FORMS_STORAGE.get(form_id)

# Make these functions and storage available to other modules
app.store_form_data = store_form_data
app.get_form_data = get_form_data
app.load_config = load_config
app.FORMS_STORAGE = FORMS_STORAGE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
