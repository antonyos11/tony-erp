// Shared finance helpers (lightweight)
// computeTotals(root, {discount, paid}) expects elements:
//  .item-total (textContent numeric) and ids: subtotal,total,total2,remaining,remaining2
function computeTotals(root, opts){
  try{
    root = root || document;
    const discount = parseFloat((opts&&opts.discount)||0) || 0;
    const paid = parseFloat((opts&&opts.paid)||0) || 0;
    let subtotal = 0;
    root.querySelectorAll('.item-total').forEach(el=>{ const v=parseFloat(el.textContent)||0; subtotal+=v; });
    const total = subtotal - discount;
    const remaining = total - paid;
    const map = {subtotal, total, total2:total, remaining, remaining2:remaining};
    Object.entries(map).forEach(([id,val])=>{ const el=root.getElementById?root.getElementById(id):document.getElementById(id); if(el) el.textContent=val.toFixed(2); });
  }catch(e){ console.warn('computeTotals error', e); }
}
window.computeTotals = computeTotals;
