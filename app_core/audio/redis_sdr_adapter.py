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
Redis SDR Source Adapter

Subscribes to Redis pub/sub channels to receive IQ samples from sdr-service,
demodulates them to audio, and provides audio to the audio controller.

This is the bridge between sdr-service (SDR hardware + IQ publishing) and
audio-service (audio processing + EAS monitoring) in separated architecture.
"""

import base64
import json
import logging
import queue
import threading
import time
import zlib
from typing import Optional, Any

import numpy as np
import redis.exceptions

from .ingest import AudioSourceAdapter, AudioSourceConfig, AudioSourceStatus, AudioMetrics

logger = logging.getLogger(__name__)


class RedisSDRSourceAdapter(AudioSourceAdapter):
    """
    Audio source adapter that receives IQ samples from Redis pub/sub.

    Subscribes to sdr:samples:{receiver_id} channel published by sdr-service,
    demodulates IQ samples to audio, and feeds audio to the broadcast queue.

    This enables separated architecture where:
    - sdr-service: SDR hardware access + IQ sample publishing
    - audio-service: IQ demodulation + audio processing + EAS monitoring
    """

    def __init__(self, config: AudioSourceConfig):
        super().__init__(config)
        self._redis_client: Optional[Any] = None
        self._pubsub: Optional[Any] = None
        # Note: self._audio_queue is created by base class via BroadcastQueue subscription
        # Don't override it - use self._source_broadcast.publish() instead
        self._receiver_id: Optional[str] = None
        self._demodulator: Optional[Any] = None
        self._last_sample_time: float = 0.0
        self._samples_received: int = 0
        self._iq_sample_rate: int = 2500000  # Will be updated from Redis messages
        self._center_frequency: int = 0  # Will be updated from Redis messages
        # Queue for audio chunks from Redis subscriber thread
        self._audio_chunk_queue: queue.Queue = queue.Queue(maxsize=100)

    def _create_demodulator(self) -> None:
        """Create or recreate demodulator with current settings."""
        demod_mode = self.config.device_params.get('demod_mode', 'FM')

        # Normalize modulation type to uppercase for consistent handling
        demod_mode = demod_mode.upper()

        # Determine stereo support based on modulation type
        # WFM (Wide FM for FM broadcast) supports stereo
        # NFM (Narrow FM for NOAA, public safety) is mono only
        stereo_enabled = (demod_mode == 'WFM' or demod_mode == 'FM')
        
        from app_core.radio.demodulation import create_demodulator, DemodulatorConfig

        demod_config = DemodulatorConfig(
            modulation_type=demod_mode,
            sample_rate=self._iq_sample_rate,  # IQ sample rate from SDR
            audio_sample_rate=self.config.sample_rate,  # Audio output rate (e.g., 44100)
            stereo_enabled=stereo_enabled,
        )

        self._demodulator = create_demodulator(demod_config)
        logger.info(
            f"Created {demod_mode} demodulator: "
            f"{self._iq_sample_rate}Hz IQ → {self.config.sample_rate}Hz audio "
            f"(stereo={'yes' if stereo_enabled else 'no'})"
        )

    def _start_capture(self) -> None:
        """Start Redis subscription and audio processing."""
        # Get receiver ID from config
        self._receiver_id = self.config.device_params.get('receiver_id')
        if not self._receiver_id:
            raise ValueError("receiver_id required in device_params for Redis SDR source")

        # Get IQ sample rate from config if provided (preferred method)
        # Otherwise will be set from first Redis message
        config_sample_rate = self.config.device_params.get('iq_sample_rate')
        if config_sample_rate:
            self._iq_sample_rate = int(config_sample_rate)
            logger.info(f"Using IQ sample rate from config: {self._iq_sample_rate}Hz")
        else:
            # Default to common Airspy rate if not specified
            # Will be updated from first Redis message if different
            self._iq_sample_rate = 2_500_000  # Airspy R2 default
            logger.warning(
                f"IQ sample rate not in config for {self._receiver_id}. "
                f"Using default {self._iq_sample_rate}Hz, will update from first sample."
            )

        # Connect to Redis
        from app_core.redis_client import get_redis_client
        try:
            self._redis_client = get_redis_client()
            logger.info(f"Connected to Redis for receiver {self._receiver_id}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}") from e

        # ALWAYS create demodulator at startup to avoid dropping initial audio
        # Sample rate will be adjusted if first Redis message has different rate
        self._create_demodulator()
        logger.info(f"Pre-created demodulator for {self._receiver_id} (rate: {self._iq_sample_rate}Hz)")

        # Subscribe to Redis pub/sub channel
        self._pubsub = self._redis_client.pubsub(ignore_subscribe_messages=True)
        channel = f"sdr:samples:{self._receiver_id}"
        self._pubsub.subscribe(channel)
        logger.info(f"Subscribed to Redis channel: {channel}")

        # Start Redis subscriber thread (separate from capture thread)
        # This thread receives IQ samples from Redis and demodulates them
        subscriber_thread = threading.Thread(
            target=self._redis_subscriber_loop,
            name=f"redis-sdr-{self._receiver_id}",
            daemon=True
        )
        subscriber_thread.start()
        logger.info(f"Started Redis SDR subscriber for {self._receiver_id}")

    def _redis_subscriber_loop(self) -> None:
        """Redis pub/sub subscriber loop - receives IQ samples and demodulates to audio."""
        logger.info(f"Redis subscriber loop started for {self._receiver_id}")
        
        last_log_time = time.time()
        messages_received = 0

        try:
            # Use _stop_event from base class instead of undefined _running
            while not self._stop_event.is_set():
                try:
                    # Use get_message with timeout instead of listen() to allow graceful shutdown
                    # Check pubsub availability inside try block to avoid race conditions
                    pubsub = self._pubsub
                    if pubsub is None:
                        logger.debug(f"Redis pubsub closed for {self._receiver_id}, exiting subscriber loop")
                        break
                    
                    message = pubsub.get_message(timeout=1.0)
                except (OSError, ConnectionError, redis.exceptions.ConnectionError) as e:
                    # Handle connection errors gracefully (e.g., socket closed during shutdown)
                    # OSError with errno 9 = Bad file descriptor (socket was closed)
                    # ConnectionError = Built-in connection reset by peer
                    # redis.exceptions.ConnectionError = Redis-specific connection errors (e.g., server closed connection)
                    if self._stop_event.is_set():
                        # Expected during shutdown - log at debug level
                        logger.debug(f"Redis connection closed during shutdown for {self._receiver_id}: {e}")
                    else:
                        # Unexpected connection error - log as error
                        logger.error(f"Redis connection error for {self._receiver_id}: {e}")
                    break

                # Log periodically if no samples received
                current_time = time.time()
                if message is None:
                    if current_time - last_log_time > 10.0:
                        if messages_received == 0:
                            logger.warning(
                                f"No IQ samples received for {self._receiver_id} in {current_time - last_log_time:.1f}s. "
                                f"Check if sdr-service is publishing to sdr:samples:{self._receiver_id}"
                            )
                        last_log_time = current_time
                    continue

                if message.get('type') != 'message':
                    continue

                try:
                    messages_received += 1
                    
                    # Parse message
                    data = json.loads(message['data'])

                    # Update metadata
                    new_sample_rate = data.get('sample_rate', self._iq_sample_rate)
                    self._center_frequency = data.get('center_frequency', self._center_frequency)

                    # Update demodulator if sample rate changed
                    if new_sample_rate != self._iq_sample_rate:
                        logger.info(
                            f"IQ sample rate changed: {self._iq_sample_rate}Hz -> {new_sample_rate}Hz. "
                            f"Recreating demodulator..."
                        )
                        self._iq_sample_rate = new_sample_rate
                        # Recreate demodulator with new sample rate
                        self._create_demodulator()
                        logger.info(f"✅ Demodulator updated for rate {new_sample_rate}Hz")

                    # Decode IQ samples
                    encoded_samples = data.get('samples', '')
                    if not encoded_samples:
                        logger.warning(f"Empty IQ sample data from {self._receiver_id}")
                        continue

                    # Decompress and decode (zlib + base64)
                    compressed = base64.b64decode(encoded_samples)
                    interleaved_bytes = zlib.decompress(compressed)
                    interleaved = np.frombuffer(interleaved_bytes, dtype=np.float32)

                    # Convert interleaved [real, imag, real, imag, ...] to complex samples
                    iq_samples = interleaved[0::2] + 1j * interleaved[1::2]

                    # Demodulate IQ to audio
                    if self._demodulator:
                        audio_samples = self._demodulator.process(iq_samples)

                        if audio_samples is not None and len(audio_samples) > 0:
                            # Put audio in queue for _read_audio_chunk() to consume
                            # The base class capture loop will handle metrics updates and broadcasting
                            try:
                                self._audio_chunk_queue.put(audio_samples, timeout=0.1)
                                self._samples_received += len(audio_samples)
                                self._last_sample_time = time.time()
                                
                                # Log first successful sample
                                if messages_received == 1:
                                    logger.info(
                                        f"✅ First audio chunk decoded for {self._receiver_id}: "
                                        f"{len(audio_samples)} samples"
                                    )
                            except queue.Full:
                                logger.warning(f"Audio chunk queue full for {self._receiver_id}, dropping samples")
                    else:
                        logger.error(f"No demodulator available for {self._receiver_id} - cannot process IQ samples")

                except Exception as e:
                    logger.error(f"Error processing Redis IQ sample: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Redis subscriber loop error: {e}", exc_info=True)
        finally:
            logger.info(
                f"Redis subscriber loop exited for {self._receiver_id}. "
                f"Processed {messages_received} messages"
            )

    def _stop_capture(self) -> None:
        """Stop Redis subscription."""
        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.close()
            except Exception as e:
                # Log at debug level since errors during cleanup are expected
                logger.debug(f"Error closing Redis pub/sub for {self._receiver_id}: {e}")
            finally:
                # Mark pubsub as None to signal subscriber loop to exit
                self._pubsub = None

        # Clear audio chunk queue
        while not self._audio_chunk_queue.empty():
            try:
                self._audio_chunk_queue.get_nowait()
            except queue.Empty:
                break

        logger.info(f"Stopped Redis SDR source for {self._receiver_id}")

    def _read_audio_chunk(self) -> Optional[np.ndarray]:
        """Read an audio chunk from the queue filled by Redis subscriber thread.
        
        This method is called by the base class's capture loop.
        The Redis subscriber thread demodulates IQ samples and puts audio in the queue.
        """
        try:
            # Get audio chunk from queue with short timeout
            # This allows the capture loop to check _stop_event periodically
            audio_chunk = self._audio_chunk_queue.get(timeout=0.1)
            return audio_chunk
        except queue.Empty:
            # No audio available yet - this is normal, return None
            return None

    def _update_metrics(self, audio_chunk: Optional[np.ndarray] = None) -> None:
        """Update metrics from Redis SDR source."""
        super()._update_metrics(audio_chunk)

        # Add Redis-specific metadata
        if self.metrics.metadata is None:
            self.metrics.metadata = {}

        self.metrics.metadata['source_type'] = 'redis_sdr'
        self.metrics.metadata['receiver_id'] = self._receiver_id
        self.metrics.metadata['iq_sample_rate'] = self._iq_sample_rate
        self.metrics.metadata['center_frequency'] = self._center_frequency
        self.metrics.metadata['receiver_frequency_hz'] = self._center_frequency  # For waterfall display
        self.metrics.metadata['receiver_modulation'] = self.config.device_params.get('demod_mode', 'FM')  # For waterfall display
        self.metrics.metadata['demodulation_enabled'] = True  # For waterfall display
        self.metrics.metadata['center_frequency_mhz'] = round(self._center_frequency / 1_000_000, 6)
        self.metrics.metadata['samples_received'] = self._samples_received
        self.metrics.metadata['last_sample_age'] = time.time() - self._last_sample_time if self._last_sample_time > 0 else None
