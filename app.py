import os
import logging
import time
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

# Create Flask app.
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

# Global configuration cache
config_cache = None
config_last_modified = None

def load_config():
    """Load configuration from JSON file with caching"""
    global config_cache, config_last_modified

    config_path = os.path.join(os.path.dirname(__file__), 'setup', 'config.json')

    try:
        # Check if file has been modified
        current_modified = os.path.getmtime(config_path)

        if config_cache is None or config_last_modified != current_modified:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_cache = json.load(f)
                config_last_modified = current_modified
                app.logger.info("Configuration loaded/reloaded from file")

        return config_cache

    except FileNotFoundError:
        app.logger.warning("Config file not found, using default configuration")
        return {}
    except json.JSONDecodeError as e:
        app.logger.error(f"Error parsing config file: {str(e)}")
        return {}

def save_config(config):
    """Save configuration (in development only)"""
    global config_cache, config_last_modified
    try:
        if not os.environ.get('VERCEL'):  # Only save in development
            os.makedirs('setup', exist_ok=True)
            with open('setup/config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            # Update cache after successful save
            config_cache = config.copy()
            config_last_modified = time.time()
        else:
            # In production, update the cache but warn about persistence
            config_cache = config.copy()
            config_last_modified = time.time()
            app.logger.warning("Production environment: Configuration saved to memory only. Changes will not persist across deployments.")
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
        try:
            # Load configuration directly from config.json file
            config_path = os.path.join('setup', 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                app.logger.info("Configuration loaded successfully from config.json")
                return jsonify(config)
            else:
                app.logger.error("config.json not found")
                return jsonify({"error": "Configuration file not found"}), 404
        except Exception as e:
            app.logger.error(f"Error loading config: {str(e)}")
            return jsonify({"error": "Failed to load configuration"}), 500

    elif request.method == 'POST':
        try:
            config_data = request.get_json()

            # Update the cache first
            global config_cache, config_last_modified
            config_cache = config_data.copy()
            config_last_modified = time.time()

            # Check if we're in Vercel environment first
            if os.environ.get('VERCEL'):
                app.logger.info("Configuration saved to memory only (Vercel environment)")
                return jsonify({
                    "success": True,
                    "message": "Configuration saved to memory only. Changes will not persist across deployments.",
                    "warning": "Running in production mode. For persistent changes, update the configuration file and redeploy."
                })
            else:
                # Only try to write to file in development environment
                try:
                    config_path = os.path.join(os.path.dirname(__file__), 'setup', 'config.json')
                    os.makedirs(os.path.dirname(config_path), exist_ok=True)

                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, indent=2, ensure_ascii=False)

                    app.logger.info("Configuration saved successfully to config.json")
                    return jsonify({
                        "success": True,
                        "message": "Configuration saved successfully to config.json"
                    })
                except Exception as file_error:
                    app.logger.warning(f"Could not save to file, using memory only: {str(file_error)}")
                    return jsonify({
                        "success": True,
                        "message": "Configuration saved to memory only (file system read-only)",
                        "warning": "Configuration could not be saved to file. Changes will not persist across restarts."
                    })
        except Exception as e:
            app.logger.error(f"Error saving configuration: {str(e)}")
            return jsonify({"error": f"Failed to save configuration: {str(e)}"}), 500

@app.route('/api/reload_config', methods=['POST'])
def reload_config():
    """Reload configuration from file"""
    try:
        # Clear any cached configuration
        global config_cache
        config_cache = None

        # Load fresh configuration
        config = load_config()

        return jsonify({
            "success": True,
            "message": "Configuration reloaded successfully",
            "config": config
        })
    except Exception as e:
        app.logger.error(f"Error reloading config: {str(e)}")
        return jsonify({"error": "Failed to reload configuration"}), 500

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
        from utils.form_generator import FormGenerator
        form_generator = FormGenerator()
        form_data = form_generator.get_form_data(form_id)

        if not form_data:
            return "Form not found", 404

        # Load current configuration to ensure latest settings
        config = load_config()
        form_data['config'] = config

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
                # Prepare all column values for batch creation
                column_values = {}
                header_data = stored_form_data.get('header_data', {})
                item_name = header_data.get('Viagem') or webhook_data.get('event', {}).get('pulseName', 'Resposta do Formulário')

                # Add header data to column values
                if header_data.get('Destino'):
                    column_values['text_mkrb17ct'] = header_data['Destino']

                if header_data.get('Data'):
                    column_values['text_mksq2j87'] = header_data['Data']

                if header_data.get('Cliente'):
                    column_values['text_mkrjdnry'] = header_data['Cliente']

                # Process all questions and add to column values
                for question in stored_form_data.get('questions', []):
                    question_id = question.get('id')
                    destination_column = question.get('destination_column')
                    question_destination_column = question.get('question_destination_column')
                    text_destination_column = question.get('text_destination_column')
                    rating_destination_column = question.get('rating_destination_column')
                    question_type = question.get('type')

                    # Skip divider questions
                    if question_type == 'divider':
                        continue

                    # For Monday column questions, save both the response and the column value
                    if question_type == 'monday_column':
                        # Save the user's response (rating)
                        response_value = submission_data.get(question_id)
                        if response_value is not None and str(response_value).strip():
                            response_str = str(response_value).strip()

                            # Convert English to Portuguese
                            if response_str.lower() == "yes":
                                response_str = "Sim"
                            elif response_str.lower() == "no":
                                response_str = "Não"

                            # Save to rating destination column
                            if rating_destination_column and rating_destination_column.strip():
                                column_values[rating_destination_column.strip()] = response_str

                        # Save the column value (question text) to text destination column
                        if text_destination_column and text_destination_column.strip():
                            column_value = question.get('column_value', '')
                            if column_value and column_value not in ['', 'Dados não encontrados', 'Erro ao carregar dados', 'Dados não disponíveis', 'Configuração incompleta']:
                                column_values[text_destination_column.strip()] = column_value

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
                                    column_values[destination_column.strip()] = response_str

                # Create item with all values in a single request
                app.logger.info(f"Processing - Creating item with {len(column_values)} column values")
                app.logger.info(f"Column values: {column_values}")

                create_result = monday_api.create_item_with_values(board_b, item_name, column_values)

                if create_result and create_result.get('create_item', {}).get('id'):
                    new_item_id = create_result['create_item']['id']
                    app.logger.info(f"Processing - Successfully created item with ID: {new_item_id} and all column values")
                else:
                    app.logger.error("Processing - Failed to create item in Board B with values")

            else:
                app.logger.error("Processing - Missing item_id or board_b configuration")
        else:
            app.logger.warning(f"Processing - No board_b configured for form type: {form_type}")

    except Exception as e:
        app.logger.error(f"Background processing error for form {form_id}: {str(e)}")


@app.route('/submit_form/<form_id>', methods=['POST'])
def submit_form(form_id):
    """Handle form submission"""
    try:
        # Get form data using FormGenerator to ensure file-based forms are loaded
        from utils.form_generator import FormGenerator
        form_generator = FormGenerator()
        form_data = form_generator.get_form_data(form_id)

        if not form_data:
            return jsonify({"error": "Form not found"}), 404

        # Get submission data
        submission_data = request.get_json()

        app.logger.info(f"Form submission for {form_id}: {submission_data}")

        # Load configuration
        config = load_config()
        form_type = form_data.get('type')

        # Monday API setup
        from utils.monday_api import MondayAPI
        monday_api = MondayAPI()

        # Get the item ID from webhook data
        webhook_data = form_data.get('webhook_data', {})
        item_id = webhook_data.get('event', {}).get('pulseId')

        form_responses = submission_data  # Assuming submission data is a dict of question_id: response

        # Process form submission using the background processor for better reliability
        try:
            process_form_background(form_id, submission_data, form_data)

            return jsonify({
                "success": True,
                "message": "Formulário enviado com sucesso! As respostas foram salvas no Monday.com."
            })
        except Exception as processing_error:
            app.logger.error(f"Error processing form: {str(processing_error)}")
            # Still return success to user but log the error
            return jsonify({
                "success": True,
                "message": "Formulário enviado com sucesso! As respostas estão sendo processadas."
            })

    except Exception as e:
        app.logger.error(f"Error submitting form: {str(e)}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@app.route('/success')
def success():
    """Display success page after form submission"""
    return render_template('success.html')

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



@app.route('/api/forms', methods=['GET'])
def list_forms():
    """List all generated forms"""
    try:
        from utils.form_generator import FormGenerator
        form_generator = FormGenerator()
        forms = form_generator.list_all_forms()
        return jsonify(forms)
    except Exception as e:
        app.logger.error(f"Error listing forms: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
