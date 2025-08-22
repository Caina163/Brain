/**
 * BRAINCHILD - JAVASCRIPT PRINCIPAL
 * Sistema de Quiz Inteligente
 * ===============================
 */

// Namespace global para evitar conflitos
const Brainchild = {
    config: {
        animationDuration: 300,
        debounceDelay: 300,
        maxFileSize: 16 * 1024 * 1024, // 16MB
        allowedImageTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    },

    utils: {},
    components: {},
    forms: {},
    ui: {}
};

// ===================================
// UTILITIES
// ===================================

Brainchild.utils = {
    /**
     * Debounce function para otimizar performance
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Formata bytes para display humano
     */
    formatBytes: function(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    },

    /**
     * Valida se arquivo é uma imagem válida
     */
    validateImageFile: function(file) {
        if (!file) return { valid: false, message: 'Nenhum arquivo selecionado' };

        if (!Brainchild.config.allowedImageTypes.includes(file.type)) {
            return {
                valid: false,
                message: 'Tipo de arquivo não permitido. Use: JPG, PNG, GIF ou WEBP'
            };
        }

        if (file.size > Brainchild.config.maxFileSize) {
            return {
                valid: false,
                message: `Arquivo muito grande. Máximo: ${Brainchild.utils.formatBytes(Brainchild.config.maxFileSize)}`
            };
        }

        return { valid: true, message: 'Arquivo válido' };
    },

    /**
     * Gera ID único
     */
    generateId: function() {
        return 'id_' + Math.random().toString(36).substr(2, 9);
    },

    /**
     * Sanitiza string para HTML
     */
    escapeHtml: function(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    },

    /**
     * Copia texto para clipboard
     */
    copyToClipboard: function(text) {
        if (navigator.clipboard) {
            return navigator.clipboard.writeText(text);
        } else {
            // Fallback para browsers antigos
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                document.body.removeChild(textArea);
                return Promise.resolve();
            } catch (err) {
                document.body.removeChild(textArea);
                return Promise.reject(err);
            }
        }
    }
};

// ===================================
// UI COMPONENTS
// ===================================

Brainchild.ui = {
    /**
     * Mostra toast notification
     */
    showToast: function(message, type = 'info', duration = 5000) {
        const toastContainer = this.getOrCreateToastContainer();
        const toast = this.createToastElement(message, type);

        toastContainer.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        // Auto remove
        setTimeout(() => {
            this.removeToast(toast);
        }, duration);

        return toast;
    },

    getOrCreateToastContainer: function() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    },

    createToastElement: function(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${Brainchild.utils.escapeHtml(message)}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="Brainchild.ui.removeToast(this.closest('.toast'))"></button>
            </div>
        `;
        return toast;
    },

    removeToast: function(toast) {
        toast.classList.add('hide');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    },

    /**
     * Mostra modal de confirmação
     */
    showConfirmModal: function(title, message, onConfirm, onCancel) {
        const modalId = 'confirmModal_' + Brainchild.utils.generateId();
        const modal = this.createConfirmModal(modalId, title, message);

        document.body.appendChild(modal);

        const bsModal = new bootstrap.Modal(modal);

        // Event listeners
        modal.querySelector('.btn-confirm').addEventListener('click', () => {
            bsModal.hide();
            if (onConfirm) onConfirm();
        });

        modal.querySelector('.btn-cancel').addEventListener('click', () => {
            bsModal.hide();
            if (onCancel) onCancel();
        });

        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });

        bsModal.show();

        return bsModal;
    },

    createConfirmModal: function(id, title, message) {
        const modal = document.createElement('div');
        modal.id = id;
        modal.className = 'modal fade';
        modal.tabIndex = -1;
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${Brainchild.utils.escapeHtml(title)}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p class="mb-0">${Brainchild.utils.escapeHtml(message)}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary btn-cancel">Cancelar</button>
                        <button type="button" class="btn btn-primary btn-confirm">Confirmar</button>
                    </div>
                </div>
            </div>
        `;
        return modal;
    },

    /**
     * Loading state para botões
     */
    setButtonLoading: function(button, loading = true, loadingText = 'Carregando...') {
        if (loading) {
            button.setAttribute('data-original-text', button.innerHTML);
            button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${loadingText}`;
            button.disabled = true;
        } else {
            const originalText = button.getAttribute('data-original-text');
            if (originalText) {
                button.innerHTML = originalText;
                button.removeAttribute('data-original-text');
            }
            button.disabled = false;
        }
    },

    /**
     * Anima contadores numericos
     */
    animateCounter: function(element, start = 0, end = null, duration = 1000) {
        if (end === null) {
            end = parseInt(element.textContent) || 0;
        }

        const startTime = performance.now();
        const startValue = start;
        const endValue = end;

        function updateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const currentValue = Math.floor(startValue + (endValue - startValue) * progress);
            element.textContent = currentValue;

            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        }

        requestAnimationFrame(updateCounter);
    }
};

// ===================================
// FORM COMPONENTS
// ===================================

Brainchild.forms = {
    /**
     * Valida formulários em tempo real
     */
    setupFormValidation: function(form) {
        const inputs = form.querySelectorAll('input, textarea, select');

        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });

            input.addEventListener('input', Brainchild.utils.debounce(() => {
                this.validateField(input);
            }, Brainchild.config.debounceDelay));
        });

        form.addEventListener('submit', (e) => {
            if (!this.validateForm(form)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    },

    validateField: function(field) {
        const value = field.value.trim();
        let isValid = true;
        let message = '';

        // Required validation
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            message = 'Este campo é obrigatório';
        }

        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                message = 'Email inválido';
            }
        }

        // Min length validation
        const minLength = field.getAttribute('minlength');
        if (minLength && value.length > 0 && value.length < parseInt(minLength)) {
            isValid = false;
            message = `Mínimo ${minLength} caracteres`;
        }

        // Max length validation
        const maxLength = field.getAttribute('maxlength');
        if (maxLength && value.length > parseInt(maxLength)) {
            isValid = false;
            message = `Máximo ${maxLength} caracteres`;
        }

        // Custom validation
        if (field.hasAttribute('data-validate')) {
            const validationType = field.getAttribute('data-validate');
            const customValidation = this.customValidations[validationType];
            if (customValidation) {
                const result = customValidation(value);
                if (!result.valid) {
                    isValid = false;
                    message = result.message;
                }
            }
        }

        this.updateFieldValidationState(field, isValid, message);
        return isValid;
    },

    validateForm: function(form) {
        const fields = form.querySelectorAll('input, textarea, select');
        let isValid = true;

        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    },

    updateFieldValidationState: function(field, isValid, message) {
        const feedbackElement = field.parentNode.querySelector('.invalid-feedback') ||
                               this.createFeedbackElement(field);

        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            feedbackElement.textContent = '';
            feedbackElement.style.display = 'none';
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            feedbackElement.textContent = message;
            feedbackElement.style.display = 'block';
        }
    },

    createFeedbackElement: function(field) {
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.appendChild(feedback);
        return feedback;
    },

    customValidations: {
        username: function(value) {
            const regex = /^[a-zA-Z0-9_]+$/;
            return {
                valid: regex.test(value),
                message: 'Username deve conter apenas letras, números e underscore'
            };
        },

        password: function(value) {
            if (value.length < 6) {
                return { valid: false, message: 'Senha deve ter pelo menos 6 caracteres' };
            }
            if (!/[a-zA-Z]/.test(value)) {
                return { valid: false, message: 'Senha deve conter pelo menos uma letra' };
            }
            if (!/[0-9]/.test(value)) {
                return { valid: false, message: 'Senha deve conter pelo menos um número' };
            }
            return { valid: true, message: '' };
        }
    },

    /**
     * Setup para upload de imagens
     */
    setupImageUpload: function(input, previewContainer) {
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) {
                this.clearImagePreview(previewContainer);
                return;
            }

            const validation = Brainchild.utils.validateImageFile(file);
            if (!validation.valid) {
                Brainchild.ui.showToast(validation.message, 'danger');
                input.value = '';
                this.clearImagePreview(previewContainer);
                return;
            }

            this.showImagePreview(file, previewContainer, input);
        });
    },

    showImagePreview: function(file, container, input) {
        const reader = new FileReader();
        reader.onload = (e) => {
            container.innerHTML = `
                <div class="image-preview-wrapper">
                    <img src="${e.target.result}" class="image-preview img-fluid rounded" alt="Preview">
                    <button type="button" class="btn btn-sm btn-outline-danger mt-2" onclick="Brainchild.forms.removeImagePreview('${input.id}', '${container.id}')">
                        <i class="bi bi-x"></i> Remover
                    </button>
                </div>
            `;
            container.style.display = 'block';
        };
        reader.readAsDataURL(file);
    },

    removeImagePreview: function(inputId, containerId) {
        const input = document.getElementById(inputId);
        const container = document.getElementById(containerId);

        input.value = '';
        this.clearImagePreview(container);
    },

    clearImagePreview: function(container) {
        container.innerHTML = '';
        container.style.display = 'none';
    }
};

// ===================================
// COMPONENTS
// ===================================

Brainchild.components = {
    /**
     * Auto-hide alerts
     */
    setupAutoHideAlerts: function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            setTimeout(() => {
                if (alert.parentNode) {
                    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                    bsAlert.close();
                }
            }, 5000);
        });
    },

    /**
     * Smooth scroll para âncoras
     */
    setupSmoothScroll: function() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    },

    /**
     * Setup tooltips
     */
    setupTooltips: function() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },

    /**
     * Animar elementos quando entram na viewport
     */
    setupScrollAnimations: function() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');

                    // Animar contadores
                    if (entry.target.classList.contains('stat-card')) {
                        const counter = entry.target.querySelector('.stat-content h3');
                        if (counter && !counter.hasAttribute('data-animated')) {
                            counter.setAttribute('data-animated', 'true');
                            Brainchild.ui.animateCounter(counter);
                        }
                    }
                }
            });
        });

        document.querySelectorAll('.stat-card, .quiz-card, .user-card').forEach(el => {
            observer.observe(el);
        });
    },

    /**
     * Character counter para textareas
     */
    setupCharacterCounters: function() {
        document.querySelectorAll('textarea[maxlength]').forEach(textarea => {
            const maxLength = parseInt(textarea.getAttribute('maxlength'));
            const counter = this.createCharacterCounter(textarea, maxLength);
            textarea.parentNode.appendChild(counter);

            textarea.addEventListener('input', () => {
                this.updateCharacterCounter(textarea, counter, maxLength);
            });

            // Initial update
            this.updateCharacterCounter(textarea, counter, maxLength);
        });
    },

    createCharacterCounter: function(textarea, maxLength) {
        const counter = document.createElement('small');
        counter.className = 'form-text text-muted character-counter';
        return counter;
    },

    updateCharacterCounter: function(textarea, counter, maxLength) {
        const currentLength = textarea.value.length;
        const remaining = maxLength - currentLength;

        counter.textContent = `${currentLength}/${maxLength} caracteres`;

        if (remaining < 50) {
            counter.classList.add('text-warning');
            counter.classList.remove('text-muted');
        } else {
            counter.classList.add('text-muted');
            counter.classList.remove('text-warning');
        }
    }
};

// ===================================
// INITIALIZATION
// ===================================

document.addEventListener('DOMContentLoaded', function() {
    // Setup components
    Brainchild.components.setupAutoHideAlerts();
    Brainchild.components.setupSmoothScroll();
    Brainchild.components.setupTooltips();
    Brainchild.components.setupScrollAnimations();
    Brainchild.components.setupCharacterCounters();

    // Setup form validation for all forms
    document.querySelectorAll('form').forEach(form => {
        Brainchild.forms.setupFormValidation(form);
    });

    // Setup image uploads
    document.querySelectorAll('input[type="file"][accept*="image"]').forEach(input => {
        const previewId = input.getAttribute('data-preview');
        if (previewId) {
            const previewContainer = document.getElementById(previewId);
            if (previewContainer) {
                Brainchild.forms.setupImageUpload(input, previewContainer);
            }
        }
    });

    // Loading states for forms with data-loading attribute
    document.querySelectorAll('form[data-loading]').forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                Brainchild.ui.setButtonLoading(submitBtn, true, 'Processando...');
            }
        });
    });

    console.log('🧠 Brainchild JavaScript initialized successfully!');
});

// ===================================
// GLOBAL FUNCTIONS (compatibilidade)
// ===================================

// Funções globais para compatibilidade com templates
window.showConfirmModal = function(title, message, callback) {
    Brainchild.ui.showConfirmModal(title, message, callback);
};

window.showToast = function(message, type, duration) {
    Brainchild.ui.showToast(message, type, duration);
};

window.copyToClipboard = function(text) {
    return Brainchild.utils.copyToClipboard(text)
        .then(() => {
            Brainchild.ui.showToast('Copiado para a área de transferência!', 'success');
        })
        .catch(() => {
            Brainchild.ui.showToast('Erro ao copiar texto', 'danger');
        });
};

// Export para uso em outros scripts
window.Brainchild = Brainchild;