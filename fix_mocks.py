import os
import re

TEST_DIR = 'tests'

def fix_under_mocks(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Find where UnderlyingSwitch or multiple switch mocks are created in tests
    # Typical mocks in tests/commons.py:
    # class MockUnderlyingSwitch(UnderlyingSwitch): ...
    # We might need to add last_change to tests/commons.py MockUnderlyingSwitch or replace in all files.
    
    # Check if we can just patch commons.py
    if not 'last_change' in content and ('MockUnderlyingSwitch' in content or 'MockUnderlyingValve' in content):
        pass

fix_under_mocks('tests/commons.py')
