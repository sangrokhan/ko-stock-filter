#!/bin/bash

# Integration Test Runner Script
# Manages Docker Compose test environment and runs integration tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_COMPOSE_FILE="../../docker/docker-compose.test.yml"
TEST_DIR="."
WAIT_TIMEOUT=60

# Functions
print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Start test environment
start_services() {
    print_header "Starting Test Environment"

    cd ../../docker

    print_info "Starting Docker Compose services..."
    docker-compose -f docker-compose.test.yml up -d

    print_success "Services started"
    cd - >/dev/null
}

# Wait for services to be ready
wait_for_services() {
    print_header "Waiting for Services"

    local services=(
        "http://localhost:5433"
        "http://localhost:6380"
        "http://localhost:8101/health"
        "http://localhost:8102/health"
        "http://localhost:8103/health"
        "http://localhost:8104/health"
        "http://localhost:8105/health"
    )

    for url in "${services[@]}"; do
        if [[ $url == *"/health"* ]]; then
            # HTTP health check
            service_name=$(echo "$url" | sed 's|http://localhost:\([0-9]*\).*|\1|')
            print_info "Waiting for service on port $service_name..."

            for i in {1..30}; do
                if curl -sf "$url" >/dev/null 2>&1; then
                    print_success "Service on port $service_name is ready"
                    break
                fi

                if [ $i -eq 30 ]; then
                    print_error "Service on port $service_name failed to start"
                    exit 1
                fi

                sleep 2
            done
        fi
    done

    print_success "All services are ready"
}

# Run tests
run_tests() {
    print_header "Running Integration Tests"

    local test_args=("$@")

    if [ ${#test_args[@]} -eq 0 ]; then
        # Default: run all integration tests
        pytest "$TEST_DIR" -v
    else
        # Run with custom arguments
        pytest "$TEST_DIR" "${test_args[@]}"
    fi
}

# Stop test environment
stop_services() {
    print_header "Stopping Test Environment"

    cd ../../docker
    docker-compose -f docker-compose.test.yml down
    print_success "Services stopped"
    cd - >/dev/null
}

# View logs
view_logs() {
    print_header "Service Logs"

    cd ../../docker
    docker-compose -f docker-compose.test.yml logs "$@"
    cd - >/dev/null
}

# Show status
show_status() {
    print_header "Service Status"

    cd ../../docker
    docker-compose -f docker-compose.test.yml ps
    cd - >/dev/null
}

# Main execution
main() {
    case "${1:-all}" in
        start)
            check_docker
            start_services
            wait_for_services
            ;;
        stop)
            stop_services
            ;;
        status)
            show_status
            ;;
        logs)
            shift
            view_logs "$@"
            ;;
        test)
            shift
            run_tests "$@"
            ;;
        all)
            check_docker
            start_services
            wait_for_services
            run_tests "${@:2}"
            ;;
        clean)
            stop_services
            cd ../../docker
            docker-compose -f docker-compose.test.yml down -v
            cd - >/dev/null
            print_success "Test environment cleaned"
            ;;
        help)
            echo "Integration Test Runner"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  all         - Start services, run tests, keep services running (default)"
            echo "  start       - Start test environment"
            echo "  stop        - Stop test environment"
            echo "  test        - Run tests (services must be running)"
            echo "  status      - Show service status"
            echo "  logs        - View service logs"
            echo "  clean       - Stop services and remove volumes"
            echo "  help        - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run all tests"
            echo "  $0 test -v                           # Run with verbose output"
            echo "  $0 test -m e2e                       # Run only E2E tests"
            echo "  $0 test test_e2e_workflow.py         # Run specific file"
            echo "  $0 logs data-collector-test          # View specific service logs"
            echo ""
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
