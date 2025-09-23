#!/bin/bash
# GeoExhibit pre-commit hook
# Runs black, ruff, and mypy before each commit

echo "🔍 Running pre-commit checks..."

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

# Add local bin to PATH if it exists (for tools installed with --user)
if [ -d "$HOME/.local/bin" ]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Initialize error flag
ERRORS_FOUND=0

# 1. BLACK FORMATTING CHECK
echo "🎨 Checking code formatting with black..."
if command_exists black; then
    if ! black --check --quiet .; then
        echo -e "${RED}❌ Code formatting issues found!${NC}"
        echo -e "${YELLOW}💡 Run 'black .' to auto-format your code${NC}"
        echo ""
        echo "Files that would be reformatted:"
        black --check --diff . | grep -E "^would reformat|^\+\+\+|^---" || true
        ERRORS_FOUND=1
    else
        echo -e "${GREEN}✅ Code formatting looks good${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  black not found. Install with: pip install --user black${NC}"
    echo -e "${YELLOW}   Or run: ./setup_dev.sh${NC}"
    ERRORS_FOUND=1
fi

# 2. RUFF LINTING CHECK  
echo "🔍 Checking code quality with ruff..."
if command_exists ruff; then
    if ! ruff check --quiet .; then
        echo -e "${RED}❌ Linting issues found!${NC}"
        echo -e "${YELLOW}💡 Run 'ruff check .' to see details${NC}"
        echo -e "${YELLOW}💡 Run 'ruff check --fix .' to auto-fix some issues${NC}"
        echo ""
        echo "Linting issues:"
        ruff check . --no-fix | head -20
        ERRORS_FOUND=1
    else
        echo -e "${GREEN}✅ Code quality checks passed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  ruff not found. Install with: pip install --user ruff${NC}"
    echo -e "${YELLOW}   Or run: ./setup_dev.sh${NC}"
    ERRORS_FOUND=1
fi

# 3. MYPY TYPE CHECKING
echo "🔬 Checking types with mypy..."
if command_exists mypy; then
    # Only check the main geoexhibit package, exclude tests to avoid dependency issues
    # Capture mypy output and exit code
    mypy_output=$(mypy geoexhibit 2>&1)
    mypy_exit_code=$?
    
    if [ $mypy_exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ Type checking passed${NC}"
    else
        echo -e "${RED}❌ Type checking issues found!${NC}"
        echo -e "${YELLOW}💡 Run 'mypy geoexhibit' to see details${NC}"
        echo ""
        echo "Type checking issues:"
        echo "$mypy_output" | head -10
        ERRORS_FOUND=1
    fi
else
    echo -e "${YELLOW}⚠️  mypy not found. Install with: pip install --user mypy${NC}"
    echo -e "${YELLOW}   Or run: ./setup_dev.sh${NC}"
    ERRORS_FOUND=1
fi

# 4. CHECK FOR STAGED FILES
if git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  No staged files found. Use 'git add' to stage changes.${NC}"
fi

# Final result
echo ""
if [ $ERRORS_FOUND -eq 0 ]; then
    echo -e "${GREEN}🎉 All pre-commit checks passed! Proceeding with commit.${NC}"
    exit 0
else
    echo -e "${RED}❌ Pre-commit checks failed. Please fix the issues above before committing.${NC}"
    echo -e "${YELLOW}💡 You can bypass this hook with 'git commit --no-verify' (not recommended)${NC}"
    echo ""
    echo -e "${YELLOW}Quick fixes:${NC}"
    echo -e "${YELLOW}  • Run: black . && ruff check --fix . && mypy geoexhibit${NC}"
    echo -e "${YELLOW}  • Then: git add . && git commit${NC}"
    exit 1
fi