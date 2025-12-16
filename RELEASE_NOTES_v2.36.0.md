# EAS Station v2.36.0 - Critical Fixes Summary

## Issues Fixed in This Release

### 1. ✅ LED Sign IP Address Configuration
**Problem**: No way to configure the IP address of the serial-to-ethernet converter for the LED sign.

**Solution**: 
- Added IP Address and Port fields to the Hardware tab in the Admin page
- Configuration is saved to the database and used by the hardware service
- Navigate to: **Admin → Hardware Tab → LED Sign section**

### 2. ✅ SSL/Certbot Management Consolidation  
**Problem**: Two separate locations for obtaining SSL certificates, causing confusion.

**Solution**:
- Simplified SSL tab in admin page shows quick status overview
- Advanced SSL/Certbot management moved to dedicated page at `/admin/certbot`
- Clear separation: **Admin → SSL/Certbot tab** for status, **Settings → SSL Certificates** for full management

### 3. ✅ Zone Catalog Permission Denied
**Problem**: Zone Catalog showed "You do not have permission to access that page" error.

**Solution**:
- Fixed incorrect permission requirement (was using non-existent `admin.settings`, now uses `system.configure`)
- Zone catalog now accessible to all users with `system.configure` permission
- Navigate to: **Admin → Zone Catalog tab**

### 4. ✅ **CRITICAL: Admin Users Show "No Role"**
**Problem**: Admin account created during installation has "No Role" assigned, preventing access to most features.

**Solution**:
- Fixed user creation to initialize roles before creating the first admin
- Created fix script for existing installations

**ACTION REQUIRED** - Run this command to fix existing admin users:
```bash
python3 scripts/fix_admin_roles.py
```

This script will:
- Initialize roles and permissions if not already done
- Assign the "admin" role to any users that have "No Role"
- Verify all users have proper role assignments

### 5. ✅ Hardware Settings Permission Issue
**Problem**: `/admin/hardware` page required superuser 'admin' permission, causing access denied errors.

**Solution**:
- Changed permission from `admin` to `system.configure`
- Regular admin users can now access advanced hardware settings

---

## Icecast and Audio Monitor Issues

**Status**: These are **deployment/configuration issues**, not code bugs.

### Likely Causes:
1. **Audio Service Not Running** - The `audio-service` may not be started
2. **Nginx Proxy Not Configured** - Nginx needs to proxy `/api/audio/stream/` to `audio-service:5002`
3. **Icecast Not Running** - The `icecast2` service may not be running or configured

### Troubleshooting Steps:
```bash
# Check if audio-service is running
sudo systemctl status eas-audio-service  # or docker ps

# Check if icecast2 is running  
sudo systemctl status icecast2

# Check nginx configuration
cat /etc/nginx/sites-enabled/eas-station | grep audio

# Check icecast configuration
cat /etc/icecast2/icecast.xml | grep password
```

---

## Installation Instructions

If you haven't already, pull the latest changes:

```bash
cd /path/to/eas-station
git pull origin main
```

### **IMPORTANT: Fix Admin Roles**

If your admin user shows "No Role" in the Admin → Users tab:

```bash
python3 scripts/fix_admin_roles.py
```

After running this script, log out and log back in for changes to take effect.

---

## Version Information

**Version**: 2.36.0
**Release Date**: December 16, 2024
**Type**: Bug fixes and feature enhancements

### Changes:
- **Added**: LED IP/port configuration in Hardware tab
- **Added**: Admin role fix script
- **Enhanced**: SSL/Certbot management simplified
- **Enhanced**: User creation with automatic role initialization
- **Fixed**: Zone catalog permissions
- **Fixed**: Hardware settings permissions  
- **Fixed**: Admin users without roles
- **Fixed**: Duplicate return statement in LED config
- **Fixed**: IP address validation improved

### Security:
- ✅ Code review completed - all issues addressed
- ✅ CodeQL security scan - 0 vulnerabilities found
- ✅ Proper IP address validation using `ipaddress` module

---

## Support

If you encounter any issues:

1. Check the `/bugs` directory for known issues
2. Run the fix script: `python3 scripts/fix_admin_roles.py`
3. Review service status (icecast, audio-service, nginx)
4. Check logs in `/var/log/eas-station/` or `docker logs`

For questions or bug reports, open an issue on GitHub.
