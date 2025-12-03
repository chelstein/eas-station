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
Rate limiting for authentication to prevent brute force attacks.

Provides in-memory tracking of failed login attempts per IP address
with automatic cleanup of old entries.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict
import threading


class LoginRateLimiter:
    """Rate limiter for login attempts to prevent brute force attacks."""
    
    # Configuration
    MAX_ATTEMPTS = 5  # Maximum failed attempts before lockout
    LOCKOUT_DURATION = timedelta(minutes=15)  # How long to lock out after max attempts
    ATTEMPT_WINDOW = timedelta(minutes=5)  # Time window to count attempts
    
    def __init__(self):
        """Initialize the rate limiter with thread-safe storage."""
        self._attempts: Dict[str, List[datetime]] = defaultdict(list)
        self._lockouts: Dict[str, datetime] = {}
        self._lock = threading.Lock()
    
    def record_failed_attempt(self, ip_address: str) -> None:
        """
        Record a failed login attempt for an IP address.
        
        Args:
            ip_address: The IP address making the attempt
        """
        if not ip_address:
            return
        
        with self._lock:
            now = datetime.utcnow()
            
            # Add this attempt
            self._attempts[ip_address].append(now)
            
            # Clean up old attempts outside the window
            cutoff = now - self.ATTEMPT_WINDOW
            self._attempts[ip_address] = [
                attempt for attempt in self._attempts[ip_address]
                if attempt > cutoff
            ]
            
            # If max attempts reached, lock out
            if len(self._attempts[ip_address]) >= self.MAX_ATTEMPTS:
                self._lockouts[ip_address] = now
    
    def is_locked_out(self, ip_address: str) -> Tuple[bool, int]:
        """
        Check if an IP address is currently locked out.
        
        Args:
            ip_address: The IP address to check
            
        Returns:
            Tuple of (is_locked_out, seconds_remaining)
        """
        if not ip_address:
            return False, 0
        
        with self._lock:
            now = datetime.utcnow()
            
            # Check if there's an active lockout
            if ip_address in self._lockouts:
                lockout_time = self._lockouts[ip_address]
                lockout_end = lockout_time + self.LOCKOUT_DURATION
                
                if now < lockout_end:
                    seconds_remaining = int((lockout_end - now).total_seconds())
                    return True, seconds_remaining
                else:
                    # Lockout expired, clean up
                    del self._lockouts[ip_address]
                    if ip_address in self._attempts:
                        self._attempts[ip_address] = []
            
            return False, 0
    
    def clear_attempts(self, ip_address: str) -> None:
        """
        Clear failed attempts for an IP address (call on successful login).
        
        Args:
            ip_address: The IP address to clear
        """
        if not ip_address:
            return
        
        with self._lock:
            if ip_address in self._attempts:
                self._attempts[ip_address] = []
            if ip_address in self._lockouts:
                del self._lockouts[ip_address]
    
    def get_remaining_attempts(self, ip_address: str) -> int:
        """
        Get the number of remaining attempts before lockout.
        
        Args:
            ip_address: The IP address to check
            
        Returns:
            Number of remaining attempts
        """
        if not ip_address:
            return self.MAX_ATTEMPTS
        
        with self._lock:
            now = datetime.utcnow()
            cutoff = now - self.ATTEMPT_WINDOW
            
            # Count recent attempts
            if ip_address in self._attempts:
                recent_attempts = [
                    attempt for attempt in self._attempts[ip_address]
                    if attempt > cutoff
                ]
                return max(0, self.MAX_ATTEMPTS - len(recent_attempts))
            
            return self.MAX_ATTEMPTS
    
    def cleanup_old_entries(self) -> None:
        """
        Clean up expired lockouts and old attempts.
        
        Should be called periodically to prevent memory growth.
        """
        with self._lock:
            now = datetime.utcnow()
            
            # Clean up expired lockouts
            expired_lockouts = [
                ip for ip, lockout_time in self._lockouts.items()
                if now > lockout_time + self.LOCKOUT_DURATION
            ]
            for ip in expired_lockouts:
                del self._lockouts[ip]
                if ip in self._attempts:
                    self._attempts[ip] = []
            
            # Clean up old attempts
            cutoff = now - self.ATTEMPT_WINDOW
            for ip in list(self._attempts.keys()):
                self._attempts[ip] = [
                    attempt for attempt in self._attempts[ip]
                    if attempt > cutoff
                ]
                # Remove empty entries
                if not self._attempts[ip]:
                    del self._attempts[ip]


# Global rate limiter instance
_rate_limiter = LoginRateLimiter()


def get_rate_limiter() -> LoginRateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter
