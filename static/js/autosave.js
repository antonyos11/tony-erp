/**
 * Autosave and Conflict Detection JavaScript
 * Automatically saves form data and detects editing conflicts
 */

class AutosaveManager {
    constructor(options) {
        this.model = options.model;  // e.g., 'invoice', 'quotation'
        this.instanceId = options.instanceId || 'new';
        this.formSelector = options.formSelector;
        this.interval = options.interval || 30000;  // 30 seconds
        this.onSaved = options.onSaved || null;
        this.onError = options.onError || null;
        this.onConflict = options.onConflict || null;
        
        this.autosaveTimer = null;
        this.isLocked = false;
        this.isDirty = false;
        
        this.init();
    }
    
    init() {
        // Load any existing draft
        this.loadDraft();
        
        // Acquire edit lock
        this.acquireLock();
        
        // Start autosave timer
        this.startAutosave();
        
        // Track form changes
        this.trackChanges();
        
        // Release lock on page unload
        this.setupUnloadHandler();
    }
    
    async loadDraft() {
        try {
            const response = await fetch(
                `/api/autosave/draft/load/?model=${this.model}&instance_id=${this.instanceId}`,
                {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': this.getCookie('csrftoken')
                    }
                }
            );
            
            const result = await response.json();
            
            if (result.success && result.data) {
                if (confirm(`تم العثور على مسودة محفوظة من ${result.saved_at}. هل تريد استعادتها؟`)) {
                    this.restoreFormData(result.data);
                }
            }
        } catch (error) {
            console.error('Failed to load draft:', error);
        }
    }
    
    async acquireLock() {
        try {
            const response = await fetch('/api/autosave/lock/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    model: this.model,
                    instance_id: this.instanceId
                })
            });
            
            const result = await response.json();
            
            if (response.status === 409) {
                // Conflict - someone else is editing
                this.isLocked = true;
                if (this.onConflict) {
                    this.onConflict(result.locked_by);
                } else {
                    alert(`تحذير: هذا السجل قيد التحرير من قبل ${result.locked_by}`);
                }
            } else if (result.success) {
                this.isLocked = false;
            }
        } catch (error) {
            console.error('Failed to acquire lock:', error);
        }
    }
    
    async releaseLock() {
        try {
            await fetch(
                `/api/autosave/lock/release/?model=${this.model}&instance_id=${this.instanceId}`,
                {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': this.getCookie('csrftoken')
                    }
                }
            );
        } catch (error) {
            console.error('Failed to release lock:', error);
        }
    }
    
    startAutosave() {
        this.autosaveTimer = setInterval(() => {
            if (this.isDirty && !this.isLocked) {
                this.save();
            }
        }, this.interval);
    }
    
    stopAutosave() {
        if (this.autosaveTimer) {
            clearInterval(this.autosaveTimer);
            this.autosaveTimer = null;
        }
    }
    
    trackChanges() {
        const form = document.querySelector(this.formSelector);
        if (!form) return;
        
        form.addEventListener('input', () => {
            this.isDirty = true;
        });
        
        form.addEventListener('change', () => {
            this.isDirty = true;
        });
    }
    
    async save() {
        const formData = this.getFormData();
        
        try {
            const response = await fetch('/api/autosave/draft/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    model: this.model,
                    instance_id: this.instanceId,
                    data: formData
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.isDirty = false;
                this.showSaveIndicator();
                if (this.onSaved) {
                    this.onSaved();
                }
            } else {
                if (this.onError) {
                    this.onError(result.error);
                }
            }
        } catch (error) {
            console.error('Autosave failed:', error);
            if (this.onError) {
                this.onError(error.message);
            }
        }
    }
    
    async clearDraft() {
        try {
            await fetch(
                `/api/autosave/draft/clear/?model=${this.model}&instance_id=${this.instanceId}`,
                {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': this.getCookie('csrftoken')
                    }
                }
            );
        } catch (error) {
            console.error('Failed to clear draft:', error);
        }
    }
    
    getFormData() {
        const form = document.querySelector(this.formSelector);
        if (!form) return {};
        
        const formData = {};
        const elements = form.elements;
        
        for (let i = 0; i < elements.length; i++) {
            const element = elements[i];
            
            if (!element.name) continue;
            
            if (element.type === 'checkbox') {
                formData[element.name] = element.checked;
            } else if (element.type === 'radio') {
                if (element.checked) {
                    formData[element.name] = element.value;
                }
            } else {
                formData[element.name] = element.value;
            }
        }
        
        return formData;
    }
    
    restoreFormData(data) {
        const form = document.querySelector(this.formSelector);
        if (!form) return;
        
        for (const [name, value] of Object.entries(data)) {
            const element = form.elements[name];
            if (!element) continue;
            
            if (element.type === 'checkbox') {
                element.checked = value;
            } else if (element.type === 'radio') {
                const radioElement = form.querySelector(`input[name="${name}"][value="${value}"]`);
                if (radioElement) {
                    radioElement.checked = true;
                }
            } else {
                element.value = value;
            }
        }
        
        this.isDirty = false;
    }
    
    showSaveIndicator() {
        // Show a brief "saved" indicator
        let indicator = document.getElementById('autosave-indicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'autosave-indicator';
            indicator.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                z-index: 9999;
                opacity: 0;
                transition: opacity 0.3s;
            `;
            indicator.textContent = 'تم الحفظ التلقائي ✓';
            document.body.appendChild(indicator);
        }
        
        indicator.style.opacity = '1';
        
        setTimeout(() => {
            indicator.style.opacity = '0';
        }, 2000);
    }
    
    setupUnloadHandler() {
        window.addEventListener('beforeunload', (e) => {
            this.releaseLock();
            
            if (this.isDirty) {
                e.preventDefault();
                e.returnValue = 'لديك تغييرات غير محفوظة. هل أنت متأكد؟';
                return e.returnValue;
            }
        });
        
        // Also release lock when form is submitted
        const form = document.querySelector(this.formSelector);
        if (form) {
            form.addEventListener('submit', () => {
                this.stopAutosave();
                this.clearDraft();
                this.releaseLock();
            });
        }
    }
    
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    destroy() {
        this.stopAutosave();
        this.releaseLock();
    }
}

// Export for use in templates
window.AutosaveManager = AutosaveManager;
