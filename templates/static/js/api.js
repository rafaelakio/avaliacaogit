/**
 * API Module
 * Responsabilidade: comunicação com backend
 * - requisições HTTP à API
 * - gestão de tasks assincronamente
 */

class APIClient {
  static async startAnalysis(mode, input, noAI, token, maxRepos, anthropicKey = '') {
    const body = {
      mode,
      no_ai: noAI,
      token: token || '',
      max_repos: maxRepos,
      anthropic_api_key: anthropicKey || '',
    };

    if (mode === 'user' || mode === 'contributions') {
      body.user = input;
    } else {
      body.url = input;
    }

    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  }

  static async getStatus(taskId) {
    const response = await fetch(`/api/status/${taskId}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  }

  static exportJson(taskId) {
    return `/api/export/${taskId}/json`;
  }

  static exportCsv(taskId) {
    return `/api/export/${taskId}/csv`;
  }

  static async searchByPrefix(prefix, token, maxResults = 50) {
    const response = await fetch('/api/prefix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prefix, token: token || '', max_results: maxResults }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${response.status}`);
    }
    return await response.json();
  }
}

export default APIClient;
