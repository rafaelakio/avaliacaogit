import re

GITHUB_API_BASE = "https://api.github.com"
MAX_COMMITS = 300
COMMITS_PER_PAGE = 100

# Conventional commit pattern
CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .+"
)

# Seniority thresholds (0–100 composite score)
SENIORITY_THRESHOLDS = {"junior": 35, "mid": 60}

# Scoring dimension weights
SCORE_WEIGHTS = {
    "commit_quality": 0.20,
    "testing": 0.18,
    "cicd": 0.12,
    "documentation": 0.12,
    "project_structure": 0.12,
    "framework_sophistication": 0.10,
    "pr_workflow": 0.08,
    "issue_tracking": 0.08,
}

# Framework/library detection maps
FRAMEWORK_MAP = {
    # Python
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "tornado": "Tornado",
    "aiohttp": "aiohttp",
    "sqlalchemy": "SQLAlchemy",
    "celery": "Celery",
    "pytest": "pytest",
    "numpy": "NumPy",
    "pandas": "Pandas",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "tensorflow": "TensorFlow",
    "torch": "PyTorch",
    "keras": "Keras",
    "pydantic": "Pydantic",
    "alembic": "Alembic",
    # JavaScript / TypeScript
    "react": "React",
    "vue": "Vue.js",
    "angular": "Angular",
    "next": "Next.js",
    "nuxt": "Nuxt.js",
    "express": "Express",
    "fastify": "Fastify",
    "nestjs": "NestJS",
    "koa": "Koa",
    "jest": "Jest",
    "mocha": "Mocha",
    "vitest": "Vitest",
    "webpack": "Webpack",
    "vite": "Vite",
    "typescript": "TypeScript",
    "tailwindcss": "Tailwind CSS",
    "prisma": "Prisma",
    "graphql": "GraphQL",
    "apollo": "Apollo",
    "redux": "Redux",
    "zustand": "Zustand",
    "trpc": "tRPC",
    # Java / Kotlin
    "spring-boot": "Spring Boot",
    "spring": "Spring",
    "hibernate": "Hibernate",
    "junit": "JUnit",
    "mockito": "Mockito",
    "quarkus": "Quarkus",
    "micronaut": "Micronaut",
    # Go
    "gin-gonic": "Gin",
    "echo": "Echo",
    "fiber": "Fiber",
    "gorilla": "Gorilla",
    "gorm": "GORM",
    # Rust
    "actix-web": "Actix-web",
    "axum": "Axum",
    "tokio": "Tokio",
    "serde": "Serde",
    # Ruby
    "rails": "Ruby on Rails",
    "sinatra": "Sinatra",
    "rspec": "RSpec",
    # PHP
    "laravel": "Laravel",
    "symfony": "Symfony",
    # Mobile
    "react-native": "React Native",
    "flutter": "Flutter",
    "expo": "Expo",
    # DevOps / IaC
    "terraform": "Terraform",
    "ansible": "Ansible",
    "kubernetes": "Kubernetes",
    "helm": "Helm",
    # Databases
    "redis": "Redis",
    "mongodb": "MongoDB",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    # Tooling
    "eslint": "ESLint",
    "prettier": "Prettier",
    "black": "Black",
    "flake8": "flake8",
    "mypy": "mypy",
    "ruff": "ruff",
    "pylint": "pylint",
    "docker": "Docker",
}

# Developer profile rules
PROFILE_RULES = {
    "data_engineer": {
        "languages": ["python", "scala", "sql"],
        "frameworks": ["numpy", "pandas", "scikit-learn", "tensorflow", "torch", "keras", "spark"],
    },
    "mobile": {
        "languages": ["swift", "kotlin", "dart", "objective-c"],
        "frameworks": ["react-native", "flutter", "expo"],
    },
    "devops": {
        "languages": ["dockerfile", "hcl", "shell", "yaml"],
        "frameworks": ["terraform", "ansible", "kubernetes", "helm"],
        "files": ["Dockerfile", "docker-compose.yml", ".github/workflows"],
    },
    "frontend": {
        "languages": ["javascript", "typescript", "css", "html"],
        "frameworks": ["react", "vue", "angular", "next", "nuxt", "vite", "webpack"],
    },
    "backend": {
        "languages": ["python", "go", "java", "rust", "php", "c#", "ruby", "kotlin"],
        "frameworks": ["django", "flask", "fastapi", "spring", "gin-gonic", "actix-web", "rails", "laravel"],
    },
    "fullstack": {
        "languages": ["javascript", "typescript"],
        "frameworks": ["react", "vue", "express", "nestjs", "next", "nuxt"],
    },
}

# Files indicating quality practices
QUALITY_FILES = [
    ".editorconfig",
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    ".eslintrc.yml",
    ".prettierrc",
    ".prettierrc.json",
    "pyproject.toml",
    ".flake8",
    "setup.cfg",
    ".mypy.ini",
    "ruff.toml",
    ".rubocop.yml",
    ".golangci.yml",
    ".golangci.yaml",
    "sonar-project.properties",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "CHANGELOG",
    "LICENSE",
    "LICENSE.md",
    ".gitignore",
    ".dockerignore",
]

# CI/CD configuration files
CI_FILES = [
    ".github/workflows",
    ".travis.yml",
    "Jenkinsfile",
    ".circleci/config.yml",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    ".drone.yml",
    "bitbucket-pipelines.yml",
    "appveyor.yml",
    ".semaphore/semaphore.yml",
    "Makefile",
]

# Test directory/file patterns
TEST_PATTERNS = [
    "test",
    "tests",
    "__tests__",
    "spec",
    "specs",
    "e2e",
    "integration",
    "unit",
]

DEPENDENCY_FILES = [
    "package.json",
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
    "composer.json",
    "pubspec.yaml",
    "Package.swift",
    "*.csproj",
    "mix.exs",
]
