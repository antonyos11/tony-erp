/**
 * Journal Entry Utilities - Modern JavaScript ES6+ utilities for enhanced accounting system
 * Developed for Arabic RTL accounting system with advanced features
 */

class JournalEntryUtils {
    constructor() {
        this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        this.apiUrls = {
            accountSearch: '/accounting/api/accounts/search/',
            validate: '/accounting/api/journal-entry/validate/',
            draftSave: '/accounting/api/journal-entry/draft/save/',
            templates: '/accounting/api/templates/'
        };
        this.cache = new Map();
        this.debounceTimers = new Map();
        this.lastSaveTime = null;
    }

    /**
     * Format currency for Arabic RTL display
     */
    formatCurrency(amount, currency = 'ر.س') {
        if (!amount || isNaN(amount)) return '0.00';
        const num = parseFloat(amount);
        return new Intl.NumberFormat('ar-SA', {
            style: 'decimal',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(num) + ` ${currency}`;
    }

    /**
     * Parse currency from Arabic formatted string
     */
    parseCurrency(value) {
        if (!value) return 0;
        // Remove currency symbols and Arabic formatting
        const cleaned = value.toString()
            .replace(/[^\d.,\-]/g, '')
            .replace(/,/g, '');
        return parseFloat(cleaned) || 0;
    }

    /**
     * Debounced function executor
     */
    debounce(key, func, delay = 300) {
        if (this.debounceTimers.has(key)) {
            clearTimeout(this.debounceTimers.get(key));
        }
        
        const timer = setTimeout(() => {
            func();
            this.debounceTimers.delete(key);
        }, delay);
        
        this.debounceTimers.set(key, timer);
    }

    /**
     * Enhanced account search with caching
     */
    async searchAccounts(query) {
        if (!query || query.length < 2) return [];
        
        const cacheKey = `account_search_${query}`;
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        try {
            const response = await fetch(`${this.apiUrls.accountSearch}?q=${encodeURIComponent(query)}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            const results = data.results || [];
            
            // Cache for 5 minutes
            this.cache.set(cacheKey, results);
            setTimeout(() => this.cache.delete(cacheKey), 300000);
            
            return results;
        } catch (error) {
            console.error('Account search error:', error);
            this.showNotification('خطأ في البحث عن الحسابات', 'error');
            return [];
        }
    }

    /**
     * Real-time journal entry validation
     */
    async validateJournalEntry(formData) {
        try {
            const response = await fetch(this.apiUrls.validate, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) throw new Error('Validation request failed');
            
            return await response.json();
        } catch (error) {
            console.error('Validation error:', error);
            return {
                valid: false,
                errors: ['حدث خطأ في التحقق من صحة القيد']
            };
        }
    }

    /**
     * Auto-save draft functionality
     */
    async saveDraft(formData) {
        try {
            const response = await fetch(this.apiUrls.draftSave, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) throw new Error('Draft save failed');
            
            const result = await response.json();
            this.lastSaveTime = new Date();
            return result;
        } catch (error) {
            console.error('Draft save error:', error);
            return { saved: false, error: error.message };
        }
    }

    /**
     * Get journal entry templates
     */
    async getTemplates() {
        const cacheKey = 'journal_templates';
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        try {
            const response = await fetch(this.apiUrls.templates, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Templates request failed');
            
            const data = await response.json();
            const templates = data.templates || [];
            
            // Cache templates for 30 minutes
            this.cache.set(cacheKey, templates);
            setTimeout(() => this.cache.delete(cacheKey), 1800000);
            
            return templates;
        } catch (error) {
            console.error('Templates error:', error);
            this.showNotification('خطأ في تحميل القوالب', 'error');
            return [];
        }
    }

    /**
     * Enhanced notification system
     */
    showNotification(message, type = 'info', duration = 5000) {
        // Remove existing notifications
        const existing = document.querySelectorAll('.je-notification');
        existing.forEach(el => el.remove());

        const notification = document.createElement('div');
        notification.className = `je-notification alert alert-${this.getBootstrapAlertType(type)} alert-dismissible fade show`;
        notification.innerHTML = `
            <i class="bi bi-${this.getIconForType(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Add to page
        const container = document.querySelector('.notification-container') || document.body;
        container.appendChild(notification);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.classList.remove('show');
                    setTimeout(() => notification.remove(), 150);
                }
            }, duration);
        }
    }

    /**
     * Get Bootstrap alert type from custom type
     */
    getBootstrapAlertType(type) {
        const typeMap = {
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'info': 'info'
        };
        return typeMap[type] || 'info';
    }

    /**
     * Get icon for notification type
     */
    getIconForType(type) {
        const iconMap = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        };
        return iconMap[type] || 'info-circle';
    }

    /**
     * Format date for Arabic locale
     */
    formatDate(date, includeTime = false) {
        if (!date) return '';
        
        const d = date instanceof Date ? date : new Date(date);
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            calendar: 'gregory',
            numberingSystem: 'arab'
        };

        if (includeTime) {
            options.hour = '2-digit';
            options.minute = '2-digit';
        }

        return new Intl.DateTimeFormat('ar-SA', options).format(d);
    }

    /**
     * Calculate balance for journal entry items
     */
    calculateBalance(items) {
        let totalDebit = 0;
        let totalCredit = 0;

        items.forEach(item => {
            const debit = this.parseCurrency(item.debit || 0);
            const credit = this.parseCurrency(item.credit || 0);
            totalDebit += debit;
            totalCredit += credit;
        });

        return {
            debit: totalDebit,
            credit: totalCredit,
            difference: totalDebit - totalCredit,
            balanced: Math.abs(totalDebit - totalCredit) < 0.01
        };
    }

    /**
     * Generate unique ID for form elements
     */
    generateId(prefix = 'je') {
        return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Keyboard shortcuts handler
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+S: Save draft
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                this.triggerAutoSave();
            }
            
            // Ctrl+Enter: Submit form
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                const submitBtn = document.querySelector('button[type="submit"]');
                if (submitBtn) submitBtn.click();
            }
            
            // Ctrl+N: Add new row
            if (e.ctrlKey && e.key === 'n') {
                e.preventDefault();
                const addRowBtn = document.querySelector('.add-row-btn');
                if (addRowBtn) addRowBtn.click();
            }
        });
    }

    /**
     * Trigger auto-save with current form data
     */
    triggerAutoSave() {
        const event = new CustomEvent('je:autoSave');
        document.dispatchEvent(event);
    }

    /**
     * Local storage utilities
     */
    saveToLocalStorage(key, data, expiryMinutes = 60) {
        const expiry = new Date().getTime() + (expiryMinutes * 60 * 1000);
        localStorage.setItem(key, JSON.stringify({
            data: data,
            expiry: expiry
        }));
    }

    loadFromLocalStorage(key) {
        try {
            const item = localStorage.getItem(key);
            if (!item) return null;
            
            const parsed = JSON.parse(item);
            if (new Date().getTime() > parsed.expiry) {
                localStorage.removeItem(key);
                return null;
            }
            
            return parsed.data;
        } catch (error) {
            console.error('LocalStorage load error:', error);
            return null;
        }
    }

    /**
     * Print utilities
     */
    printJournalEntry(entryData) {
        const printWindow = window.open('', '_blank');
        const printContent = this.generatePrintContent(entryData);
        
        printWindow.document.write(printContent);
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
        printWindow.close();
    }

    generatePrintContent(entryData) {
        return `
            <!DOCTYPE html>
            <html dir="rtl" lang="ar">
            <head>
                <meta charset="UTF-8">
                <title>قيد محاسبي</title>
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Arial, sans-serif; margin: 20px; }
                    .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }
                    .entry-info { margin: 20px 0; }
                    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
                    th { background-color: #f5f5f5; }
                    .totals { font-weight: bold; background-color: #f9f9f9; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>قيد محاسبي</h2>
                    <p>رقم القيد: ${entryData.number || 'جديد'}</p>
                    <p>التاريخ: ${this.formatDate(entryData.date)}</p>
                </div>
                <div class="entry-info">
                    <p><strong>البيان:</strong> ${entryData.description || ''}</p>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>رقم الحساب</th>
                            <th>اسم الحساب</th>
                            <th>البيان</th>
                            <th>مدين</th>
                            <th>دائن</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${entryData.items?.map(item => `
                            <tr>
                                <td>${item.account_code || ''}</td>
                                <td>${item.account_name || ''}</td>
                                <td>${item.description || ''}</td>
                                <td>${item.debit ? this.formatCurrency(item.debit) : ''}</td>
                                <td>${item.credit ? this.formatCurrency(item.credit) : ''}</td>
                            </tr>
                        `).join('') || ''}
                    </tbody>
                    <tfoot>
                        <tr class="totals">
                            <td colspan="3">الإجمالي</td>
                            <td>${this.formatCurrency(entryData.total_debit || 0)}</td>
                            <td>${this.formatCurrency(entryData.total_credit || 0)}</td>
                        </tr>
                    </tfoot>
                </table>
            </body>
            </html>
        `;
    }
}

// Create global instance
window.journalEntryUtils = new JournalEntryUtils();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JournalEntryUtils;
}