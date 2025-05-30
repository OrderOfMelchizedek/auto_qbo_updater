# File Organization Update

## Date: May 30, 2025

### CLAUDE.md Updates

Added comprehensive file organization guidelines to ensure all new files are placed in their correct directories:

#### 1. Source Code Organization
- Models → `src/models/`
- Routes → `src/routes/`
- Services → `src/services/`
- Utils → `src/utils/`
- Config → `src/config/`
- Templates → `src/templates/`
- Static files → `src/static/`

#### 2. Test Organization
- Unit Tests → `tests/unit/`
- Integration Tests → `tests/integration/`
- E2E Tests → `tests/e2e/`

#### 3. Scripts Organization
- Shell scripts → `scripts/`
- Python utilities → `scripts/utils/`
- Monitoring scripts → `scripts/monitoring/`

#### 4. Prompts Organization
- Current prompts (refactored code) → `lib/current_prompts/`
- Legacy prompts → `lib/legacy_prompts/`
- Archive prompts → `lib/prompts_archive/`

#### 5. Logs Organization
- **All log files** → `logs/`
- Naming convention: `{component}_{date}.log`
- Updated logging configuration already uses `logs/` directory
- Moved E2E test logs from `tests/e2e/logs/` to main `logs/` directory
- Updated test files to use the centralized logs directory

### Key Rules Added to CLAUDE.md

1. **No loose files in root directory** - Only config files, deployment files, and key documentation
2. **All logs must go to logs/ directory** - Never create logs elsewhere
3. **Use existing logging configuration** - `src/config/logging_config.py`
4. **Follow file naming conventions** - Especially for logs and tests

### Changes Made

1. Updated `tests/e2e/test_full_pipeline.py` to use main logs directory
2. Moved 12 E2E test log files to `logs/`
3. Updated `tests/e2e/README.md` to reflect correct log location
4. Added logging guidelines section to CLAUDE.md

The project structure is now well-organized and documented for consistent file placement going forward.
