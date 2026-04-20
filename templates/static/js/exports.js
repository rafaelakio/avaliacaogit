/**
 * Exports Module
 */

class ExportManager {
  static exportJson(taskId) {
    if (taskId) window.location.href = `/api/export/${taskId}/json`;
  }

  static exportCsv(taskId) {
    if (taskId) window.location.href = `/api/export/${taskId}/csv`;
  }

  static async exportPng(tabId, button) {
    const captureArea = document.getElementById(`capture-${tabId}`);
    if (!captureArea) return;

    if (typeof html2canvas === 'undefined') {
      alert('Biblioteca html2canvas não carregada. Verifique sua conexão de internet.');
      return;
    }

    const originalText = button.textContent;
    button.textContent = 'Gerando...';
    button.disabled = true;

    try {
      const canvas = await html2canvas(captureArea, {
        backgroundColor: '#0d1117',
        scale: 2,
        useCORS: true,
        logging: false,
        allowTaint: true,
      });
      const link = document.createElement('a');
      link.download = `analysis-${tabId}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      alert('Erro ao gerar PNG: ' + error.message);
    } finally {
      button.textContent = originalText;
      button.disabled = false;
    }
  }
}

export default ExportManager;
