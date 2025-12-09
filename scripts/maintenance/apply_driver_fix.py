
import os
import sys

file_path = 'app_core/radio/drivers.py'

if not os.path.exists(file_path):
    print(f"Error: {file_path} not found")
    sys.exit(1)

with open(file_path, 'r') as f:
    content = f.read()

old_code = """        self._running.clear()
        if self._thread:
            self._thread.join(timeout=2.0)

        self._teardown_handle()"""

new_code = """        self._running.clear()

        # Attempt to stop the stream to unblock readStream if it's stuck
        # This is critical for drivers that block indefinitely on readStream
        if self._handle:
            try:
                self._handle.device.deactivateStream(self._handle.stream)
            except Exception:
                # Ignore errors here - we're shutting down anyway
                # and _teardown_handle will try again
                pass

        if self._thread:
            self._thread.join(timeout=2.0)

        self._teardown_handle()"""

if new_code in content:
    print("Patch already applied.")
    sys.exit(0)

if old_code not in content:
    print("Error: Could not find the code block to replace. The file might have changed.")
    # Try to find a smaller chunk or warn
    sys.exit(1)

new_content = content.replace(old_code, new_code)

with open(file_path, 'w') as f:
    f.write(new_content)

print("Successfully patched app_core/radio/drivers.py")
