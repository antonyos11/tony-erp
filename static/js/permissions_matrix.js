/**
 * Permissions Matrix Interactive Management
 * إدارة مصفوفة الصلاحيات - تفاعلية
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ============================================================================
    // تفعيل النقر على الدوائر لتغيير الصلاحيات
    // ============================================================================
    
    const permissionCells = document.querySelectorAll('.permission-cell');
    
    permissionCells.forEach(cell => {
        cell.addEventListener('click', function(e) {
            e.preventDefault();
            
            const roleId = this.dataset.roleId;
            const module = this.dataset.module;
            const action = this.dataset.action;
            const currentStatus = this.dataset.allowed === 'true';
            
            // تغيير الحالة
            const newStatus = !currentStatus;
            
            // تحديث الواجهة فوراً (Optimistic UI)
            updateCellUI(this, newStatus);
            
            // إرسال للسيرفر
            updatePermissionAjax(roleId, module, action, newStatus, this);
        });
        
        // تغيير المؤشر ليد
        cell.style.cursor = 'pointer';
    });
    
    // ============================================================================
    // تحديث واجهة الخلية
    // ============================================================================
    
    function updateCellUI(cell, isAllowed) {
        const circle = cell.querySelector('.permission-circle');
        const checkbox = cell.querySelector('input[type="checkbox"]');
        
        if (isAllowed) {
            circle.style.backgroundColor = '#28a745'; // أخضر
            circle.innerHTML = '✓';
            if (checkbox) checkbox.checked = true;
        } else {
            circle.style.backgroundColor = '#dc3545'; // أحمر
            circle.innerHTML = '✗';
            if (checkbox) checkbox.checked = false;
        }
        
        cell.dataset.allowed = isAllowed;
    }
    
    // ============================================================================
    // إرسال تحديث عبر AJAX
    // ============================================================================
    
    function updatePermissionAjax(roleId, module, action, isAllowed, cell) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        fetch('/users/permissions/update-ajax/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: new URLSearchParams({
                'role_id': roleId,
                'module': module,
                'action': action,
                'is_allowed': isAllowed
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // نجح التحديث
                showToast('تم التحديث بنجاح', 'success');
            } else {
                // فشل - إرجاع الحالة القديمة
                updateCellUI(cell, !isAllowed);
                showToast('خطأ: ' + data.message, 'error');
            }
        })
        .catch(error => {
            // خطأ في الاتصال - إرجاع الحالة القديمة
            updateCellUI(cell, !isAllowed);
            showToast('خطأ في الاتصال بالسيرفر', 'error');
            console.error('Error:', error);
        });
    }
    
    // ============================================================================
    // تطبيق قالب افتراضي
    // ============================================================================
    
    const applyTemplateButtons = document.querySelectorAll('.apply-template-btn');
    
    applyTemplateButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            const roleId = this.dataset.roleId;
            const roleName = this.dataset.roleName;
            
            if (confirm(`هل تريد تطبيق القالب الافتراضي على دور "${roleName}"؟\n\nسيتم استبدال كل الصلاحيات الحالية.`)) {
                window.location.href = `/users/permissions/apply-template/${roleId}/`;
            }
        });
    });
    
    // ============================================================================
    // نسخ صلاحيات من دور لآخر
    // ============================================================================
    
        const exportBtn = document.getElementById('export-matrix-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', function() {
                showToast('تحميل Excel قريباً (يرجى الحفظ كـ PDF مؤقتاً)', 'info');
            });
        }
            const toRole = toRoleSelect.value;
            
            if (!fromRole || !toRole) {
                showToast('يرجى اختيار الدورين', 'warning');
                return;
    const style = document.createElement('style');
    style.textContent = `
        @media print { .no-print { display: none !important; } }
    `;
    document.head.appendChild(style);
    const columnHeaders = document.querySelectorAll('.action-header');
    
    columnHeaders.forEach(header => {
        header.addEventListener('dblclick', function() {
            const action = this.dataset.action;
            const cells = document.querySelectorAll(`.permission-cell[data-action="${action}"]`);
            
            // فحص إذا كانت كلها مفعّلة
            let allEnabled = true;
            cells.forEach(cell => {
                if (cell.dataset.allowed !== 'true') {
                    allEnabled = false;
                }
            });
            
            // عكس الحالة
            const newStatus = !allEnabled;
            
            cells.forEach(cell => {
                const roleId = cell.dataset.roleId;
                const module = cell.dataset.module;
                
                updateCellUI(cell, newStatus);
                updatePermissionAjax(roleId, module, action, newStatus, cell);
            });
        });
        
        // إضافة hint
        header.title = 'انقر مرتين لتفعيل/تعطيل كل صلاحيات هذا العمود';
    });
    
    // ============================================================================
    // Toast notifications
    // ============================================================================
    
    function showToast(message, type = 'info') {
        // إنشاء toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#ffc107'};
            color: white;
            border-radius: 5px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 9999;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(toast);
        
        // إزالة بعد 3 ثواني
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
    
    // ============================================================================
    // طباعة المصفوفة
    // ============================================================================
    
    const printBtn = document.getElementById('print-matrix-btn');
    
    if (printBtn) {
        printBtn.addEventListener('click', function() {
            window.print();
        });
    }
    
    // ============================================================================
    // تصدير إلى Excel
    // ============================================================================
    
    const exportBtn = document.getElementById('export-matrix-btn');
    
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            // TODO: تنفيذ التصدير
            showToast('جاري تصدير المصفوفة...', 'info');
        });
    }
    
});

// ============================================================================
// CSS Animations
// ============================================================================

const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .permission-cell {
        transition: all 0.2s ease;
    }
    
    .permission-cell:hover {
        transform: scale(1.1);
    }
    
    .permission-circle {
        transition: all 0.3s ease;
    }
    
    @media print {
        .no-print {
            display: none !important;
        }
    }
`;

document.head.appendChild(style);


