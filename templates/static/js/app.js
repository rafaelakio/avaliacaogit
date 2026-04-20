/**
 * App Initialization
 * Responsabilidade: setup inicial e event binding
 * - inicializa UI
 * - configura event listeners
 * - expõe API global para HTML
 */

import AnalysisController from './analysis.js';
import APIClient from './api.js';
import State from './state.js';
import UIManager from './ui.js';

class App {
  constructor() {
    this.analysis = AnalysisController;
  }

  /**
   * Inicializa a aplicação
   */
  init() {
    this.setupInitialUI();
    this.bindModeTabEvents();
    this.bindFormEvents();
    this.bindExportEvents();
    this.subscribeToStateChanges();
  }

  /**
   * Setup inicial da UI
   */
  setupInitialUI() {
    UIManager.showFormSection();
  }

  /**
   * Binding de eventos das abas de modo
   */
  bindModeTabEvents() {
    document.querySelectorAll('.mode-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        this.handleModeChange(btn);
      });
    });
  }

  /**
   * Trata mudança de modo (repo/user)
   */
  handleModeChange(btn) {
    document.querySelectorAll('.mode-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const mode = btn.dataset.mode;
    State.setMode(mode);

    const inp = document.getElementById('main-input');
    const maxG = document.getElementById('max-repos-group');

    if (mode === 'repo') {
      inp.placeholder = 'https://github.com/owner/repo';
    } else if (mode === 'prefix') {
      inp.placeholder = 'Prefixo do repositório (ex: poc-)';
    } else {
      inp.placeholder = 'https://github.com/owner  ou  owner';
    }

    maxG.style.display = (mode !== 'repo' && mode !== 'prefix') ? 'block' : 'none';
  }

  /**
   * Binding de eventos do formulário
   */
  bindFormEvents() {
    const mainInput = document.getElementById('main-input');

    mainInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        this.handleAnalyzeClick();
      }
    });

    document.getElementById('com-ai-chk').addEventListener('change', e => {
      const keyInput = document.getElementById('anthropic-key-input');
      keyInput.style.display = e.target.checked ? 'inline-block' : 'none';
      if (!e.target.checked) keyInput.value = '';
    });
  }

  /**
   * Binding de eventos de exportação
   */
  bindExportEvents() {
    document.getElementById('btn-json').addEventListener('click', () => {
      this.analysis.exportJson(State.currentTaskId);
    });

    document.getElementById('btn-csv').addEventListener('click', () => {
      this.analysis.exportCsv(State.currentTaskId);
    });

    document.getElementById('btn-png').addEventListener('click', () => {
      this.analysis.exportPng(State.currentTaskId);
    });

    document.getElementById('btn-reset').addEventListener('click', () => {
      this.resetForm();
    });

    document.getElementById('btn-prefix-csv').addEventListener('click', () => {
      this._exportPrefixCsv();
    });

    document.getElementById('btn-prefix-reset').addEventListener('click', () => {
      document.getElementById('prefix-section').style.display = 'none';
      document.getElementById('main-input').value = '';
      document.getElementById('main-input').focus();
    });
  }

  /**
   * Subscribe a mudanças de estado
   */
  subscribeToStateChanges() {
    State.subscribe((event, data) => {
      if (event === 'stepChanged') {
        UIManager.setStep(data);
      }
    });
  }

  // ─── GLOBAL API (para HTML) ───

  /**
   * Inicia análise (chamado do HTML)
   */
  startAnalysis() {
    const mode = State.currentMode;
    const input = document.getElementById('main-input').value;
    const useAI = document.getElementById('com-ai-chk').checked;
    const anthropicKey = document.getElementById('anthropic-key-input').value.trim();
    const token = document.getElementById('token-input').value;
    const maxRepos = parseInt(document.getElementById('max-repos-input').value) || 8;

    if (useAI && !anthropicKey) {
      document.getElementById('anthropic-key-input').focus();
      return;
    }

    if (mode === 'prefix') {
      this.runPrefixSearch(input, token);
      return;
    }

    this.analysis.startAnalysis(mode, input, !useAI, token, maxRepos, anthropicKey);
  }

  async runPrefixSearch(prefix, token) {
    if (!prefix.trim()) {
      document.getElementById('main-input').focus();
      return;
    }

    const btn = document.getElementById('analyze-btn');
    btn.disabled = true;
    btn.textContent = 'Buscando…';

    document.getElementById('prefix-section').style.display = 'none';
    document.getElementById('error-section').style.display = 'none';

    try {
      const data = await APIClient.searchByPrefix(prefix.trim(), token);
      this._renderPrefixResults(data);
    } catch (err) {
      document.getElementById('error-section').style.display = '';
      document.getElementById('error-msg').textContent = err.message;
    } finally {
      btn.disabled = false;
      btn.textContent = 'Analisar';
    }
  }

  _renderPrefixResults(data) {
    const fmt = iso => {
      if (!iso) return '—';
      const d = new Date(iso);
      return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    };

    document.getElementById('prefix-summary').textContent =
      `${data.total} repositório(s) encontrado(s) com prefixo "${data.prefix}"`;

    const tbody = document.getElementById('prefix-table-body');
    tbody.innerHTML = '';

    if (!data.repos.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="padding:16px;text-align:center;color:var(--muted)">Nenhum repositório encontrado.</td></tr>';
    } else {
      for (const r of data.repos) {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid var(--border)';
        tr.innerHTML = `
          <td style="padding:8px 12px; font-weight:500">${r.full_name}</td>
          <td style="padding:8px 12px">${r.owner}</td>
          <td style="padding:8px 12px; white-space:nowrap">${fmt(r.pushed_at || r.updated_at)}</td>
          <td style="padding:8px 12px">${r.language || '—'}</td>
          <td style="padding:8px 12px; color:var(--muted)">${r.description || '—'}</td>
        `;
        tbody.appendChild(tr);
      }
    }

    this._prefixData = data;
    document.getElementById('prefix-section').style.display = '';
  }

  _exportPrefixCsv() {
    if (!this._prefixData) return;
    const rows = [['Repositório', 'Proprietário', 'Última atualização', 'Linguagem', 'Descrição']];
    for (const r of this._prefixData.repos) {
      const dt = r.pushed_at || r.updated_at || '';
      rows.push([r.full_name, r.owner, dt, r.language || '', r.description || '']);
    }
    const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `repos_${this._prefixData.prefix}.csv`;
    a.click();
  }

  /**
   * Reseta formulário (chamado do HTML)
   */
  resetForm() {
    document.getElementById('main-input').value = '';
    document.getElementById('token-input').value = '';
    document.getElementById('com-ai-chk').checked = false;
    const keyInput = document.getElementById('anthropic-key-input');
    keyInput.value = '';
    keyInput.style.display = 'none';
    document.getElementById('sticky-results-bar').style.display = 'none';
    document.getElementById('prefix-section').style.display = 'none';
    this._prefixData = null;
    this.analysis.resetForm();
  }
}

// ─── INITIALIZATION ───

const app = new App();

// Inicializa quando o DOM está pronto
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    app.init();
  });
} else {
  app.init();
}

// Expõe API global para HTML
window.startAnalysis = () => app.startAnalysis();
window.resetForm = () => app.resetForm();
window.exportJson = () => app.analysis.exportJson(State.currentTaskId);
window.exportCsv = () => app.analysis.exportCsv(State.currentTaskId);
window.exportPng = () => app.analysis.exportPng(State.currentTaskId);

export default app;
