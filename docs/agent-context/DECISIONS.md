# GeoExhibit Implementation Decisions

This document records numbered implementation decisions with rationale and links to relevant code/commits.

## Decision 1: Canonical S3/STAC Layout (Hard-coded)

**Decision**: All S3 and STAC paths follow a fixed canonical layout under `jobs/<job_id>/` with no user configuration.

**Rationale**: 
- Eliminates configuration complexity and user errors
- Ensures consistent layout for TiTiler compatibility
- Simplifies relative path resolution for web hosting
- Prevents path conflicts between different job runs

**Implementation**: [`geoexhibit/layout.py`](geoexhibit/layout.py)  
**Commit**: [2c01638](https://github.com/burrbd/geoexhibit/commit/2c01638)

## Decision 2: HREF Rules Enforcement 

**Decision**: COG assets use fully qualified S3 URLs while all other HREFs use strictly relative paths.

**Rationale**:
- TiTiler requires absolute S3 URLs to access COG files
- Web hosting requires relative paths for portability
- Internal enforcement prevents user configuration errors
- Maintains STAC compliance while enabling TiTiler integration

**Implementation**: [`geoexhibit/stac_writer.py:HrefResolver`](geoexhibit/stac_writer.py)  
**Commit**: [9f4d2b5](https://github.com/burrbd/geoexhibit/commit/9f4d2b5)

## Decision 3: Declarative-First Time Providers

**Decision**: Primary time extraction uses declarative JSON configuration with callable providers for advanced cases.

**Rationale**:
- Zero Python required for common date extraction patterns
- Reduces complexity for non-developers
- Supports complex scenarios through callable escape hatch
- Configuration-driven approach scales better than code-based

**Implementation**: [`geoexhibit/declarative_time.py`](geoexhibit/declarative_time.py)  
**Commit**: [c5a7bf3](https://github.com/burrbd/geoexhibit/commit/c5a7bf3)

## Decision 4: ULID for Job and Item IDs

**Decision**: Use ULIDs for all job IDs and item IDs instead of UUIDs or timestamps.

**Rationale**:
- Lexicographically sortable (temporal ordering)
- URL-safe and case-insensitive  
- Shorter than UUIDs (26 vs 36 characters)
- Built-in timestamp component useful for debugging

**Implementation**: [`geoexhibit/orchestrator.py`](geoexhibit/orchestrator.py)  
**Commit**: [719c48f](https://github.com/burrbd/geoexhibit/commit/719c48f)

## Decision 5: DemoAnalyzer with Synthetic COGs

**Decision**: Ship with a DemoAnalyzer that generates synthetic but valid Cloud Optimized GeoTIFFs.

**Rationale**:
- Enables complete end-to-end testing without real analysis dependencies
- Demonstrates proper COG structure (tiling, overviews, compression)
- Provides working example for users to understand Analyzer interface
- Includes time-based variation to show temporal analysis concepts

**Implementation**: [`geoexhibit/demo_analyzer.py`](geoexhibit/demo_analyzer.py)  
**Commit**: [347fdca](https://github.com/burrbd/geoexhibit/commit/347fdca)

## Decision 6: Pre-commit Hooks for Local Linting

**Decision**: Use git pre-commit hooks to run linters (black, ruff, mypy) before each commit, excluding tests from mypy.

**Rationale**:
- Catches formatting/linting issues before CI
- Faster feedback loop than waiting for CI
- Excludes tests from mypy to speed up commits  
- Maintains code quality without slowing development

**Implementation**: [`.git/hooks/pre-commit`](.git/hooks/pre-commit)  
**Commit**: [8d02b4f](https://github.com/burrbd/geoexhibit/commit/8d02b4f)

## Decision 7: CI Gate Check Every 4 Commits

**Decision**: Automatically check GitHub Actions CI status every 4 commits using GitHub REST API.

**Rationale**:
- Balances early failure detection with development velocity
- Prevents accumulating too many commits before discovering CI issues
- Enforces green CI discipline without being overly intrusive
- Uses GitHub API for reliable status checking

**Implementation**: [`ci_gate.py`](ci_gate.py) + [`.git/hooks/pre-commit`](.git/hooks/pre-commit)  
**Commit**: [525873e](https://github.com/burrbd/geoexhibit/commit/525873e)

## Decision 8: PMTiles for Vector Feature Overlay

**Decision**: Use PMTiles format for vector feature tiles in the web map rather than GeoJSON.

**Rationale**:
- Efficient for large feature collections (tiled vector data)
- Better performance than loading full GeoJSON in browser
- Standard format with good Leaflet integration via protomaps
- Preserves feature properties including feature_id for interaction

**Implementation**: [`web_scaffold/app.js`](web_scaffold/app.js)  
**Commit**: [cfd9516](https://github.com/burrbd/geoexhibit/commit/cfd9516)

## Decision 9: Abstract Publisher Interface

**Decision**: Create abstract Publisher interface with S3Publisher and LocalPublisher implementations.

**Rationale**:
- Enables flexible output destinations (S3 vs local filesystem)
- Facilitates testing with LocalPublisher (no AWS dependencies)
- Clean separation of concerns between publishing logic and storage
- Supports dry-run mode for both publisher types

**Implementation**: [`geoexhibit/publisher.py`](geoexhibit/publisher.py)  
**Commit**: [81e5f56](https://github.com/burrbd/geoexhibit/commit/81e5f56)

## Decision 10: Module-Specific MyPy Configuration

**Decision**: Use pyproject.toml mypy overrides for external libraries rather than broad ignore flags.

**Rationale**:
- Maintains strict type checking for our code
- Handles untyped external dependencies (numpy, rasterio, shapely) gracefully
- Avoids weakening type safety with broad ignore flags
- Provides targeted solutions for specific import issues

**Implementation**: [`pyproject.toml`](pyproject.toml)  
**Commit**: [159c290](https://github.com/burrbd/geoexhibit/commit/159c290)

## Decision 11: Auto-Discovery of Features Files

**Decision**: CLI automatically discovers feature files in common locations rather than requiring explicit paths.

**Rationale**:
- Reduces friction for common use cases (features.json, data.geojson, etc.)
- Follows convention-over-configuration principle
- Still supports explicit file specification when needed
- Improves user experience for typical workflows

**Implementation**: [`geoexhibit/cli.py:_discover_features_file`](geoexhibit/cli.py)  
**Commit**: [d1a6854](https://github.com/burrbd/geoexhibit/commit/d1a6854)

## Decision 12: Test Coverage Target of 95%+

**Decision**: Enforce 95% test coverage threshold with comprehensive testing strategy.

**Rationale**:
- High confidence in code correctness for geospatial/raster operations
- Prevents regressions in complex integration scenarios
- Forces thoughtful API design (testable code)
- 100% coverage on core modules (stac_writer, publisher) for critical paths

**Implementation**: [`pyproject.toml:pytest.ini_options`](pyproject.toml)  
**Current Coverage**: 96%+ across all modules

## Decision 13: Steel Thread End-to-End Testing Strategy

**Decision**: Implement simple end-to-end test that mimics web map sequence instead of complex validation frameworks.

**Rationale**:
- Steel thread test should mirror actual user workflow (web map sequence)
- Simpler test script easier to maintain and understand
- Direct validation of the data flow documented in AGENTS.md
- Avoids over-engineering for infrastructure validation

**Flow Tested**:
1. Collection JSON loading (CloudFront → S3)
2. PMTiles vector layer access  
3. STAC Item loading (feature click simulation)
4. TiTiler TileJSON generation
5. Raster tile rendering

**Implementation**: [`steel_thread_test.py`](steel_thread_test.py)

**Commit**: [Issue #3 implementation](https://github.com/burrbd/geoexhibit/pull/14)  
**Commit**: [ebae30e](https://github.com/burrbd/geoexhibit/commit/ebae30e)