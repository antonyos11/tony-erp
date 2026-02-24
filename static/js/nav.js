(function () {
  // Minimal nav helpers; prevent errors if referenced from templates
  document.addEventListener('DOMContentLoaded', function () {
    // Sidebar mobile backdrop toggle
    var sidebar = document.querySelector('.app-sidebar');
    var backdrop = document.getElementById('sidebarMobileBackdrop');
    var toggles = document.querySelectorAll('[data-toggle="sidebar"]');
    toggles.forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!sidebar) return;
        var open = sidebar.classList.toggle('open');
        if (backdrop) {
          if (open) { backdrop.removeAttribute('hidden'); }
          else { backdrop.setAttribute('hidden', ''); }
        }
      });
    });
    if (backdrop) {
      backdrop.addEventListener('click', function () {
        if (sidebar && sidebar.classList.contains('open')) {
          sidebar.classList.remove('open');
          backdrop.setAttribute('hidden', '');
        }
      });
    }
  });
})();
