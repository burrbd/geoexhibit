#!/bin/bash
# GeoExhibit pre-push hook
# Runs test suite before pushing changes

echo "🧪 Running pre-push checks..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Not in a git repository${NC}"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if pytest is available
if ! command_exists pytest; then
    echo -e "${RED}❌ pytest not found. Install with: pip install pytest pytest-cov${NC}"
    echo -e "${RED}❌ Or run: ./setup_dev.sh to set up the development environment.${NC}"
    exit 1
fi

# Run the test suite with coverage
echo "🔬 Running test suite with coverage..."
if ! python3 -m pytest --cov=geoexhibit --cov-report=term-missing --cov-fail-under=80 -q; then
    echo -e "${RED}❌ Tests failed or coverage below 80%. Fix tests before pushing.${NC}"
    echo -e "${YELLOW}💡 Run 'python3 -m pytest -v' for detailed test output${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All tests passed with sufficient coverage!${NC}"

# Check for any uncommitted changes that might affect tests
if ! git diff --quiet HEAD; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes that might affect tests${NC}"
    echo -e "${YELLOW}   Consider committing all changes before pushing${NC}"
fi

# Optional: Check if we're pushing to main/master branch
current_branch=$(git symbolic-ref --short HEAD)
remote_name="$1"
remote_url="$2"

# Read the push details from stdin
while read local_ref local_sha remote_ref remote_sha; do
    if [[ "$remote_ref" == "refs/heads/main" || "$remote_ref" == "refs/heads/master" ]]; then
        echo -e "${YELLOW}⚠️  Pushing to main/master branch. Extra validation passed!${NC}"
        
        # For main/master, also run linting checks
        echo "🔍 Running additional linting checks for main branch..."
        
        if command_exists black && command_exists ruff; then
            if ! black --check --quiet .; then
                echo -e "${RED}❌ Code formatting issues found. Run: black .${NC}"
                exit 1
            fi
            
            if ! ruff check --quiet .; then
                echo -e "${RED}❌ Linting issues found. Run: ruff check .${NC}"
                exit 1
            fi
            
            echo -e "${GREEN}✅ All linting checks passed for main branch${NC}"
        fi
    fi
done

echo -e "${GREEN}🚀 Pre-push checks completed successfully! Ready to push.${NC}"
exit 0