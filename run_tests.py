#!/usr/bin/env python3
"""
Verdant-Minds Test Runner Script

This script runs the complete test suite with coverage reporting and
provides a comprehensive summary of test results.

Usage:
    python run_tests.py [options]

Options:
    --unit          Run only unit tests
    --integration   Run only integration tests (slow)
    --no-cov        Skip coverage reporting
    --html          Generate HTML coverage report
    --verbose       Verbose output
    --fast          Skip slow tests
    --ci            CI/CD mode (optimized for automation)
    --help          Show this help message

Examples:
    python run_tests.py                    # Run all tests with coverage
    python run_tests.py --fast             # Run only fast tests
    python run_tests.py --unit --html      # Unit tests with HTML report
    python run_tests.py --ci               # CI/CD mode
"""

import sys
import subprocess
import argparse
import os
import webbrowser
from pathlib import Path
from typing import List, Optional

# Terminal colors
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

    @classmethod
    def supports_color(cls):
        """Check if terminal supports color."""
        return (
            hasattr(sys.stdout, 'isatty') and
            sys.stdout.isatty() and
            os.getenv('TERM') != 'dumb'
        )


class TestRunner:
    """Main test runner class."""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_dir = self.project_root / "tests"
        self.use_color = Colors.supports_color()

    def print_colored(self, text: str, color: str):
        """Print colored text if terminal supports it."""
        if self.use_color:
            print(f"{color}{text}{Colors.NC}")
        else:
            print(text)

    def print_header(self, text: str):
        """Print a header."""
        print()
        self.print_colored("=" * 60, Colors.BLUE)
        self.print_colored(text, Colors.BLUE)
        self.print_colored("=" * 60, Colors.BLUE)
        print()

    def print_success(self, text: str):
        """Print success message."""
        self.print_colored(f"✓ {text}", Colors.GREEN)

    def print_error(self, text: str):
        """Print error message."""
        self.print_colored(f"✗ {text}", Colors.RED)

    def print_warning(self, text: str):
        """Print warning message."""
        self.print_colored(f"⚠ {text}", Colors.YELLOW)

    def print_info(self, text: str):
        """Print info message."""
        self.print_colored(f"ℹ {text}", Colors.BLUE)

    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed."""
        self.print_header("Checking Dependencies")

        try:
            # Check Python version
            python_version = sys.version.split()[0]
            self.print_success(f"Python {python_version}")

            # Check pytest
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.print_error("pytest not installed")
                print("Install with: pip install pytest pytest-cov")
                return False

            pytest_version = result.stdout.strip().split('\n')[0]
            self.print_success(pytest_version)

            # Check pytest-cov
            result = subprocess.run(
                [sys.executable, "-c", "import pytest_cov"],
                capture_output=True
            )
            if result.returncode == 0:
                self.print_success("pytest-cov installed")
            else:
                self.print_warning("pytest-cov not installed (coverage disabled)")

            return True

        except Exception as e:
            self.print_error(f"Dependency check failed: {e}")
            return False

    def build_pytest_command(
        self,
        run_unit: bool,
        run_integration: bool,
        coverage: bool,
        html_report: bool,
        verbose: bool,
        fast_mode: bool,
        ci_mode: bool
    ) -> List[str]:
        """Build the pytest command with appropriate arguments."""
        cmd = [sys.executable, "-m", "pytest"]

        # Select test files
        if run_unit and run_integration:
            cmd.append(str(self.test_dir))
        elif run_unit:
            cmd.append(str(self.test_dir / "test_cognitive_chunk.py"))
        elif run_integration:
            cmd.append(str(self.test_dir / "test_system_integration.py"))

        # Verbosity
        if verbose or ci_mode:
            cmd.append("-v")
        else:
            cmd.append("-q")

        # Coverage options
        if coverage:
            try:
                import pytest_cov
                cmd.extend(["--cov=src", "--cov-report=term-missing"])

                if html_report:
                    cmd.append("--cov-report=html")

                if ci_mode:
                    cmd.append("--cov-report=xml")
            except ImportError:
                self.print_warning("pytest-cov not available, skipping coverage")

        # Fast mode - skip slow tests
        if fast_mode:
            cmd.extend(["-m", "not slow"])

        # CI mode - additional options
        if ci_mode:
            cmd.extend(["--tb=short", "--maxfail=5"])

        return cmd

    def run_tests(
        self,
        run_unit: bool = True,
        run_integration: bool = True,
        coverage: bool = True,
        html_report: bool = False,
        verbose: bool = False,
        fast_mode: bool = False,
        ci_mode: bool = False
    ) -> int:
        """Run the test suite."""
        self.print_header("Verdant-Minds Test Suite")

        print(f"Run Unit Tests: {run_unit}")
        print(f"Run Integration Tests: {run_integration}")
        print(f"Coverage Reporting: {coverage}")
        print(f"HTML Report: {html_report}")
        print(f"Fast Mode: {fast_mode}")
        print(f"CI Mode: {ci_mode}")
        print()

        # Check dependencies
        if not self.check_dependencies():
            return 1

        # Build command
        cmd = self.build_pytest_command(
            run_unit, run_integration, coverage, html_report,
            verbose, fast_mode, ci_mode
        )

        # Run tests
        self.print_header("Running Tests")
        print(f"Command: {' '.join(cmd)}")
        print()

        try:
            result = subprocess.run(cmd, cwd=self.project_root)
            exit_code = result.returncode
        except KeyboardInterrupt:
            self.print_warning("\nTest run interrupted by user")
            return 130
        except Exception as e:
            self.print_error(f"Test run failed: {e}")
            return 1

        # Results summary
        self.print_header("Test Results Summary")

        if exit_code == 0:
            self.print_success("All tests passed!")

            if html_report:
                print()
                html_path = self.project_root / "htmlcov" / "index.html"
                self.print_info(f"HTML coverage report generated: {html_path}")

                # Try to open in browser (non-CI mode)
                if not ci_mode and html_path.exists():
                    try:
                        webbrowser.open(f"file://{html_path.absolute()}")
                        self.print_info("Opening coverage report in browser...")
                    except Exception:
                        pass

            print()
            self.print_success("Test run completed successfully")
            return 0
        else:
            self.print_error(f"Some tests failed (exit code: {exit_code})")
            print()

            if not verbose:
                self.print_info("Run with --verbose for detailed output")

            if fast_mode:
                self.print_info("Running in fast mode - integration tests may have been skipped")

            print()
            self.print_error("Test run completed with failures")
            return exit_code


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Verdant-Minds test suite with coverage reporting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run all tests with coverage
  %(prog)s --fast             # Run only fast tests
  %(prog)s --unit --html      # Unit tests with HTML report
  %(prog)s --ci               # CI/CD mode
        """
    )

    parser.add_argument(
        '--unit',
        action='store_true',
        help='Run only unit tests'
    )

    parser.add_argument(
        '--integration',
        action='store_true',
        help='Run only integration tests (slow)'
    )

    parser.add_argument(
        '--no-cov',
        action='store_true',
        help='Skip coverage reporting'
    )

    parser.add_argument(
        '--html',
        action='store_true',
        help='Generate HTML coverage report'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    parser.add_argument(
        '--fast',
        action='store_true',
        help='Skip slow tests'
    )

    parser.add_argument(
        '--ci',
        action='store_true',
        help='CI/CD mode (optimized for automation)'
    )

    args = parser.parse_args()

    # Determine which tests to run
    run_unit = True
    run_integration = True

    if args.unit and not args.integration:
        run_integration = False
    elif args.integration and not args.unit:
        run_unit = False

    # Create runner and execute
    runner = TestRunner()

    try:
        exit_code = runner.run_tests(
            run_unit=run_unit,
            run_integration=run_integration,
            coverage=not args.no_cov,
            html_report=args.html,
            verbose=args.verbose,
            fast_mode=args.fast,
            ci_mode=args.ci
        )
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
