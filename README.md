# Entersys Backend

Backend API for the Entersys.mx project.

## Project Structure

```
app/
├── api/           # API endpoints and routes
├── services/      # Business logic services  
├── repositories/  # Data access layer
├── main.py        # FastAPI application entry point
tests/             # Test files
```

## Development Setup

### Prerequisites
- Python 3.8+
- Poetry
- Docker and Docker Compose

### Quick Start with Docker

1. Clone the repository
2. Run with Docker Compose:
```bash
docker-compose up
```

The API will be available at:
- Main API: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

### Manual Installation

1. Install dependencies with Poetry:
```bash
poetry install
```

2. Activate virtual environment:
```bash
poetry shell
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the development server:
```bash
uvicorn app.main:app --reload
```

## Dependencies

### Production
- **FastAPI**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for FastAPI
- **Pydantic**: Data validation using Python type annotations
- **Pydantic Settings**: Settings management with environment variables
- **SQLAlchemy**: SQL toolkit and ORM

### Development
- **Black**: Code formatter
- **Flake8**: Code linter
- **Pytest**: Testing framework

## Development Commands

- Code formatting: `poetry run black .`
- Linting: `poetry run flake8`  
- Tests: `poetry run pytest`
- Install dependencies: `poetry install`
- Add dependency: `poetry add <package>`
- Add dev dependency: `poetry add --group dev <package>`

## Docker Commands

- Build and start services: `docker-compose up --build`
- Start in background: `docker-compose up -d`
- Stop services: `docker-compose down`
- View logs: `docker-compose logs -f`
- Rebuild: `docker-compose build --no-cache`

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/entersys

# API
API_V1_STR=/api/v1
PROJECT_NAME=Entersys Backend

# Environment  
ENVIRONMENT=development
DEBUG=True
```