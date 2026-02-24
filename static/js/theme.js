// Tony ERB Theme Manager: light/dark toggle with persistence and RTL support
(function() {
  function applyTheme(theme) {
    console.log('تطبيق الثيم:', theme);
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (e) {}
    var icon = document.getElementById('themeIcon');
    if (icon) {
      icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
    }
    // Add body class for CSS hooks if needed
    document.body.classList.toggle('theme-dark', theme === 'dark');
  }

  document.addEventListener('DOMContentLoaded', function() {
    console.log('تحميل مدير الثيمات...');
    var btn = document.getElementById('themeToggle');
    if (btn) {
      console.log('تم العثور على زر تبديل الثيم');
      btn.addEventListener('click', function() {
        var current = document.documentElement.getAttribute('data-theme') || 'light';
        console.log('الثيم الحالي:', current);
        var newTheme = current === 'dark' ? 'light' : 'dark';
        console.log('الثيم الجديد:', newTheme);
        applyTheme(newTheme);
      });
    } else {
      console.error('لم يتم العثور على زر تبديل الثيم!');
    }
    // Ensure icon matches current theme after DOM ready
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    console.log('تطبيق الثيم المحفوظ:', current);
    applyTheme(current);
  });
})();
