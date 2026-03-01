// RITA ERP - Main JS
// نقطة الدخول الرئيسية لملفات JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // إغلاق التنبيهات تلقائياً بعد 5 ثواني
    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
});
