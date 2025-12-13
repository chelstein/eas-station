# Bidirectional Communication with Alpha LED Signs

## Overview

**Alpha LED signs support full bidirectional (duplex) communication**, allowing you to:
- ✅ **Send commands** to the sign (display messages, set time, etc.)
- ✅ **Read responses** from the sign (ACK/NAK, status, configuration)
- ✅ **Query sign data** (current message, memory usage, etc.)
- ✅ **Set configuration** (time/date, brightness, etc.)

The EAS Station LED controller and Waveshare adapter **fully support bidirectional communication**.

---

## How It Works

### Communication Flow

```
EAS Station ←→ TCP Socket ←→ Waveshare ←→ RS232 ←→ Alpha LED Sign
   (Python)                  (Network)    (Serial)      (M-Protocol)
```

### Bidirectional Data

**Outbound (EAS → Sign):**
- Display text messages
- Set colors and modes
- Configure time/date
- Read memory/status commands

**Inbound (Sign → EAS):**
- ACK (0x06) - Command accepted
- NAK (0x15) - Command rejected  
- Status responses
- Configuration data
- Error codes

---

## EAS Station LED Controller Support

The LED controller (`scripts/led_sign_controller.py`) implements full bidirectional M-Protocol:

### Sending Data

```python
def send_message(self, lines, color, mode, ...):
    # 1. Drain any pending input
    self._drain_input_buffer()
    
    # 2. Send M-Protocol message
    self.socket.sendall(message)
    
    # 3. Wait for acknowledgment
    ack = self._read_acknowledgement()
    
    # 4. Send EOT if ACK received
    if ack == self.ACK:
        self._send_eot()
```

### Reading Responses

```python
def _read_acknowledgement(self) -> Optional[bytes]:
    """Read an ACK (0x06) or NAK (0x15) response from the sign."""
    
    self.socket.settimeout(2)  # 2 second timeout
    while True:
        chunk = self.socket.recv(1)  # Read one byte at a time
        if chunk in (self.ACK, self.NAK):
            return chunk
```

### Key Features

- ✅ **Waits for ACK/NAK** after every command
- ✅ **Handles timeouts** gracefully (2 second default)
- ✅ **Drains input buffer** before sending (prevents stale data)
- ✅ **Completes transaction** with EOT after ACK
- ✅ **Full M-Protocol** compliance

---

## Waveshare Adapter Configuration

### Critical Settings for Bidirectional

**Network A Settings:**
```
Mode: Server
Protocol: TCP
Port: 10001
TCP Time out: 0  ⭐ CRITICAL: Must be 0 or high for responses
```

**UART AutoFrame:**
```
UART AutoFrame: Enable  ⭐ CRITICAL: Frames responses properly
AutoFrame Time: 500 ms
AutoFrame Length: 512 bytes
```

**Socket Distribution:**
```
Socket Distribution: on  ⭐ CRITICAL: Enables bidirectional flow
```

**Flow Control:**
```
Flow Control: None  ⭐ IMPORTANT: Most Alpha signs don't use hardware flow control
```

### Why These Settings Matter

**TCP Time out: 0**
- If set too low, connection drops before sign can respond
- Sign may take 100-500ms to process and respond
- Setting to 0 means "never timeout"

**UART AutoFrame: Enable**
- Captures complete responses from sign
- Prevents partial ACK/NAK packets
- Ensures EOT is sent after complete transaction

**Socket Distribution: on**
- Enables simultaneous TX and RX
- Required for duplex communication
- Without this, responses may be lost

---

## M-Protocol Bidirectional Commands

### Commands That Expect Responses

**1. Write Text (Type A)**
```
Format: <NULL><NULL><NULL><NULL><NULL><ID><CMD><FILE><TEXT><EOT>
Send: Display message
Receive: ACK or NAK
```

**2. Read Text (Type B)**
```
Format: <NULL><NULL><NULL><NULL><NULL><ID><CMD><FILE><ETX>
Send: Request to read file
Receive: ACK + File contents or NAK
```

**3. Read Special Functions (Type E)**
```
Format: <NULL><NULL><NULL><NULL><NULL><ID><CMD><FUNCTION><ETX>
Send: Read memory, serial number, etc.
Receive: ACK + Function data or NAK
```

**4. Write Special Functions (Type E)**
```
Format: <NULL><NULL><NULL><NULL><NULL><ID><CMD><FUNCTION><DATA><ETX>
Send: Set time, date, speaker, etc.
Receive: ACK or NAK
```

### Response Codes

| Code | Value | Meaning |
|------|-------|---------|
| **ACK** | 0x06 | Command accepted and executed |
| **NAK** | 0x15 | Command rejected (error) |

---

## Testing Bidirectional Communication

### Test 1: Send Message and Read ACK

Using the LED controller:

```python
from scripts.led_sign_controller import AlphaLEDController

# Create controller
led = AlphaLEDController(host='192.168.8.122', port=10001)

# Send message (controller automatically reads ACK)
result = led.send_message(
    lines=['TEST', 'MESSAGE', 'LINE 3', 'LINE 4'],
    color=led.Color.GREEN
)

# Check logs for ACK
# You should see: "Received ACK from sign"
```

### Test 2: Manual Bidirectional Test with netcat

**Send command and read response:**

```bash
# Send test message and read response
(echo -ne '\x00\x00\x00\x00\x00\x01\x5A\x30\x30TEST\x04'; sleep 1) | nc 192.168.8.122 10001 | xxd

# Expected response: 06 (ACK)
```

### Test 3: Python Socket Test

```python
import socket
import time

# Connect to Waveshare
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('192.168.8.122', 10001))

# Send simple Write Text command
# Format: <NULL>x5 <ID=01> <CMD=5A> <FILE=30> <TEXT> <EOT=04>
command = b'\x00\x00\x00\x00\x00\x01\x5A\x30\x30TEST\x04'
sock.sendall(command)

# Wait for response
sock.settimeout(2)
response = sock.recv(1)

if response == b'\x06':
    print("✅ Received ACK - Sign accepted command")
elif response == b'\x15':
    print("❌ Received NAK - Sign rejected command")
else:
    print(f"❓ Unexpected response: {response.hex()}")

sock.close()
```

### Test 4: Check Waveshare Logs

Some Waveshare models have web UI logs showing bidirectional traffic:

1. Access: http://192.168.8.122
2. Navigate to: Status or Logs section
3. Look for:
   - Sent bytes (TX)
   - Received bytes (RX)
   - Verify RX shows ACK/NAK responses

---

## Advanced: Reading Sign Data

### Read Current Message

**Command Structure:**
```
Read Text: <NULL>x5 <ID> <CMD=42> <FILE> <ETX>
```

**Example (read file 0x30):**
```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('192.168.8.122', 10001))

# Read Text command for file 0x30
command = b'\x00\x00\x00\x00\x00\x01\x42\x30\x03'
sock.sendall(command)

# Read response
sock.settimeout(2)
response = sock.recv(1024)

print(f"Sign response: {response}")
# Should contain ACK + message text

sock.close()
```

### Set Time/Date

**Command Structure:**
```
Set Time: <NULL>x5 <ID> <CMD=45> <FUNCTION=20> <TIME> <ETX>
Time Format: 10 bytes ASCII (HH:MM:SS\x0DMM/DD/YY)
```

**Example:**
```python
import socket
from datetime import datetime

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('192.168.8.122', 10001))

# Get current time
now = datetime.now()
time_str = now.strftime("%H:%M:%S\r%m/%d/%y")

# Set Time command (0x45 0x20)
command = b'\x00\x00\x00\x00\x00\x01\x45\x20' + time_str.encode() + b'\x03'
sock.sendall(command)

# Read ACK/NAK
response = sock.recv(1)
if response == b'\x06':
    print("✅ Time set successfully")
else:
    print("❌ Failed to set time")

sock.close()
```

### Read Sign Serial Number

**Command Structure:**
```
Read Serial: <NULL>x5 <ID> <CMD=45> <FUNCTION=24> <ETX>
```

**Example:**
```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('192.168.8.122', 10001))

# Read serial number command
command = b'\x00\x00\x00\x00\x00\x01\x45\x24\x03'
sock.sendall(command)

# Read response
sock.settimeout(2)
response = sock.recv(1024)

# Parse response (ACK + data)
if response[0:1] == b'\x06':
    serial = response[1:].decode('ascii', errors='ignore')
    print(f"Sign serial number: {serial}")

sock.close()
```

---

## Troubleshooting Bidirectional

### No ACK Received

**Symptoms:**
- Commands seem to work (sign displays message)
- But logs show "No ACK/NAK received"

**Causes:**
1. ✅ TCP timeout too low on Waveshare
2. ✅ AutoFrame disabled
3. ✅ Socket Distribution off

**Solutions:**
```
1. Set TCP Time out: 0 (no timeout)
2. Enable UART AutoFrame
3. Enable Socket Distribution
4. Increase AutoFrame Time to 500-1000ms
```

### Garbled Responses

**Symptoms:**
- Receive data but it's corrupted
- ACK/NAK not recognized

**Causes:**
1. ✅ Baud rate mismatch
2. ✅ AutoFrame settings too aggressive
3. ✅ Buffer overflow

**Solutions:**
```
1. Verify baud: 9600 on both sides
2. Increase AutoFrame Time: 500ms
3. Increase AutoFrame Length: 512 bytes
4. Check wiring: TX↔RX, RX↔TX, GND↔GND
```

### Responses Timeout

**Symptoms:**
- First command works (receives ACK)
- Subsequent commands timeout

**Causes:**
1. ✅ Input buffer not drained
2. ✅ EOT not sent
3. ✅ Stale data in buffer

**Solutions:**
```
1. EAS controller drains buffer before send
2. Verify EOT sent after ACK
3. Power cycle sign to reset state
```

### Connection Drops After Response

**Symptoms:**
- Receive ACK/NAK
- Then connection closes

**Causes:**
1. ✅ TCP timeout too aggressive
2. ✅ MAX TCP Num set to 0

**Solutions:**
```
1. Set TCP Time out: 0
2. Set MAX TCP Num: 1 or higher
3. Disable connection password
```

---

## Waveshare Settings Summary (Bidirectional)

**CRITICAL SETTINGS:**
```
Network A:
  Mode: Server
  Protocol: TCP
  Port: 10001
  TCP Time out: 0  ⭐ Must be 0 for responses

UART:
  Baudrate: 9600
  Data: 8-N-1
  Flow Control: None

AutoFrame:
  Enable: Yes  ⭐ Critical for responses
  Time: 500 ms
  Length: 512 bytes

Socket Distribution: on  ⭐ Required for duplex

Other:
  Registered Package: off
  Custom Heartbeat: off
  Modbus Polling: off
```

---

## EAS Station Configuration

**No changes needed!** The LED controller already:
- ✅ Sends data bidirectionally
- ✅ Reads ACK/NAK responses
- ✅ Handles timeouts
- ✅ Implements M-Protocol properly

**Just configure:**
```bash
LED_SIGN_IP=192.168.8.122
LED_SIGN_PORT=10001
```

---

## Verification Checklist

Verify bidirectional communication is working:

- [ ] Sign displays messages (outbound works)
- [ ] Logs show "Received ACK from sign" (inbound works)
- [ ] No timeout errors in logs
- [ ] Sign responds to multiple commands without reconnecting
- [ ] Can set time/date successfully (advanced test)

---

## Reference: M-Protocol Response Format

**Write Command Response:**
```
ACK (0x06) - Success
NAK (0x15) - Failure
```

**Read Command Response:**
```
ACK (0x06) + Data + ETX (0x03)
NAK (0x15) - Failure
```

**Common NAK Causes:**
- Invalid sign ID
- File doesn't exist
- Invalid command
- Sign memory full
- Checksum error

---

## Support

- **Alpha Protocol Docs**: M-Protocol specification
- **EAS Station**: LED controller already supports bidirectional
- **Waveshare**: Ensure AutoFrame and Socket Distribution enabled
- **GitHub**: https://github.com/KR8MER/eas-station/issues

---

**Bottom Line**: The Waveshare adapter and EAS Station LED controller fully support bidirectional communication with Alpha LED signs. Just configure the adapter settings correctly (TCP timeout=0, AutoFrame=Enable, Socket Distribution=on) and it will work!
