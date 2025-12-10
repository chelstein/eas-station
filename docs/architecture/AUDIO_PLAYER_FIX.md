# Audio Player Fix for SDR Audio Sources

## Problem Summary

The user reported that the SDR system was not functioning correctly:
1. The demodulated signal was not being mounted to an Icecast stream
2. Audio playback on the website was broken - no audio player visible
3. Clicking play button resulted in no audio

## Root Cause Analysis

After investigating the codebase, I identified the following issues:

### 1. Missing Audio Player in UI
- The screenshot showed the user was on the `/audio/sources` page (audio_sources.html)
- This page uses `audio_monitoring.js` to render source cards
- **CRITICAL FINDING**: The `createSourceCard()` function in `audio_monitoring.js` did NOT include an audio player component
- The audio player existed in a different template (`audio_monitoring.html`) but not in the current page

### 2. Architecture Understanding
The system has a proper architecture for audio streaming:
- **SDR Service** (`sdr_service.py`): Reads from SDR hardware, publishes IQ samples to Redis
- **Audio Service** (`audio_service.py`): Subscribes to Redis, demodulates audio, streams to Icecast
- **Auto-Streaming Service** (`auto_streaming.py`): Automatically creates Icecast mountpoints for each audio source
- **Icecast Output** (`icecast_output.py`): Handles FFmpeg encoding and streaming to Icecast server

The backend architecture is sound - the issue was purely in the frontend UI.

## Fixes Applied

### 1. Added Audio Player to Source Cards
**File**: `static/js/audio_monitoring.js`

Added a complete audio player section to the `createSourceCard()` function that:
- Only displays when source status is 'running'
- Uses Icecast URL as primary audio source (if available)
- Falls back to Flask proxy stream (`/api/audio/stream/{source_name}`) if Icecast unavailable
- Shows stream information (bitrate, uptime, etc.)
- Displays appropriate messaging based on stream type

**Code Added**:
```javascript
${source.status === 'running' ? `
<div class="row mt-3">
    <div class="col-12">
        <div class="audio-player-container">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <small class="text-muted">
                    <i class="fas fa-volume-up"></i> Audio Stream
                </small>
                ${source.icecast_url ? `
                <small class="text-muted">
                    <i class="fas fa-broadcast-tower"></i> Icecast Stream
                    ${source.streaming && source.streaming.icecast ? `
                        ${typeof source.streaming.icecast.bitrate_kbps === 'number' ? ` • ${Number(source.streaming.icecast.bitrate_kbps).toFixed(1)} kbps` : ''}
                    ` : ''}
                </small>
                ` : ''}
            </div>
            <audio 
                controls 
                preload="none" 
                class="w-100"
                id="audio-player-${safeId}"
                style="height: 40px;">
                ${source.icecast_url ? `<source src="${escapeHtml(source.icecast_url)}" type="audio/mpeg">` : ''}
                <source src="/api/audio/stream/${encodeURIComponent(source.name)}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
            ${source.icecast_url ? `
            <small class="text-muted d-block mt-1">
                <i class="fas fa-info-circle"></i> Stream URL: <a href="${escapeHtml(source.icecast_url)}" target="_blank" class="text-decoration-none">${escapeHtml(source.icecast_url)}</a>
            </small>
            ` : `
            <small class="text-muted d-block mt-1">
                <i class="fas fa-info-circle"></i> Using built-in proxy stream
            </small>
            `}
        </div>
    </div>
</div>
` : ''}
```

### 2. Added CSS Styles for Audio Player
**File**: `templates/audio_sources.html`

Added styling for the audio player container:
```css
.audio-player-container {
    background: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1rem;
}

.audio-player-container audio {
    width: 100%;
    border-radius: 4px;
}

.waveform-canvas {
    width: 100%;
    height: 120px;
    background: var(--bg-primary);
    border-radius: 4px;
    border: 1px solid var(--border-color);
}
```

## How It Works

### Audio Streaming Flow
1. **SDR → Redis**: SDR service reads from hardware and publishes IQ samples to Redis
2. **Redis → Audio Service**: Audio service subscribes to Redis, demodulates audio
3. **Audio Service → Icecast**: Auto-streaming service creates Icecast mountpoint and streams audio via FFmpeg
4. **Icecast → Browser**: Web UI displays audio player with Icecast stream URL
5. **Fallback**: If Icecast unavailable, uses Flask proxy stream endpoint

### API Data Flow
The `/api/audio/sources` endpoint returns:
```json
{
  "sources": [
    {
      "id": "source_name",
      "name": "source_name",
      "status": "running",
      "icecast_url": "http://icecast:8000/source_name.mp3",
      "streaming": {
        "icecast": {
          "bitrate_kbps": 128.0,
          "uptime_seconds": 3600,
          "mount": "/source_name.mp3"
        }
      }
    }
  ]
}
```

The JavaScript uses this data to:
1. Check if source is running
2. Get Icecast URL if available
3. Render audio player with appropriate source
4. Display streaming statistics

## Testing Recommendations

1. **Verify Icecast is Running**:
   ```bash
   docker-compose ps icecast
   ```

2. **Check Audio Service Logs**:
   ```bash
   docker-compose logs audio-service | grep -i icecast
   ```

3. **Verify Mountpoints**:
   - Navigate to `http://your-server:8000/` (Icecast admin)
   - Check if mountpoints are listed

4. **Test Audio Playback**:
   - Start an SDR source from the UI
   - Wait for status to show "running"
   - Audio player should appear below the waveform
   - Click play button to test audio

## Expected Behavior After Fix

1. When an audio source is **running**:
   - Audio player appears below the waveform monitor
   - If Icecast is configured: Shows "Icecast Stream" with bitrate info
   - If Icecast unavailable: Shows "Using built-in proxy stream"
   - Clicking play button starts audio playback

2. When an audio source is **stopped**:
   - No audio player is shown (prevents confusion)
   - User must start the source first

3. Stream Priority:
   - Primary: Icecast URL (direct from Icecast server)
   - Fallback: Flask proxy (`/api/audio/stream/{name}`)

## Files Modified

1. `static/js/audio_monitoring.js` - Added audio player to source card template
2. `templates/audio_sources.html` - Added CSS styles for audio player

## Additional Notes

- The backend audio streaming architecture is working correctly
- The issue was purely a frontend UI problem - missing audio player component
- The fix maintains compatibility with both Icecast and proxy streaming modes
- Audio player only shows when source is actively running
- Graceful fallback if Icecast is not available