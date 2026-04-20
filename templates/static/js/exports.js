/**
 * Exports Module
 * Responsabilidade: lógica de exportação de dados
 * - exportar para JSON
 * - exportar para CSV
 * - exportar para PNG
 */

class ExportManager {
  static async exportJson(taskId) {
    const url = `/api/export/${taskId}/json`;
    window.location.href = url;
  }

  static async exportCsv(taskId) {
    const url = `/api/export/${taskId}/csv`;
    window.location.href = url;
  }

  static async exportPng(taskId) {
    const captureArea = document.getElementById('capture-area');
    const button = document.getElementById('btn-png');

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
      link.download = 'analysis.png';
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
