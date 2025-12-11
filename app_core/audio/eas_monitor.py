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
EAS Continuous Monitor - Simplified Single Implementation

Provides continuous EAS/SAME alert monitoring with:
- Robust audio reading with timeout detection
- Consistent status reporting
- Clear health metrics
- Proper error recovery
- FIPS code filtering utilities
"""

import hashlib
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

import numpy as np

from app_utils import utc_now
from app_utils.eas_codes import get_event_name, get_originator_name
from .fips_utils import determine_fips_matches

logger = logging.getLogger(__name__)


# =============================================================================
# Alert Types
# =============================================================================

@dataclass
class EASAlert:
    """
    Detected EAS alert with metadata.

    Used by self_test.py and other utilities that need structured alert data.
    The core EASMonitor uses dict alerts for simplicity.
    """
    timestamp: Any  # datetime
    raw_text: str
    headers: List[Dict[str, Any]]
    confidence: float
    duration_seconds: float
    source_name: str
    audio_file_path: Optional[str] = None


# =============================================================================
# Alert Utilities
# =============================================================================

def compute_alert_signature(alert: Dict[str, Any]) -> str:
    """
    Create a deterministic hash of alert data for deduplication.

    Args:
        alert: Alert dictionary with keys like 'raw_header', 'event_code', etc.

    Returns:
        SHA256 hash string
    """
    # Try to use raw header text first
    raw_header = alert.get('raw_header') or alert.get('raw_text', '')

    if raw_header:
        base_text = raw_header.strip()
    else:
        # Fall back to event code + location codes + timestamp
        event_code = alert.get('event_code', 'UNKNOWN')
        location_codes = alert.get('location_codes', [])
        source_name = alert.get('source_name', 'unknown')

        parts = [event_code, ','.join(location_codes), source_name]
        base_text = '|'.join(parts)

    if not base_text:
        # Last resort: use timestamp
        base_text = str(time.time())

    return hashlib.sha256(base_text.encode('utf-8', 'ignore')).hexdigest()


def _store_received_alert(
    alert: Dict[str, Any],
    forwarding_decision: str,
    forwarding_reason: str,
    matched_fips: List[str],
    generated_message_id: Optional[int] = None
) -> None:
    """
    Store received EAS alert in database with forwarding decision.

    Args:
        alert: Alert dictionary
        forwarding_decision: 'forwarded', 'ignored', or 'error'
        forwarding_reason: Human-readable reason for the decision
        matched_fips: List of FIPS codes that matched (if any)
        generated_message_id: FK to eas_messages table if forwarded
    """
    try:
        from app_core.models import ReceivedEASAlert
        from app_core.extensions import db
        from flask import has_app_context

        if not has_app_context():
            logger.debug("Not in Flask app context, skipping database storage")
            return

        # Extract data from alert dict
        event_code = alert.get('event_code', 'UNKNOWN')
        event_name = get_event_name(event_code) if event_code != 'UNKNOWN' else None
        originator_code = alert.get('originator', 'UNKNOWN')
        originator_name = get_originator_name(originator_code) if originator_code != 'UNKNOWN' else None
        fips_codes = alert.get('location_codes', [])
        callsign = alert.get('callsign')
        raw_same_header = alert.get('raw_header') or alert.get('raw_text')
        source_name = alert.get('source_name', 'unknown')

        # Parse timestamps if present
        issue_datetime = None
        purge_datetime = None
        issue_time = alert.get('issue_time')
        purge_time = alert.get('purge_time')
        if issue_time:
            issue_datetime = datetime.fromisoformat(issue_time) if isinstance(issue_time, str) else issue_time
        if purge_time:
            purge_datetime = datetime.fromisoformat(purge_time) if isinstance(purge_time, str) else purge_time

        # Check for duplicates within 10 minute window
        dedup_cutoff = utc_now() - timedelta(minutes=10)
        duplicate_filters = [ReceivedEASAlert.received_at >= dedup_cutoff]
        if raw_same_header:
            duplicate_filters.append(ReceivedEASAlert.raw_same_header == raw_same_header)
        else:
            duplicate_filters.append(ReceivedEASAlert.event_code == event_code)
            duplicate_filters.append(ReceivedEASAlert.originator_code == originator_code)
            if callsign:
                duplicate_filters.append(ReceivedEASAlert.callsign == callsign)

        duplicate_exists = db.session.query(ReceivedEASAlert.id).filter(*duplicate_filters).first()
        if duplicate_exists:
            logger.info(
                "Duplicate received alert suppressed within 10-minute window: %s",
                raw_same_header or event_code,
            )
            return

        # Create database record
        received_alert = ReceivedEASAlert(
            received_at=utc_now(),
            source_name=source_name,
            raw_same_header=raw_same_header,
            event_code=event_code,
            event_name=event_name,
            originator_code=originator_code,
            originator_name=originator_name,
            fips_codes=fips_codes,
            issue_datetime=issue_datetime,
            purge_datetime=purge_datetime,
            callsign=callsign,
            forwarding_decision=forwarding_decision,
            forwarding_reason=forwarding_reason,
            matched_fips_codes=matched_fips,
            generated_message_id=generated_message_id,
            forwarded_at=utc_now() if forwarding_decision == 'forwarded' else None,
            decode_confidence=alert.get('confidence', 0.0),
            full_alert_data=alert
        )

        db.session.add(received_alert)
        db.session.commit()
        logger.info(f"Stored received alert in database: {event_code} from {source_name}")

    except Exception as e:
        logger.error(f"Failed to store received alert in database: {e}", exc_info=True)
        try:
            from app_core.extensions import db
            db.session.rollback()
        except Exception:
            pass


def create_fips_filtering_callback(
    configured_fips_codes: List[str],
    forward_callback: Callable[[Dict[str, Any]], Any],
    logger_instance: Optional[logging.Logger] = None
) -> Callable[[Dict[str, Any]], None]:
    """
    Create an alert callback that filters by FIPS codes.

    Args:
        configured_fips_codes: List of FIPS codes to match
        forward_callback: Function to call when alert matches FIPS codes
        logger_instance: Optional logger (defaults to module logger)

    Returns:
        Callback function for EASMonitor
    """
    log = logger_instance or logger

    def fips_filtering_callback(alert: Dict[str, Any]) -> None:
        """Filter alerts by FIPS codes."""
        # Extract alert info
        alert_fips_codes = alert.get('location_codes', [])
        event_code = alert.get('event_code', 'UNKNOWN')
        originator = alert.get('originator', 'UNKNOWN')

        # If no FIPS codes configured, accept ALL alerts
        if not configured_fips_codes:
            log.warning(
                f"NO FIPS FILTERING - ACCEPTING ALL: Event={event_code} | "
                f"Originator={originator} | FIPS={','.join(alert_fips_codes) or 'NONE'}"
            )
            try:
                result = forward_callback(alert)
                generated_message_id = _extract_message_id(result)
                _store_received_alert(
                    alert=alert,
                    forwarding_decision='forwarded',
                    forwarding_reason='No FIPS filtering configured - accepting all alerts',
                    matched_fips=alert_fips_codes,
                    generated_message_id=generated_message_id
                )
            except Exception as e:
                log.error(f"Error forwarding alert: {e}", exc_info=True)
                _store_received_alert(
                    alert=alert,
                    forwarding_decision='error',
                    forwarding_reason=f"Forwarding failed: {str(e)}",
                    matched_fips=[]
                )
            return

        # Check for FIPS match
        matched_fips_list = determine_fips_matches(alert_fips_codes, configured_fips_codes)

        if matched_fips_list:
            # FIPS match - forward alert
            forwarding_reason = f"FIPS match: {', '.join(matched_fips_list)}"
            log.warning(
                f"FIPS MATCH - FORWARDING: Event={event_code} | "
                f"Originator={originator} | Matched={','.join(matched_fips_list)}"
            )
            try:
                result = forward_callback(alert)
                generated_message_id = _extract_message_id(result)
                _store_received_alert(
                    alert=alert,
                    forwarding_decision='forwarded',
                    forwarding_reason=forwarding_reason,
                    matched_fips=matched_fips_list,
                    generated_message_id=generated_message_id
                )
            except Exception as e:
                log.error(f"Error forwarding alert: {e}", exc_info=True)
                _store_received_alert(
                    alert=alert,
                    forwarding_decision='error',
                    forwarding_reason=f"Forwarding failed: {str(e)}",
                    matched_fips=matched_fips_list
                )
        else:
            # No FIPS match - ignore
            log.info(
                f"NO FIPS MATCH - IGNORING: Event={event_code} | "
                f"Alert FIPS={','.join(alert_fips_codes) or 'NONE'}"
            )
            if alert_fips_codes:
                forwarding_reason = f"No FIPS match. Alert: {', '.join(alert_fips_codes)}"
            else:
                forwarding_reason = "No FIPS codes in alert"
            _store_received_alert(
                alert=alert,
                forwarding_decision='ignored',
                forwarding_reason=forwarding_reason,
                matched_fips=[]
            )

    return fips_filtering_callback


def _extract_message_id(result: Any) -> Optional[int]:
    """Extract message ID from various callback return types."""
    if result is None:
        return None
    if isinstance(result, int):
        return result
    if isinstance(result, dict):
        return result.get('message_id') or result.get('id')
    if hasattr(result, 'id'):
        return getattr(result, 'id')
    return None


# =============================================================================
# Health Tracking
# =============================================================================

@dataclass
class MonitorHealth:
    """Health tracking for EAS monitor."""
    last_audio_time: float = 0.0
    consecutive_empty_reads: int = 0
    consecutive_errors: int = 0
    total_errors: int = 0
    audio_flowing: bool = False
    health_score: float = 1.0


# =============================================================================
# EAS Monitor
# =============================================================================

class EASMonitor:
    """
    Continuous EAS/SAME alert monitor.

    Features:
    - Robust audio pipeline with health tracking
    - Clear, consistent status reporting
    - Proper timeout detection
    - Graceful error recovery
    - Real-time health metrics
    """

    def __init__(
        self,
        audio_source,
        sample_rate: int = 16000,
        alert_callback: Optional[Callable] = None,
        source_name: str = "unknown"
    ):
        """
        Initialize monitor.

        Args:
            audio_source: Object with read_audio(num_samples) method
            sample_rate: Target sample rate for decoder (16kHz for SAME)
            alert_callback: Function to call when alert detected
            source_name: Human-readable name for this source
        """
        self.audio_source = audio_source
        self.sample_rate = sample_rate
        self.alert_callback = alert_callback
        self.source_name = source_name

        # Get source sample rate if available
        self.source_sample_rate = getattr(audio_source, 'sample_rate', sample_rate)

        # Initialize streaming decoder
        from .streaming_same_decoder import StreamingSAMEDecoder
        self._decoder = StreamingSAMEDecoder(
            sample_rate=sample_rate,
            alert_callback=self._handle_alert
        )

        # State management
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None
        self._alerts_detected = 0
        self._samples_processed = 0

        # Health tracking
        self._health = MonitorHealth()
        self._health_lock = threading.Lock()

        # Configuration
        self._chunk_duration_ms = 100
        self._chunk_size = int(self.sample_rate * self._chunk_duration_ms / 1000)
        self._audio_timeout_seconds = 5.0
        self._max_empty_reads = 50
        self._max_errors = 100

        logger.info(
            f"EASMonitor initialized for '{source_name}': "
            f"{self.source_sample_rate}Hz -> {sample_rate}Hz, "
            f"chunk={self._chunk_duration_ms}ms ({self._chunk_size} samples)"
        )

    def start(self) -> bool:
        """Start monitoring."""
        if self._running:
            logger.warning(f"Monitor '{self.source_name}' already running")
            return False

        self._running = True
        self._start_time = time.time()
        self._samples_processed = 0
        self._alerts_detected = 0

        with self._health_lock:
            self._health = MonitorHealth()

        self._thread = threading.Thread(
            target=self._monitor_loop,
            name=f"eas-monitor-{self.source_name}",
            daemon=True
        )
        self._thread.start()

        logger.info(f"EAS monitor '{self.source_name}' started")
        return True

    def stop(self) -> None:
        """Stop monitoring."""
        if not self._running:
            return

        logger.info(f"Stopping EAS monitor '{self.source_name}'...")
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning(f"Monitor thread '{self.source_name}' did not stop cleanly")

        logger.info(
            f"EAS monitor '{self.source_name}' stopped. "
            f"Processed {self._samples_processed:,} samples, "
            f"detected {self._alerts_detected} alerts"
        )

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        decoder_stats = self._decoder.get_stats()

        with self._health_lock:
            health = self._health

        if self._running and self._start_time:
            wall_clock_runtime = time.time() - self._start_time
            if self._samples_processed > 0:
                audio_runtime = self._samples_processed / self.sample_rate
                samples_per_second = self._samples_processed / max(wall_clock_runtime, 0.1)
                health_percentage = min(1.0, samples_per_second / self.sample_rate)
            else:
                audio_runtime = 0
                samples_per_second = 0
                health_percentage = 0.0
        else:
            wall_clock_runtime = 0
            audio_runtime = 0
            samples_per_second = 0
            health_percentage = 0.0

        time_since_audio = time.time() - health.last_audio_time if health.last_audio_time > 0 else 999999
        audio_flowing = (
            self._running and
            self._samples_processed > 0 and
            time_since_audio < self._audio_timeout_seconds
        )

        adapter_stats = {}
        if hasattr(self.audio_source, 'get_stats'):
            try:
                adapter_stats = self.audio_source.get_stats()
            except Exception:
                pass

        return {
            "running": self._running,
            "mode": "streaming",
            "source_name": self.source_name,
            "audio_flowing": audio_flowing,
            "samples_processed": self._samples_processed,
            "samples_per_second": int(samples_per_second),
            "wall_clock_runtime_seconds": wall_clock_runtime,
            "runtime_seconds": audio_runtime,
            "health_percentage": health_percentage,
            "time_since_last_audio": time_since_audio,
            "consecutive_empty_reads": health.consecutive_empty_reads,
            "consecutive_errors": health.consecutive_errors,
            "total_errors": health.total_errors,
            "decoder_synced": decoder_stats.get('synced', False),
            "decoder_in_message": decoder_stats.get('in_message', False),
            "decoder_bytes_decoded": decoder_stats.get('bytes_decoded', 0),
            "alerts_detected": self._alerts_detected,
            "sample_rate": self.sample_rate,
            "source_sample_rate": self.source_sample_rate,
            "audio_buffer_samples": adapter_stats.get("buffer_samples", 0),
            "audio_queue_depth": adapter_stats.get("queue_size", 0),
            "audio_underruns": adapter_stats.get("underrun_count", 0),
        }

    def _handle_alert(self, alert_data: dict) -> None:
        """Handle detected alert."""
        self._alerts_detected += 1
        alert_data['source_name'] = self.source_name

        logger.info(
            f"EAS Alert detected on '{self.source_name}': "
            f"{alert_data.get('event_code', 'UNKNOWN')}"
        )

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
            if samples.ndim == 2:
                samples = samples.mean(axis=1)
            elif samples.ndim > 2:
                samples = samples.flatten()

            if samples.dtype != np.float32:
                samples = samples.astype(np.float32)

            ratio = self.sample_rate / float(self.source_sample_rate)
            new_length = max(1, int(len(samples) * ratio))

            old_indices = np.arange(len(samples))
            new_indices = np.linspace(0, len(samples) - 1, new_length)
            resampled = np.interp(new_indices, old_indices, samples)

            return resampled.astype(np.float32)

        except Exception as e:
            logger.error(f"Resampling error on '{self.source_name}': {e}")
            with self._health_lock:
                self._health.total_errors += 1
            return samples

    def _update_health(self, got_audio: bool, error: bool = False) -> None:
        """Update health tracking."""
        with self._health_lock:
            if error:
                self._health.consecutive_errors += 1
                self._health.total_errors += 1
                self._health.consecutive_empty_reads = 0
            elif got_audio:
                self._health.last_audio_time = time.time()
                self._health.consecutive_empty_reads = 0
                self._health.consecutive_errors = 0
                self._health.audio_flowing = True
            else:
                self._health.consecutive_empty_reads += 1
                self._health.consecutive_errors = 0
                time_since_audio = time.time() - self._health.last_audio_time if self._health.last_audio_time > 0 else 999999
                if time_since_audio > self._audio_timeout_seconds:
                    self._health.audio_flowing = False

            health_factors = [
                1.0 - min(1.0, self._health.consecutive_errors / 100),
                1.0 - min(1.0, self._health.consecutive_empty_reads / 100),
                1.0 if self._health.audio_flowing else 0.5,
            ]
            self._health.health_score = sum(health_factors) / len(health_factors)

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        logger.info(f"Monitor loop starting for '{self.source_name}'...")

        while self._running:
            try:
                samples = self.audio_source.read_audio(self._chunk_size)

                if samples is None or len(samples) == 0:
                    self._update_health(got_audio=False)

                    with self._health_lock:
                        empty_reads = self._health.consecutive_empty_reads

                    if empty_reads == self._max_empty_reads:
                        logger.warning(
                            f"'{self.source_name}': No audio for {empty_reads} reads"
                        )
                    elif empty_reads > self._max_empty_reads and empty_reads % 100 == 0:
                        logger.warning(
                            f"'{self.source_name}': Still no audio after {empty_reads} reads"
                        )

                    time.sleep(0.05)
                    continue

                self._update_health(got_audio=True)

                if self.source_sample_rate != self.sample_rate:
                    samples = self._resample_linear(samples)

                self._decoder.process_samples(samples)
                self._samples_processed += len(samples)

            except Exception as e:
                logger.error(f"Error in monitor loop for '{self.source_name}': {e}", exc_info=True)
                self._update_health(got_audio=False, error=True)

                with self._health_lock:
                    if self._health.consecutive_errors >= self._max_errors:
                        logger.error(
                            f"'{self.source_name}': Too many errors, stopping monitor"
                        )
                        self._running = False
                        break

                time.sleep(0.1)

        logger.info(f"Monitor loop exited for '{self.source_name}'")


# Backwards compatibility aliases
EASMonitorV2 = EASMonitor
ContinuousEASMonitor = EASMonitor
