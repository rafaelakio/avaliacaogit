/**
 * Analysis Controller
 * Responsabilidade: orquestração do fluxo de análise por aba
 */

import APIClient from './api.js';
import UIManager from './ui.js';
import Renderers from './renderers.js';
import ExportManager from './exports.js';

class AnalysisController {
  constructor() {
    this.pollTimers    = {};  // tabId → intervalId
    this.elapsedTimers = {};  // tabId → intervalId
    this.taskIds       = {};  // tabId → taskId
    this.elapsedSecs   = {};  // tabId → number
    this.currentSteps  = {};  // tabId → number
  }

  // ─── PUBLIC API ───

  async startAnalysis(tabId, mode, input, noAI, token, maxRepos, anthropicKey = '') {
    if (!input.trim()) {
      document.getElementById(`input-${tabId}`).focus();
      return;
    }

    UIManager.showLoading(tabId);
    UIManager.resetSteps(tabId);
    this.currentSteps[tabId] = -1;

    try {
      const response = await APIClient.startAnalysis(mode, input.trim(), noAI, token, maxRepos, anthropicKey);
      this.taskIds[tabId] = response.task_id;
      this._startElapsedTimer(tabId);
      this._startPolling(tabId);
    } catch (error) {
      UIManager.showError(tabId, 'Não foi possível conectar ao servidor: ' + error.message);
    }
  }

  exportJson(tabId) {
    ExportManager.exportJson(this.taskIds[tabId]);
  }

  exportCsv(tabId) {
    ExportManager.exportCsv(this.taskIds[tabId]);
  }

  async exportPng(tabId) {
    await ExportManager.exportPng(tabId, document.getElementById(`btn-png-${tabId}`));
  }

  clearTab(tabId) {
    this._stopPolling(tabId);
    this._stopElapsedTimer(tabId);
    delete this.taskIds[tabId];
    UIManager.clearTab(tabId);
  }

  // ─── PRIVATE ───

  _startElapsedTimer(tabId) {
    this._stopElapsedTimer(tabId);
    this.elapsedSecs[tabId] = 0;
    this.elapsedTimers[tabId] = setInterval(() => {
      this.elapsedSecs[tabId] = (this.elapsedSecs[tabId] || 0) + 1;
      UIManager.updateElapsedDisplay(tabId, this.elapsedSecs[tabId]);
    }, 1000);
  }

  _stopElapsedTimer(tabId) {
    if (this.elapsedTimers[tabId]) {
      clearInterval(this.elapsedTimers[tabId]);
      delete this.elapsedTimers[tabId];
    }
  }

  _startPolling(tabId) {
    this._stopPolling(tabId);
    this.pollTimers[tabId] = setInterval(() => this._pollStatus(tabId), 1000);
  }

  _stopPolling(tabId) {
    if (this.pollTimers[tabId]) {
      clearInterval(this.pollTimers[tabId]);
      delete this.pollTimers[tabId];
    }
  }

  async _pollStatus(tabId) {
    try {
      const task = await APIClient.getStatus(this.taskIds[tabId]);

      if (task.status === 'running') {
        const txt = task.progress || 'Processando...';
        UIManager.updateProgressText(tabId, txt);
        this._updateStep(tabId, txt);
      } else if (task.status === 'done') {
        this._stopPolling(tabId);
        this._stopElapsedTimer(tabId);
        UIManager.setStep(tabId, 4);
        setTimeout(() => {
          UIManager.showResults(tabId);
          this._renderResults(tabId, task.result);
          UIManager.scrollToTop();
        }, 400);
      } else if (task.status === 'error') {
        this._stopPolling(tabId);
        this._stopElapsedTimer(tabId);
        UIManager.showError(tabId, task.message || 'Erro desconhecido.');
      }
    } catch (_) {
      // network hiccup — keep polling
    }
  }

  _updateStep(tabId, text) {
    const lower = text.toLowerCase();
    let step = this.currentSteps[tabId] || 0;

    if (lower.includes('gerando') || lower.includes('textual'))        step = 4;
    else if (lower.includes('agregando') || lower.includes('calculando')) step = 3;
    else if (lower.includes('analisando') || lower.includes('métricas'))  step = 2;
    else if (lower.includes('coletando') || lower.includes('buscando'))   step = 1;

    if (step !== this.currentSteps[tabId]) {
      this.currentSteps[tabId] = step;
      UIManager.setStep(tabId, step);
    }
  }

  _renderResults(tabId, result) {
    document.getElementById(`profile-header-${tabId}`).innerHTML      = Renderers.renderProfileHeader(result);
    document.getElementById(`frameworks-${tabId}`).innerHTML           = Renderers.renderFrameworks(result);
    document.getElementById(`metrics-grid-${tabId}`).innerHTML         = Renderers.renderMetrics(result);
    document.getElementById(`dim-rows-${tabId}`).innerHTML             = Renderers.renderScoreBreakdown(result);
    document.getElementById(`analysis-panel-${tabId}`).innerHTML       = Renderers.renderAnalysis(result);

    const isUser = result.mode === 'user' || result.mode === 'contributions';
    document.getElementById(`repo-list-${tabId}`).innerHTML =
      (isUser && result.repo_names && result.repo_names.length)
        ? Renderers.renderRepoList(result)
        : '';

    requestAnimationFrame(() => requestAnimationFrame(() => {
      document.querySelectorAll(`#capture-${tabId} .dim-bar-fill[data-score]`).forEach(el => {
        el.style.width = el.dataset.score + '%';
      });
    }));
  }
}

export default new AnalysisController();
