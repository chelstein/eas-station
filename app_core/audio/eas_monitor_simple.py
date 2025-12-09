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
Simple EAS Continuous Monitor

This is a simplified, robust implementation that:
- Reads audio from a source
- Feeds it to streaming SAME decoder
- Reports alerts
- Tracks simple status

No watchdogs, no restarts, no complexity.
"""

import logging
import threading
import time
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)


class SimpleEASMonitor:
    """
    Simple continuous EAS monitor.

    Reads audio, decodes SAME, reports alerts. That's it.
    """

    def __init__(
        self,
        audio_source,
        sample_rate: int = 16000,
        alert_callback: Optional[Callable] = None
    ):
        """
        Initialize monitor.

        Args:
            audio_source: Object with read_audio(num_samples) method
            sample_rate: Target sample rate for decoder (16kHz for SAME)
            alert_callback: Function to call when alert detected
        """
        self.audio_source = audio_source
        self.sample_rate = sample_rate
        self.alert_callback = alert_callback

        # Get source sample rate if available
        self.source_sample_rate = getattr(audio_source, 'sample_rate', sample_rate)

        # Initialize streaming decoder
        from .streaming_same_decoder import StreamingSAMEDecoder
        self._decoder = StreamingSAMEDecoder(
            sample_rate=sample_rate,
            alert_callback=self._handle_alert
        )

        # Simple state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None
        self._alerts_detected = 0

        logger.info(f"SimpleEASMonitor initialized: {self.source_sample_rate}Hz -> {sample_rate}Hz")

    def start(self) -> bool:
        """Start monitoring."""
        if self._running:
            logger.warning("Monitor already running")
            return False

        self._running = True
        self._start_time = time.time()

        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="simple-eas-monitor",
            daemon=True
        )
        self._thread.start()

        logger.info("✅ EAS monitor started")
        return True

    def stop(self) -> None:
        """Stop monitoring."""
        if not self._running:
            return

        logger.info("Stopping EAS monitor...")
        self._running = False

        if self._thread:
            self._thread.join(timeout=5.0)

        logger.info(f"EAS monitor stopped. Detected {self._alerts_detected} alerts")

    def get_status(self) -> dict:
        """Get current status with all metrics."""
        decoder_stats = self._decoder.get_stats()
        samples_processed = decoder_stats.get('samples_processed', 0)

        # Calculate runtime - if monitor is running, report it as running
        if self._running and self._start_time:
            wall_clock_runtime = time.time() - self._start_time
            if samples_processed > 0:
                audio_runtime = samples_processed / self.sample_rate
                samples_per_second = samples_processed / max(wall_clock_runtime, 0.1)
                audio_flowing = True
            else:
                # Monitor running but no samples yet - still starting up
                audio_runtime = 0
                samples_per_second = 0
                # Only report audio flowing if we've actually received samples
                audio_flowing = False
        else:
            wall_clock_runtime = 0
            audio_runtime = 0
            samples_per_second = 0
            audio_flowing = False

        # Get audio adapter stats if available
        adapter_stats = {}
        if hasattr(self.audio_source, 'get_stats'):
            try:
                adapter_stats = self.audio_source.get_stats()
            except Exception:
                pass

        return {
            # Core status
            "running": self._running,
            "mode": "streaming",
            "audio_flowing": audio_flowing,

            # Decoder metrics
            "samples_processed": samples_processed,
            "samples_per_second": int(samples_per_second),
            "wall_clock_runtime_seconds": wall_clock_runtime,
            "runtime_seconds": audio_runtime,

            # Decoder state
            "decoder_synced": decoder_stats.get('synced', False),
            "decoder_in_message": decoder_stats.get('in_message', False),
            "decoder_bytes_decoded": decoder_stats.get('bytes_decoded', 0),

            # Alert tracking
            "alerts_detected": self._alerts_detected,

            # Sample rate info
            "sample_rate": self.sample_rate,
            "source_sample_rate": self.source_sample_rate,

            # Audio adapter health (always return values, not None)
            "audio_buffer_samples": adapter_stats.get("buffer_samples", 0),
            "audio_queue_depth": adapter_stats.get("queue_size", 0),
            "audio_underruns": adapter_stats.get("underrun_count", 0),
            "audio_subscriber_id": adapter_stats.get("subscriber_id", ""),
        }

    def _handle_alert(self, alert_data: dict) -> None:
        """Handle detected alert."""
        self._alerts_detected += 1
        logger.info(f"🚨 EAS Alert detected: {alert_data}")

        if self.alert_callback:
            try:
                self.alert_callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}", exc_info=True)

    def _resample_linear(self, samples: np.ndarray) -> np.ndarray:
        """Fast linear resampling."""
        if self.source_sample_rate == self.sample_rate:
            return samples

        try:
            # Convert stereo to mono if needed
            if samples.ndim == 2:
                samples = samples.mean(axis=1)
            elif samples.ndim > 2:
                samples = samples.flatten()

            # Resample using linear interpolation
            ratio = self.sample_rate / float(self.source_sample_rate)
            new_length = int(len(samples) * ratio)

            if new_length < 1:
                return samples

            old_indices = np.arange(len(samples))
            new_indices = np.linspace(0, len(samples) - 1, new_length)
            resampled = np.interp(new_indices, old_indices, samples)

            return resampled.astype(np.float32)

        except Exception as e:
            logger.error(f"Resampling error: {e}")
            return samples

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("Monitor loop starting...")

        # Request ~100ms chunks
        chunk_size = int(self.sample_rate * 0.1)

        consecutive_errors = 0
        max_consecutive_errors = 50  # Increased from 10 - don't stop on transient issues

        while self._running:
            try:
                # Read audio from source
                samples = self.audio_source.read_audio(chunk_size)

                if samples is None or len(samples) == 0:
                    # No audio available, wait briefly
                    time.sleep(0.05)
                    consecutive_errors += 1
                    if consecutive_errors > max_consecutive_errors:
                        logger.warning(f"No audio for {consecutive_errors} consecutive reads")
                        time.sleep(0.5)  # Back off
                        consecutive_errors = 0  # Reset to keep trying
                    continue

                # Reset error counter on successful read
                consecutive_errors = 0

                # Resample if needed
                if self.source_sample_rate != self.sample_rate:
                    samples = self._resample_linear(samples)

                # Feed to decoder
                self._decoder.process_samples(samples)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                consecutive_errors += 1
                # Never stop - keep trying
                time.sleep(0.1)

        logger.info("Monitor loop exited")
