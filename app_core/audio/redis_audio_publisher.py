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
Redis Audio Publisher

Subscribes to audio broadcast queue and publishes audio samples to Redis
for consumption by eas-service.

This enables 3-tier separated architecture where:
- sdr-service: SDR hardware + IQ publishing
- audio-service: IQ demodulation + audio publishing (this module)
- eas-service: EAS monitoring + alert storage
"""

import base64
import json
import logging
import threading
import time
from typing import Optional, Any

import numpy as np

from .broadcast_adapter import BroadcastAudioAdapter
from .broadcast_queue import BroadcastQueue

logger = logging.getLogger(__name__)


class RedisAudioPublisher:
    """
    Publishes audio samples from broadcast queue to Redis pub/sub.

    Subscribes to audio controller's broadcast queue and publishes
    audio samples to Redis channel audio:samples:{source_name} for
    consumption by eas-service.
    """

    def __init__(
        self,
        broadcast_queue: BroadcastQueue,
        source_name: str = "audio",
        sample_rate: int = 44100,
        publish_interval_ms: int = 100
    ):
        """
        Initialize Redis audio publisher.

        Args:
            broadcast_queue: BroadcastQueue to subscribe to
            source_name: Name for this audio source (used in Redis channel)
            sample_rate: Audio sample rate
            publish_interval_ms: Interval between Redis publications (milliseconds)
        """
        self.broadcast_queue = broadcast_queue
        self.source_name = source_name
        self.sample_rate = sample_rate
        self.publish_interval = publish_interval_ms / 1000.0

        self._redis_client: Optional[Any] = None
        self._audio_adapter: Optional[BroadcastAudioAdapter] = None
        self._publisher_thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._samples_published: int = 0
        self._last_publish_time: float = 0.0

        logger.info(
            f"Redis audio publisher created: {source_name} "
            f"(rate={sample_rate}Hz, interval={publish_interval_ms}ms)"
        )

    def start(self) -> bool:
        """Start publishing audio to Redis."""
        try:
            # Connect to Redis
            from app_core.redis_client import get_redis_client
            self._redis_client = get_redis_client()
            logger.info("Connected to Redis for audio publishing")

            # Subscribe to broadcast queue
            self._audio_adapter = BroadcastAudioAdapter(
                broadcast_queue=self.broadcast_queue,
                subscriber_id=f"redis-publisher-{self.source_name}",
                sample_rate=self.sample_rate,
                read_timeout=0.5
            )
            logger.info(f"Subscribed to broadcast queue for Redis publishing")

            # Start publisher thread
            self._running.set()
            self._publisher_thread = threading.Thread(
                target=self._publisher_loop,
                name=f"redis-pub-{self.source_name}",
                daemon=True
            )
            self._publisher_thread.start()
            logger.info(f"✅ Redis audio publisher started for '{self.source_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to start Redis audio publisher: {e}", exc_info=True)
            return False

    def _publisher_loop(self) -> None:
        """Main publisher loop - reads audio and publishes to Redis."""
        logger.info(f"Redis publisher loop started for '{self.source_name}'")

        # Calculate chunk size based on publish interval
        chunk_samples = int(self.sample_rate * self.publish_interval)

        try:
            while self._running.is_set():
                try:
                    # Read audio chunk from broadcast queue
                    audio_chunk = self._audio_adapter.read_audio(chunk_samples)

                    if audio_chunk is not None and len(audio_chunk) > 0:
                        # Encode audio samples as base64 (float32 array)
                        sample_bytes = audio_chunk.astype(np.float32).tobytes()
                        encoded_samples = base64.b64encode(sample_bytes).decode('ascii')

                        # Create message
                        message = {
                            'source_name': self.source_name,
                            'timestamp': time.time(),
                            'sample_count': len(audio_chunk),
                            'sample_rate': self.sample_rate,
                            'encoding': 'base64_float32',
                            'samples': encoded_samples,
                        }

                        # Publish to Redis channel
                        channel = f"audio:samples:{self.source_name}"
                        self._redis_client.publish(channel, json.dumps(message))

                        self._samples_published += len(audio_chunk)
                        self._last_publish_time = time.time()

                    else:
                        # No audio available, sleep briefly
                        time.sleep(0.02)

                except Exception as e:
                    logger.error(f"Error in Redis publisher loop: {e}", exc_info=True)
                    time.sleep(0.1)

        except Exception as e:
            logger.error(f"Fatal error in Redis publisher loop: {e}", exc_info=True)
        finally:
            logger.info(f"Redis publisher loop exited for '{self.source_name}'")

    def stop(self) -> None:
        """Stop publishing audio to Redis."""
        self._running.clear()

        if self._publisher_thread and self._publisher_thread.is_alive():
            self._publisher_thread.join(timeout=5.0)

        if self._audio_adapter:
            try:
                self._audio_adapter.unsubscribe()
            except Exception as e:
                logger.error(f"Error unsubscribing audio adapter: {e}")

        logger.info(f"✅ Redis audio publisher stopped for '{self.source_name}'")

    def get_stats(self) -> dict:
        """Get publisher statistics."""
        return {
            'source_name': self.source_name,
            'samples_published': self._samples_published,
            'last_publish_time': self._last_publish_time,
            'running': self._running.is_set(),
        }

    def __repr__(self) -> str:
        return f"<RedisAudioPublisher '{self.source_name}'>"
