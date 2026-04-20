/**
 * App Initialization
 * Responsabilidade: setup inicial, tab switching e event binding
 */

import AnalysisController from './analysis.js';
import APIClient from './api.js';

const ANALYSIS_TABS = ['repo', 'user', 'contributions'];
const ALL_TABS      = [...ANALYSIS_TABS, 'prefix'];

// ─── Tab switching ───────────────────────────────────────────────────

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  ALL_TABS.forEach(id => {
    const panel = document.getElementById(`tab-${id}`);
    if (panel) panel.style.display = id === tabId ? 'block' : 'none';
  });
}

// ─── Analyze actions ─────────────────────────────────────────────────

function getTabInput(tabId) {
  return document.getElementById(`input-${tabId}`).value.trim();
}

function getToken(tabId) {
  return document.getElementById(`token-${tabId}`).value.trim();
}

function getMaxRepos(tabId) {
  const el = document.getElementById(`maxr-${tabId}`);
  return el ? (parseInt(el.value) || 8) : 8;
}

function getAISettings(tabId) {
  const chk = document.getElementById(`ai-${tabId}`);
  const key = document.getElementById(`apikey-${tabId}`);
  return {
    useAI: chk ? chk.checked : false,
    anthropicKey: key ? key.value.trim() : '',
  };
}

function analyzeTab(tabId) {
  const input = getTabInput(tabId);
  if (!input) { document.getElementById(`input-${tabId}`).focus(); return; }

  if (tabId === 'prefix') { runPrefixSearch(); return; }

  const { useAI, anthropicKey } = getAISettings(tabId);
  if (useAI && !anthropicKey) { document.getElementById(`apikey-${tabId}`).focus(); return; }

  const modeMap = { repo: 'repo', user: 'user', contributions: 'contributions' };
  AnalysisController.startAnalysis(
    tabId,
    modeMap[tabId],
    input,
    !useAI,
    getToken(tabId),
    getMaxRepos(tabId),
    anthropicKey,
  );
}

// ─── Prefix search ───────────────────────────────────────────────────

let prefixData = null;

async function runPrefixSearch() {
  const prefix = getTabInput('prefix');
  if (!prefix) { document.getElementById('input-prefix').focus(); return; }

  const btn = document.getElementById('btn-analyze-prefix');
  btn.disabled = true;
  btn.textContent = 'Buscando…';

  document.getElementById('error-prefix').style.display   = 'none';
  document.getElementById('results-prefix').style.display = 'none';

  try {
    const data = await APIClient.searchByPrefix(prefix, getToken('prefix'));
    prefixData = data;
    renderPrefixResults(data);
  } catch (err) {
    document.getElementById('error-prefix').style.display = 'block';
    document.getElementById('error-prefix').querySelector('.error-msg').textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Buscar';
  }
}

function renderPrefixResults(data) {
  const fmt = iso => {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  };

  document.getElementById('prefix-summary').textContent =
    `${data.total} repositório(s) com prefixo "${data.prefix}"`;

  const tbody = document.getElementById('prefix-table-body');
  tbody.innerHTML = '';

  if (!data.repos.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="padding:16px;text-align:center;color:var(--muted)">Nenhum repositório encontrado.</td></tr>';
  } else {
    for (const r of data.repos) {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid var(--border)';
      tr.innerHTML = `
        <td style="padding:8px 12px;font-weight:500">${r.full_name}</td>
        <td style="padding:8px 12px">${r.owner}</td>
        <td style="padding:8px 12px;white-space:nowrap">${fmt(r.pushed_at || r.updated_at)}</td>
        <td style="padding:8px 12px">${r.language || '—'}</td>
        <td style="padding:8px 12px;color:var(--muted)">${r.description || '—'}</td>
      `;
      tbody.appendChild(tr);
    }
  }
  document.getElementById('results-prefix').style.display = 'block';
}

function exportPrefixCsv() {
  if (!prefixData) return;
  const rows = [['Repositório', 'Proprietário', 'Última atualização', 'Linguagem', 'Descrição']];
  for (const r of prefixData.repos) {
    rows.push([r.full_name, r.owner, r.pushed_at || r.updated_at || '', r.language || '', r.description || '']);
  }
  const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `repos_${prefixData.prefix}.csv`;
  a.click();
}

function clearPrefixTab() {
  prefixData = null;
  document.getElementById('results-prefix').style.display = 'none';
  document.getElementById('error-prefix').style.display   = 'none';
  document.getElementById('input-prefix').value = '';
  document.getElementById('input-prefix').focus();
}

// ─── Bootstrap ───────────────────────────────────────────────────────

function init() {
  // Tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Per-tab analyze buttons + Enter key
  ALL_TABS.forEach(tabId => {
    const btn = document.getElementById(`btn-analyze-${tabId}`);
    const inp = document.getElementById(`input-${tabId}`);
    if (btn) btn.addEventListener('click', () => analyzeTab(tabId));
    if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') analyzeTab(tabId); });
  });

  // AI checkbox toggles per analysis tab
  ANALYSIS_TABS.forEach(tabId => {
    const chk = document.getElementById(`ai-${tabId}`);
    const key = document.getElementById(`apikey-${tabId}`);
    if (chk && key) {
      chk.addEventListener('change', () => {
        key.style.display = chk.checked ? 'inline-block' : 'none';
        if (!chk.checked) key.value = '';
      });
    }
  });

  // Export buttons for analysis tabs
  ANALYSIS_TABS.forEach(tabId => {
    document.getElementById(`btn-json-${tabId}`)
      ?.addEventListener('click', () => AnalysisController.exportJson(tabId));
    document.getElementById(`btn-csv-${tabId}`)
      ?.addEventListener('click', () => AnalysisController.exportCsv(tabId));
    document.getElementById(`btn-png-${tabId}`)
      ?.addEventListener('click', () => AnalysisController.exportPng(tabId));
    document.getElementById(`btn-clear-${tabId}`)
      ?.addEventListener('click', () => AnalysisController.clearTab(tabId));
  });

  // Prefix tab buttons
  document.getElementById('btn-csv-prefix')  ?.addEventListener('click', exportPrefixCsv);
  document.getElementById('btn-clear-prefix')?.addEventListener('click', clearPrefixTab);

  // Show first tab
  switchTab('repo');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
