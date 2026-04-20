/**
 * Renderers Module
 * Responsabilidade: renderização dos resultados da análise
 * - cada função renderiza um componente específico
 * - funções de helper (colorização, formatting)
 */

class Renderers {
  // Utilities
  static scoreColor(score) {
    return score >= 70 ? 'var(--green)' : score >= 40 ? 'var(--yellow)' : 'var(--red)';
  }

  static scoreClass(score) {
    return score >= 70 ? 'ok' : score >= 40 ? 'warn' : 'bad';
  }

  static boolVal(value) {
    return value
      ? '<span class="ok">✓ Sim</span>'
      : '<span class="bad">✗ Não</span>';
  }

  static capitalize(str) {
    return str ? str[0].toUpperCase() + str.slice(1) : '';
  }

  static seniorityBadge(seniority) {
    const classMap = {
      senior: 'badge-senior',
      'mid-level': 'badge-mid',
      junior: 'badge-junior',
    };
    const cls = classMap[seniority] || 'badge-junior';
    return `<span class="seniority-badge ${cls}">${seniority}</span>`;
  }

  // Score visualization (SVG circle)
  static scoreRing(score) {
    const radius = 48;
    const centerCoord = 60;
    const circumference = +(2 * Math.PI * radius).toFixed(2);
    const offset = +(circumference * (1 - score / 100)).toFixed(2);
    const color = this.scoreColor(score);

    return `
      <svg viewBox="0 0 120 120" width="120" height="120">
        <circle cx="${centerCoord}" cy="${centerCoord}" r="${radius}" fill="none" stroke="#1c2128" stroke-width="8"/>
        <circle cx="${centerCoord}" cy="${centerCoord}" r="${radius}" fill="none" stroke="${color}" stroke-width="8"
          stroke-linecap="round"
          stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
          transform="rotate(-90 ${centerCoord} ${centerCoord})"
          style="transition:stroke-dashoffset 1.2s ease"/>
        <text x="${centerCoord}" y="${centerCoord - 4}" text-anchor="middle" fill="${color}"
              font-size="26" font-weight="700" font-family="system-ui,sans-serif">${score.toFixed(0)}</text>
        <text x="${centerCoord}" y="${centerCoord + 14}" text-anchor="middle" fill="#8b949e"
              font-size="11" font-family="system-ui,sans-serif">/100</text>
      </svg>
    `;
  }

  // Main components
  static renderProfileHeader(result) {
    const isUser = result.mode === 'user' || result.mode === 'contributions';
    const title = isUser
      ? `${result.user_name} (@${result.owner})`
      : `${result.owner} / ${result.repo}`;
    const sub = result.mode === 'contributions'
      ? `${result.repos_analyzed} repos ativos recentes analisados · ${result.user_followers} seguidores`
      : isUser
        ? `${result.repos_analyzed} repos analisados · ${result.user_followers} seguidores`
        : `${result.metrics.stars} ★  ${result.metrics.forks} forks`;
    const desc = isUser ? result.user_bio : result.description;
    const avatarSrc = (isUser && result.user_avatar)
      ? result.user_avatar
      : `https://github.com/${result.owner}.png`;
    const avatar = `<img class="profile-avatar" src="${avatarSrc}" alt="avatar"
      onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'avatar-placeholder',textContent:'👤'}))" />`;
    const langs = result.languages
      .slice(0, 7)
      .map(l => `<span class="lang-pill">${l}</span>`)
      .join('');

    return `
      <div class="profile-header">
        ${avatar}
        <div class="profile-info">
          <h2>${title}</h2>
          <div class="sub">${sub}</div>
          ${desc ? `<div class="desc">${desc}</div>` : ''}
          <div class="lang-pills">${langs}</div>
        </div>
        <div class="score-block">
          ${this.scoreRing(result.composite_score)}
          ${this.seniorityBadge(result.seniority)}
          <div class="profile-type">${result.detected_profile}</div>
        </div>
      </div>
    `;
  }

  static renderFrameworks(result) {
    if (!result.frameworks || !result.frameworks.length) {
      return '';
    }

    const pills = result.frameworks
      .map(f => `<span class="fw-pill">${f}</span>`)
      .join('');

    return `
      <div class="fw-section">
        <div class="section-title" style="margin-bottom:10px">Frameworks &amp; Bibliotecas</div>
        <div class="fw-grid">${pills}</div>
      </div>
    `;
  }

  static renderRepoList(result) {
    if (!result.repo_names || !result.repo_names.length) {
      return '';
    }

    const title = result.mode === 'contributions'
      ? 'Repositórios com Atividade Recente'
      : 'Repositórios Analisados';

    const rows = result.repo_names
      .map(name => `
        <div class="repo-list-row">
          <span class="rn">
            <a href="https://github.com/${name}" target="_blank" rel="noopener">${name}</a>
          </span>
        </div>
      `)
      .join('');

    return `
      <div class="repo-list-wrap">
        <div class="repo-list-head section-title" style="margin-bottom:0">
          ${title}
        </div>
        ${rows}
      </div>
    `;
  }

  static renderMetrics(result) {
    const m = result.metrics;
    const rColors = { none: 'bad', minimal: 'warn', basic: 'warn', good: 'ok', comprehensive: 'ok' };
    const sColors = { flat: 'bad', basic: 'warn', organized: 'ok', 'well-organized': 'ok' };
    const freq = m.commit_frequency_per_week ? `${m.commit_frequency_per_week}/sem` : '—';
    const ci = m.ci_cd_systems && m.ci_cd_systems.length ? m.ci_cd_systems.join(', ') : '—';
    const qf = m.quality_files && m.quality_files.length ? `${m.quality_files.length} arquivo(s)` : 'nenhum';

    const cards = [
      {
        label: 'Testes Automatizados',
        val: this.boolVal(m.has_tests),
        sub: `${m.test_files_count} arquivo(s) de teste`,
      },
      { label: 'CI/CD', val: this.boolVal(m.has_ci_cd), sub: ci },
      { label: 'Containerização', val: this.boolVal(m.has_dockerfile), sub: 'Dockerfile / Compose' },
      {
        label: 'README',
        val: `<span class="${rColors[m.readme_quality] || 'info'}">${this.capitalize(m.readme_quality)}</span>`,
        sub: `${m.readme_length.toLocaleString()} chars`,
      },
      {
        label: 'Estrutura do Projeto',
        val: `<span class="${sColors[m.project_structure] || 'info'}">${this.capitalize(m.project_structure)}</span>`,
        sub: `Complexidade: ${result.complexity_level}`,
      },
      {
        label: 'Commits Analisados',
        val: `<span class="info">${m.total_commits_sampled}</span>`,
        sub: `${freq} · ${m.conventional_commit_ratio}% conv.`,
      },
      {
        label: 'Pull Requests',
        val: `<span class="info">${m.pr_count}</span>`,
        sub: `${m.branch_count} branch(es)`,
      },
      {
        label: 'Boas Práticas',
        val: `<span class="info">${m.quality_files ? m.quality_files.length : 0}</span>`,
        sub: qf,
      },
      { label: 'CONTRIBUTING', val: this.boolVal(m.has_contributing), sub: 'guia de contribuição' },
      { label: 'CHANGELOG', val: this.boolVal(m.has_changelog), sub: 'histórico de mudanças' },
    ];

    return cards
      .map(
        c => `
      <div class="metric-card">
        <div class="metric-label">${c.label}</div>
        <div class="metric-val">${c.val}</div>
        <div class="metric-sub">${c.sub}</div>
      </div>
    `
      )
      .join('');
  }

  static renderScoreBreakdown(result) {
    const rows = result.dimensions
      .map(d => {
        const col = this.scoreColor(d.score);
        const cls = this.scoreClass(d.score);
        return `
        <div class="dim-row">
          <div class="dim-name" title="${d.details.join(' | ')}">${d.name}</div>
          <div class="dim-bar-bg">
            <div class="dim-bar-fill" data-score="${d.score}" style="background:${col};width:0%"></div>
          </div>
          <div class="dim-score ${cls}">${d.score.toFixed(0)}</div>
        </div>
      `;
      })
      .join('');

    const cc = this.scoreColor(result.composite_score);
    const composite = `
      <div class="dim-row" style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
        <div class="dim-name" style="font-weight:700">SCORE COMPOSTO</div>
        <div class="dim-bar-bg">
          <div class="dim-bar-fill" data-score="${result.composite_score}" style="background:${cc};width:0%"></div>
        </div>
        <div class="dim-score" style="color:${cc};font-weight:700">${result.composite_score.toFixed(0)}</div>
      </div>
    `;

    return rows + composite;
  }

  static renderAnalysis(result) {
    const an = result.analysis;
    const src = an.used_ai
      ? '<span class="analysis-source">✦ Powered by Claude AI</span>'
      : '<span class="analysis-source">⚙ Análise baseada em regras</span>';

    const strengths = an.strengths
      .map(s => `<li><span class="icon ok">✓</span><span>${s}</span></li>`)
      .join('');
    const weaknesses = an.weaknesses
      .map(w => `<li><span class="icon bad">✗</span><span>${w}</span></li>`)
      .join('');
    const recs = an.recommendations
      .map((rec, i) => `<li><span class="icon info">${i + 1}.</span><span>${rec}</span></li>`)
      .join('');

    return `
      ${src}
      <div class="analysis-block">
        <h3 class="yellow">Perfil do Desenvolvedor</h3>
        <p>${an.developer_profile}</p>
      </div>
      <div class="analysis-block">
        <h3 class="yellow">Estimativa de Senioridade</h3>
        <div class="seniority-estimate">
          ${this.seniorityBadge(an.seniority_estimate)}
          <span style="color:var(--muted);font-size:13px">Score: ${result.seniority_score.toFixed(0)}/100</span>
        </div>
        <p class="seniority-just">${an.seniority_justification}</p>
      </div>
      ${strengths ? `<div class="analysis-block"><h3 class="green">Pontos Fortes</h3><ul class="analysis-list">${strengths}</ul></div>` : ''}
      ${weaknesses ? `<div class="analysis-block"><h3 class="red">Áreas de Melhoria</h3><ul class="analysis-list">${weaknesses}</ul></div>` : ''}
      ${recs ? `<div class="analysis-block"><h3 class="blue">Recomendações</h3><ul class="analysis-list">${recs}</ul></div>` : ''}
    `;
  }
}

export default Renderers;
