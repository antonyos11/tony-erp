/**
 * Modal Backdrop Fix - إصلاح مشكلة الطبقة الرمادية المتبقية
 * يعمل على إزالة backdrop الـ modal عند إغلاقه
 */
(function() {
    'use strict';

    // منع إنشاء أي backdrop من Bootstrap نهائياً
    function disableBootstrapBackdrop() {
        try {
            if (window.bootstrap && bootstrap.Modal && bootstrap.Modal.Default) {
                bootstrap.Modal.Default.backdrop = false;
                bootstrap.Modal.Default.keyboard = true;
            }
            // تأكيد على كل الـ modals الموجودة
            document.querySelectorAll('.modal').forEach(function(modal) {
                modal.setAttribute('data-bs-backdrop', 'false');
                modal.setAttribute('data-bs-keyboard', 'true');
            });
        } catch (e) {
            // تجاهل الخطأ، سنحاول لاحقاً عبر setTimeout
        }
    }

    // تنظيف الـ backdrop - قوي ومباشر
    function cleanupBackdrop() {
        // إزالة جميع الـ modal-backdrop بالقوة
        document.querySelectorAll('.modal-backdrop, .modal-backdrop.fade, .modal-backdrop.show, .modal-backdrop.fade.show').forEach(function(backdrop) {
            try {
                backdrop.style.display = 'none';
                backdrop.style.opacity = '0';
                backdrop.style.visibility = 'hidden';
                backdrop.style.pointerEvents = 'none';
                backdrop.parentNode.removeChild(backdrop);
            } catch (e) {
                // تجاهل
            }
        });
        
        // التحقق من عدم وجود modals مفتوحة
        const openModals = document.querySelectorAll('.modal.show');
        if (openModals.length === 0) {
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');
            document.body.style.removeProperty('margin-right');
            document.body.style.overflow = 'auto';
        }
    }
    
    // إزالة فورية للـ backdrop
    function forceRemoveBackdrop() {
        requestAnimationFrame(function() {
            cleanupBackdrop();
            // تأخير إضافي للتأكد
            setTimeout(cleanupBackdrop, 100);
            setTimeout(cleanupBackdrop, 300);
            setTimeout(cleanupBackdrop, 500);
        });
    }

    // إغلاق sidebar عند فتح modal
    function closeSidebarOnModalOpen() {
        document.body.classList.remove('sidebar-open');
        const sidebarBackdrop = document.getElementById('sidebarMobileBackdrop');
        if (sidebarBackdrop) {
            sidebarBackdrop.setAttribute('hidden', 'true');
        }
    }

    // إضافة مستمع لجميع الـ modals
    function initModalFix() {
        // مستمع عام لفتح الـ modal - إغلاق sidebar
        document.addEventListener('show.bs.modal', function(e) {
            closeSidebarOnModalOpen();
        });
        
        // مستمع عام لإغلاق الـ modal - أقوى
        document.addEventListener('hidden.bs.modal', function(e) {
            forceRemoveBackdrop();
        });
        
        // مستمع لـ hide أيضاً
        document.addEventListener('hide.bs.modal', function(e) {
            setTimeout(forceRemoveBackdrop, 50);
        });

        // مستمع للنقر على الـ backdrop - مباشر
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('modal-backdrop')) {
                e.preventDefault();
                e.stopPropagation();
                // إغلاق جميع الـ modals المفتوحة
                document.querySelectorAll('.modal.show').forEach(function(modal) {
                    const bsModal = bootstrap.Modal.getInstance(modal);
                    if (bsModal) {
                        bsModal.hide();
                    }
                    modal.classList.remove('show');
                    modal.style.display = 'none';
                });
                forceRemoveBackdrop();
            }
        });

        // مستمع لزر Escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                forceRemoveBackdrop();
            }
        });

        // إصلاح الـ modals الموجودة
        document.querySelectorAll('.modal').forEach(function(modal) {
            modal.addEventListener('show.bs.modal', closeSidebarOnModalOpen);
            modal.addEventListener('hidden.bs.modal', forceRemoveBackdrop);
            modal.addEventListener('hide.bs.modal', function() {
                setTimeout(forceRemoveBackdrop, 50);
            });
        });
        
        // تنظيف أي backdrop متبقي عند تحميل الصفحة
        setTimeout(cleanupBackdrop, 100);
        setTimeout(cleanupBackdrop, 500);
        setTimeout(cleanupBackdrop, 1000);
    }

    // تشغيل عند تحميل الصفحة
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initModalFix);
    } else {
        initModalFix();
    }

    // محاولة تعطيل الـ backdrop مباشرة وبعد التحميل
    disableBootstrapBackdrop();
    setTimeout(disableBootstrapBackdrop, 50);
    setTimeout(disableBootstrapBackdrop, 200);
    setTimeout(disableBootstrapBackdrop, 500);
    document.addEventListener('DOMContentLoaded', disableBootstrapBackdrop);

    // تصدير للاستخدام الخارجي
    window.cleanupModalBackdrop = cleanupBackdrop;
    window.forceRemoveBackdrop = forceRemoveBackdrop;

})();
