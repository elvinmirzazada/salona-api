#!/usr/bin/env python3
"""
Run tests from the command line.
Usage: python run_tests.py
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = str(project_root)

def run_pytest():
    """Run pytest if available."""
    try:
        import pytest
        return pytest.main([
            "tests/test_professionals.py", 
            "tests/test_businesses.py",
            "-v", 
            "--tb=short"
        ])
    except ImportError:
        print("❌ pytest not installed. Run: pip install pytest")
        return 1

def run_simple_test():
    """Run the simple API test."""
    try:
        # Import and run the simple test
        import test_api
        test_api.run_tests()
        return 0
    except Exception as e:
        print(f"❌ Simple test failed: {e}")
        return 1

if __name__ == "__main__":
    print("🧪 Salona API Test Runner")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        print("Running simple API tests...")
        sys.exit(run_simple_test())
    else:
        print("Running pytest tests...")
        exit_code = run_pytest()
        if exit_code != 0:
            print("\n" + "=" * 40)
            print("💡 If pytest failed, try running the simple test:")
            print("   python run_tests.py --simple")
        sys.exit(exit_code)
