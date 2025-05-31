"""
Test runner script specifically for V3 workflow enforcement tests.
This ensures all V3 compliance tests pass before any deployment.
"""

import os
import sys
from pathlib import Path

import pytest


def run_v3_enforcement_tests():
    """Run all V3 enforcement tests to ensure compliance."""
    # Test files to run
    v3_test_files = [
        "tests/integration/test_v3_workflow_enforcement.py",
        "tests/unit/test_v3_format_enforcement.py",
        "tests/e2e/test_frontend_v3_compatibility.py",
    ]

    print("🔍 Running V3 Workflow Enforcement Tests...")
    print("=" * 60)

    # Run tests with detailed output
    args = [
        "--verbose",
        "--tb=short",
        "--color=yes",
        "-x",  # Stop on first failure
    ] + v3_test_files

    result = pytest.main(args)

    if result == 0:
        print("\n✅ All V3 enforcement tests passed!")
        print("✅ The application is compliant with V3 refactored workflow.")
        print("✅ No legacy format usage detected.")
        return True
    else:
        print("\n❌ V3 enforcement tests failed!")
        print("❌ The application may have regressed to legacy format.")
        print("❌ Fix the issues before deploying.")
        return False


def run_v3_performance_tests():
    """Run V3 performance tests to ensure efficiency."""
    print("\n🚀 Running V3 Performance Tests...")
    print("=" * 60)

    # Run only performance-related tests
    args = ["--verbose", "-k", "performance or scalability", "tests/integration/test_v3_workflow_enforcement.py"]

    result = pytest.main(args)
    return result == 0


def validate_v3_codebase():
    """Validate that the codebase uses only V3 components."""
    print("\n🔎 Validating V3 Codebase Structure...")
    print("=" * 60)

    # Check for deprecated components in active use
    src_path = Path("src")
    issues = []

    # Files that should NOT be imported anymore
    deprecated_imports = [
        "from .file_processor import",
        "from src.utils.file_processor import",
        "from .gemini_service import",
        "from src.utils.gemini_service import",
        "import file_processor",
        "import gemini_service",
    ]

    for py_file in src_path.rglob("*.py"):
        # Skip deprecated folder
        if "deprecated" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            for deprecated in deprecated_imports:
                if deprecated in content:
                    issues.append(f"❌ {py_file}: Found deprecated import: {deprecated}")
        except Exception as e:
            print(f"Warning: Could not read {py_file}: {e}")

    # Check for V3 component usage
    required_v3_files = [
        "src/utils/enhanced_file_processor_v3_second_pass.py",
        "src/utils/gemini_adapter_v3.py",
        "src/utils/payment_combiner_v2.py",
        "src/utils/alias_matcher.py",
    ]

    for required_file in required_v3_files:
        if not Path(required_file).exists():
            issues.append(f"❌ Missing required V3 component: {required_file}")

    if issues:
        print("Found codebase issues:")
        for issue in issues:
            print(issue)
        return False
    else:
        print("✅ Codebase structure is V3 compliant")
        return True


def validate_frontend_v3():
    """Validate that frontend uses V3 format."""
    print("\n🎨 Validating Frontend V3 Compatibility...")
    print("=" * 60)

    frontend_js = Path("src/static/js/app.js")

    if not frontend_js.exists():
        print("❌ Frontend JavaScript file not found")
        return False

    with open(frontend_js, "r") as f:
        content = f.read()

    # Check for V3 patterns
    v3_indicators = ["payer_info", "payment_info", "match_status", "qbo_customer_id", "internal_id"]

    found_v3 = sum(1 for indicator in v3_indicators if indicator in content)

    if found_v3 >= 4:  # Should have most V3 indicators
        print(f"✅ Frontend appears to be V3 compatible ({found_v3}/5 indicators found)")
        return True
    else:
        print(f"❌ Frontend may not be V3 compatible ({found_v3}/5 indicators found)")
        return False


def main():
    """Main test runner for V3 enforcement."""
    print("🔧 V3 Workflow Enforcement Test Suite")
    print("=" * 60)
    print("This test suite ensures the application uses only V3 refactored components")
    print("and enriched payment format, preventing regression to legacy format.")
    print("=" * 60)

    # Change to project root
    os.chdir(Path(__file__).parent.parent)

    all_passed = True

    # 1. Validate codebase structure
    if not validate_v3_codebase():
        all_passed = False

    # 2. Validate frontend
    if not validate_frontend_v3():
        all_passed = False

    # 3. Run enforcement tests
    if not run_v3_enforcement_tests():
        all_passed = False

    # 4. Run performance tests
    if not run_v3_performance_tests():
        print("⚠️  Performance tests failed, but not blocking deployment")

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL V3 ENFORCEMENT TESTS PASSED!")
        print("🚀 Application is ready for deployment with V3 workflow")
        sys.exit(0)
    else:
        print("💥 V3 ENFORCEMENT TESTS FAILED!")
        print("🛑 DO NOT deploy until all issues are resolved")
        sys.exit(1)


if __name__ == "__main__":
    main()
