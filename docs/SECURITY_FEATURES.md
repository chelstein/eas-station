# EAS Station Security Features

## Overview

This document describes the comprehensive security features implemented to protect against malicious login attempts, SQL injection, command injection, and brute force attacks.

## Features

### 1. Input Validation

**Location**: `app_core/auth/input_validation.py`

The input validator checks for:
- SQL injection patterns (`' OR 1=1`, `UNION SELECT`, etc.)
- Command injection patterns (`&&`, `||`, `;`, backticks, etc.)
- Non-printable characters
- Overly long inputs

All malicious inputs are:
- Rejected immediately
- Sanitized before logging
- Logged for security analysis
- Trigger automatic IP banning (24 hours)

### 2. Rate Limiting

**Location**: `app_core/auth/rate_limiter.py`

**Configuration**:
- Max attempts: 5 failed logins
- Lockout duration: 15 minutes
- Attempt window: 5 minutes

Features:
- Per-IP tracking of failed attempts
- Automatic lockout after threshold
- Cleanup of old entries

### 3. Flood Protection

**Location**: `app_core/auth/ip_filter.py` (FloodProtection class)

**Configuration**:
- Max attempts per minute: 10
- Auto-ban duration: 1 hour

Detects and automatically bans IPs making rapid-fire login attempts.

### 4. IP Filtering (Allowlist/Blocklist)

**Location**: `app_core/auth/ip_filter.py`

**Database Table**: `ip_filters`

Features:
- **Allowlist**: Trusted IPs/ranges that bypass all checks
- **Blocklist**: Banned IPs/ranges that cannot access the system
- CIDR range support (e.g., `192.168.1.0/24`)
- Optional expiration times
- Active/inactive toggle
- Manual and automatic entries

**Auto-ban Triggers**:
1. **Malicious Input** (24 hours): SQL/command injection attempt
2. **Brute Force** (24 hours): 5 failed login attempts
3. **Flooding** (1 hour): >10 attempts per minute

### 5. Security Logging

**Location**: `app_core/auth/security_logger.py`

**Log File**: `/var/log/eas-station/security.log`

**Event Types**:
- `MALICIOUS_LOGIN`: SQL/command injection attempt
- `FAILED_LOGIN`: Regular failed login
- `RATE_LIMIT_EXCEEDED`: Too many attempts

**Format** (fail2ban compatible):
```
[YYYY-MM-DD HH:MM:SS UTC] EVENT_TYPE from IP_ADDRESS username=USERNAME details=DETAILS
```

### 6. Audit Logging

**Location**: `app_core/auth/audit.py`

**Database Table**: `audit_logs`

Comprehensive audit trail of all security events including:
- Login successes/failures
- MFA events
- IP filter changes
- Permission denials

## fail2ban Integration

### Installation

1. **Install fail2ban**:
```bash
sudo apt-get install fail2ban
```

2. **Configure Jail** (`/etc/fail2ban/jail.local`):
```ini
[eas-station-malicious]
enabled = true
port = http,https
filter = eas-station-malicious
logpath = /var/log/eas-station/security.log
maxretry = 1
bantime = 3600
findtime = 600

[eas-station-auth]
enabled = true
port = http,https
filter = eas-station-auth
logpath = /var/log/eas-station/security.log
maxretry = 5
bantime = 1800
findtime = 600
```

3. **Create Malicious Filter** (`/etc/fail2ban/filter.d/eas-station-malicious.conf`):
```ini
[Definition]
failregex = ^.*MALICIOUS_LOGIN from <HOST>.*$
ignoreregex =
```

4. **Create Auth Filter** (`/etc/fail2ban/filter.d/eas-station-auth.conf`):
```ini
[Definition]
failregex = ^.*(FAILED_LOGIN|RATE_LIMIT_EXCEEDED) from <HOST>.*$
ignoreregex =
```

5. **Restart fail2ban**:
```bash
sudo systemctl restart fail2ban
```

### Testing

```bash
# Check status
sudo fail2ban-client status eas-station-malicious
sudo fail2ban-client status eas-station-auth

# View banned IPs
sudo fail2ban-client get eas-station-malicious banned

# Unban an IP
sudo fail2ban-client set eas-station-malicious unbanip 192.168.1.1
```

## Web Interface

### Malicious Login Attempts Page

**URL**: `/admin/malicious-logins`

**Features**:
- View all malicious login attempts
- Statistics dashboard (total attempts, unique IPs, today's attempts)
- Top attacking IP addresses
- Quick ban from statistics
- fail2ban configuration viewer

### IP Filter Management

**Location**: Same page as malicious logins

**Actions**:
- Add to allowlist/blocklist
- Support for single IPs or CIDR ranges
- Set expiration time (blocklist only)
- Toggle active/inactive
- Delete filters
- View reason and description

**Example Allowlist Entries**:
- `192.168.1.0/24` - Internal network
- `10.0.0.5` - Admin workstation

**Example Blocklist Entries**:
- `1.2.3.4` - Known attacker
- `5.6.7.0/24` - Malicious subnet

## API Endpoints

### IP Filters

- `GET /security/ip-filters` - List all filters
- `POST /security/ip-filters` - Add new filter
- `DELETE /security/ip-filters/<id>` - Delete filter
- `POST /security/ip-filters/<id>/toggle` - Toggle active status
- `POST /security/ip-filters/cleanup` - Clean up expired filters

### Audit Logs

- `GET /security/audit-logs` - List audit logs
- `GET /security/malicious-login-attempts` - List malicious attempts with IP statistics

## Database Migrations

To apply the IP filters table migration:

```bash
cd /home/runner/work/eas-station/eas-station
alembic upgrade head
```

Or if using Docker:

```bash
docker-compose exec eas-station alembic upgrade head
```

## Configuration

### Rate Limiting

Edit `app_core/auth/rate_limiter.py`:
```python
MAX_ATTEMPTS = 5  # Maximum failed attempts before lockout
LOCKOUT_DURATION = timedelta(minutes=15)  # How long to lock out
ATTEMPT_WINDOW = timedelta(minutes=5)  # Time window to count attempts
```

### Flood Protection

Edit `app_core/auth/ip_filter.py`:
```python
MAX_ATTEMPTS_PER_MINUTE = 10  # Max attempts per minute
FLOOD_BAN_HOURS = 1  # Ban duration for flooding
```

### Auto-Ban

Edit `app_core/auth/ip_filter.py`:
```python
FAILED_ATTEMPTS_THRESHOLD = 5  # Failed attempts before auto-ban
BAN_DURATION_HOURS = 24  # Ban duration
```

## Security Best Practices

1. **Enable fail2ban** for external IP blocking
2. **Add your admin IPs to allowlist** to prevent accidental lockout
3. **Monitor the malicious logins page** regularly
4. **Review auto-banned IPs** periodically
5. **Set up log rotation** for security logs
6. **Enable MFA** for all admin accounts
7. **Use strong passwords** with minimum 12 characters

## Troubleshooting

### Locked Out Admin

If an admin IP is accidentally blocked:

1. **Via Database**:
```sql
DELETE FROM ip_filters WHERE ip_address = '1.2.3.4';
```

2. **Via fail2ban**:
```bash
sudo fail2ban-client set eas-station-auth unbanip 1.2.3.4
```

### Check Security Logs

```bash
tail -f /var/log/eas-station/security.log
```

### View Recent Audit Logs

```bash
# Via API
curl http://localhost:5000/security/audit-logs?days=1

# Via Database
psql -d eas_station -c "SELECT * FROM audit_logs WHERE timestamp > NOW() - INTERVAL '1 day' ORDER BY timestamp DESC LIMIT 20;"
```

## Monitoring

Recommended monitoring:
- Track failed login attempts per hour
- Alert on >50 malicious attempts in 1 hour
- Alert on auto-ban triggers
- Weekly review of blocklist entries
- Monitor fail2ban ban count

## Updates

To update security features:

1. Pull latest code
2. Run migrations: `alembic upgrade head`
3. Restart application
4. Review new configuration options
5. Update fail2ban filters if needed

## Support

For security concerns or questions:
- Open an issue on GitHub
- Review audit logs for suspicious activity
- Check fail2ban status regularly
