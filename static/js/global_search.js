// Global search / command palette functionality extracted
(function(){
  document.addEventListener('DOMContentLoaded', function(){
    const searchInput = document.getElementById('globalSearch');
    const resultsBox = document.getElementById('globalSearchResults');
    if(!searchInput || !resultsBox) return;
    let allLinks = [];
    const NORMALIZE = (t)=> (t||'').toLowerCase().trim();
    function collectLinks(){
      const selectors = '.app-sidebar a[href]';
      const seen = new Set();
      allLinks = Array.from(document.querySelectorAll(selectors))
        .filter(a=> a.getAttribute('href') && a.getAttribute('href') !== '#' && a.textContent.trim())
        .map(a=>({text: a.textContent.trim(), href: a.getAttribute('href'), norm: NORMALIZE(a.textContent)}))
        .filter(obj=>{ const key = obj.norm+'|'+obj.href; if(seen.has(key)) return false; seen.add(key); return true; });
    }
    function highlight(text, query){
      const words = query.split(/\s+/).filter(Boolean);
      let html = text;
      words.forEach(w=>{ const rx = new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi'); html = html.replace(rx, m=>`<mark class="px-0 bg-warning bg-opacity-50">${m}</mark>`); });
      return html;
    }
    function renderResults(items, query){
      if(!items.length){ if(query){ resultsBox.innerHTML = '<div class="text-muted small px-2 py-1">لا نتائج</div>'; resultsBox.classList.remove('d-none'); } else { resultsBox.classList.add('d-none'); resultsBox.innerHTML=''; } return; }
      const limited = items.slice(0,12);
      resultsBox.innerHTML = limited.map((it,i)=>`<button type="button" class="list-group-item list-group-item-action" data-href="${it.href}" data-index="${i}" role="option">${highlight(it.text, query)}</button>`).join('');
      resultsBox.classList.remove('d-none');
    }
    function filterLinks(q){
      q = NORMALIZE(q);
      if(!q){ renderResults([], q); return; }
      const words = q.split(/\s+/).filter(Boolean);
      const matches = allLinks.filter(it=> words.every(w=> it.norm.includes(w)) );
      renderResults(matches, q);
    }
    function goFirst(){
      const first = resultsBox.querySelector('[data-href]');
      if(first){ window.location.href = first.getAttribute('data-href'); }
    }
    collectLinks();
    searchInput.addEventListener('focus', ()=>{
      if(allLinks.length===0) collectLinks();
      if(searchInput.value.trim()===''){
        const sample = allLinks.slice(0,8);
        resultsBox.innerHTML = sample.map((it,i)=>`<button type="button" class="list-group-item list-group-item-action" data-href="${it.href}" data-index="${i}" role="option">${it.text}</button>`).join('');
        if(sample.length){ resultsBox.classList.remove('d-none'); }
      }
    });
    const paletteBtn = document.getElementById('commandPaletteBtn');
    paletteBtn && paletteBtn.addEventListener('click', (e)=>{ e.preventDefault(); searchInput.focus(); });
    document.addEventListener('keydown', (e)=>{
      if((e.ctrlKey && (e.key==='k' || e.key==='K')) || (e.ctrlKey && e.shiftKey && (e.key==='f'||e.key==='F'))){ e.preventDefault(); searchInput.focus(); }
    });
    document.addEventListener('click', e=>{ if(!resultsBox.contains(e.target) && e.target !== searchInput){ resultsBox.classList.add('d-none'); }});
    searchInput.addEventListener('input', e=> filterLinks(e.target.value));
    searchInput.addEventListener('keydown', e=>{
      if(e.key==='Enter'){ e.preventDefault(); goFirst(); }
      if(e.key==='ArrowDown'){ const btns = resultsBox.querySelectorAll('button'); if(btns.length){ e.preventDefault(); btns[0].focus(); }}
      if(e.key==='Escape'){ resultsBox.classList.add('d-none'); }
    });
    resultsBox.addEventListener('click', e=>{ const btn = e.target.closest('button[data-href]'); if(btn){ window.location.href = btn.getAttribute('data-href'); } });
    resultsBox.addEventListener('keydown', e=>{
      const btns = Array.from(resultsBox.querySelectorAll('button'));
      const idx = btns.indexOf(document.activeElement);
      if(e.key==='ArrowDown'){ e.preventDefault(); if(idx < btns.length-1) btns[idx+1].focus(); }
      else if(e.key==='ArrowUp'){ e.preventDefault(); if(idx>0) btns[idx-1].focus(); else searchInput.focus(); }
      else if(e.key==='Enter'){ e.preventDefault(); document.activeElement.click(); }
      else if(e.key==='Escape'){ resultsBox.classList.add('d-none'); searchInput.focus(); }
    });
    document.querySelectorAll('.sidebar-collapse-btn').forEach(btn=> btn.addEventListener('click', ()=> setTimeout(collectLinks, 400)));
    setTimeout(collectLinks, 1000);
  });
})();
