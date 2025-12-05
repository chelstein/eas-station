"""
Datetime parsing utilities.

This module provides utilities for parsing datetime strings, particularly
NWS (National Weather Service) datetime formats.

Functions:
    parse_nws_datetime: Parse NWS datetime string wrapper
"""


def parse_nws_datetime(dt_string):
    """
    Parse NWS datetime string.
    
    This is a wrapper around app_utils.time.parse_nws_datetime for
    backward compatibility and convenient access.
    
    Args:
        dt_string: NWS datetime string to parse
        
    Returns:
        Parsed datetime object
        
    Example:
        >>> from datetime import datetime
        >>> dt = parse_nws_datetime("2025-12-05T12:00:00-05:00")
        >>> isinstance(dt, datetime)
        True
    """
    from app_utils.time import parse_nws_datetime as _parse
    return _parse(dt_string)


__all__ = ['parse_nws_datetime']
