import os
import sys
import pytest
from _pytest.runner import TestReport
from _pytest.terminal import TerminalReporter
from pathlib import Path

class TestResultCollector:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []
        self.error_details = {}
        self.current_test_module = None

    def pytest_runtest_logreport(self, report):
        # Extract the test module name from the nodeid
        if '::' in report.nodeid:
            test_module = report.nodeid.split('::')[0]
            if test_module.startswith('tests/'):
                test_module = test_module[6:]  # Remove 'tests/' prefix
            if test_module.endswith('.py'):
                test_module = test_module[:-3]  # Remove '.py' suffix
            self.current_test_module = test_module
        
        if report.when == 'call':
            if report.passed:
                self.passed.append(report.nodeid)
            elif report.failed:
                self.failed.append(report.nodeid)
                if hasattr(report, 'longrepr'):
                    self.error_details[report.nodeid] = str(report.longrepr)
            elif report.skipped:
                self.skipped.append(report.nodeid)

    def generate_report(self):
        report = ["# Test Execution Report\n"]
        
        report.append("## Summary\n")
        report.append(f"- Total tests: {len(self.passed) + len(self.failed) + len(self.skipped)}")
        report.append(f"- Passed: {len(self.passed)}")
        report.append(f"- Failed: {len(self.failed)}")
        report.append(f"- Skipped: {len(self.skipped)}\n")
        
        if self.failed:
            report.append("## Failed Tests Analysis\n")
            for test_id in self.failed:
                test_name = test_id.split("::")[-1]
                report.append(f"### {test_name}\n")
                
                # Extract error message and details
                error_text = self.error_details.get(test_id, "No detailed error information available")
                
                # Parse the error message to extract relevant information
                if "AssertionError" in error_text:
                    lines = error_text.split('\n')
                    assertion_line = next((line for line in lines if "AssertionError" in line), "")
                    expected_actual = [line for line in lines if "where" in line]
                    
                    report.append("**Problem**: Assertion failed\n")
                    if assertion_line:
                        report.append(f"**Error**: {assertion_line.strip()}\n")
                    if expected_actual:
                        report.append("**Details**:\n")
                        for line in expected_actual:
                            report.append(f"- {line.strip()}\n")
                elif "KeyError" in error_text:
                    key_error_line = next((line for line in error_text.split('\n') if "KeyError" in line), "")
                    report.append("**Problem**: Key not found in DataFrame\n")
                    report.append(f"**Error**: {key_error_line.strip()}\n")
                    report.append("**Explanation**: The filter expression parser is not handling complex expressions correctly.\n")
                else:
                    report.append(f"**Error Details**:\n```\n{error_text}\n```\n")
                
                # Add explanations based on test name
                if "comparison_operators" in test_name:
                    report.append("**Explanation**: The implementation applies conditions with OR logic instead of AND logic between comparison operators for the same field.\n")
                elif "from_str_complex" in test_name:
                    report.append("**Explanation**: The string filter parser doesn't correctly handle logical operators like OR in complex expressions.\n")
                elif "with_parentheses" in test_name:
                    report.append("**Explanation**: The string filter parser doesn't properly evaluate expressions with parentheses.\n")
                
                report.append("**Suggested Fix**: Update the implementation to correctly handle these cases.\n")
        
        return "\n".join(report)

@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """Print debug info at start of test session."""
    print("\nTest Session Debug Info:")
    print(f"Python path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    try:
        import qto_buccaneer
        print(f"qto_buccaneer location: {qto_buccaneer.__file__}")
    except ImportError as e:
        print(f"Failed to import qto_buccaneer: {e}")
    config.test_collector = TestResultCollector()
    config.pluginmanager.register(config.test_collector)

@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    collector = getattr(config, "test_collector", None)
    if collector:
        report = collector.generate_report()
        
        # Create reports directory if it doesn't exist
        reports_dir = Path("test_reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Generate a report file name based on the current test module
        if collector.current_test_module:
            report_file = reports_dir / f"test_report_{collector.current_test_module}.md"
        else:
            report_file = reports_dir / "test_report.md"
        
        # Write the report
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"\n\nTest report generated: {report_file}")

# Add a hook to track which test module is currently running
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    collector = getattr(item.config, "test_collector", None)
    if collector:
        # Extract module name from the test item
        module_name = item.module.__name__
        if module_name.startswith('tests.'):
            module_name = module_name[6:]  # Remove 'tests.' prefix
        collector.current_test_module = module_name 