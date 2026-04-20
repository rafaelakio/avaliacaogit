/**
 * Analysis Controller
 * Responsabilidade: orquestração do fluxo de análise
 * - coordena API, State, UI e Renderers
 * - gerencia polling e timers
 * - detecta progressão de steps
 */

import APIClient from './api.js';
import State from './state.js';
import UIManager from './ui.js';
import Renderers from './renderers.js';
import ExportManager from './exports.js';

class AnalysisController {
  constructor() {
    this.pollTimer = null;
    this.elapsedTimer = null;
    this.stepKeywords = [
      ['Iniciando', 'Validando', 'Conectando'], // step 0
      ['Coletando', 'Buscando repositórios'], // step 1
      ['Analisando', 'Calculando métricas'], // step 2
      ['Calculando métricas', 'Agregando'], // step 3
      ['Gerando análise', 'textual'], // step 4
    ];
  }

  // ─── PUBLIC API ───

  /**
   * Inicia uma análise
   */
  async startAnalysis(mode, input, noAI, token, maxRepos) {
    if (!input.trim()) {
      document.getElementById('main-input').focus();
      return;
    }

    UIManager.showLoadingSection();
    UIManager.resetSteps();
    UIManager.setAnalyzeButtonDisabled(true);

    try {
      State.setMode(mode);
      State.reset();

      const response = await APIClient.startAnalysis(mode, input.trim(), noAI, token, maxRepos);
      State.setTaskId(response.task_id);

      this.startElapsedTimer();
      this.startPolling();
    } catch (error) {
      this.handleAnalysisError('Não foi possível conectar ao servidor: ' + error.message);
    }
  }

  /**
   * Exporta resultado em JSON
   */
  exportJson(taskId) {
    return ExportManager.exportJson(taskId);
  }

  /**
   * Exporta resultado em CSV
   */
  exportCsv(taskId) {
    return ExportManager.exportCsv(taskId);
  }

  /**
   * Exporta resultado em PNG
   */
  async exportPng(taskId) {
    return await ExportManager.exportPng(taskId);
  }

  /**
   * Reseta formulário
   */
  resetForm() {
    this.stopPolling();
    this.stopElapsedTimer();
    State.reset();
    UIManager.showFormSection();
    UIManager.setAnalyzeButtonDisabled(false);
    UIManager.scrollToTop();
  }

  // ─── PRIVATE METHODS ───

  /**
   * Inicia timer de tempo decorrido
   */
  startElapsedTimer() {
    State.setElapsedSecs(0);
    this.stopElapsedTimer();

    this.elapsedTimer = setInterval(() => {
      State.incrementElapsedSecs();
      UIManager.updateElapsedDisplay(State.elapsedSecs);
    }, 1000);
  }

  /**
   * Para timer de tempo decorrido
   */
  stopElapsedTimer() {
    if (this.elapsedTimer) {
      clearInterval(this.elapsedTimer);
      this.elapsedTimer = null;
    }
  }

  /**
   * Inicia polling de status
   */
  startPolling() {
    this.stopPolling();

    this.pollTimer = setInterval(() => {
      this.pollStatus();
    }, 1000);
  }

  /**
   * Para polling
   */
  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  /**
   * Verifica status da análise
   */
  async pollStatus() {
    try {
      const task = await APIClient.getStatus(State.currentTaskId);

      if (task.status === 'running') {
        const txt = task.progress || 'Processando...';
        UIManager.updateProgressText(txt);
        this.updateProgressStep(txt);
      } else if (task.status === 'done') {
        this.stopPolling();
        this.stopElapsedTimer();
        State.setCurrentStep(4);

        // Brief pause para deixar o usuário ver o último step
        setTimeout(() => {
          UIManager.showResultsSection();
          this.renderResults(task.result);
          UIManager.scrollToTop();
        }, 400);
      } else if (task.status === 'error') {
        this.stopPolling();
        this.stopElapsedTimer();
        this.handleAnalysisError(task.message || 'Erro desconhecido.');
      }
    } catch (error) {
      // Network hiccup, keep polling
    }
  }

  /**
   * Atualiza step baseado no texto de progresso
   */
  updateProgressStep(text) {
    const lower = text.toLowerCase();

    if (lower.includes('gerando') || lower.includes('textual')) {
      State.setCurrentStep(4);
    } else if (lower.includes('agregando') || lower.includes('calculando')) {
      State.setCurrentStep(3);
    } else if (lower.includes('analisando') || lower.includes('métricas')) {
      State.setCurrentStep(2);
    } else if (lower.includes('coletando') || lower.includes('buscando')) {
      State.setCurrentStep(1);
    }

    // Update UI
    UIManager.setStep(State.currentStep);
  }

  /**
   * Renderiza todos os resultados
   */
  renderResults(result) {
    // Renderiza componentes
    document.getElementById('profile-header-card').innerHTML = Renderers.renderProfileHeader(result);
    document.getElementById('frameworks-section').innerHTML = Renderers.renderFrameworks(result);

    if (result.mode === 'user' && result.repo_names && result.repo_names.length) {
      document.getElementById('repo-list-section').innerHTML = Renderers.renderRepoList(result);
    } else {
      document.getElementById('repo-list-section').innerHTML = '';
    }

    document.getElementById('metrics-grid').innerHTML = Renderers.renderMetrics(result);
    document.getElementById('dim-rows').innerHTML = Renderers.renderScoreBreakdown(result);
    document.getElementById('analysis-panel').innerHTML = Renderers.renderAnalysis(result);

    // Trigger bar animations após um tick
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.querySelectorAll('.dim-bar-fill[data-score]').forEach(el => {
          el.style.width = el.dataset.score + '%';
        });
      });
    });
  }

  /**
   * Trata erros de análise
   */
  handleAnalysisError(message) {
    UIManager.setErrorMessage(message);
    UIManager.showErrorSection();
    UIManager.setAnalyzeButtonDisabled(false);
  }
}

export default new AnalysisController();
