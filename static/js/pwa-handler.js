/**
 * PWA Handler - معالج تطبيق الويب التقدمي
 * يدير تسجيل Service Worker وعرض زر التثبيت
 */

(function() {
  'use strict';

  // متغير لحفظ حدث التثبيت
  let deferredPrompt = null;
  let installButton = null;

  // تسجيل Service Worker
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/js/service-worker.js')
        .then((registration) => {
          console.log('✅ Service Worker مسجل بنجاح:', registration.scope);
          
          // التحقق من التحديثات
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // يوجد تحديث جديد
                showUpdateNotification();
              }
            });
          });
        })
        .catch((error) => {
          console.log('❌ فشل تسجيل Service Worker:', error);
        });
    });
  }

  // التقاط حدث التثبيت
  window.addEventListener('beforeinstallprompt', (e) => {
    console.log('📱 التطبيق قابل للتثبيت');
    e.preventDefault();
    deferredPrompt = e;
    showInstallButton();
  });

  // إنشاء زر التثبيت
  function showInstallButton() {
    // تحقق إذا كان الزر موجود مسبقاً
    if (document.getElementById('pwa-install-btn')) {
      document.getElementById('pwa-install-btn').style.display = 'flex';
      return;
    }

    // إنشاء الزر العائم
    installButton = document.createElement('button');
    installButton.id = 'pwa-install-btn';
    installButton.className = 'pwa-install-button';
    installButton.innerHTML = `
      <i class="bi bi-download"></i>
      <span>تثبيت التطبيق</span>
    `;
    installButton.setAttribute('title', 'تثبيت الشامل ERP كتطبيق');
    
    // إضافة الأنماط
    const style = document.createElement('style');
    style.textContent = `
      .pwa-install-button {
        position: fixed;
        bottom: 20px;
        left: 20px;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px 20px;
        background: linear-gradient(135deg, #00d4aa 0%, #00b894 100%);
        color: white;
        border: none;
        border-radius: 50px;
        font-size: 14px;
        font-weight: 600;
        font-family: inherit;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0, 212, 170, 0.4);
        transition: all 0.3s ease;
        animation: pwa-pulse 2s infinite;
      }
      
      .pwa-install-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 212, 170, 0.5);
      }
      
      .pwa-install-button i {
        font-size: 18px;
      }
      
      @keyframes pwa-pulse {
        0%, 100% { box-shadow: 0 4px 15px rgba(0, 212, 170, 0.4); }
        50% { box-shadow: 0 4px 25px rgba(0, 212, 170, 0.6); }
      }
      
      @media (max-width: 576px) {
        .pwa-install-button {
          bottom: 70px;
          left: 50%;
          transform: translateX(-50%);
          padding: 10px 16px;
          font-size: 13px;
        }
        .pwa-install-button:hover {
          transform: translateX(-50%) translateY(-2px);
        }
      }
      
      .pwa-update-toast {
        position: fixed;
        bottom: 80px;
        left: 20px;
        right: 20px;
        max-width: 400px;
        margin: 0 auto;
        z-index: 10000;
        background: #1e3a5f;
        color: white;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        gap: 12px;
        animation: slideUp 0.3s ease;
      }
      
      @keyframes slideUp {
        from { transform: translateY(100px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
      }
      
      .pwa-update-toast button {
        background: #00d4aa;
        border: none;
        color: #1e3a5f;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        white-space: nowrap;
      }
    `;
    document.head.appendChild(style);
    
    // إضافة الزر للصفحة
    document.body.appendChild(installButton);
    
    // حدث النقر
    installButton.addEventListener('click', installApp);
  }

  // تثبيت التطبيق
  async function installApp() {
    if (!deferredPrompt) {
      console.log('لا يوجد حدث تثبيت');
      return;
    }

    // إخفاء الزر
    if (installButton) {
      installButton.style.display = 'none';
    }

    // عرض نافذة التثبيت
    deferredPrompt.prompt();
    
    // انتظار اختيار المستخدم
    const { outcome } = await deferredPrompt.userChoice;
    console.log('اختيار المستخدم:', outcome);
    
    if (outcome === 'accepted') {
      console.log('✅ تم تثبيت التطبيق');
      showSuccessMessage();
    } else {
      // إظهار الزر مجدداً
      if (installButton) {
        installButton.style.display = 'flex';
      }
    }
    
    deferredPrompt = null;
  }

  // عرض رسالة نجاح التثبيت
  function showSuccessMessage() {
    const toast = document.createElement('div');
    toast.className = 'pwa-update-toast';
    toast.innerHTML = `
      <i class="bi bi-check-circle-fill" style="font-size: 24px; color: #00d4aa;"></i>
      <span style="flex: 1;">تم تثبيت التطبيق بنجاح! يمكنك الآن فتحه من الشاشة الرئيسية</span>
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.remove();
    }, 5000);
  }

  // عرض إشعار التحديث
  function showUpdateNotification() {
    const toast = document.createElement('div');
    toast.className = 'pwa-update-toast';
    toast.innerHTML = `
      <i class="bi bi-arrow-repeat" style="font-size: 24px;"></i>
      <span style="flex: 1;">يتوفر تحديث جديد للتطبيق</span>
      <button onclick="location.reload()">تحديث الآن</button>
    `;
    document.body.appendChild(toast);
  }

  // التحقق من حالة التشغيل كتطبيق
  window.addEventListener('appinstalled', () => {
    console.log('✅ التطبيق مثبت الآن');
    deferredPrompt = null;
    if (installButton) {
      installButton.remove();
    }
  });

  // عرض معلومات التطبيق في وضع standalone
  if (window.matchMedia('(display-mode: standalone)').matches) {
    console.log('📱 التطبيق يعمل في وضع التطبيق المستقل');
    document.body.classList.add('pwa-standalone');
  }

})();
