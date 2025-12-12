# Audio Dropped Packets Explained

## Overview

If you see log messages like:
```
Broadcast pump status: 1/1 sources running, 1 subscribers ['controller-legacy'], 
119 chunks published (last 10.0s), 0 empty reads, total published: 22479, dropped: 20479
```

**This is NORMAL and EXPECTED behavior** for the EAS Station audio broadcast system.

## Why Dropped Packets Happen

The audio system uses a **broadcast queue** pattern with a circular buffer design. This architecture prevents slow consumers (subscribers) from blocking or slowing down real-time audio processing.

### How It Works

1. **Audio Source** → Publishes audio chunks to broadcast queue
2. **Broadcast Queue** → Maintains separate queues for each subscriber
3. **Subscribers** → Read audio at their own pace (EAS monitoring, Icecast streaming, web streaming)

When a subscriber's queue fills up (default: 100 chunks), the oldest chunks are automatically dropped to make room for new ones.

## Common Scenarios with High Drop Rates

### 1. Cold Start / Reconnecting Clients (Most Common)
When the audio service starts or network streaming clients reconnect:
- Buffer fills up quickly with initial audio
- Streaming clients aren't connected yet
- Old chunks are dropped as new ones arrive
- **Drop rate can be 90%+ temporarily**
- **This is normal and self-correcting**

### 2. Network Streaming Clients
Icecast/web streaming subscribers that:
- Disconnect and reconnect frequently
- Have slow network connections
- Experience buffering issues

### 3. Inactive Subscribers
Subscribers registered but not actively consuming audio:
- The 'controller-legacy' subscriber in the example
- May not be reading audio chunks fast enough
- Queue fills and older chunks are dropped

## When to Be Concerned

High drop rates are **NOT a problem** unless you experience:
- ❌ Audio quality issues in broadcasts
- ❌ Missing EAS alerts
- ❌ Frequent disconnections
- ❌ System performance degradation

If none of these occur, the system is working as designed.

## Understanding the Numbers

From the example log:
```
total published: 22479, dropped: 20479
```

- **Published**: Total chunks broadcast since service start (cumulative)
- **Dropped**: Total chunks dropped across ALL subscribers (cumulative)
- **Drop Rate**: 20479/22479 = 91% (high but normal for cold start)

This counter is **cumulative since service start** and will naturally grow over time.

## Tuning (Advanced)

If you need to adjust the behavior, you can modify the queue size in the audio service configuration:

```python
# In BroadcastQueue initialization
max_queue_size = 100  # Default, increase if needed
```

**Larger queue size**:
- ✅ Fewer drops during temporary slowdowns
- ❌ More memory usage
- ❌ Longer latency for real-time monitoring

**Smaller queue size**:
- ✅ Lower memory usage
- ✅ More responsive to real-time changes
- ❌ More frequent drops

## Monitoring Recommendations

1. **Watch for audio quality issues** - the real indicator of problems
2. **Check subscriber list** - remove unused subscribers
3. **Monitor system resources** - CPU/memory usage
4. **Review logs for errors** - broken pipes, connection failures

## Technical Details

The broadcast queue implements a **FIFO (First-In-First-Out) circular buffer**:
- When queue is full, oldest chunk is removed
- New chunk is added to the end
- This ensures real-time audio processing continues uninterrupted
- No subscriber can block the audio pipeline

This design is industry-standard for real-time audio/video streaming systems.

## Related Files

- `app_core/audio/broadcast_queue.py` - Broadcast queue implementation
- `app_core/audio/ingest.py` - Audio pump and source management
- `app_core/audio/icecast_output.py` - Network streaming subscriber

## Summary

**Dropped packets in the audio broadcast queue are a feature, not a bug.** They ensure that:
1. Real-time audio processing never blocks
2. Slow consumers don't affect fast consumers
3. The system remains responsive under all conditions
4. Network issues don't crash the audio pipeline

Focus on audio quality and system functionality, not the drop counter.
