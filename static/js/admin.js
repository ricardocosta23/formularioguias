// Admin Interface JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeAdminInterface();
});

function initializeAdminInterface() {
    // Initialize tab switching functionality
    initializeTabSwitching();

    // Load existing configuration
    loadConfiguration();

    // Initialize event listeners
    initializeEventListeners();
}

function initializeTabSwitching() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const configForms = document.querySelectorAll('.config-form');

    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');

            // Remove active class from all tabs and forms
            tabButtons.forEach(btn => btn.classList.remove('active'));
            configForms.forEach(form => {
                form.classList.remove('active');
                form.style.display = 'none';
            });

            // Add active class to clicked tab
            this.classList.add('active');

            // Show corresponding form
            const targetForm = document.getElementById(targetTab + '-config');
            if (targetForm) {
                targetForm.classList.add('active');
                targetForm.style.display = 'block';
            }

            // Update current tab reference
            window.currentTab = targetTab;
        });
    });
}

function initializeEventListeners() {
    // Save configuration button
    const saveConfigBtn = document.getElementById('saveConfig');
    if (saveConfigBtn) {
        saveConfigBtn.addEventListener('click', saveConfiguration);
    }



    // Add question button
    const addQuestionBtn = document.getElementById('addQuestionBtn');
    if (addQuestionBtn) {
        addQuestionBtn.addEventListener('click', function() {
            if (window.currentTab && window.currentTab !== 'forms') {
                addQuestion(window.currentTab);
            }
        });
    }

    // Refresh forms button
    const refreshFormsBtn = document.getElementById('refreshForms');
    if (refreshFormsBtn) {
        refreshFormsBtn.addEventListener('click', loadForms);
    }
}

// Set initial tab
window.currentTab = 'guias';

// Configuration management functions
function loadConfiguration() {
    fetch('/api/config')
        .then(response => response.json())
        .then(config => {
            console.log('Loaded config:', config);
            populateConfigurationForm(config);
        })
        .catch(error => {
            console.error('Error loading configuration:', error);
        });
}

function populateConfigurationForm(config) {
    // Populate form fields for each tab
    ['guias', 'clientes', 'fornecedores'].forEach(formType => {
        const formConfig = config[formType] || {};

        // Populate basic fields
        const boardAField = document.getElementById(`${formType}-board-a`);
        const boardBField = document.getElementById(`${formType}-board-b`);
        const linkColumnField = document.getElementById(`${formType}-link-column`);

        if (boardAField) boardAField.value = formConfig.board_a || '';
        if (boardBField) boardBField.value = formConfig.board_b || '';
        if (linkColumnField) linkColumnField.value = formConfig.link_column || '';

        // Populate header fields
        if (formConfig.header_fields) {
            formConfig.header_fields.forEach((field, index) => {
                const titleField = document.getElementById(`${formType}-header-${index + 1}-title`);
                const columnField = document.getElementById(`${formType}-header-${index + 1}-column`);

                if (titleField) titleField.value = field.title || '';
                if (columnField) columnField.value = field.monday_column || '';
            });
        }

        // Populate questions
        if (formConfig.questions) {
            console.log('Rendering questions for:', formType, formConfig.questions);
            renderQuestions(formType, formConfig.questions);
        }
    });
}

function renderQuestions(formType, questions) {
    const questionsContainer = document.getElementById(`${formType}-questions`);
    if (!questionsContainer) {
        console.error('Questions container not found for:', formType);
        return;
    }

    // Clear existing questions
    questionsContainer.innerHTML = '';

    questions.forEach((question, index) => {
        const questionElement = createQuestionElement(formType, question, index);
        questionsContainer.appendChild(questionElement);
    });
}

function createQuestionElement(formType, question, index) {
    const questionDiv = document.createElement('div');
    questionDiv.className = 'question-item mb-4 p-3 border rounded';
    questionDiv.setAttribute('data-question-id', question.id);

    let questionHtml = '';

    if (question.type === 'divider') {
        questionHtml = `
            <div class="divider-question">
                <h5 class="text-primary">
                    <i data-feather="minus"></i>
                    ${question.title || 'Divisor'}
                </h5>
                <div class="row">
                    <div class="col-md-8">
                        <label class="form-label">Título do Divisor:</label>
                        <input type="text" class="form-control" value="${question.title || ''}" 
                               onchange="updateQuestionField('${formType}', ${index}, 'title', this.value)">
                    </div>
                    <div class="col-md-4 d-flex align-items-end">
                        <button type="button" class="btn btn-danger btn-sm" onclick="removeQuestion('${formType}', ${index})">
                            <i data-feather="trash-2"></i> Remover
                        </button>
                    </div>
                </div>
            </div>
        `;
    } else {
        const typeOptions = {
            'text': 'Texto',
            'longtext': 'Texto Longo',
            'yesno': 'Sim/Não',
            'rating': 'Avaliação (1-10)',
            'dropdown': 'Lista Suspensa',
            'monday_column': 'Coluna Monday'
        };

        questionHtml = `
            <div class="regular-question">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">Pergunta ${index + 1}</h6>
                    <button type="button" class="btn btn-danger btn-sm" onclick="removeQuestion('${formType}', ${index})">
                        <i data-feather="trash-2"></i> Remover
                    </button>
                </div>

                <div class="row">
                    <div class="col-md-6">
                        <label class="form-label">Tipo:</label>
                        <select class="form-control" onchange="updateQuestionField('${formType}', ${index}, 'type', this.value)">
                            ${Object.entries(typeOptions).map(([value, text]) => 
                                `<option value="${value}" ${question.type === value ? 'selected' : ''}>${text}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Obrigatória:</label>
                        <select class="form-control" onchange="updateQuestionField('${formType}', ${index}, 'required', this.value === 'true')">
                            <option value="false" ${!question.required ? 'selected' : ''}>Não</option>
                            <option value="true" ${question.required ? 'selected' : ''}>Sim</option>
                        </select>
                    </div>
                </div>

                <div class="row mt-3">
                    <div class="col-12">
                        <label class="form-label">Texto da Pergunta:</label>
                        <textarea class="form-control" rows="2" 
                                  onchange="updateQuestionField('${formType}', ${index}, 'text', this.value)">${question.text || ''}</textarea>
                    </div>
                </div>

                ${question.type === 'dropdown' ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <label class="form-label">Opções (separadas por ponto e vírgula):</label>
                        <input type="text" class="form-control" value="${question.dropdown_options || ''}"
                               placeholder="Opção 1;Opção 2;Opção 3"
                               onchange="updateQuestionField('${formType}', ${index}, 'dropdown_options', this.value)">
                    </div>
                </div>
                ` : ''}

                ${question.type === 'monday_column' ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <label class="form-label">Coluna de Origem (Monday):</label>
                        <input type="text" class="form-control" value="${question.source_column || ''}"
                               placeholder="Ex: text_mkrj9z52, dropdown_mksd123"
                               onchange="updateQuestionField('${formType}', ${index}, 'source_column', this.value)">
                        <small class="form-text text-muted">ID da coluna do Monday.com que será usada como nome/valor da pergunta</small>
                    </div>
                </div>
                ` : ''}

                <div class="row mt-3">
                    <div class="col-md-6">
                        <label class="form-label">Coluna de Destino (Monday):</label>
                        <input type="text" class="form-control" value="${question.destination_column || ''}"
                               placeholder="Ex: text_mksd123"
                               onchange="updateQuestionField('${formType}', ${index}, 'destination_column', this.value)">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">ID da Pergunta:</label>
                        <input type="text" class="form-control" value="${question.id || ''}" readonly>
                    </div>
                </div>

                ${question.conditional ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="alert alert-info">
                            <strong>Pergunta Condicional:</strong> Depende de "${question.conditional.depends_on}"
                        </div>
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    }

    questionDiv.innerHTML = questionHtml;
    return questionDiv;
}

function addQuestion(formType) {
    const questionId = 'question_' + Date.now();
    const newQuestion = {
        id: questionId,
        type: 'text',
        text: '',
        required: false,
        source: 'manual',
        destination_column: ''
    };

    // Get current questions
    const questionsContainer = document.getElementById(`${formType}-questions`);
    const currentQuestions = getCurrentQuestions(formType);

    // Add new question
    currentQuestions.push(newQuestion);

    // Re-render questions
    renderQuestions(formType, currentQuestions);

    // Scroll to new question
    setTimeout(() => {
        const newQuestionElement = questionsContainer.lastElementChild;
        if (newQuestionElement) {
            newQuestionElement.scrollIntoView({ behavior: 'smooth' });
        }
    }, 100);
}

function removeQuestion(formType, index) {
    if (confirm('Tem certeza que deseja remover esta pergunta?')) {
        const currentQuestions = getCurrentQuestions(formType);
        currentQuestions.splice(index, 1);
        renderQuestions(formType, currentQuestions);
    }
}

function updateQuestionField(formType, index, field, value) {
    const currentQuestions = getCurrentQuestions(formType);
    if (currentQuestions[index]) {
        currentQuestions[index][field] = value;

        // If the type field is being changed, re-render the questions to show/hide conditional fields
        if (field === 'type') {
            renderQuestions(formType, currentQuestions);
        }
    }
}

function getCurrentQuestions(formType) {
    const questionsContainer = document.getElementById(`${formType}-questions`);
    if (!questionsContainer) return [];

    const questions = [];
    const questionElements = questionsContainer.querySelectorAll('.question-item');

    questionElements.forEach((element, index) => {
        const questionId = element.getAttribute('data-question-id');

        if (element.querySelector('.divider-question')) {
            // Divider question
            const titleInput = element.querySelector('input[type="text"]');
            questions.push({
                id: questionId,
                type: 'divider',
                title: titleInput ? titleInput.value : ''
            });
        } else {
            // Regular question
            const typeSelect = element.querySelector('select');
            const requiredSelect = element.querySelectorAll('select')[1];
            const textTextarea = element.querySelector('textarea');
            const dropdownInput = element.querySelector('input[placeholder*="Opção"]');
            const destinationInput = element.querySelector('input[placeholder*="text_mksd"]');

            const question = {
                id: questionId,
                type: typeSelect ? typeSelect.value : 'text',
                text: textTextarea ? textTextarea.value : '',
                required: requiredSelect ? requiredSelect.value === 'true' : false,
                source: 'manual'
            };

            if (destinationInput && destinationInput.value) {
                question.destination_column = destinationInput.value;
            }

            if (dropdownInput && dropdownInput.value) {
                question.dropdown_options = dropdownInput.value;
            }

            // Handle source column for monday_column type questions
            const sourceColumnInput = element.querySelector('input[placeholder*="text_mkrj9z52"]');
            if (sourceColumnInput && sourceColumnInput.value) {
                question.source_column = sourceColumnInput.value;
            }

            // Handle conditional question data
            const dependsOnSelect = element.querySelector('.conditional-depends-on');
            const showIfSelect = element.querySelector('.conditional-show-if');
            
            if (dependsOnSelect && dependsOnSelect.value) {
                question.conditional = {
                    depends_on: dependsOnSelect.value,
                    show_if: showIfSelect ? showIfSelect.value : 'Sim'
                };
                question.is_conditional = true;
            } else {
                question.is_conditional = false;
            }

            questions.push(question);
        }
    });

    return questions;
}

function saveConfiguration() {
    const config = {
        guias: extractFormConfig('guias'),
        clientes: extractFormConfig('clientes'),
        fornecedores: extractFormConfig('fornecedores')
    };

    console.log('Saving configuration:', config);

    fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Save response:', data);
        if (data.error) {
            alert('Erro ao salvar configuração: ' + data.error);
        } else {
            // Copy configuration to clipboard
            const jsonString = JSON.stringify(config, null, 2);
            copyConfigToClipboard(jsonString);

            if (data.success) {
                alert(data.message || 'Configuração salva com sucesso e copiada para área de transferência!');
                if (data.warning) {
                    alert('Aviso: ' + data.warning);
                }
            } else {
                alert('Configuração salva com sucesso e copiada para área de transferência!');
            }

            // Reload configuration to confirm changes were saved
            loadConfiguration();
        }
    })
    .catch(error => {
        console.error('Error saving configuration:', error);
        alert('Erro ao salvar configuração: ' + error.message);
    });
}

function extractFormConfig(formType) {
    const config = {
        board_a: document.getElementById(`${formType}-board-a`)?.value || '',
        board_b: document.getElementById(`${formType}-board-b`)?.value || '',
        link_column: document.getElementById(`${formType}-link-column`)?.value || '',
        header_fields: [],
        questions: []
    };

    // Extract header fields
    for (let i = 1; i <= 4; i++) {
        const titleField = document.getElementById(`${formType}-header-${i}-title`);
        const columnField = document.getElementById(`${formType}-header-${i}-column`);

        if (titleField && columnField) {
            const title = titleField.value.trim();
            const column = columnField.value.trim();

            config.header_fields.push({
                title: title,
                monday_column: column
            });
        }
    }

    // Extract questions
    config.questions = getCurrentQuestions(formType);

    return config;
}

function loadForms() {
    // Load and display created forms
    const formsLoading = document.getElementById('formsLoading');
    const formsEmpty = document.getElementById('formsEmpty');
    const formsList = document.getElementById('formsList');
    const formsCount = document.getElementById('formsCount');

    // Show loading state
    if (formsLoading) formsLoading.style.display = 'block';
    if (formsEmpty) formsEmpty.style.display = 'none';
    if (formsList) formsList.style.display = 'none';

    fetch('/api/forms')
        .then(response => response.json())
        .then(forms => {
            // Hide loading
            if (formsLoading) formsLoading.style.display = 'none';

            if (forms && forms.length > 0) {
                renderFormsList(forms);
                if (formsList) formsList.style.display = 'block';
                if (formsCount) formsCount.textContent = forms.length;
            } else {
                if (formsEmpty) formsEmpty.style.display = 'block';
                if (formsCount) formsCount.textContent = '0';
            }
        })
        .catch(error => {
            console.error('Error loading forms:', error);
            if (formsLoading) formsLoading.style.display = 'none';
            if (formsEmpty) formsEmpty.style.display = 'block';
            if (formsCount) formsCount.textContent = '0';
        });
}

function renderFormsList(forms) {
    const formsList = document.getElementById('formsList');
    if (!formsList) return;

    formsList.innerHTML = '';

    forms.forEach(form => {
        const formCard = createFormCard(form);
        formsList.appendChild(formCard);
    });
}

function createFormCard(form) {
    const col = document.createElement('div');
    col.className = 'col-md-6 col-lg-4 mb-3';

    col.innerHTML = `
        <div class="card h-100">
            <div class="card-body">
                <h6 class="card-title">${form.title || 'Formulário'}</h6>
                <p class="card-text small text-muted">
                    ID: ${form.id}<br>
                    Tipo: ${form.type || 'N/A'}<br>
                    Criado: ${form.created_at || 'N/A'}
                </p>
                <div class="d-flex gap-2">
                    <a href="/form/${form.id}" target="_blank" class="btn btn-primary btn-sm">
                        <i data-feather="external-link"></i> Abrir
                    </a>
                    <button class="btn btn-danger btn-sm" onclick="deleteForm('${form.id}')">
                        <i data-feather="trash-2"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

    return col;
}

function deleteForm(formId) {
    if (confirm('Tem certeza que deseja excluir este formulário?')) {
        fetch(`/api/forms/${formId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Erro ao excluir formulário: ' + data.error);
            } else {
                alert('Formulário excluído com sucesso!');
                loadForms(); // Reload the forms list
            }
        })
        .catch(error => {
            console.error('Error deleting form:', error);
            alert('Erro ao excluir formulário');
        });
    }
}

function copyConfigToClipboard(jsonString) {
    // Try to copy to clipboard
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(jsonString).then(() => {
            console.log('config.json copiado para área de transferência!');
        }).catch(err => {
            console.error('Erro ao copiar para área de transferência:', err);
            fallbackCopyToClipboard(jsonString);
        });
    } else {
        fallbackCopyToClipboard(jsonString);
    }
}

function fallbackCopyToClipboard(text) {
    // Fallback method for copying to clipboard
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        document.execCommand('copy');
        console.log('config.json copiado para área de transferência!');
    } catch (err) {
        console.error('Erro ao copiar:', err);
        // Show the JSON in a modal/alert as last resort
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 20px;
            border: 2px solid #ccc;
            border-radius: 10px;
            max-width: 80vw;
            max-height: 80vh;
            overflow: auto;
            z-index: 9999;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        `;

        modal.innerHTML = `
            <h3>Copie o JSON abaixo:</h3>
            <textarea readonly style="width: 100%; height: 400px; font-family: monospace; font-size: 12px;">${text}</textarea>
            <br><br>
            <button onclick="this.parentElement.remove()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">Fechar</button>
        `;

        document.body.appendChild(modal);
    }

    document.body.removeChild(textArea);
}

function switchTab(tabName) {
    console.log('Switching to tab:', tabName);

    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Hide all config forms
    document.querySelectorAll('.config-form').forEach(form => {
        form.classList.remove('active');
        form.style.display = 'none';
    });

    // Add active class to clicked tab button
    const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }

    // Show corresponding config form
    const targetForm = document.getElementById(`${tabName}-config`);
    if (targetForm) {
        targetForm.classList.add('active');
        targetForm.style.display = 'block';
        console.log('Showing form:', targetForm.id);
    } else {
        console.error('Target form not found:', `${tabName}-config`);
    }
}

// Initialize when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAdminInterface);
} else {
    initializeAdminInterface();
}

function getAllYesNoQuestions(formType) {
    // Get current questions
    const questionsContainer = document.getElementById(`${formType}-questions`);
    const currentQuestions = getCurrentQuestions(formType);
    const yesNoQuestions = currentQuestions.filter(q => q.type === 'yesno');
    return yesNoQuestions;
}

//Add conditional questions
function createQuestionElement(formType, question, index) {
    const questionDiv = document.createElement('div');
    questionDiv.className = 'question-item mb-4 p-3 border rounded';
    questionDiv.setAttribute('data-question-id', question.id);

    let questionHtml = '';

    if (question.type === 'divider') {
        questionHtml = `
            <div class="divider-question">
                <h5 class="text-primary">
                    <i data-feather="minus"></i>
                    ${question.title || 'Divisor'}
                </h5>
                <div class="row">
                    <div class="col-md-8">
                        <label class="form-label">Título do Divisor:</label>
                        <input type="text" class="form-control" value="${question.title || ''}" 
                               onchange="updateQuestionField('${formType}', ${index}, 'title', this.value)">
                    </div>
                    <div class="col-md-4 d-flex align-items-end">
                        <button type="button" class="btn btn-danger btn-sm" onclick="removeQuestion('${formType}', ${index})">
                            <i data-feather="trash-2"></i> Remover
                        </button>
                    </div>
                </div>
            </div>
        `;
    } else {
        const typeOptions = {
            'text': 'Texto',
            'longtext': 'Texto Longo',
            'yesno': 'Sim/Não',
            'rating': 'Avaliação (1-10)',
            'dropdown': 'Lista Suspensa',
            'monday_column': 'Coluna Monday'
        };

        questionHtml = `
            <div class="regular-question">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">Pergunta ${index + 1}</h6>
                    <button type="button" class="btn btn-danger btn-sm" onclick="removeQuestion('${formType}', ${index})">
                        <i data-feather="trash-2"></i> Remover
                    </button>
                </div>

                <div class="row">
                    <div class="col-md-6">
                        <label class="form-label">Tipo:</label>
                        <select class="form-control" onchange="updateQuestionField('${formType}', ${index}, 'type', this.value)">
                            ${Object.entries(typeOptions).map(([value, text]) => 
                                `<option value="${value}" ${question.type === value ? 'selected' : ''}>${text}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Obrigatória:</label>
                        <select class="form-control" onchange="updateQuestionField('${formType}', ${index}, 'required', this.value === 'true')">
                            <option value="false" ${!question.required ? 'selected' : ''}>Não</option>
                            <option value="true" ${question.required ? 'selected' : ''}>Sim</option>
                        </select>
                    </div>
                </div>

                <div class="row mt-3">
                    <div class="col-12">
                        <label class="form-label">Texto da Pergunta:</label>
                        <textarea class="form-control" rows="2" 
                                  onchange="updateQuestionField('${formType}', ${index}, 'text', this.value)">${question.text || ''}</textarea>
                    </div>
                </div>

                ${question.type === 'dropdown' ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <label class="form-label">Opções (separadas por ponto e vírgula):</label>
                        <input type="text" class="form-control" value="${question.dropdown_options || ''}"
                               placeholder="Opção 1;Opção 2;Opção 3"
                               onchange="updateQuestionField('${formType}', ${index}, 'dropdown_options', this.value)">
                    </div>
                </div>
                ` : ''}

                ${question.type === 'monday_column' ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <label class="form-label">Coluna de Origem (Monday):</label>
                        <input type="text" class="form-control" value="${question.source_column || ''}"
                               placeholder="Ex: text_mkrj9z52, dropdown_mksd123"
                               onchange="updateQuestionField('${formType}', ${index}, 'source_column', this.value)">
                        <small class="form-text text-muted">ID da coluna do Monday.com que será usada como nome/valor da pergunta</small>
                    </div>
                </div>
                ` : ''}

                <div class="row mt-3">
                    <div class="col-md-6">
                        <label class="form-label">Coluna de Destino (Monday):</label>
                        <input type="text" class="form-control" value="${question.destination_column || ''}"
                               placeholder="Ex: text_mksd123"
                               onchange="updateQuestionField('${formType}', ${index}, 'destination_column', this.value)">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">ID da Pergunta:</label>
                        <input type="text" class="form-control" value="${question.id || ''}" readonly>
                    </div>
                </div>

                <div class="row mt-3">
                    <div class="col-md-6">
                        <label class="form-label">Depende da pergunta (Sim/Não):</label>
                        <select class="form-control conditional-depends-on" onchange="updateQuestionConditional('${formType}', ${index}, 'depends_on', this.value)">
                            <option value="">Nenhuma</option>
                            ${getAllYesNoQuestions(formType).map(q => 
                                `<option value="${q.id}" ${question.conditional && question.conditional.depends_on === q.id ? 'selected' : ''}>${q.text || q.id}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Mostrar se a resposta for:</label>
                        <select class="form-control conditional-show-if" onchange="updateQuestionConditional('${formType}', ${index}, 'show_if', this.value)">
                            <option value="Sim" ${question.conditional && question.conditional.show_if === 'Sim' ? 'selected' : ''}>Sim</option>
                            <option value="Não" ${question.conditional && question.conditional.show_if === 'Não' ? 'selected' : ''}>Não</option>
                        </select>
                    </div>
                </div>

                ${question.conditional ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="alert alert-info">
                            <strong>Pergunta Condicional:</strong> Depende de "${question.conditional.depends_on}"
                        </div>
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    }

    questionDiv.innerHTML = questionHtml;
    return questionDiv;
}

function updateQuestionConditional(formType, index, field, value) {
    const currentQuestions = getCurrentQuestions(formType);
    if (currentQuestions[index]) {
        if (!currentQuestions[index].conditional) {
            currentQuestions[index].conditional = {};
        }
        currentQuestions[index].conditional[field] = value;
    }
}
