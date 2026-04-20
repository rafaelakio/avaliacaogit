/**
 * UI Module
 * Responsabilidade: manipulação do DOM e visibilidade de componentes
 * - mostrar/ocultar seções
 * - adicionar/remover classes
 * - atualizar elementos básicos do DOM
 */

class UIManager {
  // Section visibility
  static showFormSection() {
    document.getElementById('form-section').style.display = 'block';
    document.getElementById('form-section').classList.remove('loading');
    document.getElementById('loading-section').style.display = 'none';
    document.getElementById('error-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';
  }

  static showLoadingSection() {
    document.getElementById('form-section').classList.add('loading');
    document.getElementById('loading-section').style.display = 'block';
    document.getElementById('error-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';
  }

  static showErrorSection() {
    document.getElementById('loading-section').style.display = 'none';
    document.getElementById('error-section').style.display = 'block';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('form-section').classList.remove('loading');
  }

  static showResultsSection() {
    document.getElementById('loading-section').style.display = 'none';
    document.getElementById('form-section').style.display = 'none';
    document.getElementById('error-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'block';
  }

  // Button state
  static setAnalyzeButtonDisabled(disabled) {
    document.getElementById('analyze-btn').disabled = disabled;
  }

  static setExportButtonsDisabled(disabled) {
    document.getElementById('btn-json').disabled = disabled;
    document.getElementById('btn-csv').disabled = disabled;
    document.getElementById('btn-png').disabled = disabled;
  }

  // Progress/status display
  static updateProgressText(text) {
    const el = document.getElementById('progress-text');
    el.innerHTML = text + '<span class="dots"></span>';
  }

  static updateElapsedDisplay(secs) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    const display = m > 0 ? `${m}m ${s}s decorridos` : `${s} segundo${s !== 1 ? 's' : ''} decorridos`;
    document.getElementById('elapsed-display').textContent = display;
  }

  // Step tracking
  static resetSteps() {
    document.querySelectorAll('.step-item').forEach(el => {
      el.classList.remove('active', 'done');
    });
  }

  static setStep(stepNum) {
    // Mark previous steps as done
    for (let i = 0; i < stepNum; i++) {
      const el = document.getElementById(`step-${i}`);
      if (el) {
        el.classList.remove('active');
        el.classList.add('done');
      }
    }

    // Mark current step as active
    const active = document.getElementById(`step-${stepNum}`);
    if (active) {
      active.classList.remove('done');
      active.classList.add('active');
    }
  }

  // Error display
  static setErrorMessage(message) {
    document.getElementById('error-msg').textContent = message;
  }

  // Scroll
  static scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Export button text
  static setExportButtonText(button, text) {
    button.textContent = text;
  }
}

export default UIManager;
