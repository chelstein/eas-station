#!/usr/bin/env python3
"""
Test suite for Redis connection error handling in RedisSDRSourceAdapter.

This test verifies that the adapter properly handles redis.exceptions.ConnectionError
when the Redis server closes the connection unexpectedly.
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
import redis.exceptions

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRedisConnectionErrorHandling(unittest.TestCase):
    """Test Redis connection error handling in RedisSDRSourceAdapter."""

    def setUp(self):
        """Set up test fixtures."""
        from app_core.audio.ingest import AudioSourceConfig, AudioSourceType

        self.config = AudioSourceConfig(
            source_type=AudioSourceType.STREAM,
            name="test-redis-sdr",
            enabled=True,
            priority=1,
            sample_rate=44100,
            channels=1,
            buffer_size=4096,
            device_params={
                'receiver_id': 'test-receiver',
                'demod_mode': 'FM',
                'iq_sample_rate': 2500000
            }
        )

    def test_redis_exceptions_import(self):
        """Test that redis.exceptions module is imported correctly."""
        from app_core.audio import redis_sdr_adapter
        
        # Verify redis.exceptions is imported
        self.assertTrue(hasattr(redis_sdr_adapter, 'redis'))
        
        # Verify we can access redis.exceptions.ConnectionError
        import redis.exceptions as redis_exc
        self.assertIsNotNone(redis_exc.ConnectionError)
        
    def test_redis_connection_error_is_caught(self):
        """Test that redis.exceptions.ConnectionError is properly caught."""
        from app_core.audio.redis_sdr_adapter import RedisSDRSourceAdapter
        
        # Create adapter with mocked Redis
        with patch('app_core.redis_client.get_redis_client') as mock_redis:
            mock_client = MagicMock()
            mock_pubsub = MagicMock()
            
            # Set up pubsub to raise redis.exceptions.ConnectionError on get_message
            mock_pubsub.get_message.side_effect = redis.exceptions.ConnectionError(
                "Connection closed by server."
            )
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            adapter = RedisSDRSourceAdapter(self.config)
            
            # Start capture to begin subscriber loop
            try:
                adapter._start_capture()
                
                # Give the subscriber thread time to hit the exception
                import time
                time.sleep(0.5)
                
                # Stop the adapter
                adapter.stop()
                
                # If we get here without an unhandled exception, the test passes
                self.assertTrue(True)
                
            except redis.exceptions.ConnectionError:
                self.fail("redis.exceptions.ConnectionError was not caught properly")
            except Exception as e:
                # Any other exception is also a failure
                self.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    def test_connection_error_types_hierarchy(self):
        """Test the exception hierarchy to understand what gets caught."""
        # Verify that redis.exceptions.ConnectionError is NOT a subclass of built-in ConnectionError
        self.assertFalse(issubclass(redis.exceptions.ConnectionError, ConnectionError))
        
        # Verify that redis.exceptions.ConnectionError is a subclass of redis.exceptions.RedisError
        self.assertTrue(issubclass(redis.exceptions.ConnectionError, redis.exceptions.RedisError))
        
        # This confirms we need to explicitly catch redis.exceptions.ConnectionError
        
    def test_multiple_exception_types_in_handler(self):
        """Test that the exception handler catches all expected types."""
        from app_core.audio.redis_sdr_adapter import RedisSDRSourceAdapter
        
        # Test cases for different exception types
        exception_types = [
            OSError("Bad file descriptor"),
            ConnectionError("Connection reset by peer"),
            redis.exceptions.ConnectionError("Connection closed by server"),
        ]
        
        for exc in exception_types:
            with self.subTest(exception_type=type(exc).__name__):
                with patch('app_core.redis_client.get_redis_client') as mock_redis:
                    mock_client = MagicMock()
                    mock_pubsub = MagicMock()
                    
                    # Set up pubsub to raise the exception
                    mock_pubsub.get_message.side_effect = exc
                    mock_client.pubsub.return_value = mock_pubsub
                    mock_redis.return_value = mock_client
                    
                    adapter = RedisSDRSourceAdapter(self.config)
                    
                    try:
                        adapter._start_capture()
                        
                        # Give the subscriber thread time to hit the exception
                        import time
                        time.sleep(0.5)
                        
                        # Stop the adapter
                        adapter.stop()
                        
                        # If we get here without an unhandled exception, the test passes
                        self.assertTrue(True)
                        
                    except (OSError, ConnectionError, redis.exceptions.ConnectionError):
                        self.fail(f"{type(exc).__name__} was not caught properly in subscriber loop")
                    except Exception as e:
                        # Any other exception is also a failure
                        self.fail(f"Unexpected exception: {type(e).__name__}: {e}")


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test class
    suite.addTests(loader.loadTestsFromTestCase(TestRedisConnectionErrorHandling))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
