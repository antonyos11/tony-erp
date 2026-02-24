/**
 * مولد الأكواد التلقائي - Universal Auto Code Generator
 * يعمل مع جميع النماذج في النظام
 * 
 * الاستخدام:
 * 1. أضف data-code-model="app.Model" للحقل input
 * 2. سيتم إضافة زر التوليد تلقائياً
 * 
 * أو يدوياً:
 * <div class="code-generator-wrapper">
 *   <input type="text" id="id_code" data-code-model="branches.Branch">
 *   <button type="button" class="btn-generate-code" data-target="id_code" data-model="branches.Branch">
 *     <i class="fas fa-magic"></i> توليد
 *   </button>
 * </div>
 */

(function() {
    'use strict';

    const API_URL = '/dashboard/api/generate-code/';

    // الحصول على CSRF token
    function getCSRFToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        if (cookie) return cookie.split('=')[1];
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input) return input.value;
        return '';
    }

    // توليد كود جديد
    async function generateCode(model, prefix, field) {
        let url = `${API_URL}?model=${encodeURIComponent(model)}`;
        if (prefix) url += `&prefix=${encodeURIComponent(prefix)}`;
        if (field) url += `&field=${encodeURIComponent(field)}`;

        const response = await fetch(url, {
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest',
            }
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'فشل في توليد الكود');
        }
        
        return data.code;
    }

    // إنشاء زر التوليد
    function createGenerateButton(input, model, prefix, field) {
        // تجنب الإضافة المزدوجة
        if (input.dataset.codeGenInitialized) return;
        input.dataset.codeGenInitialized = 'true';

        const wrapper = document.createElement('div');
        wrapper.className = 'code-generator-wrapper';
        wrapper.style.cssText = 'position: relative; display: flex; align-items: center; gap: 6px;';

        // لف الحقل بالـ wrapper
        const parent = input.parentNode;
        parent.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        // إنشاء الزر
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-outline-primary btn-sm btn-generate-code';
        btn.title = 'توليد كود تلقائي';
        btn.style.cssText = 'white-space: nowrap; min-width: 42px; height: 38px; border-radius: 6px; display: flex; align-items: center; justify-content: center; gap: 4px; font-size: 13px; transition: all 0.2s;';
        btn.innerHTML = '<i class="fas fa-magic"></i> <span class="d-none d-md-inline">توليد</span>';

        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const originalHTML = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            try {
                const code = await generateCode(model, prefix, field);
                input.value = code;
                input.focus();
                
                // تأثير بصري للنجاح
                input.style.borderColor = '#28a745';
                input.style.boxShadow = '0 0 0 0.2rem rgba(40, 167, 69, 0.25)';
                btn.innerHTML = '<i class="fas fa-check text-success"></i>';
                btn.className = 'btn btn-outline-success btn-sm btn-generate-code';
                
                setTimeout(() => {
                    input.style.borderColor = '';
                    input.style.boxShadow = '';
                    btn.innerHTML = originalHTML;
                    btn.className = 'btn btn-outline-primary btn-sm btn-generate-code';
                }, 2000);
                
                // إطلاق حدث change
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new Event('input', { bubbles: true }));
                
            } catch (error) {
                console.error('Code generation error:', error);
                input.style.borderColor = '#dc3545';
                input.style.boxShadow = '0 0 0 0.2rem rgba(220, 53, 69, 0.25)';
                btn.innerHTML = '<i class="fas fa-times text-danger"></i>';
                btn.className = 'btn btn-outline-danger btn-sm btn-generate-code';
                
                // عرض رسالة الخطأ
                showToast(error.message || 'فشل في توليد الكود', 'error');
                
                setTimeout(() => {
                    input.style.borderColor = '';
                    input.style.boxShadow = '';
                    btn.innerHTML = originalHTML;
                    btn.className = 'btn btn-outline-primary btn-sm btn-generate-code';
                }, 3000);
            } finally {
                btn.disabled = false;
            }
        });

        wrapper.appendChild(btn);
    }

    // عرض رسالة toast
    function showToast(message, type) {
        // محاولة استخدام toastr إذا كان متاحاً
        if (typeof toastr !== 'undefined') {
            if (type === 'error') toastr.error(message);
            else toastr.success(message);
            return;
        }
        
        // fallback: إنشاء toast بسيط
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
            z-index: 99999; padding: 12px 24px; border-radius: 8px;
            color: #fff; font-size: 14px; font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            background: ${type === 'error' ? '#dc3545' : '#28a745'};
            animation: slideDown 0.3s ease;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideUp 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // إضافة CSS animations
    function addStyles() {
        if (document.getElementById('code-generator-styles')) return;
        const style = document.createElement('style');
        style.id = 'code-generator-styles';
        style.textContent = `
            @keyframes slideDown {
                from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
                to { opacity: 1; transform: translateX(-50%) translateY(0); }
            }
            @keyframes slideUp {
                from { opacity: 1; transform: translateX(-50%) translateY(0); }
                to { opacity: 0; transform: translateX(-50%) translateY(-20px); }
            }
            .btn-generate-code:hover {
                transform: scale(1.05);
                box-shadow: 0 2px 8px rgba(0,123,255,0.3);
            }
            .code-generator-wrapper input {
                flex: 1;
            }
        `;
        document.head.appendChild(style);
    }

    // البحث عن جميع حقول الكود وإضافة الأزرار تلقائياً
    function initAutoCodeGenerators() {
        addStyles();

        // 1. البحث عن الحقول بـ data-code-model
        document.querySelectorAll('input[data-code-model]').forEach(input => {
            const model = input.dataset.codeModel;
            const prefix = input.dataset.codePrefix || '';
            const field = input.dataset.codeField || '';
            createGenerateButton(input, model, prefix, field);
        });

        // 2. البحث التلقائي عن حقول الكود المعروفة بناءً على اسم الحقل
        const codeFieldMappings = {
            'id_code': null,           // سيتم تحديد الموديل من السياق
            'id_customer_code': 'crm.Customer',
            'id_internal_code': 'inventory.Product',
            'id_employee_id': null,    // خاص بالمستخدمين
            'id_barcode': null,        // باركود مختلف
        };

        // تحديد الموديل بناءً على URL الصفحة
        function detectModelFromURL() {
            const path = window.location.pathname.toLowerCase();
            const mappings = [
                [/\/branches\//, 'branches.Branch'],
                [/\/accounting\/cost-centers?\//, 'accounting.CostCenter'],
                [/\/accounting\/accounts?\//, 'accounting.Account'],
                [/\/accounting\/banks?\//, 'accounting.Bank'],
                [/\/accounting\/electronic-accounts?\//, 'accounting.ElectronicAccount'],
                [/\/accounting\/treasur/, 'accounting.Treasury'],
                [/\/accounting\/fawry/, 'accounting.FawryMachine'],
                [/\/accounting\/visa-machine/, 'accounting.VisaMachine'],
                [/\/accounting\/cost-drivers?\//, 'accounting.CostDriver'],
                [/\/accounting\/cost-pools?\//, 'accounting.CostPool'],
                [/\/accounting\/financial-analysis-?1/, 'accounting.FinancialAnalysis1'],
                [/\/accounting\/financial-analysis-?2/, 'accounting.FinancialAnalysis2'],
                [/\/accounting\/fixed-assets?\//, 'accounting.FixedAsset'],
                [/\/inventory\/products?\//, 'inventory.Product'],
                [/\/inventory\/locations?\//, 'inventory.Location'],
                [/\/crm\/customers?\//, 'crm.Customer'],
                [/\/crm\/regions?\//, 'crm.Region'],
                [/\/hr\/departments?\//, 'hr.Department'],
                [/\/hr\/job-positions?\//, 'hr.JobPosition'],
                [/\/hr\/allowance-types?\//, 'hr.AllowanceType'],
                [/\/hr\/deduction-types?\//, 'hr.DeductionType'],
                [/\/projects\/types?\//, 'projects.ProjectType'],
                [/\/projects\/categories?\//, 'projects.ProjectCategory'],
                [/\/projects\/(?:create|add|\d+\/edit)/, 'projects.Project'],
                [/\/projects\/contractors?\//, 'projects.Contractor'],
                [/\/contracting\/projects?\//, 'contracting.ContractingProject'],
                [/\/contracting\/materials?\//, 'contracting.ContractingMaterial'],
                [/\/contracting\/equipment\//, 'contracting.ContractingEquipment'],
                [/\/taxes\/categor/, 'taxes.TaxCategory'],
                [/\/tax[_-]system\/types?\//, 'tax_system.TaxType'],
                [/\/fixed[_-]assets\/categor/, 'fixed_assets.AssetCategory'],
                [/\/ecommerce\/coupons?\//, 'ecommerce.Coupon'],
                [/\/production\/work-centers?\//, 'production.ProductionWorkCenter'],
                [/\/production\/stages?\//, 'production.ProductionStage'],
                [/\/maintenance\/machine-categor/, 'maintenance.MachineCategory'],
                [/\/maintenance\/machines?\//, 'maintenance.Machine'],
                [/\/maintenance\/types?\//, 'maintenance.MaintenanceType'],
                [/\/maintenance\/spare-parts?\//, 'maintenance.SparePart'],
                [/\/quality[_-]control\/standards?\//, 'quality_control.QualityStandard'],
                [/\/quality[_-]control\/inspection-types?\//, 'quality_control.InspectionType'],
                [/\/quality[_-]control\/inspections?\//, 'quality_control.QualityInspection'],
                [/\/quality[_-]control\/issues?\//, 'quality_control.QualityIssue'],
                [/\/home[_-]services\/service-types?\//, 'home_services.ServiceType'],
                [/\/home[_-]services\/maintenance-categor/, 'home_services.MaintenanceCategory'],
                [/\/home[_-]services\/cleaning-packages?\//, 'home_services.CleaningPackage'],
                [/\/shipping\/companies?\//, 'shipping.ShippingCompany'],
                [/\/shipping\/zones?\//, 'shipping.ShippingZone'],
                [/\/loyalty\/programs?\//, 'loyalty.LoyaltyProgram'],
                [/\/partners\/suppliers?\//, 'partners.Supplier'],
                [/\/subscriptions\/plans?\//, 'subscriptions.SubscriptionPlan'],
                [/\/budgeting\/fiscal-years?\//, 'budgeting.FiscalYear'],
                [/\/compliance[_-]management\/standards?\//, 'compliance_management.ComplianceStandard'],
                [/\/attendance\/work-locations?\//, 'attendance.WorkLocation'],
                [/\/showrooms?\//, 'showrooms.Showroom'],
                [/\/dashboard\/pages?\//, 'core.Page'],
                [/\/dashboard\/branches\//, 'core.Branch'],
            ];

            for (const [pattern, model] of mappings) {
                if (pattern.test(path)) return model;
            }
            return null;
        }

        // البحث عن حقول code في الصفحة بدون data-code-model
        const codeInput = document.getElementById('id_code');
        if (codeInput && !codeInput.dataset.codeModel && !codeInput.dataset.codeGenInitialized) {
            const model = detectModelFromURL();
            if (model) {
                createGenerateButton(codeInput, model, '', '');
            }
        }

        // حقل customer_code
        const customerCodeInput = document.getElementById('id_customer_code');
        if (customerCodeInput && !customerCodeInput.dataset.codeGenInitialized) {
            createGenerateButton(customerCodeInput, 'crm.Customer', '', 'customer_code');
        }

        // حقل internal_code
        const internalCodeInput = document.getElementById('id_internal_code');
        if (internalCodeInput && !internalCodeInput.dataset.codeGenInitialized) {
            createGenerateButton(internalCodeInput, 'inventory.Product', '', 'internal_code');
        }
    }

    // تهيئة عند تحميل الصفحة
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAutoCodeGenerators);
    } else {
        initAutoCodeGenerators();
    }

    // مراقبة التغييرات الديناميكية (للنماذج التي تُحمل بـ AJAX)
    const observer = new MutationObserver(function(mutations) {
        let hasNewInputs = false;
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) {
                    if (node.querySelector && (
                        node.querySelector('input[data-code-model]') ||
                        node.querySelector('#id_code') ||
                        node.querySelector('#id_customer_code') ||
                        node.querySelector('#id_internal_code')
                    )) {
                        hasNewInputs = true;
                    }
                }
            });
        });
        if (hasNewInputs) {
            setTimeout(initAutoCodeGenerators, 100);
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    // تصدير الدوال للاستخدام الخارجي
    window.CodeGenerator = {
        generate: generateCode,
        init: initAutoCodeGenerators,
        addButton: createGenerateButton,
    };

})();
