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
            renderQuestions(formType, formConfig.questions);
        }
    });
}

function saveConfiguration() {
    const config = {
        guias: extractFormConfig('guias'),
        clientes: extractFormConfig('clientes'),
        fornecedores: extractFormConfig('fornecedores')
    };

    fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Erro ao salvar configuração: ' + data.error);
        } else {
            alert('Configuração salva com sucesso!');
            if (data.warning) {
                alert('Aviso: ' + data.warning);
            }
        }
    })
    .catch(error => {
        console.error('Error saving configuration:', error);
        alert('Erro ao salvar configuração');
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

            if (title || column) {
                config.header_fields.push({
                    title: title,
                    monday_column: column
                });
            }
        }
    }

    // Extract questions
    const questionsContainer = document.getElementById(`${formType}-questions`);
    if (questionsContainer) {
        const questionItems = questionsContainer.querySelectorAll('.question-item');
        questionItems.forEach((item, index) => {
            const questionConfig = extractQuestionConfig(item, index);
            if (questionConfig) {
                config.questions.push(questionConfig);
            }
        });
    }

    return config;
}

function extractQuestionConfig(questionItem, index) {
    // This function would extract question configuration from the DOM
    // Implementation depends on the question form structure
    return null; // Placeholder
}

function addQuestion(formType) {
    // Add new question functionality
    console.log('Adding question for:', formType);
}

function renderQuestions(formType, questions) {
    // Render questions in the admin interface
    console.log('Rendering questions for:', formType, questions);
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
