/**
 * UI Module
 * Responsabilidade: manipulação do DOM por aba
 */

class UIManager {
  // ─── Tab visibility ───

  static showLoading(tabId) {
    document.getElementById(`loading-${tabId}`).style.display = 'block';
    document.getElementById(`error-${tabId}`).style.display = 'none';
    document.getElementById(`results-${tabId}`).style.display = 'none';
    document.getElementById(`btn-analyze-${tabId}`).disabled = true;
  }

  static showResults(tabId) {
    document.getElementById(`loading-${tabId}`).style.display = 'none';
    document.getElementById(`error-${tabId}`).style.display = 'none';
    document.getElementById(`results-${tabId}`).style.display = 'block';
    document.getElementById(`btn-analyze-${tabId}`).disabled = false;
  }

  static showError(tabId, message) {
    document.getElementById(`loading-${tabId}`).style.display = 'none';
    document.getElementById(`error-${tabId}`).style.display = 'block';
    document.getElementById(`error-${tabId}`).querySelector('.error-msg').textContent = message;
    document.getElementById(`results-${tabId}`).style.display = 'none';
    document.getElementById(`btn-analyze-${tabId}`).disabled = false;
  }

  static clearTab(tabId) {
    document.getElementById(`loading-${tabId}`).style.display = 'none';
    document.getElementById(`error-${tabId}`).style.display = 'none';
    document.getElementById(`results-${tabId}`).style.display = 'none';
    document.getElementById(`btn-analyze-${tabId}`).disabled = false;
    document.getElementById(`input-${tabId}`).value = '';
    document.getElementById(`input-${tabId}`).focus();
  }

  // ─── Progress ───

  static updateProgressText(tabId, text) {
    const el = document.getElementById(`progress-${tabId}`);
    if (el) el.innerHTML = text + '<span class="dots"></span>';
  }

  static updateElapsedDisplay(tabId, secs) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    const display = m > 0 ? `${m}m ${s}s decorridos` : `${s} segundo${s !== 1 ? 's' : ''} decorridos`;
    const el = document.getElementById(`elapsed-${tabId}`);
    if (el) el.textContent = display;
  }

  // ─── Steps ───

  static resetSteps(tabId) {
    for (let i = 0; i <= 4; i++) {
      const el = document.getElementById(`step-${tabId}-${i}`);
      if (el) el.classList.remove('active', 'done');
    }
  }

  static setStep(tabId, stepNum) {
    for (let i = 0; i < stepNum; i++) {
      const el = document.getElementById(`step-${tabId}-${i}`);
      if (el) { el.classList.remove('active'); el.classList.add('done'); }
    }
    const active = document.getElementById(`step-${tabId}-${stepNum}`);
    if (active) { active.classList.remove('done'); active.classList.add('active'); }
  }

  // ─── Scroll ───

  static scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

export default UIManager;
