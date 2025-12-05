"""
Environment variable parsing utilities.

This module provides functions for parsing environment variables with proper
type conversion and validation.

Functions:
    parse_env_list: Parse comma-separated environment variable into list
    parse_int_env: Parse integer environment variable with fallback default
"""

import os
from typing import List


def parse_env_list(name: str) -> List[str]:
    """
    Parse a comma-separated environment variable into a list of strings.
    
    Args:
        name: The name of the environment variable
        
    Returns:
        A list of non-empty, stripped strings. Returns empty list if variable
        is not set or is empty.
        
    Example:
        >>> os.environ['EMAILS'] = 'user1@example.com, user2@example.com'
        >>> parse_env_list('EMAILS')
        ['user1@example.com', 'user2@example.com']
    """
    raw_value = os.environ.get(name, '')
    if not raw_value:
        return []
    return [entry.strip() for entry in raw_value.split(',') if entry and entry.strip()]


def parse_int_env(name: str, default: int) -> int:
    """
    Parse an integer environment variable with a fallback default.
    
    Args:
        name: The name of the environment variable
        default: The default value to return if parsing fails
        
    Returns:
        The parsed integer value, or the default if the variable is not set
        or cannot be parsed as an integer.
        
    Example:
        >>> os.environ['INTERVAL'] = '300'
        >>> parse_int_env('INTERVAL', 60)
        300
        >>> parse_int_env('MISSING', 60)
        60
    """
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return int(str(raw_value).strip())
    except (TypeError, ValueError):
        return default


__all__ = ['parse_env_list', 'parse_int_env']
