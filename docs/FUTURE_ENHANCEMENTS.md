# Future Enhancements

This document tracks planned future enhancements for EAS Station. These are features that would improve the system but are not required for current functionality.

## Priority: Medium

### 1. Redis Command Queue for Radio Coordination
**File:** `poller/cap_poller.py:883`
**Status:** Planned

**Description:**
Migrate radio capture coordination to use Redis command queue pattern for containerized deployments.

**Current State:**
Radio captures from CAP poller are currently disabled in containerized deployments due to USB access limitations.

**Proposed Solution:**
- Send capture requests to sdr-service via Redis (`sdr:commands`)
- Receive capture results via Redis (`sdr:command_result:{command_id}`)
- See `docs/troubleshooting/CONTAINERIZATION_FIXES.md` for architecture details

**Benefits:**
- Enable radio capture coordination in containerized deployments
- Better separation of concerns
- Improved fault tolerance

---

### 2. Full Alert Processing Pipeline
**File:** `app_core/eas_processing.py:71`
**Status:** Partial Implementation

**Description:**
Expand the alert processing logic to include a complete end-to-end workflow.

**Current State:**
Basic alert logging is implemented. Alerts are received and logged successfully.

**Planned Features:**
1. Generate EAS message (create EASMessage record)
2. Synthesize audio (SAME header + attention signal + message)
3. Queue for broadcast
4. Send notifications (LED, VFD, push notifications, etc.)
5. Update alert status with processing results

**Benefits:**
- Complete automated alert workflow
- Multi-channel notification support
- Comprehensive audit trail

---

## Priority: Low

### 3. Historical Health Tracking for EAS Monitor
**File:** `app_core/audio/eas_monitor.py:757`
**Status:** Enhancement

**Description:**
Track EAS monitor health metrics over time for trend analysis and diagnostics.

**Current State:**
`get_health_history()` method returns only current state snapshot.

**Proposed Features:**
- Time-series storage of health metrics
- Configurable retention period
- Health trend visualization
- Historical health score analysis

**Benefits:**
- Better diagnostics for intermittent issues
- Performance trend monitoring
- Predictive maintenance capabilities

---

## Contributing

If you'd like to implement any of these enhancements, please:
1. Create an issue on GitHub referencing this document
2. Discuss the approach in the issue before starting work
3. Submit a pull request with tests and documentation

## Archive

When an enhancement is completed, move it to this section with:
- Implementation date
- Pull request number
- Brief summary of final approach
