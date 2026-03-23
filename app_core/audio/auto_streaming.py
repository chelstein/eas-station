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

from __future__ import annotations

"""
Automatic Icecast Streaming for Audio Sources

Automatically creates and maintains Icecast streams for all running audio sources.
Falls back gracefully if Icecast is not available.

Features:
- Auto-start streaming when audio source starts
- Auto-stop streaming when audio source stops
- Health monitoring and automatic reconnection
- Per-source mount points
- Configurable quality settings
"""

import logging
import threading
import time
from types import SimpleNamespace
from typing import Dict, Optional, TYPE_CHECKING

from .icecast_output import IcecastConfig, IcecastStreamer, StreamFormat
from .mount_points import generate_mount_point, StreamFormat as MountStreamFormat

if TYPE_CHECKING:
    from .ingest import AudioIngestController

logger = logging.getLogger(__name__)

# Internal key used to track the EAS ingest Icecast stream inside _streamers
_EAS_INGEST_KEY = "_eas-ingest"


class EASIngestShim:
    """
    Duck-type shim that exposes a source's 16 kHz EAS broadcast queue as
    a plain broadcast queue so IcecastStreamer can stream it without
    modification.

    IcecastStreamer calls ``audio_source.get_broadcast_queue()`` to subscribe
    to audio chunks and reads ``audio_source.config.sample_rate`` /
    ``audio_source.config.channels`` to configure FFmpeg.  This shim maps
    those calls onto the source's EAS-specific queue (pre-resampled 16 kHz
    float32 mono), giving Icecast clients an always-current view of exactly
    what the EAS decoder is processing.
    """

    def __init__(self, source_adapter):
        self._source = source_adapter
        # Expose the same config interface IcecastStreamer expects
        self.config = SimpleNamespace(sample_rate=16000, channels=1)

    def get_broadcast_queue(self):
        """Return the source's EAS (16 kHz) broadcast queue."""
        return self._source.get_eas_broadcast_queue()

    @property
    def status(self):
        """Mirror the underlying source's status for health checks."""
        return getattr(self._source, 'status', None)


class AutoStreamingService:
    """
    Manages automatic Icecast streaming for audio sources.

    Creates and maintains an Icecast stream for each running audio source.
    Handles lifecycle management and automatic failover.
    """

    def __init__(
        self,
        icecast_server: str = "localhost",
        icecast_port: int = 8000,
        icecast_password: str = "",
        icecast_admin_user: Optional[str] = None,
        icecast_admin_password: Optional[str] = None,
        default_bitrate: int = 128,
        default_format: StreamFormat = StreamFormat.MP3,
        enabled: bool = False,
        audio_controller: Optional['AudioIngestController'] = None
    ):
        """
        Initialize auto-streaming service.

        Args:
            icecast_server: Icecast server hostname
            icecast_port: Icecast server port
            icecast_password: Source password for Icecast
            default_bitrate: Default bitrate for streams (kbps)
            default_format: Default audio format (MP3 or OGG)
            enabled: Whether service is enabled
            audio_controller: AudioIngestController for broadcast queue access
        """
        self.icecast_server = icecast_server
        self.icecast_port = icecast_port
        self.icecast_password = icecast_password
        self.icecast_admin_user = icecast_admin_user
        self.icecast_admin_password = icecast_admin_password
        self.default_bitrate = default_bitrate
        self.default_format = default_format
        self.enabled = enabled
        self.audio_controller = audio_controller

        # Active streamers: source_name -> IcecastStreamer
        self._streamers: Dict[str, IcecastStreamer] = {}
        self._lock = threading.Lock()

        # Tracks which real source the EAS ingest stream is currently using
        self._eas_ingest_source_name: Optional[str] = None

        # Monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        logger.info(
            f"AutoStreamingService initialized: {icecast_server}:{icecast_port} "
            f"(enabled={enabled}, broadcast_mode={audio_controller is not None})"
        )

    def start(self) -> bool:
        """
        Start the auto-streaming service.

        Returns:
            True if started successfully
        """
        if not self.enabled:
            logger.info("AutoStreamingService is disabled, not starting")
            return False

        if not self.icecast_password:
            logger.warning(
                "AutoStreamingService: No Icecast password configured, "
                "streaming will not work"
            )
            return False

        self._stop_event.clear()

        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="auto-streaming-monitor",
            daemon=True
        )
        self._monitor_thread.start()

        logger.info("AutoStreamingService started")
        return True

    def stop(self) -> None:
        """Stop the auto-streaming service and all active streams."""
        logger.info("Stopping AutoStreamingService")
        self._stop_event.set()

        # Stop all active streamers
        with self._lock:
            for source_name, streamer in list(self._streamers.items()):
                try:
                    streamer.stop()
                except Exception as e:
                    logger.error(f"Error stopping streamer for {source_name}: {e}")

            self._streamers.clear()

        # Wait for monitor thread
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)

        logger.info("AutoStreamingService stopped")

    def add_source(self, source_name: str, audio_source, bitrate: Optional[int] = None) -> bool:
        """
        Add an audio source for streaming.

        Args:
            source_name: Unique name for the source
            audio_source: Audio source object (AudioSourceAdapter) - will be wrapped in broadcast adapter
            bitrate: Optional custom bitrate (uses default if None)

        Returns:
            True if streaming started successfully
        """
        if not self.enabled:
            logger.debug(f"AutoStreaming disabled, not adding {source_name}")
            return False

        # For StreamSourceAdapter with preserve_native_rate=True, FFmpeg detects
        # the actual sample rate asynchronously from its stderr output and updates
        # config.sample_rate only after parsing the stream info line.  That
        # detection happens *before* the first audio packet is delivered, so
        # waiting until _last_connection_time is set guarantees the rate in
        # config.sample_rate is correct.
        #
        # This wait is intentionally placed BEFORE acquiring self._lock so that
        # up to 5 seconds of blocking does not stall other lock holders.
        #
        # Without this wait, add_source() could read config.sample_rate = 44100
        # (the default) for a source that actually streams at 48000 Hz.  The
        # resulting IcecastConfig would tell FFmpeg ("-ar 44100") to interpret
        # 48000 Hz PCM as 44100 Hz, encoding an MP3 that plays at 91.9% speed —
        # making 10 minutes of audio take ~11 minutes.
        if hasattr(audio_source, '_last_connection_time'):  # StreamSourceAdapter
            deadline = time.time() + 5.0
            while time.time() < deadline and audio_source._last_connection_time is None:
                time.sleep(0.05)

        with self._lock:
            if source_name in self._streamers:
                logger.warning(f"Streamer for {source_name} already exists")
                return False

            try:
                # CRITICAL: Each Icecast stream outputs its OWN source's audio
                # at the source's NATIVE sample rate - DO NOT alter the stream!
                # Use the source's native sample rate and channels
                sample_rate = 44100  # Default
                if hasattr(audio_source, 'config') and hasattr(audio_source.config, 'sample_rate'):
                    sample_rate = audio_source.config.sample_rate
                elif hasattr(audio_source, 'sample_rate'):
                    sample_rate = audio_source.sample_rate

                channels = 2 if getattr(audio_source.config, 'channels', 1) > 1 else 1

                # Convert StreamFormat enum to MountStreamFormat enum
                mount_format = MountStreamFormat.MP3 if self.default_format == StreamFormat.MP3 else MountStreamFormat.OGG

                # Generate mount point using centralized logic
                mount_point = generate_mount_point(source_name, format=mount_format)

                config = IcecastConfig(
                    server=self.icecast_server,
                    port=self.icecast_port,
                    password=self.icecast_password,
                    mount=mount_point,
                    name=f"{source_name} - EAS Monitor",
                    description=f"Live stream from {source_name}",
                    genre="Emergency Alert System",
                    bitrate=bitrate or self.default_bitrate,
                    format=self.default_format,
                    public=False,
                    sample_rate=sample_rate,  # Use source's native sample rate
                    channels=channels,
                    admin_user=self.icecast_admin_user,
                    admin_password=self.icecast_admin_password,
                )

                # CRITICAL: Each Icecast stream subscribes to its OWN source's audio
                # via the source's BroadcastQueue. This ensures it gets an independent
                # copy of the audio without starving the EAS monitor or other consumers.
                # This ensures WNCI stream outputs WNCI audio, WIMT outputs WIMT audio, etc.
                logger.info(
                    f"Icecast stream '{source_name}' will subscribe to source "
                    f"at native {sample_rate} Hz (broadcast mode)"
                )

                # Create and start streamer with direct source access
                streamer = IcecastStreamer(config, audio_source)
                if streamer.start():
                    self._streamers[source_name] = streamer
                    logger.info(
                        f"Started Icecast stream for {source_name} at "
                        f"http://{self.icecast_server}:{self.icecast_port}{mount_point}"
                    )
                    return True
                else:
                    logger.error(f"Failed to start Icecast stream for {source_name}")
                    return False

            except Exception as e:
                logger.error(f"Error creating streamer for {source_name}: {e}")
                return False

    def remove_source(self, source_name: str) -> bool:
        """
        Remove an audio source and stop its stream.

        Args:
            source_name: Name of source to remove

        Returns:
            True if removed successfully
        """
        with self._lock:
            streamer = self._streamers.pop(source_name, None)

            if not streamer:
                logger.warning(f"No streamer found for {source_name}")
                return False

            try:
                streamer.stop()
                logger.info(f"Stopped Icecast stream for {source_name}")
                return True
            except Exception as e:
                logger.error(f"Error stopping streamer for {source_name}: {e}")
                return False

    def get_stream_url(self, source_name: str) -> Optional[str]:
        """
        Get the Icecast stream URL for a source.

        Args:
            source_name: Name of the source

        Returns:
            Stream URL if source is streaming, None otherwise
        """
        with self._lock:
            streamer = self._streamers.get(source_name)
            if streamer:
                mount_point = getattr(streamer.config, 'mount', None)
                if mount_point:
                    return (
                        f"http://{self.icecast_server}:{self.icecast_port}{mount_point}"
                    )
            return None

    def get_status(self) -> dict:
        """
        Get service status and statistics.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            active_streams = {}
            for source_name, streamer in self._streamers.items():
                active_streams[source_name] = streamer.get_stats()

            return {
                "enabled": self.enabled,
                "server": f"{self.icecast_server}:{self.icecast_port}",
                "active_stream_count": len(self._streamers),
                "active_streams": active_streams,
            }

    def is_available(self) -> bool:
        """
        Check if Icecast streaming is available.

        Returns:
            True if enabled and configured
        """
        return self.enabled and bool(self.icecast_password)

    def _add_eas_ingest_stream(self, source_name: str, source_adapter) -> bool:
        """
        Create an Icecast stream for the EAS decoder input (16 kHz mono).

        The mount point is always ``/eas-ingest.mp3``.  The stream carries the
        same 16 kHz float32 audio the EAS decoder processes, so operators can
        confirm what the decoder is hearing without needing CLI access.

        Args:
            source_name: Human-readable name of the underlying source (for logging).
            source_adapter: Running AudioSourceAdapter whose EAS queue to stream.

        Returns:
            True if the stream started successfully.
        """
        try:
            shim = EASIngestShim(source_adapter)
            config = IcecastConfig(
                server=self.icecast_server,
                port=self.icecast_port,
                password=self.icecast_password,
                mount="/eas-ingest.mp3",
                name="EAS Decoder Input",
                description=f"16 kHz mono — what the EAS decoder hears (source: {source_name})",
                genre="Emergency Alert System",
                bitrate=48,          # 48 kbps is plenty for a 16 kHz mono diagnostic stream
                format=StreamFormat.MP3,
                public=False,
                sample_rate=16000,
                channels=1,
                admin_user=self.icecast_admin_user,
                admin_password=self.icecast_admin_password,
            )
            streamer = IcecastStreamer(config, shim)
            with self._lock:
                if _EAS_INGEST_KEY in self._streamers:
                    return False  # Created concurrently, skip
                if streamer.start():
                    self._streamers[_EAS_INGEST_KEY] = streamer
                    self._eas_ingest_source_name = source_name
                    logger.info(
                        "✅ EAS ingest Icecast stream started: "
                        "http://%s:%s/eas-ingest.mp3 (from source '%s')",
                        self.icecast_server, self.icecast_port, source_name,
                    )
                    return True
                else:
                    logger.error("Failed to start EAS ingest Icecast stream")
                    return False
        except Exception as exc:
            logger.error("Error creating EAS ingest Icecast stream: %s", exc, exc_info=True)
            return False

    def _monitor_loop(self) -> None:
        """Monitor active streams, discover new sources, and handle reconnections."""
        logger.debug("Auto-streaming monitor loop started")

        while not self._stop_event.is_set():
            try:
                if self.audio_controller:
                    from .ingest import AudioSourceStatus

                    all_sources = self.audio_controller.get_all_sources()

                    # ── 1. Auto-discover RUNNING sources for native-rate streams ──
                    for source_name, source_adapter in all_sources.items():
                        with self._lock:
                            if source_name in self._streamers:
                                continue
                        if source_adapter.status == AudioSourceStatus.RUNNING:
                            try:
                                if self.add_source(source_name, source_adapter):
                                    logger.info(
                                        "Auto-discovered and added source '%s' "
                                        "to Icecast streaming",
                                        source_name,
                                    )
                            except Exception as exc:
                                logger.debug(
                                    "Failed to add auto-discovered source '%s': %s",
                                    source_name, exc,
                                )

                    # ── 2. Manage EAS ingest stream (16 kHz decoder input) ────────
                    with self._lock:
                        eas_ingest_active = _EAS_INGEST_KEY in self._streamers

                    if not eas_ingest_active:
                        # Find a running source that has an EAS broadcast queue
                        for source_name, source_adapter in all_sources.items():
                            if (
                                source_adapter.status == AudioSourceStatus.RUNNING
                                and hasattr(source_adapter, 'get_eas_broadcast_queue')
                            ):
                                self._add_eas_ingest_stream(source_name, source_adapter)
                                break
                    else:
                        # Check whether the source backing the EAS ingest stream is
                        # still running; if not, tear the stream down so the next
                        # loop iteration can rebuild it from a live source.
                        eas_source = all_sources.get(self._eas_ingest_source_name or "")
                        if not eas_source or eas_source.status != AudioSourceStatus.RUNNING:
                            logger.info(
                                "EAS ingest source '%s' no longer running — "
                                "stopping EAS ingest stream",
                                self._eas_ingest_source_name,
                            )
                            self.remove_source(_EAS_INGEST_KEY)
                            self._eas_ingest_source_name = None

                    # ── 3. Health-check all streamers ────────────────────────────
                    with self._lock:
                        for sn, streamer in list(self._streamers.items()):
                            if not streamer.get_stats().get("running", False):
                                logger.warning("Streamer for '%s' stopped unexpectedly", sn)

                        # ── 4. Remove native-rate streamers for stopped sources ──
                        if self.audio_controller:
                            for source_name in list(self._streamers.keys()):
                                if source_name == _EAS_INGEST_KEY:
                                    continue  # Lifecycle managed above in step 2
                                source_adapter = all_sources.get(source_name)
                                if (
                                    not source_adapter
                                    or source_adapter.status != AudioSourceStatus.RUNNING
                                ):
                                    logger.info(
                                        "Removing Icecast stream for '%s' "
                                        "(source stopped or removed)",
                                        source_name,
                                    )
                                    self.remove_source(source_name)

                time.sleep(10.0)

            except Exception as exc:
                logger.error("Error in auto-streaming monitor loop: %s", exc)
                time.sleep(5.0)

        logger.debug("Auto-streaming monitor loop stopped")


__all__ = ['AutoStreamingService', 'EASIngestShim']
