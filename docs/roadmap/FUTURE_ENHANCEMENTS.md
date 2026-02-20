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
- Use Redis command queue pattern for better separation of concerns

**Benefits:**
- Enable radio capture coordination in containerized deployments
- Better separation of concerns
- Improved fault tolerance

---

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

### Full Alert Processing Pipeline
**File:** `app_core/eas_processing.py`
**Completed:** February 2026

**Summary:**
Implemented `process_eas_alert()` as a fully functional standalone entry point for
the broadcast pipeline. The function normalizes both dict and object alert inputs,
loads EAS config and location settings from the database, and delegates to
`auto_forward_ota_alert()` for the full pipeline: cross-source deduplication,
SAME FSK audio generation, EASMessage record creation, BroadcastQueue publishing,
GPIO relay activation, and email/SMS notification dispatch.

Also fixed `_extract_message_id()` in `eas_monitor.py` to correctly extract the
`record_id` from the nested `broadcast_detail` dict returned by
`forward_alert_to_api()`, ensuring `ReceivedEASAlert.generated_message_id` is
properly populated for every successful broadcast.
