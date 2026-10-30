# Contributing Guidelines

Thank you for your interest in contributing to the Student Resource Library!

## Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/student-library.git
   cd student-library
   ```
3. **Backend setup**
   ```bash
   cd backend
   python -m venv venv
   # Windows: venv\Scripts\activate   |   Linux/Mac: source venv/bin/activate
   pip install -r requirements.txt -r requirements-dev.txt
   # Create backend/.env — every variable is documented in docs/OWNER_GUIDE.md
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
4. **Frontend setup**
   ```bash
   cd frontend
   npm install
   npm run dev        # http://localhost:3000
   ```

No Docker or external database is required for development (SQLite +
in-memory caches; file storage needs Telegram credentials — see
`docs/OWNER_GUIDE.md`).

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

1. Create feature branch from `main`
2. Make your changes
3. Write/update tests
4. Update documentation
5. Submit PR to `main`

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
npm run type-check
```

## Testing

### Backend

```bash
cd backend
venv\Scripts\python.exe -m pytest tests/ -q --no-header -p no:cacheprovider
```

(Isolated temp SQLite DB; Telegram is faked. On PowerShell the process may
exit 1 even when green — read the "N passed" line.)

### Frontend

```bash
cd frontend
npm run type-check
npm run lint
```

There is no frontend unit-test runner yet; UI changes are verified with
`npm run build` in CI and (for preview/UX work) headless-browser checks.

## Questions?

Open an issue or discussion!
