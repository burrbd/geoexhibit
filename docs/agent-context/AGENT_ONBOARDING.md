# GeoExhibit Agent Onboarding Meta-Prompt

This is a **comprehensive meta-prompt** for introducing AI agents to the GeoExhibit codebase. Follow this exactly to ensure proper understanding and adherence to all project guidelines.

## 🚀 **MANDATORY FIRST STEPS**

### Step 1: Read Core Architecture (REQUIRED)
```
Read and understand: docs/agent-context/AGENTS.md
```
**This is the single most important document.** It contains:
- Complete technical architecture overview
- Pipeline pattern: Features → TimeProvider → Analyzer → STAC Writer → Publisher → S3
- Critical implementation notes (ULID usage, PySTAC extensions, etc.)
- Data flow documentation
- **CRITICAL**: Development environment setup requirements

### Step 2: Understand Current Project Status (REQUIRED)
```
Read: docs/agent-context/PROJECT_STATUS.md
```
**Before starting work, understand:**
- What acceptance criteria are already achieved (8/8 complete)
- Current code quality metrics and CI status
- Project structure and component completion status

### Step 3: Review Implementation Decisions (REQUIRED)
```
Read: docs/agent-context/DECISIONS.md  
```
**Contains 13 numbered architectural decisions with rationale.** Understand WHY certain patterns exist before modifying them.

## ⚠️ **CRITICAL DEVELOPMENT RULES**

### **Environment Setup (MANDATORY)**
```bash
# ALWAYS run this before development:
pip install -e .              # Install ALL runtime dependencies
./setup_dev.sh               # Install dev tools + hooks
```

**🚨 NEVER add `# type: ignore[import-not-found]` for runtime dependencies!**
- If MyPy fails on imports like `from ulid import new`, install dependencies properly
- Runtime deps are in `pyproject.toml` - MyPy needs actual modules
- Type ignore comments mask real issues and pollute codebase

### **Testing Requirements (MANDATORY)**
- **London School TDD**: Focus on **inputs/outputs and behavior**, not implementation details
- **Unit tests**: Each component tested **in isolation with mocks** of collaborators
- **Coverage**: **Requirement defined by pre-push hook** (see `pre-push-hook.sh --cov-fail-under`)
- **⚠️ NEVER document specific coverage percentages** - they change frequently and create maintenance burden
- **Mock collaborators**: Mock dependencies/collaborators, not internal state
- **Test behavior**: Verify what the component does, not how it does it
- **No real I/O**: Mock filesystem, network, external services

**Example of CORRECT London School unit test:**
```python
@patch('geoexhibit.publisher.boto3')
def test_s3_publisher_publishes_plan(mock_boto3):
    """Test S3Publisher behavior: given a plan, it uploads files to S3."""
    # Arrange: Mock collaborators
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    publisher = S3Publisher(config)
    plan = create_test_plan()
    
    # Act: Call the method under test
    publisher.publish_plan(plan)
    
    # Assert: Verify behavior (interactions with collaborators)
    mock_client.upload_file.assert_called()  # Verify it uploaded
    # Test outputs/behavior, not internal state
```

**Example of WRONG implementation-focused test:**
```python
def test_s3_publisher_internal_state():  # ❌ DON'T DO THIS  
    publisher = S3Publisher(config)
    assert publisher._internal_counter == 0  # Testing implementation details
    publisher.publish_plan(plan)
    assert publisher._internal_counter == 1  # Testing how it works, not what it does
```

### **SOLID Principles (MANDATORY)**
- **Single Responsibility**: Each class has one reason to change
- **Open/Closed**: Open for extension, closed for modification (see plugin system)
- **Liskov Substitution**: Subclasses must be substitutable for base classes
- **Interface Segregation**: Clients shouldn't depend on interfaces they don't use
- **Dependency Inversion**: Depend on abstractions, not concretions (see `Analyzer` interface)

### **Comments & Documentation Philosophy (CRITICAL)**
**Comments are a code smell** - code should be self-documenting through:
- **Clear naming**: Function/variable names that explain intent
- **Good structure**: Logical organization and separation of concerns
- **Well-designed interfaces**: Clean abstractions that are obvious to use

**ONLY add comments for:**
- **Unexpected code** that is unavoidable (workarounds, external API quirks)
- **Decision context** where complexity/choices need explanation (security, performance)
- **Business logic** that isn't obvious from code structure

**NEVER add comments for:**
- **What the code does** (should be obvious from naming)
- **How the code works** (implementation details)
- **Redundant explanations** of clear, well-named functions

**Documentation strategy:**
- **README**: Primary user documentation with examples
- **Docstrings**: Module/public API documentation only
- **Agent context**: Complete technical context for developers
- **No separate documentation files** unless absolutely necessary

### **Code Quality Standards (ENFORCED BY HOOKS)**
- **Black formatting**: Automatic via pre-commit hook
- **Ruff linting**: Automatic via pre-commit hook  
- **MyPy --strict**: Type hints everywhere, passes cleanly
- **Commit discipline**: Conventional commits, one unit + test per commit
- **Coverage**: Enforced by pre-push hook

### **Architecture Patterns (MANDATORY)**
- **Pipeline pattern**: Don't break the core flow
- **Interface abstractions**: All analyzers implement same `Analyzer` interface
- **Dependency injection**: Use patterns from existing codebase
- **HREF rules**: COG assets = S3 URLs, everything else = relative paths
- **Canonical layout**: Never user-configurable, hard-coded paths

## 📋 **GITHUB WORKFLOW (MANDATORY)**

### If Working on Existing Issues:
```
Read: docs/agent-context/PLAYBOOK.md
```
Follow the GitHub API workflow:
1. Start from issue → create branch → implement → PR → respond to comments

### If Creating New Issues:
```
Read: docs/agent-context/ROADMAP.md
```
Understand development phases and dependencies before creating new work.

## 🔍 **COMPONENT-SPECIFIC GUIDANCE**

### **Working on Analyzers (#4 - Plugin System)**
- **Interface**: Extend `geoexhibit/analyzer.py:Analyzer` abstract class
- **Registration**: Use `@plugin_registry.register("name")` decorator
- **Security**: Plugin discovery limited to safe, controlled sources only
- **Example**: See `analyzers/example_analyzer.py`

### **Working on Time Providers** 
- **Declarative first**: Zero Python for common cases via config
- **Callable escape hatch**: For complex time extraction logic
- **Example**: See `geoexhibit/declarative_time.py`

### **Working on Publishers**
- **Abstract interface**: `Publisher` with S3 and Local implementations
- **S3 mocking**: Use boto3 stubber for isolated testing
- **Layout enforcement**: Never expose path configuration to users

### **Working on STAC Writers**
- **HREF rules**: Critically important for TiTiler compatibility
- **Extensions**: Must `add_to()` before `ext()` for PySTAC
- **Validation**: Requires `jsonschema` dependency

## 🧪 **TESTING STRATEGY (MANDATORY)**

### **Before Writing Any Code:**
1. **Read existing tests** for the component you're modifying
2. **Follow the isolation patterns** - see `tests/test_publisher.py` for examples
3. **Mock external dependencies** - no real AWS/filesystem/network calls
4. **Test edge cases** - error conditions, validation failures, etc.

### **London School TDD Principles:**
1. **Test behavior, not implementation** - Focus on inputs → outputs
2. **Mock all collaborators** - Use mocks for dependencies/external services
3. **Verify interactions** - Assert that correct methods were called with correct parameters
4. **Test the contract** - Test the interface, not internal workings
5. **Red-Green-Refactor** - Write failing test, make it pass, refactor

### **Coverage Requirements:**
- **Requirement defined by pre-push hook** - see `--cov-fail-under` in `pre-push-hook.sh`
- **Badge shows current coverage** - see README.md codecov badge
- **⚠️ Do not document specific percentages** - they create maintenance burden
- **Unit tests only** - integration tests should be minimal and clearly labeled

### **London School Mock Strategy:**
```python
# ✅ CORRECT: Mock collaborators, test behavior
@patch('geoexhibit.publisher.boto3')
def test_publisher_uploads_files(mock_boto3):
    """Test that publisher uploads files when given a plan."""
    # Arrange: Mock dependencies
    mock_client = Mock()
    mock_boto3.client.return_value = mock_client
    
    # Act: Call the method
    publisher = S3Publisher(config)
    publisher.publish_plan(plan)
    
    # Assert: Verify behavior (what happened, not how)
    mock_client.upload_file.assert_called_with(
        expected_file_path, 
        expected_bucket, 
        expected_key
    )

# ❌ WRONG: Testing implementation details
def test_publisher_internal_state():
    assert publisher._upload_count == 0  # Don't test internal state
    assert len(publisher._file_queue) == 5  # Don't test implementation
```

## 🚨 **COMMON PITFALLS TO AVOID**

### **❌ Don't Do (Testing & Design):**
- Add `# type: ignore[import-not-found]` for runtime dependencies
- Test implementation details (internal state, private methods)
- Write integration tests instead of isolated unit tests  
- Test multiple components together without mocking collaborators
- Hardcode file paths or external service calls in tests
- Document specific coverage percentages anywhere
- Violate SOLID principles (create classes with multiple responsibilities)
- Test HOW code works instead of WHAT it does

### **❌ Don't Do (Comments & Documentation):**
- Add comments explaining what/how code works (should be obvious from naming)
- Create separate documentation files for features (use README)
- Write redundant docstrings that repeat function names
- Over-comment obvious or well-structured code
- Document implementation details in comments

### **❌ Don't Do (Architecture):**
- Modify the canonical layout or HREF rules
- Break the pipeline pattern
- Skip pre-commit hook setup (`./setup_dev.sh`)
- Create tightly coupled components

### **✅ Always Do (Testing & Design):**
- Install dependencies properly (`pip install -e .`)
- Test behavior and outcomes using London School TDD
- Mock all collaborators and external dependencies
- Follow SOLID principles in all new code
- Write tests that focus on inputs → outputs
- Verify interactions with mocked collaborators

### **✅ Always Do (Process):**
- Follow existing architectural patterns
- Use conventional commit messages
- Reference GitHub issues in commits
- Update relevant documentation when making changes
- Let coverage badge show current numbers (don't document them)

## 📚 **REQUIRED READING ORDER**

**For ANY GeoExhibit work, read in this exact order:**

1. **`AGENTS.md`** - Technical architecture + critical notes
2. **`PROJECT_STATUS.md`** - Current completion state
3. **`DECISIONS.md`** - Why things work the way they do
4. **`PLAYBOOK.md`** - GitHub workflow (if working on issues)
5. **`ROADMAP.md`** - Development phases (if planning new work)

## 🔧 **IMMEDIATE SETUP VERIFICATION**

**Run these commands to verify proper setup:**
```bash
# 1. Install everything properly
pip install -e .
./setup_dev.sh

# 2. Verify environment
python3 -c "import ulid, pystac, boto3; print('✅ All deps available')"
mypy geoexhibit  # Should pass without type ignore comments

# 3. Verify hooks working
git add README.md && git commit -m "test: verify hooks" --dry-run

# 4. Run tests with proper coverage
python3 -m pytest --cov=geoexhibit
```

If ANY of these fail, **fix the environment setup before writing code.**

## 📖 **DOCUMENTATION MAINTENANCE**

When making significant changes:
1. **Update `DECISIONS.md`** - Add numbered decision with rationale
2. **Update `PROJECT_STATUS.md`** - Update completion metrics  
3. **Update `AGENTS.md`** - Keep architecture overview current
4. **Create/update tests** - Following isolation and mocking patterns

### **🚨 CRITICAL DOCUMENTATION RULES**

**❌ NEVER document specific coverage percentages anywhere:**
- Coverage numbers change frequently with code changes
- Creates unnecessary maintenance burden  
- README codecov badge shows current coverage automatically
- Pre-push hook defines the actual requirement

**✅ Instead:**
- Reference "coverage requirements enforced by hooks"
- Point to pre-push hook for actual threshold
- Let the codecov badge handle current numbers
- Focus documentation on patterns and principles, not metrics

## 🎯 **SUCCESS CRITERIA**

**You've successfully onboarded when:**
- ✅ All documentation read and understood
- ✅ Development environment properly set up
- ✅ Pre-commit and pre-push hooks working
- ✅ Can run existing tests with coverage requirements met
- ✅ Understand pipeline pattern and architectural constraints
- ✅ Know how to write isolated unit tests with mocks
- ✅ Familiar with GitHub workflow for issues/PRs

**Only start coding after achieving ALL success criteria above.**

---

## 🎉 **READY TO CONTRIBUTE**

Once you've completed this onboarding:
- You understand GeoExhibit's minimalist, test-driven approach
- You can maintain coverage requirements with proper unit tests
- You know how to work within the existing architectural patterns
- You can contribute safely without breaking existing functionality

**Welcome to GeoExhibit development!** 🚀