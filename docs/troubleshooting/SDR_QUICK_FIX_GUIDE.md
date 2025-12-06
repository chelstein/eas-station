# SDR Quick Fix Guide

**⚡ Fast solutions for the most common SDR problems**

---

## 🚨 Emergency Diagnostics

Run this **first** if SDR is not working:

```bash
# One-command diagnostic
bash scripts/collect_sdr_diagnostics.sh

# Or quick check:
docker compose exec app python3 scripts/sdr_diagnostics.py
```

---

## ✅ 5-Minute Checklist

Work through these in order:

### 1. Hardware Check (30 seconds)
```bash
lsusb | grep -E "RTL|Airspy|Realtek"
```
- ✅ **Device appears** → Go to step 2
- ❌ **Nothing appears** → Replug USB, try different port, check cable

### 2. Software Check (30 seconds)
```bash
docker compose exec app SoapySDRUtil --find
```
- ✅ **Device listed** → Go to step 3
- ❌ **Empty list** → Rebuild containers: `docker compose build && docker compose up -d`

### 3. Service Check (30 seconds)
```bash
docker compose ps
```
- ✅ **All "Up"** → Go to step 4
- ❌ **sdr-service restarting** → Check logs: `docker compose logs sdr-service`

### 4. Configuration Check (2 minutes)
```bash
docker compose exec app psql -U postgres -d alerts -c "
  SELECT identifier, frequency_hz, frequency_hz/1e6 as freq_mhz, 
         gain, enabled, auto_start 
  FROM radio_receivers;
"
```

**Fix common mistakes:**

| Problem | Fix |
|---------|-----|
| `frequency_hz` is small (< 1 million) | Multiply by 1,000,000 (e.g., 162.55 → 162550000) |
| `gain` is NULL or 0 | Set to 40.0 for RTL-SDR, 21.0 for Airspy |
| `enabled` is false | Set to `true` |
| `auto_start` is false | Set to `true` |

**Quick fix SQL:**
```sql
-- Fix frequency (NOAA WX7 example)
UPDATE radio_receivers SET frequency_hz = 162550000 WHERE identifier = 'your-receiver';

-- Fix gain
UPDATE radio_receivers SET gain = 40.0 WHERE driver = 'rtlsdr';

-- Enable receiver
UPDATE radio_receivers SET enabled = true, auto_start = true WHERE identifier = 'your-receiver';
```

Then restart:
```bash
docker compose restart sdr-service audio-service
```

### 5. Audio Check (1 minute)
```bash
docker compose logs audio-service | grep -E "audio chunk|demod" | tail -10
```
- ✅ **Seeing "audio chunk" messages** → Audio is working!
- ❌ **No messages** → Check audio output setting:
  ```sql
  UPDATE radio_receivers SET audio_output = true WHERE identifier = 'your-receiver';
  ```

---

## 🔥 Most Common Problems

### Problem: "No devices found"

**One-line fix (USB permissions):**
```bash
sudo usermod -aG plugdev $USER && echo "Log out and back in for this to take effect"
```

**One-line fix (Docker):**
```bash
docker compose down && docker compose up -d --build
```

---

### Problem: "Can't hear anything"

**Quick fixes to try in order:**

1. **Set gain:**
   ```sql
   UPDATE radio_receivers SET gain = 40.0 WHERE driver = 'rtlsdr';
   ```

2. **Enable audio output:**
   ```sql
   UPDATE radio_receivers SET audio_output = true;
   ```

3. **Fix modulation type:**
   ```sql
   UPDATE radio_receivers SET modulation_type = 'NFM' WHERE frequency_hz BETWEEN 162e6 AND 163e6;
   ```

4. **Restart services:**
   ```bash
   docker compose restart sdr-service audio-service
   ```

---

### Problem: "Wrong frequency"

**Always specify frequency in Hz, not MHz!**

```sql
-- ❌ WRONG
UPDATE radio_receivers SET frequency_hz = 162.55;

-- ✅ CORRECT
UPDATE radio_receivers SET frequency_hz = 162550000;
```

**Common NOAA frequencies (in Hz):**
- WX1: `162400000`
- WX2: `162425000`
- WX3: `162450000`
- WX4: `162475000`
- WX5: `162500000`
- WX6: `162525000`
- WX7: `162550000`

---

### Problem: "Airspy not working"

**Airspy R2 only supports TWO sample rates:**

```sql
-- ❌ WRONG (will fail)
UPDATE radio_receivers SET sample_rate = 2400000 WHERE driver = 'airspy';

-- ✅ CORRECT (choose one)
UPDATE radio_receivers SET sample_rate = 2500000 WHERE driver = 'airspy';
-- OR
UPDATE radio_receivers SET sample_rate = 10000000 WHERE driver = 'airspy';
```

---

### Problem: "Service keeps restarting"

**Check if device is in use:**
```bash
# Kill other SDR software
killall gqrx SDRangel sdr++ 2>/dev/null || true

# Restart services
docker compose restart sdr-service
```

---

## 🎯 Quick Configuration Templates

### NOAA Weather Radio (RTL-SDR)

```sql
INSERT INTO radio_receivers (
  identifier, display_name, driver, frequency_hz, sample_rate, 
  gain, modulation_type, audio_output, enabled, auto_start
) VALUES (
  'noaa-wx7', 'NOAA Weather WX7', 'rtlsdr', 162550000, 2400000,
  40.0, 'NFM', true, true, true
);
```

### NOAA Weather Radio (Airspy R2)

```sql
INSERT INTO radio_receivers (
  identifier, display_name, driver, frequency_hz, sample_rate,
  gain, modulation_type, audio_output, enabled, auto_start
) VALUES (
  'noaa-wx7', 'NOAA Weather WX7', 'airspy', 162550000, 2500000,
  21.0, 'NFM', true, true, true
);
```

### FM Broadcast Station (RTL-SDR)

```sql
INSERT INTO radio_receivers (
  identifier, display_name, driver, frequency_hz, sample_rate,
  gain, modulation_type, audio_output, stereo_enabled, enabled, auto_start
) VALUES (
  'fm-station', 'Local FM 101.1', 'rtlsdr', 101100000, 2400000,
  40.0, 'WFM', true, true, true, true
);
```

---

## 🔧 One-Line Diagnostics

Copy and paste these to check specific things:

```bash
# Is USB device detected?
lsusb | grep -E "RTL|Airspy|Realtek"

# Can SoapySDR see it?
docker compose exec app SoapySDRUtil --find

# Are services running?
docker compose ps | grep -E "sdr|audio"

# Any errors in logs?
docker compose logs sdr-service --tail=20 | grep -i error

# What's configured?
docker compose exec app psql -U postgres -d alerts -c "SELECT identifier, frequency_hz/1e6, gain, enabled FROM radio_receivers;"

# Test capture
docker compose exec app python3 scripts/sdr_diagnostics.py --test-capture --frequency 162550000

# Is audio flowing?
docker compose logs audio-service | grep "audio chunk" | tail -5

# Redis working?
docker compose exec redis redis-cli ping
```

---

## 📊 Expected vs Actual

### What "Working" Looks Like

**Container status:**
```
NAME                STATUS
sdr-service         Up X minutes
audio-service       Up X minutes
app                 Up X minutes
```

**SoapySDR output:**
```
[
  {
    "driver": "rtlsdr",
    "label": "Generic RTL2832U :: 00000001",
    "serial": "00000001"
  }
]
```

**Database config:**
```
 identifier  | frequency_hz | freq_mhz | gain | enabled | auto_start
-------------+--------------+----------+------+---------+------------
 noaa-wx7    |    162550000 |  162.550 | 40.0 | t       | t
```

**Service logs (no errors):**
```
✅ SDR Service started successfully
Configured 1 radio receiver(s) from database
Started 1 receiver(s) with auto_start enabled
Receiver noaa-wx7: Signal locked at 162.550 MHz
```

---

## 🆘 Still Not Working?

1. **Collect full diagnostics:**
   ```bash
   bash scripts/collect_sdr_diagnostics.sh
   ```

2. **Read the full guide:**
   - [SDR Master Troubleshooting Guide](SDR_MASTER_TROUBLESHOOTING_GUIDE.md)
   - [SDR Setup Guide](../hardware/SDR_SETUP.md)

3. **Get help:**
   - GitHub Issues: https://github.com/KR8MER/eas-station/issues
   - Include the diagnostic output file
   - Mention what you've already tried

---

## 🎓 Prevention Tips

**Avoid future problems:**

1. ✅ Always use Hz for frequency (not MHz)
2. ✅ Set gain explicitly (don't leave NULL)
3. ✅ Use correct sample rate for your hardware
4. ✅ Enable both `enabled` and `auto_start`
5. ✅ Restart services after config changes
6. ✅ Use powered USB hub for multiple devices
7. ✅ Keep antenna away from interference sources

---

**Quick Reference Card Last Updated:** December 2025
