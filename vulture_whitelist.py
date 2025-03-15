"""Whitelist of false positives for Vulture.

This file contains functions and variables that are known to be used indirectly
and should not be reported as dead code by Vulture.
"""

from vulture.whitelist import Whitelist

whitelist = Whitelist()

# Add patterns for false positives here as they are discovered
# Example:
# whitelist.pytest_functions.append('test_*')  # Pytest test functions
