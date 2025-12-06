"""
EAS Station - Emergency Alert System
Copyright (c) 2025 Timothy Kramer (KR8MER)

This file is part of EAS Station.

EAS Station is dual-licensed software:
- GNU Affero General Public License v3 (AGPL-3.0) for open-source use
- Commercial License for proprietary use

You should have received a copy of both licenses with this software.
For more information, see LICENSE and LICENSE-COMMERCIAL files.

IMPORTANT: This software cannot be rebranded or have attribution removed.
See NOTICE file for complete terms.

Repository: https://github.com/KR8MER/eas-station
"""

"""
Input validation and sanitization for authentication.

Provides security checks to detect and reject malicious login attempts
including SQL injection, command injection, and other attack patterns.
"""

import re
from typing import Tuple, Optional


class InputValidator:
    """Validator for authentication inputs to detect malicious patterns."""
    
    # Patterns that indicate SQL injection attempts
    SQL_INJECTION_PATTERNS = [
        r"'(\s)*(OR|AND|or|and)(\s)+",  # ' OR, ' AND
        r"\"(\s)*(OR|AND|or|and)(\s)+",  # " OR, " AND
        r"'\s*=\s*'",  # '=' pattern like '1'='1'
        r"--",  # SQL comment
        r"'/\*",  # SQL block comment start (with quote)
        r"/\*",  # SQL block comment start
        r";(\s)*(DROP|DELETE|UPDATE|INSERT|SELECT|drop|delete|update|insert|select)",  # SQL commands after semicolon
        r"(\s|^)(UNION|union)(\s)+(SELECT|select)",  # UNION SELECT
        r"(xp_|sp_|exec|execute|cmd|shell)",  # SQL Server stored procedures
        r"(\s|^)(1=1|0=0|true|false)(\s)*($|;|--)",  # Always true/false conditions
    ]
    
    # Patterns that indicate command injection attempts
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",  # Shell metacharacters
        r"\$\(",  # Command substitution
        r"\|\|",  # OR operator
        r"&&",  # AND operator
        r">\s*\/",  # Redirect to filesystem
    ]
    
    # Maximum allowed length for username
    MAX_USERNAME_LENGTH = 64
    MAX_PASSWORD_LENGTH = 128
    
    @classmethod
    def validate_username(cls, username: str) -> Tuple[bool, Optional[str]]:
        """
        Validate username input for security issues.
        
        Args:
            username: The username to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not username:
            return False, "Username is required"
        
        # Check length
        if len(username) > cls.MAX_USERNAME_LENGTH:
            return False, f"Username exceeds maximum length of {cls.MAX_USERNAME_LENGTH}"
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, username, re.IGNORECASE):
                return False, "Invalid username format"
        
        # Check for command injection patterns
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, username):
                return False, "Invalid username format"
        
        # Check for non-printable characters
        if not username.isprintable():
            return False, "Username contains invalid characters"
        
        return True, None
    
    @classmethod
    def validate_password(cls, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password input for security issues.
        
        Args:
            password: The password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
        # Check length
        if len(password) > cls.MAX_PASSWORD_LENGTH:
            return False, f"Password exceeds maximum length of {cls.MAX_PASSWORD_LENGTH}"
        
        return True, None
    
    @classmethod
    def sanitize_for_logging(cls, value: str, max_length: int = 100) -> str:
        """
        Sanitize a value for safe logging by removing suspicious patterns.
        
        Args:
            value: The value to sanitize
            max_length: Maximum length to include in logs
            
        Returns:
            Sanitized string safe for logging
        """
        if not value:
            return ""
        
        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length] + "..."
        
        # First, remove SQL comment markers (--) before general sanitization
        sanitized = value.replace('--', '')
        
        # Replace potentially dangerous characters
        # Keep alphanumeric, spaces, and common safe punctuation
        sanitized = re.sub(r'[^\w\s@._-]', '', sanitized)
        
        return sanitized
