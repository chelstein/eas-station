# Firewall Port Requirements

## Overview

EAS Station uses several network ports for its services. This document lists all ports that may need to be opened in your firewall for proper operation.

## Required Ports (External Access)

These ports need to be accessible from outside the host for normal operation:

| Port | Protocol | Service | Description |
|------|----------|---------|-------------|
| **443** | TCP | HTTPS (nginx) | Web interface (primary access). Uses SSL/TLS encryption. |
| **8888** | TCP | HTTP (nginx) | Redirects to HTTPS. Also allows local API access for hardware displays. |
| **8001** | TCP | Icecast | Audio streaming server for public stream access (configurable via `ICECAST_PORT`). |


These ports are used internally between services and should **not** be exposed to the internet:

| Port | Protocol | Service | Description |
|------|----------|---------|-------------|
| **5000** | TCP | Flask App | Web application backend (nginx proxies to this). |
| **5001** | TCP | Hardware Service | GPIO, network management, and hardware control API. |
| **5002** | TCP | SDR/Audio Service | Audio streaming server for internal audio processing. |
| **5432** | TCP | PostgreSQL | Database (embedded profile or external). |
| **6379** | TCP | Redis | In-memory cache for real-time updates. |
| **8000** | TCP | Icecast (internal) | Internal Icecast port (proxied to 8001 externally). |

## Firewall Configuration Examples

### UFW (Ubuntu/Debian)

```bash
# Allow HTTPS (web interface)
sudo ufw allow 443/tcp

# Allow HTTP redirect (optional, recommended)
sudo ufw allow 8888/tcp

# Allow Icecast streaming (optional, for public audio streams)
sudo ufw allow 8001/tcp

# Verify rules
sudo ufw status
```

### firewalld (RHEL/CentOS/Fedora)

```bash
# Allow HTTPS (web interface)
sudo firewall-cmd --permanent --add-port=443/tcp

# Allow HTTP redirect (optional, recommended)
sudo firewall-cmd --permanent --add-port=8888/tcp

# Allow Icecast streaming (optional, for public audio streams)
sudo firewall-cmd --permanent --add-port=8001/tcp

# Reload and verify
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

### iptables (Manual)

```bash
# Allow HTTPS (web interface)
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow HTTP redirect (optional, recommended)
sudo iptables -A INPUT -p tcp --dport 8888 -j ACCEPT

# Allow Icecast streaming (optional, for public audio streams)
sudo iptables -A INPUT -p tcp --dport 8001 -j ACCEPT

# Save rules (varies by distribution)
sudo netfilter-persistent save  # Debian/Ubuntu
sudo service iptables save      # RHEL/CentOS
```

## Cloud Provider Firewalls

If running on a cloud provider (AWS, Azure, GCP, DigitalOcean, etc.), you also need to configure the security group or network security rules:

### Minimum Required Rules

| Direction | Port | Protocol | Source | Description |
|-----------|------|----------|--------|-------------|
| Inbound | 443 | TCP | 0.0.0.0/0 | HTTPS web interface |
| Inbound | 8888 | TCP | 0.0.0.0/0 | HTTP redirect to HTTPS |
| Inbound | 22 | TCP | Your IP | SSH access (management) |

### Optional Rules

| Direction | Port | Protocol | Source | Description |
|-----------|------|----------|--------|-------------|
| Inbound | 8001 | TCP | 0.0.0.0/0 | Icecast audio streaming (if public streams enabled) |

## Troubleshooting Connection Issues

### Symptom: "Connection refused" errors in nginx logs

```
connect() failed (111: Connection refused) while connecting to upstream
```

This error indicates nginx cannot connect to the Flask backend (port 5000). Common causes:

1. **Flask app not running** - Check if the app container is healthy:
   ```bash
   ```

2. **Database migration errors** - The app may fail to start due to database issues:
   ```bash
   ```

   ```bash
   ```

### Symptom: Cannot access web interface externally

1. **Check firewall rules** - Ensure ports 443 and 8888 are open
2. **Check cloud security groups** - Verify inbound rules allow traffic
3. **Test local connectivity first**:
   ```bash
   curl -k https://localhost
   curl http://localhost:8888
   ```

### Symptom: Icecast streams not accessible

1. **Verify Icecast is running**:
   ```bash
   ```

2. **Check port mapping**:
   ```bash
   ```

3. **Test local access**:
   ```bash
   curl http://localhost:8001/status-json.xsl
   ```

## Related Documentation

- [Setup Instructions](../guides/SETUP_INSTRUCTIONS.md) - Initial deployment guide
- [Database Troubleshooting](DATABASE_CONSISTENCY_FIXES.md) - Database connection issues
