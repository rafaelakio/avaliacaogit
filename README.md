# GitHub Developer Profile Analyzer

Analisa qualquer repositório GitHub e infere o tipo de profissional e senioridade do autor com base em padrões reais de engenharia de software.

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

Copie `.env.example` para `.env` e preencha as variáveis:

```bash
cp .env.example .env
```

| Variável | Obrigatório | Descrição |
|---|---|---|
| `GITHUB_TOKEN` | Recomendado | Token GitHub (aumenta limite de 60 para 5000 req/hora) |
| `ANTHROPIC_API_KEY` | Para análise IA | Chave da API Anthropic |
| `PORT` | Opcional | Porta para aplicação web (padrão: 5000) |

## Uso

### Modo Web

Inicie a aplicação web Flask:

```bash
python web_app.py
```

Acesse `http://localhost:5000` no seu navegador. A interface oferece dois modos de análise:

#### 1. Análise de Repositório

1. Selecione a aba **"Repository"**
2. Cole a URL do repositório GitHub (ex: `https://github.com/owner/repo`)
3. Opcionalmente, adicione seu token GitHub para aumentar os limites de requisições
4. Clique em **"Analisar"**
5. Acompanhe o progresso em tempo real
6. Visualize os resultados incluindo:
   - Profile e senioridade do desenvolvedor
   - Score de qualidade (0-100)
   - Breakdown de métricas (commits, testes, CI/CD, documentação, etc.)
   - Análise textual detalhada com strengths, weaknesses e recommendations
   - Linguagens e frameworks detectados

#### 2. Análise de Desenvolvedor

1. Selecione a aba **"Developer"**
2. Digite o nome de usuário GitHub (ex: `octocat`)
3. Defina o número máximo de repositórios a analisar (até 30)
4. Opcionalmente, adicione seu token GitHub
5. Clique em **"Analisar"**
6. A análise agregará os dados de todos os repositórios públicos encontrados
7. Visualize o perfil consolidado do desenvolvedor

#### 3. Exportação de Resultados

Após a análise, você pode exportar os resultados em dois formatos:

- **JSON**: Estrutura completa com todas as métricas, scores e análises
- **CSV**: Formato tabular para import em planilhas

### Modo CLI

Para análise via linha de comando:

```bash
# Análise completa com IA
python main.py https://github.com/owner/repo

# Com output verbose (streaming da IA)
python main.py https://github.com/owner/repo --verbose

# Apenas análise baseada em regras (sem IA)
python main.py https://github.com/owner/repo --no-ai

# Exportar JSON com o relatório
python main.py https://github.com/owner/repo --output report.json

# Passar token GitHub diretamente
python main.py https://github.com/owner/repo --token ghp_xxxxx
```

## O que é analisado

| Dimensão | Métricas coletadas |
|---|---|
| Linguagens | Linguagens detectadas, proporção por bytes |
| Commits | Histórico, frequência, tamanho médio, padrões de mensagem, Conventional Commits |
| Testes | Diretórios de teste, frameworks de teste detectados |
| CI/CD | GitHub Actions, Travis CI, Dockerfile, outros sistemas |
| Documentação | README (qualidade/tamanho), CONTRIBUTING, CHANGELOG, LICENSE |
| Estrutura | Organização de diretórios, arquivos de configuração, .gitignore |
| Frameworks | Detectados via package.json, requirements.txt, go.mod, pom.xml, etc. |
| Workflow | PRs abertas/mescladas, branches, issues abertas/fechadas |
| Boas práticas | ESLint, Prettier, Black, mypy, ruff, etc. |

## Saída gerada

### Tabela de Métricas

```
╔══════════════════════════════════════════════════════════════╗
║  owner/repo                                                   ║
║  Descrição do repositório                                     ║
║  Profile: Backend Developer  |  Seniority: SENIOR  (72/100)  ║
╚══════════════════════════════════════════════════════════════╝

Repository Metrics
──────────────────────────────────────────────────────────────
Languages               Python, TypeScript        Primary: Python
Frameworks & Libraries  FastAPI, SQLAlchemy, ...  12 total
Commit Quality          78% conventional          avg 45 chars
Automated Tests         ✓ Yes                     23 test file(s)
CI/CD Automation        ✓ Yes                     .github/workflows
...
```

### Score de Qualidade

```
Quality Score Breakdown
────────────────────────
Commit Quality    82   ████████████████░░░░
Testing           75   ███████████████░░░░░
CI/CD             85   █████████████████░░░
Documentation     70   ██████████████░░░░░░
...
COMPOSITE SCORE   72   ██████████████░░░░░░  Seniority: senior
```

### Análise Textual (IA ou baseada em regras)

```
DEVELOPER PROFILE
Likely a Backend Developer with strong Python expertise...

SENIORITY ESTIMATE
SENIOR
Uses Conventional Commits consistently, has comprehensive test coverage...

STRENGTHS
  ✓ Strong commit quality with 78% conventional commit ratio
  ✓ Comprehensive CI/CD pipeline with GitHub Actions
  ...

AREAS FOR IMPROVEMENT
  ✗ CHANGELOG.md missing - recommended for open source projects
  ...

RECOMMENDATIONS
  1. Add integration tests alongside unit tests
  2. Consider publishing API documentation with OpenAPI/Swagger
  ...
```

## Exemplo de Saída JSON (`--output`)

```json
{
  "repo": "myproject",
  "owner": "developer",
  "languages": ["python", "typescript"],
  "frameworks": ["FastAPI", "React", "SQLAlchemy"],
  "detected_profile": "Fullstack Developer",
  "seniority": "senior",
  "seniority_score": 72.4,
  "composite_score": 72.4,
  "conventional_commit_ratio": 78.5,
  "has_tests": true,
  "has_ci_cd": true,
  "textual_analysis": {
    "developer_profile": "...",
    "seniority_estimate": "senior",
    "strengths": ["..."],
    "weaknesses": ["..."],
    "recommendations": ["..."]
  }
}
```

## Testes

```bash
python -m pytest tests/ -v
```

## Arquitetura

```
main.py                 # CLI entry point
src/
  config.py             # Constantes, pesos, mapas de frameworks
  collector.py          # Coleta dados da API GitHub
  analyzer.py           # Calcula métricas e scores
  ai_analyzer.py        # Análise textual via Claude API (Anthropic)
  reporter.py           # Output rico no terminal (Rich)
tests/
  test_basic.py         # 24 testes unitários
```

## Limitações

- Repositórios privados requerem `GITHUB_TOKEN` com permissão de leitura
- Análise de commits limitada aos 300 mais recentes
- Detecção de complexidade usa heurísticas simples (sem análise AST)
- Repositórios muito grandes podem ser lentos sem token
