#!/bin/bash

################################################################################
# Mnemonic Development Setup Script
#
# This script bootstraps the complete development environment from scratch.
# It is idempotent - safe to run multiple times.
#
# Features:
# - Prerequisite checking (Docker, uv, git, etc.)
# - Docker service startup with health checks
# - Backend environment setup (venv, dependencies, migrations)
# - Frontend environment setup (npm dependencies, .env)
# - Verification through smoke tests
# - Comprehensive error handling with helpful messages
#
# Usage: ./scripts/setup-dev.sh
################################################################################

set -e

################################################################################
# Configuration
################################################################################

# Project root (script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Docker compose file
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/infrastructure/docker-compose.dev.yml"

# Service health check parameters
HEALTH_CHECK_MAX_RETRIES=30
HEALTH_CHECK_INTERVAL=2

################################################################################
# Helper Functions
################################################################################

# Print error message and exit
error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

# Print success message
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Print info message
info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# Print section header
section() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Docker is installed
check_docker() {
    if ! command_exists docker; then
        error "Docker is not installed.
Please install Docker from: https://docs.docker.com/get-docker/
After installation, verify with: docker --version"
    fi
    success "Docker is installed"
}

# Check Docker is running
check_docker_running() {
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running.
Please start Docker and try again.
On Linux: sudo systemctl start docker
On macOS: Open the Docker Desktop application
On Windows: Open Docker Desktop from the Start menu"
    fi
    success "Docker daemon is running"
}

# Check Docker Compose is available
check_docker_compose() {
    if ! command_exists docker-compose; then
        error "Docker Compose is not installed.
Please install Docker Compose from: https://docs.docker.com/compose/install/
After installation, verify with: docker-compose --version"
    fi
    success "Docker Compose is installed"
}

# Check uv is installed
check_uv() {
    if ! command_exists uv; then
        error "uv package manager is not installed.
Please install uv from: https://docs.astral.sh/uv/getting-started/installation/

Quick install on Linux/macOS:
    curl -LsSf https://astral.sh/uv/install.sh | sh

After installation, verify with: uv --version"
    fi
    success "uv is installed"
}

# Check git is installed
check_git() {
    if ! command_exists git; then
        error "Git is not installed.
Please install Git from: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git"
    fi
    success "Git is installed"
}

# Check Node.js is installed
check_node() {
    if ! command_exists node; then
        error "Node.js is not installed.
Please install Node.js (version 20+) from: https://nodejs.org/
After installation, verify with: node --version"
    fi

    local node_version
    node_version=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$node_version" -lt 20 ]; then
        error "Node.js version 20+ is required.
Your version: $(node -v)
Please upgrade from: https://nodejs.org/"
    fi
    success "Node.js $(node -v) is installed"
}

# Check npm is installed
check_npm() {
    if ! command_exists npm; then
        error "npm is not installed.
npm should be installed with Node.js from: https://nodejs.org/
After installation, verify with: npm --version"
    fi
    success "npm $(npm -v) is installed"
}

# Check port is available
check_port_available() {
    local port=$1
    local service=$2

    if command_exists lsof; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            error "Port $port is already in use by another service.
This port is needed for $service.
Please stop the service using port $port and try again.

To find what's using the port:
    lsof -i :$port

To kill the process:
    kill -9 <PID>"
        fi
    fi
}

# Check all prerequisites
check_prerequisites() {
    section "Checking Prerequisites"

    check_docker
    check_docker_running
    check_docker_compose
    check_uv
    check_git
    check_node
    check_npm

    info "Checking port availability..."
    check_port_available 5432 "PostgreSQL"
    check_port_available 6379 "Redis"
    check_port_available 8000 "Backend API"
    check_port_available 5173 "Frontend dev server"
    success "All required ports are available"

    success "All prerequisites are met!"
}

################################################################################
# Docker Services Setup
################################################################################

# Start Docker services
start_docker_services() {
    section "Starting Docker Services"

    info "Starting Docker containers (postgres, redis)..."

    cd "$PROJECT_ROOT/infrastructure"

    # Start services in detached mode
    docker-compose -f docker-compose.dev.yml up -d postgres redis 2>&1 || \
        error "Failed to start Docker services.
Common causes:
- Port conflict: ports 5432 (postgres) or 6379 (redis) are in use
- Insufficient disk space
- Docker daemon issues

Try these steps:
1. Check port availability: lsof -i :5432 or lsof -i :6379
2. Clean Docker: docker-compose -f docker-compose.dev.yml down -v
3. Restart Docker daemon
4. Run this script again"

    success "Docker containers started"
}

# Wait for PostgreSQL to be healthy
wait_for_postgres() {
    local retry_count=0

    info "Waiting for PostgreSQL to be ready..."

    while [ $retry_count -lt $HEALTH_CHECK_MAX_RETRIES ]; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" exec postgres pg_isready -U mnemonic_dev -d mnemonic_dev >/dev/null 2>&1; then
            success "PostgreSQL is ready"
            return 0
        fi

        retry_count=$((retry_count + 1))
        echo -n "."
        sleep $HEALTH_CHECK_INTERVAL
    done

    error "PostgreSQL failed to become healthy within 60 seconds.
Check Docker logs:
    docker-compose -f infrastructure/docker-compose.dev.yml logs postgres

Common issues:
- Insufficient memory
- Port 5432 conflict
- Corrupted volume data: docker-compose down -v && ./scripts/setup-dev.sh"
}

# Wait for Redis to be healthy
wait_for_redis() {
    local retry_count=0

    info "Waiting for Redis to be ready..."

    while [ $retry_count -lt $HEALTH_CHECK_MAX_RETRIES ]; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" exec redis redis-cli ping >/dev/null 2>&1; then
            success "Redis is ready"
            return 0
        fi

        retry_count=$((retry_count + 1))
        echo -n "."
        sleep $HEALTH_CHECK_INTERVAL
    done

    error "Redis failed to become healthy within 60 seconds.
Check Docker logs:
    docker-compose -f infrastructure/docker-compose.dev.yml logs redis

Common issues:
- Insufficient memory
- Port 6379 conflict
- Corrupted volume data: docker-compose down -v && ./scripts/setup-dev.sh"
}

# Verify Docker services health
verify_docker_services() {
    cd "$PROJECT_ROOT/infrastructure"
    wait_for_postgres
    wait_for_redis
    success "All Docker services are healthy"
}

################################################################################
# Backend Setup
################################################################################

# Setup backend environment
setup_backend() {
    section "Setting Up Backend"

    cd "$PROJECT_ROOT/backend"

    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        info "Creating Python virtual environment..."
        uv venv || \
            error "Failed to create Python virtual environment.
Try cleaning up and running again:
    rm -rf backend/.venv
    ./scripts/setup-dev.sh"
        success "Virtual environment created"
    else
        success "Virtual environment already exists"
    fi

    # Install dependencies
    info "Installing Python dependencies (this may take a minute)..."
    uv sync --all-extras || \
        error "Failed to install Python dependencies.
This could be due to:
- Network connectivity issues
- Incompatible Python version (requires 3.11+)
- Missing system dependencies (libpq-dev for postgres client)

Try these steps:
1. Check your internet connection
2. Verify Python version: python3 --version (should be 3.11+)
3. On Ubuntu/Debian: sudo apt-get install libpq-dev
4. Clean and retry: rm -rf backend/.venv && ./scripts/setup-dev.sh"
    success "Python dependencies installed"

    # Copy .env if it doesn't exist
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            info "Creating .env from .env.example..."
            cp .env.example .env
            success ".env created (update with your settings if needed)"
        else
            error "Neither .env nor .env.example found in backend directory"
        fi
    else
        success ".env already exists"
    fi

    # Update DATABASE_URL in .env for local Docker
    info "Configuring database connection for local Docker..."
    if grep -q "DATABASE_URL=postgresql://mnemonic:" .env; then
        # Update existing local config
        sed -i 's|^DATABASE_URL=postgresql://mnemonic:.*|DATABASE_URL=postgresql://mnemonic_dev:mnemonic_dev_password@localhost:5432/mnemonic_dev|' .env
    else
        # Check if DATABASE_URL exists but points to non-dev location
        if grep -q "DATABASE_URL=" .env; then
            # Only update if it looks like the example (not a user custom config)
            if grep -q "postgresql://mnemonic:mnemonic@localhost" .env; then
                sed -i 's|^DATABASE_URL=.*|DATABASE_URL=postgresql://mnemonic_dev:mnemonic_dev_password@localhost:5432/mnemonic_dev|' .env
            fi
        else
            echo "DATABASE_URL=postgresql://mnemonic_dev:mnemonic_dev_password@localhost:5432/mnemonic_dev" >> .env
        fi
    fi
    success "Database connection configured"

    # Update REDIS_URL in .env for local Docker
    info "Configuring Redis connection for local Docker..."
    if grep -q "REDIS_URL=" .env; then
        sed -i 's|^REDIS_URL=.*|REDIS_URL=redis://localhost:6379/0|' .env
    else
        echo "REDIS_URL=redis://localhost:6379/0" >> .env
    fi
    success "Redis connection configured"

    # Run migrations
    info "Running database migrations..."
    uv run alembic upgrade head || \
        error "Failed to run database migrations.
This could be due to:
- PostgreSQL not running or not accessible
- Database connection error
- Invalid migration files

Check the error above and try:
1. Verify PostgreSQL is running: docker-compose -f infrastructure/docker-compose.dev.yml logs postgres
2. Check DATABASE_URL in backend/.env
3. Verify migrations exist: ls backend/alembic/versions/
4. Retry: cd backend && uv run alembic upgrade head"
    success "Database migrations completed"

    success "Backend setup complete"
}

################################################################################
# Frontend Setup
################################################################################

# Setup frontend environment
setup_frontend() {
    section "Setting Up Frontend"

    cd "$PROJECT_ROOT/frontend"

    # Install npm dependencies
    info "Installing npm dependencies (this may take a minute)..."
    npm install || \
        error "Failed to install npm dependencies.
This could be due to:
- Network connectivity issues
- Corrupted npm cache
- Insufficient disk space

Try these steps:
1. Check your internet connection
2. Clear npm cache: npm cache clean --force
3. Delete node_modules: rm -rf node_modules package-lock.json
4. Retry: npm install"
    success "npm dependencies installed"

    # Copy .env if it doesn't exist
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            info "Creating .env from .env.example..."
            cp .env.example .env
            success ".env created"
        else
            error "Neither .env nor .env.example found in frontend directory"
        fi
    else
        success ".env already exists"
    fi

    # Verify .env has correct API URL
    if grep -q "VITE_API_URL=" .env; then
        current_url=$(grep "VITE_API_URL=" .env | cut -d'=' -f2)
        if [ "$current_url" != "http://localhost:8000" ]; then
            info "Updating API URL to http://localhost:8000..."
            sed -i 's|^VITE_API_URL=.*|VITE_API_URL=http://localhost:8000|' .env
            success "API URL configured"
        fi
    else
        echo "VITE_API_URL=http://localhost:8000" >> .env
        success "API URL configured"
    fi

    success "Frontend setup complete"
}

################################################################################
# Verification
################################################################################

# Run smoke tests
run_smoke_tests() {
    section "Running Smoke Tests"

    cd "$PROJECT_ROOT/backend"

    info "Running Python import tests..."
    if uv run pytest tests/test_setup.py -v || \
        error "Smoke tests failed.
The environment was set up but some imports are missing.

Check the errors above and:
1. Verify all dependencies installed: uv sync --all-extras
2. Check Python version: python3 --version (should be 3.11+)
3. Check the logs for specific import failures
4. Retry: cd backend && uv run pytest tests/test_setup.py -v"
    then
        success "All smoke tests passed"
    fi
}

################################################################################
# Summary and Next Steps
################################################################################

print_summary() {
    section "Setup Complete! ✓"

    cat << 'EOF'
Your Mnemonic development environment is ready!

NEXT STEPS:

1. (Optional) Configure LLM Settings
   Edit backend/.env and set:
   - OPENROUTER_API_KEY: Get from https://openrouter.ai
   - DEFAULT_LLM_MODEL: Choose a model (e.g., openai/gpt-4)

2. Start Development Servers (choose one):

   Option A: Using Docker (recommended for full stack)
   ════════════════════════════════════════════════
   docker-compose -f infrastructure/docker-compose.dev.yml up

   Then visit:
   - Frontend: http://localhost:5173
   - API Docs: http://localhost:8000/docs

   Option B: Running Locally (requires running services in separate terminals)
   ════════════════════════════════════════════════
   Terminal 1 - Backend:
   $ cd backend
   $ uv run uvicorn mnemonic.main:app --reload

   Terminal 2 - Frontend:
   $ cd frontend
   $ npm run dev

   Then visit:
   - Frontend: http://localhost:5173
   - API Docs: http://localhost:8000/docs

3. Development Commands

   Backend:
   $ cd backend
   $ uv run pytest                    # Run all tests
   $ uv run pytest -k "test_fsrs"    # Run specific tests
   $ uv run black src tests          # Format code
   $ uv run ruff check --fix src     # Lint and auto-fix
   $ uv run mypy src                 # Type check

   Frontend:
   $ cd frontend
   $ npm test                        # Run tests
   $ npm run lint                    # Lint
   $ npm run format                  # Format code
   $ npm run build                   # Build for production

4. Documentation

   Build Sphinx docs:
   $ cd docs && make html

   View at: docs/build/html/index.html

5. Database Management

   View PostgreSQL logs:
   $ docker-compose -f infrastructure/docker-compose.dev.yml logs postgres

   Connect to PostgreSQL directly:
   $ psql -h localhost -U mnemonic_dev -d mnemonic_dev -c "SELECT version();"

   Reset database (deletes all data!):
   $ docker-compose -f infrastructure/docker-compose.dev.yml down -v

USEFUL RESOURCES:

- API Documentation: http://localhost:8000/docs (when backend running)
- Project README: README.md
- Developer Guide: docs/source/developer/
- Architecture Decisions: docs/source/adr/

TROUBLESHOOTING:

If something goes wrong:
1. Check the error message above carefully - it includes the fix
2. Review Docker logs: docker-compose -f infrastructure/docker-compose.dev.yml logs
3. Reset environment: docker-compose down -v && ./scripts/setup-dev.sh
4. Check Git issues: git status

NEED HELP?

See the README.md for more information.
For detailed error messages, run:
$ docker-compose -f infrastructure/docker-compose.dev.yml logs -f

═════════════════════════════════════════════════════════════════════════════════
EOF
}

################################################################################
# Main Script
################################################################################

main() {
    # Check prerequisites
    check_prerequisites

    # Setup Docker services
    start_docker_services
    verify_docker_services

    # Setup backend
    setup_backend

    # Setup frontend
    setup_frontend

    # Run smoke tests
    run_smoke_tests

    # Print summary
    print_summary
}

# Run main function
main
