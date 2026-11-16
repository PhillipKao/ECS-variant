'use strict';
const state = JSON.parse(document.getElementById('wiki-state').textContent);
const $ = selector => document.querySelector(selector);
const rows = [...document.querySelectorAll('.variant')];
const form = $('#lab-form');
const key = 'biolove.variant-wiki.lab-drafts.v1';
let drafts = [], storageAvailable = true, token = null;
try { drafts = JSON.parse(localStorage.getItem(key) || '[]'); if (!Array.isArray(drafts)) throw Error('草稿格式錯誤'); } catch { drafts = []; storageAvailable = false; }
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge = label => `<span class="badge ${['Pathogenic','Likely pathogenic'].includes(label) ? 'red' : ['Benign','Likely benign'].includes(label) ? 'green' : 'amber'}">${esc(label)}</span>`;
function formal(acc) { return state.labs.find(x => x.accession === acc)?.history || []; }
function isFormalDraft(d) { return state.labs.some(item => item.history.some(h => h.record_id === d.record_id || (item.accession === d.accession && ['date','classification','scope','note'].every(k => h[k] === d[k])))); }
function draftRows(acc) { return drafts.filter(x => x.accession === acc && !isFormalDraft(x)); }
function message(text, error = false) { $('#form-message').textContent = text; $('#form-message').className = error ? 'error' : 'success'; }
function persistDrafts(next) {
  if (!storageAvailable) throw Error('瀏覽器無法保存草稿。請啟動本機編輯器後再輸入。');
  localStorage.setItem(key, JSON.stringify(next)); // Change memory only after storage succeeds.
  drafts = next;
}
function combined() {
  const labs = JSON.parse(JSON.stringify(state.labs));
  for (const v of catalog()) {
    const pending = draftRows(v.accession).sort((a,b) => a.date.localeCompare(b.date));
    if (!pending.length) continue;
    let item = labs.find(x => x.accession === v.accession);
    if (!item) { item = Object.fromEntries(['gene','transcript','hgvs','protein','accession'].map(k => [k,v[k]])); item.history = []; labs.push(item); }
    for (const d of pending) {
      if (item.history.some(h => h.record_id === d.record_id || ['date','classification','scope','note'].every(k => h[k] === d[k]))) continue;
      if (item.history.length && d.date < item.history.at(-1).date) throw Error('草稿日期早於專案最近判讀，請先與維護者核對，避免覆寫歷史。');
      item.history.push({revision:(item.history.at(-1)?.revision || 0)+1,date:d.date,classification:d.classification,scope:d.scope,clinvar_version:d.clinvar_version,note:d.note,record_id:d.record_id});
    }
  }
  return labs;
}
function refresh() {
  const term = $('#query').value.trim().toLowerCase(), gene = $('#gene-filter').value, filter = $('#lab-filter').value;
  let count = 0;
  for (const row of rows) {
    const v = catalog().find(v => v.accession === row.dataset.accession);
    const has = formal(v.accession).length + draftRows(v.accession).length > 0;
    row.hidden = ![v.gene,v.transcript,v.hgvs,v.protein,v.accession].join(' ').toLowerCase().includes(term) || (gene && v.gene !== gene) || (filter === 'yes' && !has) || (filter === 'no' && has);
    if (!row.hidden) count++;
  }
  $('#count').textContent = `共 ${count} 個位點 · 點選位點查看解讀與完整歷程`;
  $('#no-results').hidden = count > 0;
}
function render() {
  updateIndex();
  $('#lab-total').textContent = state.labs.reduce((n,x) => n+x.history.length,0);
  for (const row of rows) {
    const acc = row.dataset.accession, history = formal(acc), pending = draftRows(acc);
    const entries = [...history.map(h => ({...h,draft:false})), ...pending.map(h => ({...h,draft:true}))];
    entries.sort((a,b) => a.date.localeCompare(b.date) || ((a.revision || Infinity)-(b.revision || Infinity)));
    let previous = null;
    const html = entries.map(h => {
      const change = !previous ? '首次判讀' : previous.classification === h.classification ? '分類維持不變' : `${previous.classification} → ${h.classification}`;
      previous = h;
      return `<section class="event"><small>${esc(h.date)} · ${h.draft ? '<span class="draft-tag">本機草稿・尚未寫入專案</span>' : '第 '+esc(h.revision)+' 筆'}</small><h4>${esc(change)}</h4>${badge(h.classification)}<p class="multiline">${esc(h.note)}</p><small>${esc(h.scope)} ${h.clinvar_version && /^VCV\d+\.\d+$/.test(h.clinvar_version) ? `· <a href="https://www.ncbi.nlm.nih.gov/clinvar/variation/${h.clinvar_version}/">${h.clinvar_version}</a>` : ''}</small>${h.draft ? `<p><button type="button" class="text-button discard-draft" data-record-id="${esc(h.record_id)}">刪除此筆草稿</button></p>` : ''}</section>`;
    }).reverse().join('');
    row.querySelector('[data-lab-history]').innerHTML = html || '<p class="empty">尚無實驗室判讀。可在右側表單新增第一筆紀錄。</p>';
    row.querySelector('[data-lab-latest]').innerHTML = history.length ? badge(history.at(-1).classification)+`<small>${esc(history.at(-1).date)}</small>` : '尚未判讀';
    if (pending.length) row.querySelector('[data-lab-latest]').innerHTML += `<small>另有 ${pending.length} 筆本機草稿</small>`;
  }
  const pendingCount = drafts.filter(d => !isFormalDraft(d)).length;
  $('#draft-count').textContent = pendingCount ? `此瀏覽器有 ${pendingCount} 筆未正式存檔草稿。匯出包含既有紀錄與草稿，原草稿仍會保留。` : '目前沒有本機草稿。';
  $('#sync-drafts').hidden = !(token && pendingCount);
  refresh();
}
function catalog() {
  const all = new Map(state.variants.map(v => [v.accession,v]));
  for (const item of [...state.labs,...drafts]) {
    if (!all.has(item.accession) && item.gene && item.hgvs) all.set(item.accession,item);
  }
  return [...all.values()];
}
function options(id,values) {
  const list=document.getElementById(id);
  list.replaceChildren(...[...new Set(values)].map(value=>new Option(value,value)));
}
function suggest() {
  const gene=form.elements.gene.value.trim().toUpperCase();
  const matches=catalog().filter(v=>v.gene===gene);
  options('sites',matches.map(v=>v.hgvs));
}
form.elements.gene.addEventListener('input',suggest);
form.elements.hgvs.addEventListener('input',suggest);
function updateIndex() {
  const all=catalog();
  for (const row of [...rows]) if (!all.some(v=>v.accession===row.dataset.accession)) {
    rows.splice(rows.indexOf(row),1);row.remove();
  }
  for (const v of all) {
    if (rows.some(row=>row.dataset.accession===v.accession)) continue;
    const row=document.createElement('details');
    row.className='variant';row.dataset.accession=v.accession;
    row.innerHTML=`<summary><span class="gene">${esc(v.gene)}</span><span class="variant-id"><strong>${esc(v.hgvs)}</strong><small>${esc(v.transcript)}</small></span><span>實驗室位點</span></summary><div class="variant-body"><p>ClinVar 尚無本站核對紀錄</p><h3>實驗室最近判讀</h3><div data-lab-latest></div><div class="lab-heading"><h3>實驗室判讀歷程</h3><button type="button" class="add-lab" data-target="${esc(v.accession)}">新增判讀</button></div><div data-lab-history></div></div>`;
    $('#records').append(row);rows.push(row);
  }
  const genes=[...new Set(all.map(v=>v.gene))].sort();
  options('genes',genes);
  const filter=$('#gene-filter'), saved=filter.value;
  filter.replaceChildren(new Option('全部基因',''),...genes.map(g=>new Option(g,g)));
  if (genes.includes(saved)) filter.value=saved;
  suggest();
  $('#gene-total').textContent=genes.length;
  $('#variant-total').textContent=all.length;
}
const today = new Date(); $('#lab-date').value = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;
for (const id of ['query','gene-filter','lab-filter']) $('#'+id).addEventListener(id === 'query' ? 'input' : 'change',refresh);
$('#records').addEventListener('click',event=>{
  const button=event.target.closest('.add-lab');
  if (!button) return;
  const v=catalog().find(v=>v.accession===button.dataset.target);
  for (const k of ['gene','hgvs']) form.elements[k].value=v[k];
  suggest();$('#lab-panel').scrollIntoView({behavior:'smooth'});$('#lab-date').focus({preventScroll:true});
});
async function saveToProject(entry) {
  const response = await fetch('/api/lab', {method:'POST',headers:{'Content-Type':'application/json','X-Wiki-Token':token},body:JSON.stringify(entry)});
  const data=await response.json(); if (!response.ok) throw Error(data.error || '儲存失敗');state.labs=data.labs;return data;
}
form.addEventListener('submit',async event=>{
  event.preventDefault();const button=$('#save-button');button.disabled=true;
  try {
    const entry=Object.fromEntries(new FormData(form));for (const k of ['note','classification','gene','hgvs']) entry[k]=entry[k].trim();
    entry.gene=entry.gene.toUpperCase();
    if (!entry.gene || !entry.hgvs || !entry.classification || !entry.note || [entry.gene,entry.hgvs].some(k=>k.includes('|'))) throw Error('請填寫基因、位點、判讀結果與依據。');
    message('正在查詢 NCBI ClinVar…');
    let result;
    try {result=await resolveClinVar(entry.gene,entry.hgvs);}
    catch {result={status:'ClinVar 連線失敗，待核對'};}
    const matches=catalog().filter(v=>v.gene===entry.gene && v.hgvs===entry.hgvs);
    const existing=matches.find(v=>v.accession===result.accession) || (matches.length===1 ? matches[0] : null);
    entry.transcript=result.transcript || existing?.transcript || '';
    entry.protein=result.protein || existing?.protein || '';
    entry.accession=existing?.accession || result.accession || 'LAB:'+ [entry.gene,'',entry.hgvs].join('|');
    entry.scope=result.scope || result.status;
    if (result.version) entry.clinvar_version=result.version;
    const latest=[...formal(entry.accession),...draftRows(entry.accession)].sort((a,b)=>a.date.localeCompare(b.date)).at(-1);
    if (latest && entry.date < latest.date) throw Error('日期不得早於既有判讀；歷史紀錄需依時間追加。');
    const duplicate=[...formal(entry.accession),...draftRows(entry.accession)].some(h=>['date','classification','scope','note'].every(k=>h[k]===entry[k]));
    if (duplicate) throw Error('此筆判讀已存在，未重複新增。');
    entry.record_id=globalThis.crypto?.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    if (token) {await saveToProject(entry);message('已寫入專案 data/lab.json，首頁已重建。');}
    else {persistDrafts([...drafts,entry]);message('已保存為此瀏覽器的本機草稿，尚未寫入專案或公開網站。可匯出 lab.json，或在本機編輯器中寫入專案。');}
    $('#query').value='';$('#gene-filter').value='';$('#lab-filter').value='';render();rows.find(r=>r.dataset.accession===entry.accession).open=true;
    form.elements.note.value='';
  } catch(error) {message(error.message,true);} finally {button.disabled=false;}
});
$('#export-lab').addEventListener('click',()=>{
  try {const labs=combined();const url=URL.createObjectURL(new Blob([JSON.stringify(labs,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='lab.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);message('已匯出 lab.json。離線模式請由維護者將它放入 data/，再執行 python3 scripts/build.py；匯出本身不會更新公開首頁。');}catch(error){message(error.message,true);}
});
$('#sync-drafts').addEventListener('click',async()=>{
  const button=$('#sync-drafts');button.disabled=true;
  try {for (const entry of [...drafts].sort((a,b)=>a.date.localeCompare(b.date))) {await saveToProject(entry);persistDrafts(drafts.filter(x=>x.record_id!==entry.record_id));}message('本機草稿已全部寫入專案，首頁已重建。');}
  catch(error){message(error.message+' 未完成的草稿仍保留。',true);}finally{button.disabled=false;render();}
});
async function init() {
  if (location.protocol !== 'file:') {
    try {
      const response=await fetch('/api/state',{signal:AbortSignal.timeout(3000)});
      if (response.ok && response.headers.get('Content-Type')?.includes('application/json')) {const data=await response.json();if (data.token && Array.isArray(data.labs)){token=data.token;state.labs=data.labs;}}
    } catch { /* Static hosting uses explicit local drafts. */ }
  }
  $('#storage-mode').textContent = token ? '本機編輯模式 · 儲存會直接寫入專案並重建首頁。' : '離線／展示模式 · 表單僅保存此瀏覽器草稿，不會自動公開。啟動本機編輯器即可正式存檔。';
  $('#save-button').textContent = token ? '儲存並重建首頁' : '儲存本機草稿';
  render();
}
document.getElementById('records').addEventListener('click', event => {
  const button=event.target.closest('.discard-draft');if (!button) return;
  try {persistDrafts(drafts.filter(d => d.record_id !== button.dataset.recordId));render();message('已移除此筆本機草稿，正式紀錄不受影響。');} catch(error){message(error.message,true);}
});
render();init();
