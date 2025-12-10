# pgAdmin 4 Apache2 Installation Conflict

## Overview

This document explains the Apache2 conflict issue that occurred during pgAdmin 4 installation in versions prior to 2.19.7, and how it was resolved.

## Problem Description

### Issue 1: Apache2 Dependency Conflict

When installing pgAdmin 4 using the Debian/Ubuntu package (`pgadmin4-web`), the package manager would automatically install Apache2 as a dependency. This created several problems:

1. **Port Conflict**: Apache2 tries to bind to port 80, which is already in use by nginx
2. **Service Failure**: Apache2 service fails to start with error:
   ```
   (98)Address already in use: AH00072: make_sock: could not bind to address [::]:80
   (98)Address already in use: AH00072: make_sock: could not bind to address 0.0.0.0:80
   ```
3. **Installation Interruption**: The failed Apache2 start would sometimes cause the installation to fail

### Issue 2: Missing Python Module (typer)

pgAdmin's setup script requires the `typer` Python module, which was not installed automatically:

```
Traceback (most recent call last):
  File "/usr/pgadmin4/web/setup.py", line 15, in <module>
    import typer
ModuleNotFoundError: No module named 'typer'
```

This prevented pgAdmin from being configured properly during installation.

## Solution (Version 2.19.7+)

The `install.sh` script now implements a comprehensive solution:

### 1. Block Apache2 Before Installation

An apt preferences file is created to prevent Apache2 installation:

```bash
cat > /etc/apt/preferences.d/block-apache2 << 'APT_PREFS'
Package: apache2 apache2-bin apache2-data apache2-utils libapache2-mod-wsgi-py3
Pin: version *
Pin-Priority: -1
APT_PREFS
```

The negative pin priority tells apt to **never install these packages**, even as dependencies.

### 2. Remove Existing Apache2

If Apache2 is already installed, it's removed and masked:

```bash
systemctl stop apache2
systemctl disable apache2
systemctl mask apache2
apt-get remove -y apache2 apache2-bin apache2-data apache2-utils libapache2-mod-wsgi-py3
apt-get autoremove -y
```

### 3. Install Required Dependencies

The typer module and gunicorn are installed before pgAdmin setup:

```bash
apt-get install -y python3-typer python3-gunicorn gunicorn
```

If apt installation fails, the script falls back to pip:

```bash
pip3 install typer gunicorn
```

### 4. Install pgAdmin Safely

With Apache2 blocked, pgAdmin packages can be installed without conflicts:

```bash
apt-get install -y pgadmin4-desktop pgadmin4-web
```

### 5. Clean Up

After installation, the Apache2 block is removed to allow future manual installation if needed:

```bash
rm -f /etc/apt/preferences.d/block-apache2
```

## Architecture

pgAdmin 4 is configured to run via Gunicorn WSGI server, proxied through nginx:

```
Browser → nginx (port 443) → Gunicorn (unix socket) → pgAdmin4 Python app
```

This eliminates the need for Apache2 entirely.

## Verification

After installation, verify that Apache2 is not installed:

```bash
# Check if apache2 is installed
dpkg -l | grep apache2

# Should show "no packages found" or only removed packages (rc status)
```

Verify pgAdmin is running via Gunicorn:

```bash
# Check pgAdmin service status
sudo systemctl status pgadmin4

# Should show "active (running)"
```

Access pgAdmin through nginx:
- Navigate to: `https://<your-server>/pgadmin4`
- Login with your admin credentials

## Manual Fix (If Issue Persists)

If you're experiencing this issue on an existing installation, you can manually fix it:

### Step 1: Stop and Remove Apache2

```bash
sudo systemctl stop apache2
sudo systemctl disable apache2
sudo systemctl mask apache2
sudo apt-get remove -y apache2 apache2-bin apache2-data apache2-utils libapache2-mod-wsgi-py3
sudo apt-get autoremove -y
```

### Step 2: Install Missing Dependencies

```bash
sudo apt-get install -y python3-typer python3-gunicorn gunicorn
```

### Step 3: Reconfigure pgAdmin

```bash
# Create pgAdmin systemd service if it doesn't exist
sudo cat > /etc/systemd/system/pgadmin4.service << 'EOF'
[Unit]
Description=pgAdmin 4 WSGI Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/usr/pgadmin4/web
Environment="PYTHONPATH=/usr/pgadmin4/web"
ExecStart=/usr/bin/gunicorn \
    --bind unix:/var/run/pgadmin4.sock \
    --workers 2 \
    --timeout 300 \
    --access-logfile /var/log/pgadmin/access.log \
    --error-logfile /var/log/pgadmin/error.log \
    pgadmin4:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start pgAdmin
sudo systemctl daemon-reload
sudo systemctl enable pgadmin4
sudo systemctl start pgadmin4
```

### Step 4: Configure nginx Proxy

Add this location block to your nginx config (`/etc/nginx/sites-available/eas-station`):

```nginx
# pgAdmin 4 proxy (WSGI via Gunicorn)
location /pgadmin4/ {
    proxy_pass http://unix:/var/run/pgadmin4.sock:/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Script-Name /pgadmin4;
    proxy_buffering off;
    proxy_read_timeout 300s;
}
```

Reload nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Prevention for Future Installations

The `install.sh` script (version 2.19.7+) handles this automatically. No manual intervention needed.

## Related Issues

- Port 80 conflicts between Apache2 and nginx
- Missing Python dependencies for pgAdmin
- Remote access issues (see [FIREWALL_REQUIREMENTS.md](FIREWALL_REQUIREMENTS.md))

## References

- [pgAdmin 4 Documentation](https://www.pgadmin.org/docs/)
- [Debian Package Pinning](https://wiki.debian.org/AptConfiguration)
- [nginx Reverse Proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
