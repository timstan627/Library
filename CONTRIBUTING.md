# Contributing Guidelines

Thank you for your interest in contributing to the Student Resource Library!

## Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/student-library.git
   cd student-library
   ```
3. **Set up development environment**
   ```bash
   cp .env.example .env
   docker-compose up -d
   ```

## Development Workflow

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring

Example: `feature/add-search-filters`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add search autocomplete
fix: resolve file upload timeout
docs: update API documentation
```

### Pull Requests

1. Create feature branch from `develop`
2. Make your changes
3. Write/update tests
4. Update documentation
5. Submit PR to `develop`

## Code Style

### Backend (Python)

- Follow PEP 8
- Use type hints
- Run `black` and `isort`

```bash
cd backend
black .
isort .
```

### Frontend (TypeScript)

- Use TypeScript strict mode
- Follow component patterns

```bash
cd frontend
npm run lint
npm run lint:fix
```

## Testing

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm test
```

## Questions?

Open an issue or discussion!
