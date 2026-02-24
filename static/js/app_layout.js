// Layout & nav logic (sidebar toggle, theme, dir, submenu) – unified & enhanced
(function(){
  document.addEventListener('DOMContentLoaded', function(){
    const body = document.body;
    const toggleBtn = document.getElementById('sidebarToggle');
    const toggleBtn2 = document.getElementById('sidebarToggle2');
    const closeBtn = document.getElementById('sidebarCloseBtn');
    let mobileBackdrop = document.getElementById('sidebarMobileBackdrop');
    // Fallback: ensure backdrop exists
    if(!mobileBackdrop){
      mobileBackdrop = document.createElement('div');
      mobileBackdrop.id = 'sidebarMobileBackdrop';
      mobileBackdrop.className = 'sidebar-mobile-backdrop';
      mobileBackdrop.hidden = true;
      document.body.appendChild(mobileBackdrop);
    }
    let restoreCollapsedAfterClose = false;
    let scrollPosition = 0;
    
    function openSidebar(){
      // If desktop collapsed is active, temporarily disable it on mobile so labels appear
      if(window.innerWidth < 992 && body.classList.contains('sidebar-collapsed')){
        body.classList.remove('sidebar-collapsed');
        restoreCollapsedAfterClose = true;
      }
      // Save scroll position before fixing body
      scrollPosition = window.pageYOffset || document.documentElement.scrollTop;
      body.classList.add('sidebar-open');
      body.style.top = `-${scrollPosition}px`;
      body.style.position = 'fixed';
      body.style.width = '100%';
      if(mobileBackdrop) mobileBackdrop.hidden=false;
    }
    function closeSidebar(){
      body.classList.remove('sidebar-open');
      body.style.top = '';
      body.style.position = '';
      body.style.width = '';
      // Restore scroll position
      window.scrollTo(0, scrollPosition);
      if(mobileBackdrop) mobileBackdrop.hidden=true;
      if(restoreCollapsedAfterClose && window.innerWidth < 992){
        body.classList.add('sidebar-collapsed');
        restoreCollapsedAfterClose = false;
      }
    }
    function toggleSidebar(){ body.classList.contains('sidebar-open') ? closeSidebar() : openSidebar(); }
    // If loading on mobile, ignore desktop collapsed state to avoid icons-only
    if(window.innerWidth < 992 && body.classList.contains('sidebar-collapsed')){
      body.classList.remove('sidebar-collapsed');
    }
    // Bind togglers
    toggleBtn && toggleBtn.addEventListener('click', toggleSidebar);
    toggleBtn2 && toggleBtn2.addEventListener('click', toggleSidebar);
    closeBtn && closeBtn.addEventListener('click', closeSidebar);
    document.querySelectorAll('[data-sidebar-toggle]').forEach(el=> el.addEventListener('click', toggleSidebar));
    mobileBackdrop && mobileBackdrop.addEventListener('click', closeSidebar);
    // ESC closes on mobile
    document.addEventListener('keydown', e=>{ if(e.key==='Escape' && body.classList.contains('sidebar-open')) closeSidebar(); });
    // Close if resized to desktop
    window.addEventListener('resize', ()=>{ if(window.innerWidth>=992) closeSidebar(); });
    // Edge-swipe to open (mobile)
    let touchStartX = null, touchStartY = null, swiping = false;
    window.addEventListener('touchstart', (e)=>{
      if(window.innerWidth>=992 || body.classList.contains('sidebar-open')) return;
      const dir = document.documentElement.getAttribute('dir') || 'rtl';
      const x = e.touches[0].clientX;
      const y = e.touches[0].clientY;
      const edge = 30; // px from screen edge - increased for better detection
      const isFromEdge = dir==='rtl' ? (window.innerWidth - x) <= edge : x <= edge;
      if(isFromEdge){ touchStartX = x; touchStartY = y; swiping = true; }
    }, {passive:true});
    window.addEventListener('touchmove', (e)=>{
      if(!swiping) return;
      const x = e.touches[0].clientX; const y = e.touches[0].clientY;
      const dx = Math.abs(x - touchStartX); const dy = Math.abs(y - touchStartY);
      if(dx > 30 && dx > dy){ // horizontal intent
        openSidebar(); swiping = false;
      }
    }, {passive:true});
    window.addEventListener('touchend', ()=>{ swiping = false; touchStartX = touchStartY = null; }, {passive:true});
    // Close sidebar when a sidebar link is tapped (mobile)
  document.addEventListener('click', function(e){
      const isSidebarLink = e.target.closest && e.target.closest('.app-sidebar a, .app-sidebar button.sidebar-collapse-btn, .sidebar-flyout a');
      if(isSidebarLink && window.matchMedia('(max-width: 992px)').matches){ closeSidebar(); }
    }, true);

    // New UI banner dismiss persistence
    const banner = document.getElementById('newUiBanner');
    const dismissBtn = document.getElementById('dismissNewUiBanner');
    if (banner) {
      if (localStorage.getItem('hide_new_ui_banner')==='1') { banner.style.display='none'; }
      dismissBtn && dismissBtn.addEventListener('click', ()=>{ banner.style.display='none'; localStorage.setItem('hide_new_ui_banner','1'); });
    }

    // ---------- Theme Handling (single source) ----------
    const themeBtn = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    function applyTheme(theme, userTriggered){
      document.documentElement.setAttribute('data-theme', theme);
      try { localStorage.setItem('theme', theme); } catch(e){}
      body.classList.toggle('theme-dark', theme === 'dark');
      if(themeIcon){ themeIcon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars'; }
      if(userTriggered && window.showToast){ showToast(theme === 'dark' ? 'تم تفعيل الوضع الداكن' : 'تم تفعيل الوضع الفاتح','info'); }
    }
    // Respect already-set (preload script) value, else fallback
    const initialTheme = document.documentElement.getAttribute('data-theme') || localStorage.getItem('theme') || 'light';
    applyTheme(initialTheme, false);
    themeBtn && themeBtn.addEventListener('click', ()=>{
      const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(current, true);
    });

    // ---------- Direction (RTL/LTR) Handling ----------
    const dirBtn = document.getElementById('dirToggle');
    const dirIcon = dirBtn ? dirBtn.querySelector('i') : null;
    function updateDirIcon(dir){
      if(!dirIcon) return;
      // Use different icon orientation for clarity
      dirIcon.className = dir === 'rtl' ? 'bi bi-layout-text-sidebar-reverse' : 'bi bi-layout-text-sidebar';
    }
    function applyDir(dir, userTriggered){
      document.documentElement.setAttribute('dir', dir);
      try { localStorage.setItem('dir', dir); } catch(e){}
      const link = document.getElementById('bootstrapCoreCss');
      if(link){
        const base = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap';
        const hrefTarget = dir==='rtl' ? base+'.rtl.min.css' : base+'.min.css';
        if(link.getAttribute('href') !== hrefTarget){ link.setAttribute('href', hrefTarget); }
      }
      updateDirIcon(dir);
      // أضف/أزل صنف للمساعدة في أي تخصيصات مستقبلية
      document.body.classList.toggle('dir-ltr', dir==='ltr');
      document.body.classList.toggle('dir-rtl', dir==='rtl');
  // تنظيف أي تعارض قديم
  if(dir==='ltr'){ document.body.classList.remove('dir-rtl'); } else { document.body.classList.remove('dir-ltr'); }
      if(userTriggered && window.showToast){ showToast(dir==='rtl' ? 'تم التبديل إلى الاتجاه من اليمين لليسار' : 'Switched to LTR direction','info'); }
    }
    const savedDir = localStorage.getItem('dir');
    if(savedDir){ applyDir(savedDir, false); } else {
      const docDir = document.documentElement.getAttribute('dir') || 'rtl';
      document.body.classList.add(docDir==='rtl' ? 'dir-rtl':'dir-ltr');
      updateDirIcon(docDir);
    }
    dirBtn && dirBtn.addEventListener('click', ()=>{
      const next = document.documentElement.getAttribute('dir') === 'rtl' ? 'ltr' : 'rtl';
      applyDir(next, true);
      window.dispatchEvent(new Event('directionchange'));
    });

  // ---------- Expand current submenu if active ----------
    const currentUrl = window.location.pathname;
    document.querySelectorAll('.sidebar-submenu a').forEach(a=>{
      if(a.getAttribute('href')===currentUrl){
        const ul=a.closest('.sidebar-submenu');
        if(ul && !ul.classList.contains('show')){
          try{ new bootstrap.Collapse(ul,{toggle:true}); }catch(e){}
        }
      }
    });
  });
})();
