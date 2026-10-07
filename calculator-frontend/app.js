const LOCAL_API_BASE = 'http://localhost:5050/api';
const PUBLIC_API_BASE = 'https://calculator-0bzq.onrender.com/api';
const localHosts = new Set(['', 'localhost', '127.0.0.1']);
const API_BASE = localHosts.has(window.location.hostname)
  ? LOCAL_API_BASE
  : PUBLIC_API_BASE;
const state = { history: [], total: 0, page: 1, pageSize: 10, dark: localStorage.getItem('calc-theme') === 'dark', query: '', favoriteOnly: false };
const $ = (selector) => document.querySelector(selector);
const input = $('#expressionInput');
const resultValue = $('#resultValue');
const resultHint = $('#resultHint');
const historyList = $('#historyList');
const toast = $('#toast');
let toastTimer;

function showToast(message, type = 'normal') {
  toast.textContent = message;
  toast.style.background = type === 'error' ? '#c34f62' : '#252d43';
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
}
function setStatus(online) {
  const el = $('#connectionStatus');
  el.className = `status-pill ${online ? 'status-online' : 'status-offline'}`;
  el.innerHTML = `<i></i>${online ? '后端已连接' : '后端未连接'}`;
}
function formatNumber(value) {
  if (typeof value !== 'number') return String(value);
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(10)));
}
function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function renderHistory() {
  $('#historyCount').textContent = `${state.total} 条记录 · 第 ${state.page} 页`;
  const today = new Date().toDateString();
  $('#todayCount').textContent = state.history.filter(item => new Date(item.created_at).toDateString() === today).length;
  if (!state.history.length) {
    historyList.innerHTML = '<div class="empty-state"><span class="empty-icon">◌</span><p>还没有计算记录</p></div>';
    return;
  }
  historyList.innerHTML = state.history.map(item => `
    <div class="history-item">
      <div class="history-main"><div class="history-expression">${escapeHtml(item.expression)}</div><div class="history-meta">${formatTime(item.created_at)}</div></div>
      <strong class="history-result">${escapeHtml(formatNumber(item.result))}</strong>
      <button class="favorite-history ${item.favorite ? 'is-favorite' : ''}" data-favorite-id="${item.id}" data-favorite-value="${item.favorite ? 1 : 0}" type="button" aria-label="${item.favorite ? '取消收藏' : '收藏'}">${item.favorite ? '★' : '☆'}</button>
      <button class="delete-history" data-delete-id="${item.id}" type="button" aria-label="删除这条记录">×</button>
    </div>`).join('');
}
function escapeHtml(text) { return String(text).replace(/[&<>'"]/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[char])); }
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  let body = {};
  try { body = await response.json(); } catch (_) { /* empty response */ }
  if (!response.ok || body.success === false) throw new Error(body.message || `请求失败（${response.status}）`);
  return body;
}
async function loadHistory(silent = false) {
  try {
    const params = new URLSearchParams({ page: String(state.page), page_size: String(state.pageSize) });
    if (state.query) params.set('q', state.query);
    if (state.favoriteOnly) params.set('favorite', '1');
    const data = await request(`/history?${params.toString()}`);
    state.history = data.data || [];
    state.total = data.total || 0;
    if (!state.history.length && state.page > 1 && state.total > 0) {
      state.page -= 1;
      return loadHistory(silent);
    }
    renderHistory();
    setStatus(true);
  } catch (error) {
    setStatus(false);
    if (!silent) showToast('无法读取历史：' + error.message, 'error');
  }
}
async function calculate() {
  const expression = input.value.trim();
  if (!expression) { resultHint.textContent = '请输入表达式'; showToast('先输入一个表达式', 'error'); input.focus(); return; }
  resultHint.textContent = '后端计算中…'; resultValue.textContent = '…';
  document.querySelector('[data-action="calculate"]').disabled = true;
  try {
    const data = await request('/calculate', { method: 'POST', body: JSON.stringify({ expression }) });
    resultValue.textContent = formatNumber(data.result);
    resultHint.textContent = `${data.expression} =`;
    input.value = data.expression;
    await loadHistory(true);
    showToast('计算完成，已保存到后端数据库');
  } catch (error) {
    resultValue.textContent = '—'; resultHint.textContent = '计算失败'; setStatus(false);
    showToast(error.message, 'error');
  } finally { document.querySelector('[data-action="calculate"]').disabled = false; }
}
function insertAtCursor(value) {
  const start = input.selectionStart ?? input.value.length;
  const end = input.selectionEnd ?? input.value.length;
  input.value = input.value.slice(0, start) + value + input.value.slice(end);
  input.focus(); input.setSelectionRange(start + value.length, start + value.length);
}
async function deleteHistory(id) {
  try { await request(`/history/${id}`, { method: 'DELETE' }); await loadHistory(true); showToast('记录已删除'); }
  catch (error) { showToast(error.message, 'error'); }
}
async function toggleFavorite(id, value) {
  try {
    await request(`/history/${id}/favorite`, { method: 'PATCH', body: JSON.stringify({ favorite: !Boolean(value) }) });
    await loadHistory(true);
    showToast(!Boolean(value) ? '已加入收藏' : '已取消收藏');
  } catch (error) { showToast(error.message, 'error'); }
}
async function clearHistory() {
  if (!state.history.length) { showToast('当前没有历史记录'); return; }
  try { await request('/history', { method: 'DELETE' }); state.page = 1; await loadHistory(true); showToast('历史记录已清空'); }
  catch (error) { showToast(error.message, 'error'); }
}
function setMode(mode) {
  document.querySelectorAll('.mode-tab').forEach(tab => tab.classList.toggle('is-active', tab.dataset.mode === mode));
  $('#scientificPanel').hidden = mode !== 'scientific';
  $('#basePanel').hidden = mode !== 'base';
  $('#unitPanel').hidden = mode !== 'unit';
}
const unitOptions = {
  length: [['mm', '毫米'], ['cm', '厘米'], ['m', '米'], ['km', '千米']],
  mass: [['mg', '毫克'], ['g', '克'], ['kg', '千克'], ['t', '吨']],
  temperature: [['C', '摄氏度'], ['F', '华氏度'], ['K', '开尔文']]
};
function refreshUnitOptions() {
  const options = unitOptions[$('#unitCategory').value];
  const html = options.map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
  $('#fromUnit').innerHTML = html;
  $('#toUnit').innerHTML = html;
  $('#toUnit').selectedIndex = Math.min(1, options.length - 1);
}
async function convertBase() {
  try {
    const data = await request('/convert/base', { method: 'POST', body: JSON.stringify({ value: $('#baseValue').value, fromBase: Number($('#fromBase').value), toBase: Number($('#toBase').value) }) });
    $('#baseResult').textContent = data.result;
  } catch (error) { showToast(error.message, 'error'); }
}
async function convertUnit() {
  try {
    const data = await request('/convert/unit', { method: 'POST', body: JSON.stringify({ value: Number($('#unitValue').value), category: $('#unitCategory').value, fromUnit: $('#fromUnit').value, toUnit: $('#toUnit').value }) });
    $('#unitResult').textContent = formatNumber(data.result);
  } catch (error) { showToast(error.message, 'error'); }
}
$('#themeToggle').addEventListener('click', () => { state.dark = !state.dark; document.documentElement.dataset.theme = state.dark ? 'dark' : 'light'; localStorage.setItem('calc-theme', state.dark ? 'dark' : 'light'); });
if (state.dark) document.documentElement.dataset.theme = 'dark';

document.querySelectorAll('[data-insert]').forEach(button => button.addEventListener('click', () => insertAtCursor(button.dataset.insert)));
document.querySelector('[data-action="clear"]').addEventListener('click', () => { input.value = ''; resultValue.textContent = '0'; resultHint.textContent = '等待输入表达式'; input.focus(); });
$('#clearExpression').addEventListener('click', () => { input.value = ''; resultValue.textContent = '0'; resultHint.textContent = '等待输入表达式'; input.focus(); });
$('#backspace').addEventListener('click', () => { const start = input.selectionStart ?? input.value.length; const end = input.selectionEnd ?? input.value.length; if (start !== end) insertAtCursor(''); else if (start > 0) { input.value = input.value.slice(0, start - 1) + input.value.slice(end); input.focus(); input.setSelectionRange(start - 1, start - 1); } });
document.querySelector('[data-action="calculate"]').addEventListener('click', calculate);
input.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); calculate(); } if (event.key === 'Escape') { input.value = ''; resultValue.textContent = '0'; resultHint.textContent = '等待输入表达式'; } });
historyList.addEventListener('click', event => { const button = event.target.closest('[data-delete-id]'); if (button) deleteHistory(button.dataset.deleteId); });
historyList.addEventListener('click', event => { const button = event.target.closest('[data-favorite-id]'); if (button) toggleFavorite(button.dataset.favoriteId, button.dataset.favoriteValue); });
$('#refreshHistory').addEventListener('click', () => loadHistory());
$('#clearHistory').addEventListener('click', clearHistory);
document.querySelectorAll('.mode-tab').forEach(tab => tab.addEventListener('click', () => setMode(tab.dataset.mode)));
$('#unitCategory').addEventListener('change', refreshUnitOptions);
$('#convertBase').addEventListener('click', convertBase);
$('#convertUnit').addEventListener('click', convertUnit);
refreshUnitOptions();
setMode('standard');
$('#historySearch').addEventListener('input', event => { state.query = event.target.value.trim(); state.page = 1; loadHistory(true); });
$('#favoriteOnly').addEventListener('change', event => { state.favoriteOnly = event.target.checked; state.page = 1; loadHistory(true); });
$('#prevPage').addEventListener('click', () => { if (state.page > 1) { state.page -= 1; loadHistory(); } });
$('#nextPage').addEventListener('click', () => { if (state.page * state.pageSize < state.total) { state.page += 1; loadHistory(); } });
loadHistory();
