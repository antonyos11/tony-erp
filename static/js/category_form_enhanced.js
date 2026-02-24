// تحسينات نموذج إضافة صنف
document.addEventListener('DOMContentLoaded', function() {
    // تحديث المعاينة في الوقت الفعلي
    const nameInput = document.querySelector('input[name="name"]');
    const previewName = document.getElementById('previewName');
    
    if (nameInput && previewName) {
        nameInput.addEventListener('input', function() {
            previewName.textContent = this.value || 'اسم الفئة';
        });
    }
    
    // اختيار الأيقونة
    const iconOptions = document.querySelectorAll('.icon-option');
    const iconInput = document.querySelector('input[name="icon"]');
    const previewIcon = document.querySelector('.preview-icon i');
    
    iconOptions.forEach(option => {
        option.addEventListener('click', function() {
            iconOptions.forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            
            const iconClass = this.querySelector('i').className;
            if (iconInput) iconInput.value = iconClass;
            if (previewIcon) previewIcon.className = iconClass;
            
            // تأثير الضغط
            this.style.transform = 'scale(0.9)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
    
    // اختيار اللون
    const colorOptions = document.querySelectorAll('.color-option');
    const colorInput = document.querySelector('input[name="color"]');
    const categoryPreview = document.querySelector('.category-preview');
    
    colorOptions.forEach(option => {
        option.addEventListener('click', function() {
            colorOptions.forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            
            const color = this.style.backgroundColor;
            if (colorInput) colorInput.value = color;
            if (categoryPreview) {
                // تحديث gradient بناءً على اللون المختار
                const rgb = this.style.backgroundColor.match(/\d+/g);
                if (rgb) {
                    const r = parseInt(rgb[0]);
                    const g = parseInt(rgb[1]);
                    const b = parseInt(rgb[2]);
                    
                    // إنشاء لون أغمق قليلاً للـ gradient
                    const r2 = Math.max(0, r - 30);
                    const g2 = Math.max(0, g - 30);
                    const b2 = Math.max(0, b - 30);
                    
                    categoryPreview.style.background = `linear-gradient(135deg, rgb(${r},${g},${b}) 0%, rgb(${r2},${g2},${b2}) 100%)`;
                }
            }
            
            // تأثير الاختيار
            this.style.transform = 'scale(0.9)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
    
    // رفع الصورة
    const fileInput = document.querySelector('input[type="file"]');
    const uploadArea = document.querySelector('.upload-area');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    
    if (fileInput && uploadArea) {
        // عند النقر على المنطقة
        uploadArea.addEventListener('click', function() {
            fileInput.click();
        });
        
        // عند اختيار ملف
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    if (previewImg && imagePreview) {
                        previewImg.src = event.target.result;
                        uploadArea.style.display = 'none';
                        imagePreview.style.display = 'block';
                    }
                };
                reader.readAsDataURL(file);
            }
        });
        
        // السحب والإفلات
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.style.borderColor = '#667eea';
            this.style.backgroundColor = '#f7fafc';
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.style.borderColor = '#cbd5e0';
            this.style.backgroundColor = '#f7fafc';
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.borderColor = '#cbd5e0';
            this.style.backgroundColor = '#f7fafc';
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });
    }
    
    // تفعيل التلميحات
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // التحقق من صحة النموذج
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const name = nameInput?.value.trim();
            if (!name) {
                e.preventDefault();
                alert('يرجى إدخال اسم الفئة');
                nameInput?.focus();
                return false;
            }
        });
    }
    
    // تأثيرات الأزرار
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('mousedown', function() {
            this.style.transform = 'scale(0.95)';
        });
        
        btn.addEventListener('mouseup', function() {
            this.style.transform = '';
        });
    });
    
    // تأثير التمرير على الأقسام
    const sections = document.querySelectorAll('.form-section');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });
    
    sections.forEach((section, index) => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        section.style.transition = `all 0.5s ease ${index * 0.1}s`;
        observer.observe(section);
    });
});
