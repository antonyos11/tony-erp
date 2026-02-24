#!/bin/bash
# Tony ERP - Quick Test Commands
# Make this file executable: chmod +x run_tests.sh

echo "================================"
echo "   Tony ERP Test Suite"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest not found. Installing requirements..."
    pip install -r requirements.txt
fi

# Main menu
echo "Select test type to run:"
echo ""
echo "1. Run ALL tests"
echo "2. Run P0 (Critical) tests only"
echo "3. Run Unit tests only"
echo "4. Run Accounting tests"
echo "5. Run Sales tests"
echo "6. Run with Coverage report"
echo "7. Run in Parallel (fast)"
echo "8. Run specific test file"
echo "9. Generate Coverage HTML report"
echo "10. Install/Update test dependencies"
echo ""
read -p "Enter your choice (1-10): " choice

case $choice in
    1)
        print_info "Running ALL tests..."
        pytest -v
        ;;
    2)
        print_info "Running P0 (Critical) tests only..."
        pytest -v -m p0
        ;;
    3)
        print_info "Running Unit tests only..."
        pytest -v -m unit
        ;;
    4)
        print_info "Running Accounting tests..."
        pytest -v tests/unit/test_accounting_models.py
        ;;
    5)
        print_info "Running Sales tests..."
        pytest -v tests/unit/test_sales_models.py
        ;;
    6)
        print_info "Running tests with coverage..."
        pytest --cov=. --cov-report=term-missing --cov-report=html
        print_success "Coverage report generated in htmlcov/index.html"
        ;;
    7)
        print_info "Running tests in parallel..."
        pytest -n auto -v
        ;;
    8)
        read -p "Enter test file path: " testfile
        print_info "Running $testfile..."
        pytest -v "$testfile"
        ;;
    9)
        print_info "Generating coverage report..."
        pytest --cov=. --cov-report=html
        print_success "Opening coverage report in browser..."
        if command -v xdg-open &> /dev/null; then
            xdg-open htmlcov/index.html
        elif command -v firefox &> /dev/null; then
            firefox htmlcov/index.html
        else
            print_info "Open htmlcov/index.html in your browser"
        fi
        ;;
    10)
        print_info "Installing/Updating test dependencies..."
        pip install -r requirements.txt
        print_success "Dependencies installed successfully"
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""
print_success "Done!"
