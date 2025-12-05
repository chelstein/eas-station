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
        self._subscriber_thread: Optional[threading.Thread] = None
        # Note: self._audio_queue is created by base class via BroadcastQueue subscription
        # Don't override it - use self._source_broadcast.publish() instead
        self._receiver_id: Optional[str] = None
        self._demodulator: Optional[Any] = None
        self._last_sample_time: float = 0.0
        self._samples_received: int = 0
        self._iq_sample_rate: int = 2500000  # Will be updated from Redis messages
        self._center_frequency: int = 0  # Will be updated from Redis messages

    def _start_capture(self) -> None:
        """Start Redis subscription and audio processing."""
        # Get receiver ID from config
        self._receiver_id = self.config.device_params.get('receiver_id')
        if not self._receiver_id:
            raise ValueError("receiver_id required in device_params for Redis SDR source")

        # Connect to Redis
        from app_core.redis_client import get_redis_client
        try:
            self._redis_client = get_redis_client()
            logger.info(f"Connected to Redis for receiver {self._receiver_id}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}") from e

        # Get demodulation settings from config
        demod_mode = self.config.device_params.get('demod_mode', 'FM')

        # Create demodulator
        from app_core.radio.demodulation import create_demodulator, DemodulatorConfig

        demod_config = DemodulatorConfig(
            modulation_type=demod_mode,
            sample_rate=self._iq_sample_rate,  # IQ sample rate from SDR
            audio_sample_rate=self.config.sample_rate,  # Audio output rate (e.g., 44100)
            stereo_enabled=True,  # Enable stereo decoding for FM
        )

        self._demodulator = create_demodulator(demod_config)
        logger.info(
            f"Created {demod_mode} demodulator: "
            f"{self._iq_sample_rate}Hz IQ → {self.config.sample_rate}Hz audio"
        )

        # Subscribe to Redis pub/sub channel
        self._pubsub = self._redis_client.pubsub(ignore_subscribe_messages=True)
        channel = f"sdr:samples:{self._receiver_id}"
        self._pubsub.subscribe(channel)
        logger.info(f"Subscribed to Redis channel: {channel}")

        # Start subscriber thread
        self._subscriber_thread = threading.Thread(
            target=self._redis_subscriber_loop,
            name=f"redis-sdr-{self._receiver_id}",
            daemon=True
        )
        self._subscriber_thread.start()
        logger.info(f"Started Redis SDR subscriber for {self._receiver_id}")

    def _redis_subscriber_loop(self) -> None:
        """Redis pub/sub subscriber loop - receives IQ samples and demodulates to audio."""
        logger.info(f"Redis subscriber loop started for {self._receiver_id}")

        try:
            while self._running.is_set():
                # Use get_message with timeout instead of listen() to allow graceful shutdown
                message = self._pubsub.get_message(timeout=1.0)

                if message is None:
                    continue

                if message['type'] != 'message':
                    continue

                try:
                    # Parse message
                    data = json.loads(message['data'])

                    # Update metadata
                    self._iq_sample_rate = data.get('sample_rate', self._iq_sample_rate)
                    self._center_frequency = data.get('center_frequency', self._center_frequency)

                    # Decode IQ samples
                    encoded_samples = data.get('samples', '')
                    if not encoded_samples:
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
                            # Publish to BroadcastQueue for web streams and other consumers
                            # This allows multiple independent subscribers (Icecast, web player, EAS monitor)
                            self._source_broadcast.publish(audio_samples)

                            # Update metrics
                            self._update_metrics(audio_samples)
                            self._samples_received += len(audio_samples)
                            self._last_sample_time = time.time()

                except Exception as e:
                    logger.error(f"Error processing Redis IQ sample: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Redis subscriber loop error: {e}", exc_info=True)
        finally:
            logger.info(f"Redis subscriber loop exited for {self._receiver_id}")

    def _stop_capture(self) -> None:
        """Stop Redis subscription."""
        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.close()
            except Exception as e:
                logger.error(f"Error closing Redis pub/sub: {e}")

        if self._subscriber_thread and self._subscriber_thread.is_alive():
            self._subscriber_thread.join(timeout=5.0)

        logger.info(f"Stopped Redis SDR source for {self._receiver_id}")

    # Note: get_audio_chunk() inherited from base class - reads from BroadcastQueue subscription
    # No need to override since base class handles it correctly

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
        self.metrics.metadata['center_frequency_mhz'] = round(self._center_frequency / 1_000_000, 6)
        self.metrics.metadata['samples_received'] = self._samples_received
        self.metrics.metadata['last_sample_age'] = time.time() - self._last_sample_time if self._last_sample_time > 0 else None
