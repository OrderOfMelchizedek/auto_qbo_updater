# Deprecated Code

This directory contains legacy code that has been replaced by the refactored system.

## Legacy Core Files (src/utils/)
- `file_processor.py` - Legacy file processor (replaced by `enhanced_file_processor_v3_second_pass.py`)
- `gemini_service.py` - Legacy Gemini service (replaced by `gemini_structured_v2.py`)
- `gemini_adapter.py` - Legacy Gemini adapter (replaced by `gemini_adapter_v3.py`)
- `payment_combiner.py` - Legacy payment combiner (replaced by `payment_combiner_v2.py`)

## Development Versions (src/utils/)
- `enhanced_file_processor.py` - Early enhanced version (still used legacy core)
- `enhanced_file_processor_v2.py` - V2 development version
- `enhanced_file_processor_v3.py` - V3 development version
- `enhanced_file_processor_v3_filtered.py` - V3 with filtering
- `gemini_structured.py` - V1 structured service (replaced by V2)

## Test/Debug Scripts (test_scripts/)
- Various `test_*.py` and `debug_*.py` files from project root
- `show_raw_extractions.py`, `final_demo.py` - Demo scripts
- `*.json` - Test output files

## Legacy Prompts (lib/)
- `legacy_prompts/` - Old prompt versions
- `prompts_archive/` - Archived prompts from development

## Current Active System
The current production system uses:
- `enhanced_file_processor_v3_second_pass.py`
- `gemini_structured_v2.py`
- `gemini_adapter_v3.py`
- `payment_combiner_v2.py`
- `qbo_data_enrichment.py`
- `lib/current_prompts/`

## Note
These files are kept for reference but should not be used in production. The refactored system provides:
- Structured Pydantic models
- Proper check number normalization
- Enhanced QBO data enrichment
- Improved error handling
- Better performance
