"""
EAS Station - Emergency Alert System
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

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
Unified EAS Monitor Service - V3 Architecture

CRITICAL REDESIGN: Single-threaded unified monitor service that addresses
inefficiencies in the multi-monitor architecture.

Previous Architecture (V2):
- N separate monitor threads (one per audio source)
- Manual monitor lifecycle management (add/remove monitors)
- Status aggregation overhead on every API call
- Duplicate resources (N resampling adapters, N health trackers)
- Tight coupling to audio source lifecycle

New Architecture (V3):
- Single monitor thread for ALL audio sources
- Auto-discovery of running sources
- Centralized health tracking
- Shared SAME decoder for all sources
- Lightweight per-source watchers (no threads)

Benefits:
- 1 thread instead of N threads → reduced CPU/memory
- No manual lifecycle management → simpler code
- Direct status access → no aggregation overhead
- Centralized health → consistent tracking
- Auto-discovery → decoupled from source lifecycle

Architecture:

    UnifiedEASMonitorService (1 thread)
    ├── SourceWatcher[LP1] (subscribes to LP1 broadcast queue)
    ├── SourceWatcher[LP2] (subscribes to LP2 broadcast queue)
    ├── SourceWatcher[SP1] (subscribes to SP1 broadcast queue)
    ├── HealthTracker (centralized health for all sources)
    └── StreamingSAMEDecoder (shared decoder processing all sources)

Usage:
    from app_core.audio.eas_monitor_v3 import UnifiedEASMonitorService
    
    # Initialize with audio controller reference
    monitor = UnifiedEASMonitorService(
        audio_controller=audio_controller,
        alert_callback=my_alert_handler,
        configured_fips_codes=['012345', '067890']
    )
    
    # Start unified monitor (auto-discovers sources)
    monitor.start()
    
    # Get status (no aggregation needed)
    status = monitor.get_status()
    
    # Stop when done
    monitor.stop()
"""

import logging
import threading
import time
import queue
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

import numpy as np

from app_utils import utc_now
from .streaming_same_decoder import StreamingSAMEDecoder
from .broadcast_adapter import BroadcastAudioAdapter  # Changed from ResamplingBroadcastAdapter
from .broadcast_queue import BroadcastQueue

logger = logging.getLogger(__name__)


# =============================================================================
# Health Tracking
# =============================================================================

@dataclass
class SourceHealth:
    """Health metrics for a single audio source."""
    source_name: str
    last_audio_time: float = 0.0
    consecutive_empty_reads: int = 0
    consecutive_successful_reads: int = 0  # Track recovery from no-audio state
    samples_processed: int = 0
    audio_flowing: bool = False
    last_error: Optional[str] = None
    error_count: int = 0


class HealthTracker:
    """
    Centralized health tracking for all monitored audio sources.

    Tracks per-source health metrics and provides aggregated health status.
    Thread-safe for concurrent updates from monitor thread.

    Uses hysteresis to prevent state bouncing:
    - Requires RECOVERY_THRESHOLD consecutive successful reads before marking as flowing
    - Requires TIMEOUT_THRESHOLD seconds without audio before marking as not flowing
    """

    # Hysteresis thresholds to prevent rapid state changes
    RECOVERY_THRESHOLD = 10  # Consecutive successful reads needed to recover from not-flowing state

    def __init__(self, audio_timeout_seconds: float = 5.0):
        """
        Initialize health tracker.

        Args:
            audio_timeout_seconds: Time without audio before marking source unhealthy
        """
        self._sources: Dict[str, SourceHealth] = {}
        self._lock = threading.Lock()
        self._audio_timeout_seconds = audio_timeout_seconds
        self._start_time = time.time()
        
    def register_source(self, source_name: str) -> None:
        """Register a new source for health tracking."""
        with self._lock:
            if source_name not in self._sources:
                self._sources[source_name] = SourceHealth(source_name=source_name)
                logger.debug(f"Registered source '{source_name}' in health tracker")
    
    def unregister_source(self, source_name: str) -> None:
        """Unregister a source from health tracking."""
        with self._lock:
            if source_name in self._sources:
                del self._sources[source_name]
                logger.debug(f"Unregistered source '{source_name}' from health tracker")
    
    def update_audio_received(self, source_name: str, sample_count: int) -> None:
        """
        Record that audio was received from a source.

        Uses hysteresis to prevent rapid state changes:
        - If already flowing: keeps flowing state
        - If not flowing: requires RECOVERY_THRESHOLD consecutive successful reads
          before transitioning back to flowing state
        """
        with self._lock:
            if source_name in self._sources:
                health = self._sources[source_name]
                health.last_audio_time = time.time()
                health.consecutive_empty_reads = 0
                health.samples_processed += sample_count

                # Apply hysteresis when recovering from not-flowing state
                if health.audio_flowing:
                    # Already flowing - keep it that way
                    health.consecutive_successful_reads = 0  # Reset recovery counter
                else:
                    # Not currently flowing - count consecutive successful reads
                    health.consecutive_successful_reads += 1
                    if health.consecutive_successful_reads >= self.RECOVERY_THRESHOLD:
                        # Enough consecutive successful reads - mark as flowing
                        health.audio_flowing = True
                        logger.info(
                            f"Source '{source_name}' audio flowing restored after "
                            f"{health.consecutive_successful_reads} consecutive successful reads"
                        )
                        health.consecutive_successful_reads = 0
    
    def update_no_audio(self, source_name: str) -> None:
        """
        Record that no audio was available from a source.

        Marks source as not flowing if audio timeout is exceeded.
        Resets recovery counter since we need consecutive successful reads.
        """
        with self._lock:
            if source_name in self._sources:
                health = self._sources[source_name]
                health.consecutive_empty_reads += 1
                health.consecutive_successful_reads = 0  # Reset recovery counter

                # Check if audio timeout exceeded
                if health.last_audio_time > 0:
                    time_since_audio = time.time() - health.last_audio_time
                    if time_since_audio > self._audio_timeout_seconds:
                        if health.audio_flowing:
                            # Transitioning from flowing to not flowing
                            logger.warning(
                                f"Source '{source_name}' audio stopped flowing "
                                f"(no audio for {time_since_audio:.1f}s, {health.consecutive_empty_reads} empty reads)"
                            )
                        health.audio_flowing = False
    
    def update_error(self, source_name: str, error_msg: str) -> None:
        """Record an error for a source."""
        with self._lock:
            if source_name in self._sources:
                health = self._sources[source_name]
                health.error_count += 1
                health.last_error = error_msg
                health.consecutive_empty_reads = 0
                health.consecutive_successful_reads = 0  # Reset recovery counter on error
    
    def get_source_health(self, source_name: str) -> Optional[SourceHealth]:
        """Get health metrics for a specific source."""
        with self._lock:
            return self._sources.get(source_name)
    
    def get_all_health(self) -> Dict[str, SourceHealth]:
        """Get health metrics for all sources."""
        with self._lock:
            return dict(self._sources)
    
    def get_active_source_count(self) -> int:
        """Get count of sources with flowing audio."""
        with self._lock:
            return sum(1 for h in self._sources.values() if h.audio_flowing)
    
    def get_total_samples_processed(self) -> int:
        """Get total samples processed across all sources."""
        with self._lock:
            return sum(h.samples_processed for h in self._sources.values())
    
    def get_uptime_seconds(self) -> float:
        """Get tracker uptime in seconds."""
        return time.time() - self._start_time


# =============================================================================
# Source Watcher
# =============================================================================

class SourceWatcher:
    """
    Lightweight per-source audio subscriber.
    
    This is NOT a separate thread - it's just a subscriber to a source's
    broadcast queue. The UnifiedEASMonitorService polls all watchers in
    its single monitoring thread.
    
    Responsibilities:
    - Subscribe to source's broadcast queue
    - Resample audio to 16kHz for SAME decoder
    - Buffer audio chunks for consumption
    - Track basic per-source stats
    """
    
    def __init__(
        self,
        source_name: str,
        eas_broadcast_queue: BroadcastQueue,  # Now expects 16kHz queue directly
    ):
        """
        Initialize source watcher.
        
        ARCHITECTURAL FIX: Now receives pre-resampled 16kHz audio from dedicated EAS queue.
        No more resampling needed - eliminates conversion bottleneck and reduces memory by 3x.
        
        Args:
            source_name: Name of the audio source
            eas_broadcast_queue: Source's 16kHz EAS broadcast queue (pre-resampled)
        """
        self.source_name = source_name
        self.source_sample_rate = 16000  # Always 16kHz now
        self.target_sample_rate = 16000
        
        # Subscribe directly to 16kHz queue - no resampling needed!
        subscriber_id = f"eas-unified-{source_name}"
        self._adapter = BroadcastAudioAdapter(
            broadcast_queue=eas_broadcast_queue,
            subscriber_id=subscriber_id,
            sample_rate=16000,
            read_timeout=0.1  # Short timeout so one stalled source doesn't block others
        )
        
        logger.info(
            f"SourceWatcher initialized for '{source_name}': "
            f"16kHz pre-resampled queue (no conversion needed)"
        )
    
    def read_audio(self, num_samples: int) -> Optional[np.ndarray]:
        """
        Read audio samples from this source.
        
        Args:
            num_samples: Number of samples to read at target rate
            
        Returns:
            NumPy array of samples, or None if no audio available
        """
        try:
            return self._adapter.read_audio(num_samples)
        except Exception as e:
            logger.error(f"Error reading audio from '{self.source_name}': {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        if hasattr(self._adapter, 'get_stats'):
            return self._adapter.get_stats()
        return {}


# =============================================================================
# Unified EAS Monitor Service
# =============================================================================

class UnifiedEASMonitorService:
    """
    Single-threaded unified EAS monitor service.
    
    Monitors ALL audio sources in a single thread using lightweight
    SourceWatcher subscribers. Automatically discovers and tracks
    running audio sources.
    
    This replaces the multi-monitor architecture where each source
    had its own monitor thread. Benefits:
    - 1 thread instead of N threads
    - Auto-discovery of sources (no manual add/remove)
    - Centralized health tracking
    - No status aggregation overhead
    - Shared SAME decoder
    
    The monitor thread polls all source watchers in round-robin fashion,
    processing audio from each source and feeding it to a shared SAME
    decoder. Alert callbacks include source identification.
    """
    
    def __init__(
        self,
        audio_controller,
        alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        configured_fips_codes: Optional[List[str]] = None,
        discovery_interval_seconds: float = 5.0,
        chunk_duration_ms: int = 100
    ):
        """
        Initialize unified EAS monitor service.
        
        Args:
            audio_controller: AudioSourceController instance for source discovery
            alert_callback: Function to call when alert detected
            configured_fips_codes: List of FIPS codes for filtering (None = accept all)
            discovery_interval_seconds: How often to check for new/removed sources
            chunk_duration_ms: Audio chunk size in milliseconds
        """
        self.audio_controller = audio_controller
        self.alert_callback = alert_callback
        self.configured_fips_codes = configured_fips_codes or []
        self._discovery_interval = discovery_interval_seconds
        self._chunk_duration_ms = chunk_duration_ms
        
        # Calculate chunk size at 16kHz (SAME decoder rate)
        self._target_sample_rate = 16000
        self._chunk_size = int(self._target_sample_rate * chunk_duration_ms / 1000)
        
        # Source watchers: {source_name: SourceWatcher}
        self._watchers: Dict[str, SourceWatcher] = {}
        self._watchers_lock = threading.Lock()
        
        # Health tracking
        self._health_tracker = HealthTracker(audio_timeout_seconds=5.0)
        
        # Shared SAME decoder for all sources
        self._decoder = StreamingSAMEDecoder(
            sample_rate=self._target_sample_rate,
            alert_callback=self._handle_alert
        )
        
        # State management
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None
        self._last_discovery_time = 0.0
        
        # Statistics
        self._total_alerts_detected = 0
        self._current_source_context: Optional[str] = None  # Track which source is being processed
        
        logger.info(
            f"UnifiedEASMonitorService initialized: "
            f"chunk={chunk_duration_ms}ms ({self._chunk_size} samples at 16kHz), "
            f"FIPS codes={len(self.configured_fips_codes)}, "
            f"discovery_interval={discovery_interval_seconds}s"
        )
    
    def start(self) -> bool:
        """Start the unified monitor service."""
        if self._running:
            logger.warning("UnifiedEASMonitorService already running")
            return False
        
        logger.info("Starting UnifiedEASMonitorService...")
        
        # Initial source discovery
        self._discover_sources()
        
        # Start monitoring thread
        self._running = True
        self._start_time = time.time()
        
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="eas-unified-monitor",
            daemon=True
        )
        self._thread.start()
        
        logger.info(
            f"✅ UnifiedEASMonitorService started monitoring {len(self._watchers)} source(s)"
        )
        return True
    
    def stop(self) -> None:
        """Stop the unified monitor service."""
        if not self._running:
            return
        
        logger.info("Stopping UnifiedEASMonitorService...")
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("UnifiedEASMonitorService thread did not stop cleanly")
        
        # Clean up watchers
        with self._watchers_lock:
            watcher_count = len(self._watchers)
            self._watchers.clear()
        
        logger.info(
            f"✅ UnifiedEASMonitorService stopped. "
            f"Processed audio from {watcher_count} source(s), "
            f"detected {self._total_alerts_detected} total alerts"
        )
    
    def _discover_sources(self) -> None:
        """
        Discover running audio sources and create/remove watchers.
        
        This implements auto-discovery by querying the audio controller
        for running sources and comparing with our current watchers.
        """
        from app_core.audio.ingest import AudioSourceStatus
        
        try:
            # Get currently running sources from audio controller
            running_sources = {}
            for source_name, source_adapter in self.audio_controller._sources.items():
                if source_adapter.status == AudioSourceStatus.RUNNING:
                    running_sources[source_name] = source_adapter
            
            with self._watchers_lock:
                current_watchers = set(self._watchers.keys())
                discovered_sources = set(running_sources.keys())
                
                # Add watchers for new sources
                sources_to_add = discovered_sources - current_watchers
                for source_name in sources_to_add:
                    self._add_watcher(source_name, running_sources[source_name])
                
                # Remove watchers for stopped sources
                sources_to_remove = current_watchers - discovered_sources
                for source_name in sources_to_remove:
                    self._remove_watcher(source_name)
                
                if sources_to_add or sources_to_remove:
                    logger.info(
                        f"Source discovery: +{len(sources_to_add)} -{len(sources_to_remove)} "
                        f"(now monitoring {len(self._watchers)} sources)"
                    )
        
        except Exception as e:
            logger.error(f"Error during source discovery: {e}", exc_info=True)
    
    def _add_watcher(self, source_name: str, source_adapter) -> None:
        """Add a watcher for a new source (called with lock held)."""
        try:
            # ARCHITECTURAL FIX: Get the 16kHz EAS broadcast queue
            # This queue contains pre-resampled audio, eliminating conversion bottleneck
            eas_broadcast_queue = source_adapter.get_eas_broadcast_queue()
            
            # Create watcher - no longer needs source sample rate!
            watcher = SourceWatcher(
                source_name=source_name,
                eas_broadcast_queue=eas_broadcast_queue,
            )
            
            self._watchers[source_name] = watcher
            self._health_tracker.register_source(source_name)
            
            logger.info(f"✅ Added watcher for source '{source_name}' (16kHz pre-resampled queue)")
        
        except Exception as e:
            logger.error(f"Failed to add watcher for '{source_name}': {e}", exc_info=True)
    
    def _remove_watcher(self, source_name: str) -> None:
        """Remove a watcher for a stopped source (called with lock held)."""
        watcher = self._watchers.pop(source_name, None)
        if watcher:
            self._health_tracker.unregister_source(source_name)
            logger.info(f"✅ Removed watcher for source '{source_name}'")
    
    def _handle_alert(self, alert_data) -> None:
        """
        Handle detected alert from shared decoder.

        The decoder doesn't know which source the alert came from,
        so we track that in _current_source_context.
        """
        self._total_alerts_detected += 1

        # The streaming decoder emits StreamingSAMEAlert objects; convert to dict.
        from .streaming_same_decoder import StreamingSAMEAlert
        from .eas_monitor import _same_alert_to_dict
        if isinstance(alert_data, StreamingSAMEAlert):
            alert_data = _same_alert_to_dict(alert_data)

        # Add source identification to alert
        if self._current_source_context:
            alert_data['source_name'] = self._current_source_context
        else:
            alert_data['source_name'] = 'unknown'

        logger.warning(
            f"🚨 EAS Alert detected from '{alert_data['source_name']}': "
            f"{alert_data.get('event_code', 'UNKNOWN')}"
        )

        # Call user's alert callback
        if self.alert_callback:
            try:
                self.alert_callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}", exc_info=True)
    
    def _monitor_loop(self) -> None:
        """
        Main monitoring loop (single thread for all sources).
        
        This is the core of the unified architecture. It:
        1. Periodically discovers new/removed sources
        2. Polls each source watcher in round-robin fashion
        3. Processes audio through shared SAME decoder
        4. Updates centralized health tracking
        """
        logger.info("UnifiedEASMonitorService monitor loop starting...")
        
        while self._running:
            try:
                # Periodic source discovery
                current_time = time.time()
                if current_time - self._last_discovery_time >= self._discovery_interval:
                    self._discover_sources()
                    self._last_discovery_time = current_time
                
                # Get current watchers (snapshot to avoid holding lock)
                with self._watchers_lock:
                    watchers_snapshot = list(self._watchers.items())
                
                # If no watchers, sleep and continue
                if not watchers_snapshot:
                    time.sleep(0.1)
                    continue
                
                # Poll each source watcher
                any_audio_processed = False
                for source_name, watcher in watchers_snapshot:
                    # Set source context for alert attribution
                    self._current_source_context = source_name
                    
                    try:
                        # Try to read audio from this source
                        samples = watcher.read_audio(self._chunk_size)
                        
                        if samples is not None and len(samples) > 0:
                            # Process audio through shared decoder
                            self._decoder.process_samples(samples)
                            
                            # Update health tracking
                            self._health_tracker.update_audio_received(
                                source_name,
                                len(samples)
                            )
                            
                            any_audio_processed = True
                        else:
                            # No audio available from this source
                            self._health_tracker.update_no_audio(source_name)
                    
                    except Exception as e:
                        logger.error(
                            f"Error processing audio from '{source_name}': {e}",
                            exc_info=True
                        )
                        self._health_tracker.update_error(source_name, str(e))
                
                # Clear source context
                self._current_source_context = None
                
                # Sleep to prevent CPU spinning.  Audio arrives in ~100ms chunks
                # (1600 samples at 16kHz), so polling faster than 20Hz is wasteful.
                # The blocking queue read inside read_audio() already rate-limits
                # when no data is buffered, so this sleep only matters when the
                # queue has a backlog to drain.
                if any_audio_processed:
                    time.sleep(0.05)  # 50ms — up to 20 reads/sec, 2× the chunk arrival rate
                else:
                    time.sleep(0.05)  # 50ms when idle — no urgency, save CPU
            
            except Exception as e:
                logger.error(f"Error in unified monitor loop: {e}", exc_info=True)
                time.sleep(0.1)
        
        logger.info("UnifiedEASMonitorService monitor loop exited")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status for the unified monitor.

        Returns status in format compatible with MultiMonitorManager
        for backward compatibility with existing API consumers.
        """
        # Get decoder stats (stateless, no race condition)
        decoder_stats = self._decoder.get_stats()

        # CRITICAL FIX: Capture watchers FIRST, then calculate health based on CURRENT watchers
        # This prevents race where health_percentage is from old sources but monitor_count is 0
        monitors_status = {}
        with self._watchers_lock:
            # Capture these while lock is held - prevents race with _discover_sources()
            monitor_count = len(self._watchers)
            source_names = list(self._watchers.keys())

        # Now get health ONLY for currently registered watchers
        # This ensures health metrics match current watcher state
        all_health = self._health_tracker.get_all_health()
        uptime = self._health_tracker.get_uptime_seconds()

        # Calculate aggregates based on CURRENT watchers (not stale health data)
        total_samples = 0
        active_sources = 0
        for source_name in source_names:
            health = all_health.get(source_name)
            if health:
                total_samples += health.samples_processed
                if health.audio_flowing:
                    active_sources += 1

        # Calculate health percentage from current watcher data
        if uptime > 0 and total_samples > 0 and active_sources > 0:
            samples_per_second = total_samples / uptime
            expected_rate = self._target_sample_rate * active_sources
            health_percentage = min(1.0, samples_per_second / expected_rate)
        else:
            samples_per_second = 0
            health_percentage = 0.0

        # Build per-source status for current watchers
        with self._watchers_lock:
            for source_name, watcher in self._watchers.items():
                health = all_health.get(source_name)
                if health:
                    time_since_audio = (
                        time.time() - health.last_audio_time
                        if health.last_audio_time > 0
                        else 999999
                    )

                    source_samples_per_sec = (
                        health.samples_processed / uptime
                        if uptime > 0
                        else 0
                    )

                    monitors_status[source_name] = {
                        "running": self._running,
                        "mode": "unified-streaming",
                        "source_name": source_name,
                        "audio_flowing": health.audio_flowing,
                        "samples_processed": health.samples_processed,
                        "samples_per_second": int(source_samples_per_sec),
                        "time_since_last_audio": time_since_audio,
                        "consecutive_empty_reads": health.consecutive_empty_reads,
                        "error_count": health.error_count,
                        "last_error": health.last_error,
                        "sample_rate": self._target_sample_rate,
                        "source_sample_rate": watcher.source_sample_rate,
                    }

        # Return status in MultiMonitorManager-compatible format
        # Use captured values to avoid race condition with _discover_sources()
        return {
            "running": self._running,
            "mode": "unified-streaming",
            "samples_processed": total_samples,
            "wall_clock_runtime_seconds": uptime,
            "runtime_seconds": total_samples / self._target_sample_rate if total_samples > 0 else 0,
            "samples_per_second": int(samples_per_second),
            "alerts_detected": self._total_alerts_detected,
            "monitor_count": monitor_count,  # Use captured value
            "active_sources": active_sources,
            "audio_flowing": active_sources > 0,
            "health_percentage": health_percentage,
            "source_names": source_names,  # Use captured value
            "monitors": monitors_status,
            "decoder_synced": decoder_stats.get('synced', False),
            "decoder_in_message": decoder_stats.get('in_message', False),
            "decoder_bytes_decoded": decoder_stats.get('bytes_decoded', 0),
        }
    
    def add_monitor_for_source(self, source_name: str) -> bool:
        """
        Compatibility method for manual source addition.
        
        Not needed with auto-discovery, but provided for API compatibility.
        The next discovery cycle will pick up the source automatically.
        
        Args:
            source_name: Name of the source to monitor
            
        Returns:
            True (discovery will handle it)
        """
        logger.info(
            f"add_monitor_for_source('{source_name}') called - "
            f"source will be discovered automatically"
        )
        # Trigger immediate discovery
        self._discover_sources()
        return True
    
    def remove_monitor_for_source(self, source_name: str) -> bool:
        """
        Compatibility method for manual source removal.
        
        Not needed with auto-discovery, but provided for API compatibility.
        The next discovery cycle will remove stopped sources automatically.
        
        Args:
            source_name: Name of the source to stop monitoring
            
        Returns:
            True (discovery will handle it)
        """
        logger.info(
            f"remove_monitor_for_source('{source_name}') called - "
            f"source will be removed automatically if stopped"
        )
        # Trigger immediate discovery
        self._discover_sources()
        return True


# Backward compatibility alias
UnifiedEASMonitor = UnifiedEASMonitorService
