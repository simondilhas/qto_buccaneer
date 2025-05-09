# Test Execution Report

## Summary

- Total tests: 8
- Passed: 5
- Failed: 3
- Skipped: 0

## Failed Tests Analysis

### test_filter_df_comparison_operators

**Problem**: Assertion failed

**Error**: tests\test_metadata_filter.py:52: AssertionError

**Details**:

- E        +  where 3 = len(       Name  Area     Type  IsExternal  Floor\n0  Room 101  20.0   Office        True      1\n1  Room 102  25.0  Meeting       False      1\n2  Room 103  30.0   Office        True      2)

**Explanation**: The implementation applies conditions with OR logic instead of AND logic between comparison operators for the same field.

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_filter_df_from_str_complex

**Problem**: Key not found in DataFrame

**Error**: E   KeyError: 'Type=Office OR Area'

**Explanation**: The filter expression parser is not handling complex expressions correctly.

**Explanation**: The string filter parser doesn't correctly handle logical operators like OR in complex expressions.

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_filter_df_from_str_with_parentheses

**Problem**: Assertion failed

**Error**: tests\test_metadata_filter.py:102: AssertionError

**Details**:

- E        +  where 0 = len(Empty DataFrame\nColumns: [Name, Area, Type, IsExternal, Floor]\nIndex: [])

**Explanation**: The string filter parser doesn't properly evaluate expressions with parentheses.

**Suggested Fix**: Update the implementation to correctly handle these cases.
