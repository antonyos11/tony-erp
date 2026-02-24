// Global UI helpers (auto-dismiss alerts, toast placeholder, common helpers)
(function(){
  function autoDismissAlerts(){
    const alerts = document.querySelectorAll('.alert');
    if(!alerts.length) return;
    alerts.forEach(a=>{
      // Skip if marked persistent
      if(a.classList.contains('alert-persistent')) return;
      const delayAttr = a.getAttribute('data-autoclose');
      const delay = delayAttr ? parseInt(delayAttr,10) : 5000;
      setTimeout(()=>{ try{ new bootstrap.Alert(a).close(); }catch(e){} }, delay);
    });
  }
  document.addEventListener('DOMContentLoaded', autoDismissAlerts);
  window.showToast = window.showToast || function(msg, type){
    type = type || 'info';
    const wrapId = 'globalToasts';
    let wrap = document.getElementById(wrapId);
    if(!wrap){
      wrap = document.createElement('div');
      wrap.id = wrapId;
      wrap.className = 'toast-container position-fixed bottom-0 end-0 p-3';
      document.body.appendChild(wrap);
    }
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-bg-'+(type==='warning'?'warning':'primary')+' border-0 show';
    toast.setAttribute('role','alert');
    toast.innerHTML = '<div class="d-flex"><div class="toast-body">'+msg+'</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>';
    wrap.appendChild(toast);
    setTimeout(()=>{ try{toast.remove();}catch(e){} },4000);
  };
})();
