"""
Unit tests for environment variable parsing utilities.

Tests the functions in app_core.config.environment module.
"""

import os
import pytest
from app_core.config.environment import parse_env_list, parse_int_env


class TestParseEnvList:
    """Tests for parse_env_list function."""
    
    def test_empty_environment_variable(self, monkeypatch):
        """Test that an empty environment variable returns an empty list."""
        monkeypatch.delenv('TEST_VAR', raising=False)
        result = parse_env_list('TEST_VAR')
        assert result == []
    
    def test_single_value(self, monkeypatch):
        """Test parsing a single value."""
        monkeypatch.setenv('TEST_VAR', 'value1')
        result = parse_env_list('TEST_VAR')
        assert result == ['value1']
    
    def test_multiple_values(self, monkeypatch):
        """Test parsing multiple comma-separated values."""
        monkeypatch.setenv('TEST_VAR', 'value1,value2,value3')
        result = parse_env_list('TEST_VAR')
        assert result == ['value1', 'value2', 'value3']
    
    def test_whitespace_handling(self, monkeypatch):
        """Test that whitespace around values is stripped."""
        monkeypatch.setenv('TEST_VAR', ' value1 , value2 , value3 ')
        result = parse_env_list('TEST_VAR')
        assert result == ['value1', 'value2', 'value3']
    
    def test_empty_entries_ignored(self, monkeypatch):
        """Test that empty entries between commas are ignored."""
        monkeypatch.setenv('TEST_VAR', 'value1,,value2,,,value3')
        result = parse_env_list('TEST_VAR')
        assert result == ['value1', 'value2', 'value3']
    
    def test_only_commas_returns_empty(self, monkeypatch):
        """Test that a string with only commas returns an empty list."""
        monkeypatch.setenv('TEST_VAR', ',,,')
        result = parse_env_list('TEST_VAR')
        assert result == []
    
    def test_real_world_email_list(self, monkeypatch):
        """Test with real-world email addresses."""
        monkeypatch.setenv('TEST_VAR', 'admin@example.com, ops@example.com, alerts@example.com')
        result = parse_env_list('TEST_VAR')
        assert result == ['admin@example.com', 'ops@example.com', 'alerts@example.com']


class TestParseIntEnv:
    """Tests for parse_int_env function."""
    
    def test_missing_variable_returns_default(self, monkeypatch):
        """Test that a missing variable returns the default value."""
        monkeypatch.delenv('TEST_VAR', raising=False)
        result = parse_int_env('TEST_VAR', 42)
        assert result == 42
    
    def test_valid_integer_string(self, monkeypatch):
        """Test parsing a valid integer string."""
        monkeypatch.setenv('TEST_VAR', '300')
        result = parse_int_env('TEST_VAR', 60)
        assert result == 300
    
    def test_integer_with_whitespace(self, monkeypatch):
        """Test that whitespace around the integer is handled."""
        monkeypatch.setenv('TEST_VAR', ' 300 ')
        result = parse_int_env('TEST_VAR', 60)
        assert result == 300
    
    def test_negative_integer(self, monkeypatch):
        """Test parsing a negative integer."""
        monkeypatch.setenv('TEST_VAR', '-50')
        result = parse_int_env('TEST_VAR', 0)
        assert result == -50
    
    def test_zero_value(self, monkeypatch):
        """Test parsing zero."""
        monkeypatch.setenv('TEST_VAR', '0')
        result = parse_int_env('TEST_VAR', 100)
        assert result == 0
    
    def test_invalid_string_returns_default(self, monkeypatch):
        """Test that an invalid string returns the default."""
        monkeypatch.setenv('TEST_VAR', 'not_a_number')
        result = parse_int_env('TEST_VAR', 42)
        assert result == 42
    
    def test_float_string_returns_default(self, monkeypatch):
        """Test that a float string returns the default."""
        monkeypatch.setenv('TEST_VAR', '3.14')
        result = parse_int_env('TEST_VAR', 42)
        assert result == 42
    
    def test_empty_string_returns_default(self, monkeypatch):
        """Test that an empty string returns the default."""
        monkeypatch.setenv('TEST_VAR', '')
        result = parse_int_env('TEST_VAR', 42)
        assert result == 42
    
    def test_large_integer(self, monkeypatch):
        """Test parsing a large integer."""
        monkeypatch.setenv('TEST_VAR', '999999999')
        result = parse_int_env('TEST_VAR', 0)
        assert result == 999999999
