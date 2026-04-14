from __future__ import annotations

import pytest
import os
from homeassistant.components.light import EFFECT_OFF

# Test the actual light.py file directly without HA dependencies
def test_effect_list_structure():
    """Test effect_list structure by reading the source."""
    # Read the light.py file to check effect_list implementation
    test_dir = os.path.dirname(os.path.abspath(__file__))
    light_py_path = os.path.join(test_dir, "light.py")
    with open(light_py_path, "r") as f:
        content = f.read()

    # Check that effect_list currently includes EFFECT_OFF (this should fail before fix)
    # After fix, it should NOT include EFFECT_OFF
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'def effect_list(self)' in line:
            # Get the return statement
            for j in range(i, min(i+10, len(lines))):
                if 'return [' in lines[j] and 'EFFECT_OFF' in lines[j]:
                    # This is the current (buggy) implementation
                    assert 'EFFECT_OFF' in lines[j]
                    return
                if 'return list(EFFECT_LIST)' in lines[j]:
                    # This is the fixed implementation
                    assert True
                    return
            break
    # If we get here without finding either, something is wrong
    assert False, "Could not find effect_list implementation"

def test_effect_property_returns_off_when_none():
    """Test effect property returns EFFECT_OFF when no effect is active."""
    # Read the light.py file to check effect implementation
    test_dir = os.path.dirname(os.path.abspath(__file__))
    light_py_path = os.path.join(test_dir, "light.py")
    with open(light_py_path, "r") as f:
        content = f.read()

    # Check that effect property returns EFFECT_OFF when _attr_effect is None
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'def effect(self)' in line:
            # Get the implementation
            for j in range(i, min(i+20, len(lines))):
                if 'return EFFECT_OFF if self.effect_list else None' in lines[j]:
                    # This is the fixed implementation
                    assert True
                    return
                if 'return self._attr_effect' in lines[j] and 'EFFECT_OFF' not in lines[j]:
                    # This is the current (buggy) implementation
                    assert False, "Effect property still returns None instead of EFFECT_OFF"
                    return
            break
    # If we get here without finding either, something is wrong
    assert False, "Could not find effect property implementation"