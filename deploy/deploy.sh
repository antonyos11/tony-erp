#!/bin/bash
# Tony ERP Production Deployment Script
# Usage: ./deploy.sh [start|stop|restart|logs|backup|update|ssl-init]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"
ENV_FILE="${SCRIPT_DIR}/.env"

# Print functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check requirements
check_requirements() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed!"
        exit 1
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        print_error ".env file not found!"
        echo "Copy .env.production to .env and configure it first."
        exit 1
    fi
    
    print_success "Requirements check passed"
}

# Docker compose command (supports both v1 and v2)
docker_compose() {
    if docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
    else
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
    fi
}

# Start services
start() {
    print_header "Starting Tony ERP Production"
    check_requirements
    
    echo "Building and starting containers..."
    docker_compose up -d --build
    
    echo ""
    print_success "Services started successfully!"
    echo ""
    echo "Waiting for services to be healthy..."
    sleep 10
    
    docker_compose ps
}

# Stop services
stop() {
    print_header "Stopping Tony ERP Production"
    
    echo "Stopping containers..."
    docker_compose down
    
    print_success "Services stopped"
}

# Restart services
restart() {
    print_header "Restarting Tony ERP Production"
    stop
    start
}

# View logs
logs() {
    local service=${1:-}
    
    if [ -z "$service" ]; then
        docker_compose logs -f --tail=100
    else
        docker_compose logs -f --tail=100 "$service"
    fi
}

# Create backup
backup() {
    print_header "Creating Database Backup"
    
    DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${SCRIPT_DIR}/backups/tony_erp_manual_${DATE}.sql.gz"
    
    mkdir -p "${SCRIPT_DIR}/backups"
    
    echo "Creating backup..."
    docker_compose exec -T db pg_dump -U tony_erp tony_erp_prod | gzip > "$BACKUP_FILE"
    
    if [ -f "$BACKUP_FILE" ]; then
        SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
        print_success "Backup created: $BACKUP_FILE ($SIZE)"
    else
        print_error "Backup failed!"
        exit 1
    fi
}

# Update application
update() {
    print_header "Updating Tony ERP Production"
    
    echo "Creating backup before update..."
    backup
    
    echo "Pulling latest code..."
    cd "$PROJECT_DIR"
    git pull origin main
    
    echo "Rebuilding containers..."
    docker_compose up -d --build
    
    echo "Running migrations..."
    docker_compose exec web python manage.py migrate --noinput
    
    echo "Collecting static files..."
    docker_compose exec web python manage.py collectstatic --noinput
    
    print_success "Update completed successfully!"
}

# Initialize SSL with Let's Encrypt
ssl_init() {
    print_header "Initializing SSL Certificate"
    
    if [ -z "$1" ]; then
        print_error "Usage: ./deploy.sh ssl-init yourdomain.com"
        exit 1
    fi
    
    DOMAIN=$1
    EMAIL=${2:-"admin@$DOMAIN"}
    
    echo "Requesting certificate for: $DOMAIN"
    echo "Email: $EMAIL"
    
    # Start nginx first for ACME challenge
    docker_compose up -d nginx
    
    # Request certificate
    docker_compose run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"
    
    # Restart nginx to load new certificate
    docker_compose restart nginx
    
    print_success "SSL certificate installed!"
}

# Database shell
dbshell() {
    print_header "PostgreSQL Shell"
    docker_compose exec db psql -U tony_erp tony_erp_prod
}

# Django shell
shell() {
    print_header "Django Shell"
    docker_compose exec web python manage.py shell
}

# Run management command
manage() {
    docker_compose exec web python manage.py "$@"
}

# Show status
status() {
    print_header "Tony ERP Status"
    
    docker_compose ps
    
    echo ""
    echo "Container Resource Usage:"
    docker stats --no-stream $(docker_compose ps -q) 2>/dev/null || true
}

# Health check
health() {
    print_header "Health Check"
    
    echo "Checking services..."
    
    # Web
    if curl -sf http://localhost/health/ > /dev/null 2>&1; then
        print_success "Web: Healthy"
    else
        print_error "Web: Unhealthy"
    fi
    
    # Database
    if docker_compose exec -T db pg_isready -U tony_erp > /dev/null 2>&1; then
        print_success "Database: Healthy"
    else
        print_error "Database: Unhealthy"
    fi
    
    # Redis
    if docker_compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis: Healthy"
    else
        print_error "Redis: Unhealthy"
    fi
    
    # Celery
    if docker_compose exec -T celery celery -A accountant_pro inspect ping > /dev/null 2>&1; then
        print_success "Celery: Healthy"
    else
        print_warning "Celery: May be starting..."
    fi
}

# Clean up
clean() {
    print_header "Cleaning Up"
    
    print_warning "This will remove all containers, volumes, and images!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker_compose down -v --rmi all
        print_success "Cleanup completed"
    else
        echo "Aborted"
    fi
}

# Help
help() {
    echo "Tony ERP Production Deployment Script"
    echo ""
    echo "Usage: ./deploy.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start       Start all services"
    echo "  stop        Stop all services"
    echo "  restart     Restart all services"
    echo "  logs [svc]  View logs (optionally for specific service)"
    echo "  backup      Create database backup"
    echo "  update      Pull latest code and update"
    echo "  ssl-init    Initialize SSL certificate"
    echo "  status      Show service status"
    echo "  health      Run health checks"
    echo "  shell       Open Django shell"
    echo "  dbshell     Open PostgreSQL shell"
    echo "  manage      Run Django management command"
    echo "  clean       Remove all containers and volumes"
    echo "  help        Show this help"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh start"
    echo "  ./deploy.sh logs web"
    echo "  ./deploy.sh ssl-init yourdomain.com admin@yourdomain.com"
    echo "  ./deploy.sh manage migrate"
}

# Main
case "${1:-help}" in
    start)      start ;;
    stop)       stop ;;
    restart)    restart ;;
    logs)       logs "$2" ;;
    backup)     backup ;;
    update)     update ;;
    ssl-init)   ssl_init "$2" "$3" ;;
    status)     status ;;
    health)     health ;;
    shell)      shell ;;
    dbshell)    dbshell ;;
    manage)     shift; manage "$@" ;;
    clean)      clean ;;
    help)       help ;;
    *)          echo "Unknown command: $1"; help; exit 1 ;;
esac
