#!/usr/bin/env python3
"""
Test runner script for the image extractor package.

This script provides a convenient way to run tests with proper environment setup.
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Run tests with appropriate configuration"""

    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Set up environment
    os.environ.setdefault('PYTHONPATH', str(project_root))

    # Basic test command
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '--strict-markers'
    ]

    # Add coverage if requested
    if '--cov' in sys.argv or '--coverage' in sys.argv:
        cmd.extend([
            '--cov=image_extractor',
            '--cov-report=term-missing',
            '--cov-report=html'
        ])

    # Add specific test markers if requested
    if '--unit' in sys.argv:
        cmd.extend(['-m', 'unit'])
    elif '--integration' in sys.argv:
        cmd.extend(['-m', 'integration'])
    elif '--slow' in sys.argv:
        cmd.extend(['-m', 'slow'])
    elif '--not-slow' in sys.argv:
        cmd.extend(['-m', 'not slow'])

    # Run specific test file if provided
    test_files = [arg for arg in sys.argv[1:] if arg.startswith('test_') and arg.endswith('.py')]
    if test_files:
        cmd = cmd[:-1]  # Remove 'tests/' from command
        cmd.extend([f'tests/{f}' for f in test_files])

    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Test Runner for Image Extractor

Usage:
    python run_tests.py [options] [test_files]

Options:
    --cov, --coverage    Run with coverage reporting
    --unit              Run only unit tests
    --integration       Run only integration tests
    --slow              Run only slow tests
    --not-slow          Exclude slow tests
    -h, --help          Show this help

Examples:
    python run_tests.py                    # Run all tests
    python run_tests.py --cov              # Run with coverage
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py test_client.py     # Run specific test file
    python run_tests.py --unit --cov       # Unit tests with coverage
        """)
        sys.exit(0)

    sys.exit(main())