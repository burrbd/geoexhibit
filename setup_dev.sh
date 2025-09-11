#!/bin/bash

# Development environment setup for GeoExhibit
echo "🔧 Setting up GeoExhibit development environment..."

# Install development dependencies locally
echo "📦 Installing development dependencies..."
curl -s https://bootstrap.pypa.io/get-pip.py | python3 - --user --break-system-packages black ruff mypy pytest pytest-cov

# Add local bin to PATH in current session
export PATH="$HOME/.local/bin:$PATH"

# Set up pre-commit hook
echo "🪝 Setting up pre-commit hook..."
if [ ! -f ".git/hooks/pre-commit" ]; then
    echo "❌ Git hooks directory not found. Make sure you're in a git repository."
    exit 1
fi

chmod +x .git/hooks/pre-commit
echo "✅ Pre-commit hook installed and made executable"

# Initialize commit counter
echo "0" > .git/commit_count
echo "📊 Initialized commit counter for CI gate checks"

# Test the tools
echo "🧪 Testing linting tools..."
if ~/.local/bin/black --check --quiet . && ~/.local/bin/ruff check --quiet . && ~/.local/bin/mypy geoexhibit --quiet; then
    echo "✅ All linting tools working correctly"
else
    echo "⚠️ Some linting issues found - run the tools individually to see details"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 What this setup provides:"
echo "  • Pre-commit hook that runs black, ruff, mypy before each commit"
echo "  • CI gate check every 4 commits"
echo "  • Local development tools installed in ~/.local/bin"
echo ""
echo "🚀 Ready to develop GeoExhibit following the coding standards!"