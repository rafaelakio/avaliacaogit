/**
 * App Initialization
 * Responsabilidade: setup inicial e event binding
 * - inicializa UI
 * - configura event listeners
 * - expõe API global para HTML
 */

import AnalysisController from './analysis.js';
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

    inp.placeholder = mode === 'user'
      ? 'https://github.com/owner  ou  owner'
      : 'https://github.com/owner/repo';

    maxG.style.display = mode === 'user' ? 'block' : 'none';
  }

  /**
   * Binding de eventos do formulário
   */
  bindFormEvents() {
    const mainInput = document.getElementById('main-input');

    // Enter key
    mainInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        this.handleAnalyzeClick();
      }
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
    const noAI = document.getElementById('no-ai-chk').checked;
    const token = document.getElementById('token-input').value;
    const maxRepos = parseInt(document.getElementById('max-repos-input').value) || 8;

    this.analysis.startAnalysis(mode, input, noAI, token, maxRepos);
  }

  /**
   * Reseta formulário (chamado do HTML)
   */
  resetForm() {
    document.getElementById('main-input').value = '';
    document.getElementById('token-input').value = '';
    document.getElementById('no-ai-chk').checked = false;
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
