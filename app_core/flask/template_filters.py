"""
Jinja2 template filter utilities.

This module provides custom Jinja2 template filters for Flask applications.

Functions:
    shields_escape: Escape text for shields.io badge URLs
"""


def shields_escape(text) -> str:
    """
    Escape text for use in shields.io badge URLs.
    
    Shields.io uses dashes as separators in badge URLs, requiring special
    escaping for dashes and underscores in badge text:
    - Dashes (-) must be doubled (--)
    - Underscores (_) must be doubled (__) as they represent spaces
    - Spaces remain as-is (shields.io handles them)
    
    Args:
        text: The text to escape for shields.io
        
    Returns:
        Escaped text safe for use in shields.io badge URLs.
        Returns the original text if it's empty or None.
        
    Example:
        >>> shields_escape("my-badge")
        'my--badge'
        >>> shields_escape("my_badge")
        'my__badge'
        >>> shields_escape("my-cool_badge")
        'my--cool__badge'
    """
    if not text:
        return text
    # Replace underscores first to avoid double-escaping
    escaped = str(text).replace('_', '__')
    # Replace dashes with double dashes
    escaped = escaped.replace('-', '--')
    return escaped


__all__ = ['shields_escape']
