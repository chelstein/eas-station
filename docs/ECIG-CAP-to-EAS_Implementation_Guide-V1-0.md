# ECIG Recommendations for a CAP EAS Implementation Guide

**EAS CAP Industry Group (ECIG) — EAS-CAP Implementation Guide Subcommittee**
**Version 1.0 — 17 May, 2010**

> Original PDF: [`ECIG-CAP-to-EAS_Implementation_Guide-V1-0.pdf`](./ECIG-CAP-to-EAS_Implementation_Guide-V1-0.pdf)
> © 2010 EAS-CAP Industry Group. All Rights Reserved.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [General Requirements and Specifications](#2-general-requirements-and-specifications)
3. [Implementation Guide Requirements and Specifications](#3-implementation-guide-requirements-and-specifications)
4. [Notes for Originators and Origination Software](#4-notes-for-originators-and-origination-software)
5. [CAP/EAS Examples](#5-capeas-examples)
6. [CAP-to-EAS Validation Criteria](#6-cap-to-eas-validation-criteria)

---

## 1. Introduction

### 1.1 Purpose

Public warnings intended for transmission over the Emergency Alert System (EAS) can be encoded in Common Alerting Protocol (CAP) messages in various ways. The EAS-CAP Industry Group (ECIG) produced this Implementation Guide to reduce areas of uncertainty in how an alert will be presented to the public via CAP/EAS, so that originators and distributors of alerts can deliver the intended message to the public, regardless of the vendors or platforms involved.

**Core goal:** All CAP-to-EAS devices MUST generate the EXACT same EAS message for a given CAP message.

### 1.4 Terminology

Key words (per RFC 2119): **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, **OPTIONAL**.

### 1.5 References

- [3] FCC EAS Rules: 47 CFR Part 11
- [4] CAP v1.2 specification (OASIS)
- [5] CAP v1.2 USA IPAWS Profile v1.0 (OASIS)

---

## 2. General Requirements and Specifications

### 2.1.1 Specific mimeTypes

ECIG recommends these mimeTypes for audio resources:

```
audio/x-ipaws-audio-mp3
audio/x-ipaws-audio-wav
audio/x-ipaws-streaming-audio-mp3
```

### 2.1.2 EASText Parameter

ECIG recommends a new `EASText` CAP `<parameter>` element allowing originators to dictate the exact text for video crawl and TTS. If absent, text is derived from other CAP fields (see §3.6).

---

## 3. Implementation Guide Requirements and Specifications

### 3.2 EAS Alert Activations

An EAS activation comprises up to four elements:

1. **Header code** — Sent **three times**, with a **one-second pause after each** transmission.
2. **Attention signal** — Two-tone signal, used **if and only if** a message follows.
3. **Message** — Audio message following the attention signal.
4. **End of message (EOM)** — Sent **three times**, with at least a **one-second pause after each**.

### 3.3.1 Multiple Parameters

When multiple `<parameter>` elements have the same `valueName`, and the valueName is not meant to describe a list, recipients **SHALL** accept only the **first occurrence**.

---

### 3.4 Constructing the EAS Header Code from CAP IPAWS v1.0

#### 3.4.1.1 ORG (Originator)

The EAS Originator Code **SHALL** come from the CAP `<info><parameter>` block with `<valueName>` of `"EAS-ORG"`.

Valid originator codes (FCC Part 11.31(d)):

| Code | Description |
|------|-------------|
| `PEP` | Primary Entry Point System |
| `EAS` | Broadcast station or cable system |
| `WXR` | National Weather Service |
| `CIV` | Civil authorities |

> **Note:** `EAN` originator was removed in a 2002 update; do not use.

#### 3.4.1.2 EEE (Event Code)

The EAS Event Code **SHALL** be represented using `<info><eventCode>` with `<valueName>` of `"SAME"`. The value is **case sensitive** (uppercase). A CAP message without a SAME event code **SHALL NOT** be aired.

#### 3.4.1.3 PSSCCC (Location Codes)

Each EAS location code **SHALL** come from `<area><geocode>` with `<valueName>` of `"SAME"`. Rules:

- At least one `<geocode>` must be present.
- Only the **first 31 geocodes** are placed in the ZCZC string, **in the order encountered** (required for duplicate detection).
- `000000` indicates the entire United States and Territories.

#### 3.4.1.4 TTTT (Duration)

The EAS duration **SHALL** be calculated as `<info><expires>` minus `<alert><sent>`.

**TTTT is encoded in HHMM format** (e.g., `0100` = 1 hour, `0130` = 1 hour 30 min).

Rounding rules:

| Duration range | Valid values | Increment |
|----------------|-------------|-----------|
| 0 < duration ≤ 45 min | `0015`, `0030`, `0045` | 15 minutes |
| duration > 1 hour | `0100`, `0130`, `0200`, …, `9930` | 30 minutes |

- Round **UP** to the next permitted interval.
- If duration ≤ 0 → alert is **expired**, **SHALL be ignored**.
- FCC Part 11.31(c) caps most alerts at **0600** (6 hours).

#### 3.4.1.5 JJJHHMM (Issue Time)

Derived from `<alert><sent>` in ISO 8601 format. Julian day-of-year + UTC hour + UTC minute.

#### 3.4.1.6 LLLLLLLL (Station ID)

Always inserted by the EAS device; **not** specified by any CAP element. **SHOULD** be the call sign of the CAP-to-EAS device (up to 8 characters).

#### 3.4.1.7 Governor's Must-Carry

Messages where Governor's must-carry authority applies **SHALL** include:
```xml
<parameter>
  <valueName>EAS-Must-Carry</valueName>
  <value>True</value>
</parameter>
```
This overrides originator and event code filtering for automatic forwarding. Location filters and duplicate prevention still apply.

---

### 3.5 CAP EAS Audio Processing

#### 3.5.1 Audio Selection Priority

1. If `<resource>` with `<resourceDesc>` = `"EAS Broadcast Content"` is present → **SHALL use** that audio.
2. If no attached audio and device supports TTS → **SHALL** render TTS per §3.5.4.
3. If no TTS capability → send **EAS-codes-only** with no audio.
4. If a URI cannot be accessed within a **reasonable time** (≤2 minutes for download, ≤30 seconds for streaming) → fall back to TTS.

#### 3.5.2 Recorded Audio Specs

- **MP3:** mono, 64 kbit/s, preferably 22.05 kHz (or 44.1 kHz)
- **WAV:** mono, 16-bit PCM, 22.05 kHz
- `<resourceDesc>` value **SHALL** be `"EAS Broadcast Content"`
- FCC Part 11 **two-minute limit** on EAS audio **MUST** be enforced for all alerts **except EAN**.
- Text deletions indicated by `***` (three asterisks) **SHALL** be followed by a **one-second pause**.

#### 3.5.3 Streaming Audio Specs

- `<resourceDesc>` **SHALL** be `"EAS Broadcast Content"`.
- Streaming methods: **MP3 HTTP progressive-download** or **HTTP streaming MP3 server**.

#### 3.5.4 Text-to-Speech

- TTS audio **SHALL** be an exact translation of the Alert Text (see §3.6).
- Text deletions indicated by `***` **SHALL** be followed by a **one-second pause**.
- FCC Part 11 **two-minute (120-second) limit** applies, except for EAN.

---

### 3.6 Constructing Alert Text (TTS / Video Crawl)

Maximum text length: **1800 characters**.

#### 3.6.1 Whitespace Rule

Before adding any string to TTS or display output, the device **SHALL**:
1. Remove leading and trailing whitespace.
2. Replace all whitespace characters (space, form-feed, newline, carriage return, tab) with a single space.

#### 3.6.2 EASText Parameter

If `<parameter><valueName>EASText</valueName>` is present, the EAS receiver **SHALL** use its `<value>` verbatim as the alert text (for video crawl and TTS).

#### 3.6.3 FCC Required Text

The FCC requires alert text to include at minimum:

> A sentence containing the **Originator**, **Event**, **Location**, and **valid time period** constructed from the EAS ZCZC Header Code (FCC Part 11.51(d)).

**Example:**
```
A CIVIL AUTHORITY HAS ISSUED A HAZARDOUS MATERIALS WARNING FOR THE
FOLLOWING COUNTIES/AREAS: District of Columbia, DC; AT 5:34 PM ON
MAR 11, 2009 EFFECTIVE UNTIL 6:34 PM.
```

#### 3.6.4 Alert Text Construction

The complete alert text is assembled in this order:

```
[FCC Required Text]
[If EASText present: EASText value]
[Otherwise:]
  [Optional: "Message from " + <senderName>]
  [<description> content (partial if needed)]
  [<instruction> content (partial if needed)]
```

**Space allocation algorithm** when description + instruction exceed remaining space:
```python
half = (1800 - len(fcc_required_text + sender)) / 2
if len(description) < half:
    max_description = len(description)
    max_instruction = half + (half - max_description)
else:
    max_description = half
    if len(instruction) < half:
        max_instruction = len(instruction)
        max_description = half + (half - max_instruction)
    else:
        max_instruction = half
```

Text truncations **SHALL** be indicated by `***`.

> **ECIG does NOT recommend** using `<headline>` or `<areaDesc>` in the alert text display.

---

### 3.7 Languages

- A CAP-to-EAS device **SHALL** provide for a primary language specification.
- Multiple `<info>` blocks may be used for multiple languages.
- Each `<info>` block **SHOULD** contain a `<language>` element; default is `en-US`.
- If multiple `<info>` blocks in the same language exist, only the **first** is processed.
- TTS audio per language is limited to **120 seconds**. EOM is sent after the primary language, then additional languages follow.

---

### 3.8 CAP msgType Handling

| msgType | Action |
|---------|--------|
| `Alert` | Always processed for air. |
| `Update` | Remove queued original from air queue. If in-progress, MAY halt (MUST send EOM first). Then broadcast the Update. |
| `Cancel` | Log it. MUST NOT deliver cancelled message. If in-progress, complete normally — EOM MUST be aired. No `<info>` block needed. |
| `Ack`, `Error` | Not required to process or send. |

---

### 3.9 Test Messages

- CAP `<status>` of `Test`, `Exercise`, or `Draft` **MUST NOT** be placed on air.
- EAS test messages (RMT, RWT, NPT, DMO, NMN) **MUST** have `<status>` of `Actual` to go on air.

**Recommended fields for EAS on-air tests:**
```xml
<status>Actual</status>
<urgency>Unknown</urgency>
<severity>Minor</severity>
<certainty>Unknown</certainty>
```

---

### 3.10 Older CAP Protocol Versions

- When processing CAP 1.1 messages without an originator, **SHOULD** assume `CIV`.
- A `<geocode>` with `<valueName>` of **`FIPS6` SHOULD be accepted and handled as `SAME`**.

---

### 3.11 Duplicate Alert Handling

**CAP duplicate:** Same `<identifier>`, `<sender>`, and `<sent>`.

**EAS duplicate:** Byte-wise comparison of ZCZC strings, **excluding** the LLLLLLLL (Station ID) field.

Rules:
- Duplicate CAP messages: render only **one** to EAS.
- Once an EAS message is aired, duplicate EAS alerts **SHALL NOT** be automatically aired.
- If both CAP and EAS versions of an alert exist (neither aired), **SHOULD** prefer the CAP version.

---

## 4. Notes for Originators and Origination Software

1. `EAS-ORG` parameter **MUST** be provided.
2. A SAME event code **MUST** be provided (`<eventCode><valueName>SAME</valueName>`).
3. At least one `<geocode>` with `<valueName>` of `SAME` **MUST** be provided. Only first 31 are used.
4. EAS devices may round expiration times up to the nearest valid EAS duration.
5. `EASText` parameter MAY be provided for video crawl / TTS control.
6. `<areaDesc>` is **ignored** by EAS devices; location details should go in `<description>`.
7. Total alert text **MUST** be ≤ 1800 characters; TTS truncated at 120 seconds.
8. Audio MAY be provided in WAV or MP3 format; use MP3 over WAV.
9. EAS messages aired only if `<scope>` is `Public`.
10. EAS messages aired only if `<status>` is `Actual`.
11. `<msgType>` values processed for air: `Alert`, `Update`, `Cancel`.

---

## 5. CAP/EAS Examples

### 5.1 Hazardous Materials Warning — Example ZCZC String

```
ZCZC-CIV-HMW-011001+0100-0702334-LLLLLLLL-
```

**Generated alert text:**
```
A CIVIL AUTHORITY HAS ISSUED A HAZARDOUS MATERIALS WARNING FOR THE FOLLOWING
COUNTIES/AREAS: District of Columbia, DC; AT 5:34 PM ON MAR 11, 2009 EFFECTIVE
UNTIL 6:34 PM. Message from CAP alert central. [description] [instruction]
```

### 5.2 Required Monthly Test

```
ZCZC-CIV-RMT-053029-053031-053035-053033-053061+0100-0252000-LLLLLLLL-
```
- `<status>Actual</status>` — required for on-air broadcast
- `<urgency>Unknown</urgency>`, `<severity>Minor</severity>`, `<certainty>Unknown</certainty>`

### 5.3 National Emergency Action Notification (EAN)

```
ZCZC-PEP-EAN-000000+9930-0742256-LLLLLLLL-
```
- Originator: `PEP`; Location: `000000` (entire United States)
- Audio: live streaming MP3 resource

### 5.4 National Emergency Action Termination (EAT)

```
ZCZC-PEP-EAT-000000+0030-0752200-LLLLLLLL-
```

### 5.5 CAP System Test (status=Test — NOT aired)

```xml
<status>Test</status>  <!-- MUST NOT be broadcast -->
```

---

## 6. CAP-to-EAS Validation Criteria

### 6.5 Validation Order

1. **CAP conformance** — Legal XML format. Failure → **Rejected**.
2. **CAP/EAS validation:**
   - Missing required CAP+EAS elements → **Rejected**
   - Invalid EAS-compatible elements → **Rejected**
   - Missing optional EAS elements → **Ignored** (with defaults where defined)
3. **Acceptance** → further filtered by EAS rendering rules (event codes, FIPS, etc.)

### 6.6 Result States

| State | Action |
|-------|--------|
| **Rejected** | SHALL NOT process. MAY return `<msgType>Error`. |
| **Ignored** | SHALL NOT process. MAY return `<msgType>Ack` with `<note>Ignored`. |
| **Accepted** | MAY return `<msgType>Ack` with `<note>Accepted`. |

### 6.7 Required Elements for EAS Translation

**Alert block (all required):**
`<alert>`, `<identifier>`, `<sender>`, `<sent>`, `<status>`, `<msgType>`, `<scope>`

**Info block:**
`<info>`, `<eventCode>` (with `valueName=SAME`)

**Area block:**
`<area>`, `<geocode>` (with `valueName=SAME`, at least one)

**Conditional (if `<resource>` present):**
`<resourceDesc>`, `<mimeType>`, `<uri>`

**Additional IPAWS conformance requirements:**
`<alert><code>` containing `"IPAWSv1.0"`, `<info><expires>`, `<parameter><valueName>EAS-ORG`

### Validation Table — Key Mappings

| CAP Element | EAS Mapping | Constraint |
|-------------|-------------|------------|
| `<status>` | Filter | **SHALL** be `Actual` for on-air broadcast |
| `<scope>` | Filter | **SHALL** be `Public`; others **ignored** |
| `<msgType>` | Processing mode | `Alert`, `Update`, `Cancel` only |
| `<sent>` | JJJHHMM | Maps to EAS issue time |
| `<expires>` | TTTT | Duration = expires − sent, rounded up (HHMM format) |
| `<eventCode valueName=SAME>` | EEE | 3-letter SAME event code; required |
| `<parameter valueName=EAS-ORG>` | ORG | `EAS`, `CIV`, `WXR`, or `PEP`; required for IPAWS |
| `<geocode valueName=SAME>` | PSSCCC | Up to 31, order preserved; required |
| `<geocode valueName=FIPS6>` | PSSCCC | Treated as SAME (non-IPAWS systems, §3.10) |
| `<description>` | Alert text | Used in TTS/crawl after FCC Required Text |
| `<instruction>` | Alert text | Used in TTS/crawl after description |
| `<headline>` | — | **NOT used** in alert text |
| `<areaDesc>` | — | **NOT used** in alert text |
| `<senderName>` | Alert text (opt.) | Optional "Message from …" prefix |
| `<parameter valueName=EASText>` | TTS/crawl | **SHALL** use verbatim if present |
| `<parameter valueName=EAS-Must-Carry>` | Must-carry | Overrides event/originator filters |
