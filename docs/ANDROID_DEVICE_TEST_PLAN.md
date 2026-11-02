# Sindhi Digital Classroom (SDC) — Physical Android Device Test Protocol

**Project:** Sindhi Digital Classroom (SDC)  
**Document ID:** SDC-TEST-AND-04  
**Date:** 2026-10-16  
**Audience:** Field Deployment Engineers, SELD School IT Monitors, QA Engineers  
**Target Hardware:** Low-cost Android tablets and smartphones utilized in rural Sindh schools  
**Verification Status:** **BLOCKED (Awaiting Physical Pilot Hardware)**  
*Note: In compliance with strict audit requirements, all metrics herein define target thresholds and test procedures. Zero simulated or fabricated device measurements are reported.*

---

## 1. Scope & Objective

SDC is designed as an offline-capable Progressive Web Application (PWA) supporting students in Classes 6–10 across rural Sindh. Because rural schools experience frequent power blackouts and nonexistent or intermittent cellular coverage, the software must function reliably on low-resource Android hardware without active network connectivity.

This protocol defines the exact test battery to execute on physical devices before greenlighting broad classroom rollouts.

---

## 2. Target Device Profiles

Testing must be executed across at least two representative device tiers:

| Parameter | Device Tier 1: Ultra-Low-Spec (Minimum Baseline) | Device Tier 2: Standard Pilot Tablet |
| :--- | :--- | :--- |
| **Example Models** | Infinix Smart 6 / 7, QMobile, Sparx, Itel A60 | Samsung Galaxy Tab A7 Lite, Lenovo Tab M8 / M10 |
| **SoC / Chipset** | Unisoc SC9863A / MediaTek Helio A22 | MediaTek Helio P22T / Unisoc T610 |
| **RAM** | **2 GB RAM** (Android Go Edition) | **3 GB – 4 GB RAM** (Standard Android) |
| **Internal Storage** | 32 GB eMMC 5.1 (≤ 6 GB free user storage) | 32 GB – 64 GB |
| **OS Version** | Android 10 (Go Edition) / Android 11 (Go Edition) | Android 11 / 12 / 13 |
| **Browser Runtime** | Android System WebView / Google Chrome 95+ | Google Chrome 110+ / Microsoft Edge |
| **Screen & PPI** | 6.5" 720x1600 (270 ppi), 60Hz | 8.0" or 8.7" 800x1340 (179 ppi) |

---

## 3. Test Environment Configurations

Each test scenario must be evaluated under the following controlled network conditions:

1. **ENV-A: Fully Offline (Airplane Mode)**
   - Wi-Fi Disabled, Mobile Data Disabled, Bluetooth Disabled.
   - Used to verify IndexedDB retrieval, service worker cache response, and transcript search.
2. **ENV-B: Intermittent Edge Connection (Rural 2G/3G Simulation)**
   - Bandwidth throttled to 256 kbps down / 64 kbps up; 400ms latency; 5% random packet loss.
   - Simulates patchy cellular tower coverage in rural talukas.
3. **ENV-C: Local School Server (Intranet Wi-Fi)**
   - Local access point connected to a Raspberry Pi 4 / localized desktop school server at `http://192.168.x.x:8000` with no upstream internet.

---

## 4. Test Battery & Execution Procedures

### Protocol 1: PWA Installation, Cold Launch, and Shell Responsiveness
- **Objective:** Verify PWA installs correctly and launches from Android home screen without internet.
- **Procedure:**
  1. Open Chrome on Android, browse to SDC web root.
  2. Tap browser menu > *"Add to Home screen"* (or tap the Sindhi PWA install prompt).
  3. Verify app icon and splash screen appear with Sindhi title *"سنڌي ڊجيٽل ڪلاس روم"*.
  4. Enable Airplane Mode. Force-stop the browser app via Android App Info.
  5. Tap the home screen SDC app icon to initiate cold launch.
- **Pass / Fail Thresholds:**
  - **Cold Launch Time:** Application shell renders within **≤ 2.5 seconds** (Target: ≤ 2.0s).
  - **Memory Usage:** Heap allocation remains below **80 MB** during launch.
  - **Layout:** UI renders in full Right-to-Left (`dir="rtl"`) with proper Noto Sans Arabic typography.

### Protocol 2: Offline Unit Pack Download & Storage Footprint
- **Objective:** Verify unit packs download without exhausting device storage or causing out-of-memory errors.
- **Procedure:**
  1. Connect to Wi-Fi. Log in as Student (`STU-101`).
  2. Select Class 6 Science Unit 1 (*Photosynthesis*).
  3. Tap *"آف لائن پيڪ ڊائونلوڊ ڪريو (Save Unit Offline)"*.
  4. Measure download elapsed time, network transfer bytes, and IndexedDB storage size via Chrome Remote Debugging (`chrome://inspect`).
- **Pass / Fail Thresholds:**
  - **Metadata & Transcript Bundle Size:** **≤ 500 KB** (JSON payload).
  - **Full Unit with Demo Media:** **≤ 30 MB**.
  - **Completion Time on 3G:** **≤ 45 seconds**.
  - **Toast Feedback:** Visual confirmation toast in Sindhi confirms download completion.

### Protocol 3: Offline Playback, Video Quiz Popups & Audio-Only Mode
- **Objective:** Verify video plays smoothly, pauses at question timestamps, and survives low memory pressure.
- **Procedure:**
  1. Enable Airplane Mode. Open downloaded Unit 1.
  2. Start video playback. Observe playback frame rate and audio sync.
  3. Verify video automatically pauses at question marker (`timestamp_seconds = 120s`).
  4. Answer question 1; skip question 2. Verify answer feedback displays in Sindhi.
  5. Tap *"رڳو آواز ٻڌو (Audio-Only Mode)"*. Verify video track dims/hides while audio stream continues seamlessly.
- **Pass / Fail Thresholds:**
  - **Video Frame Drops:** ≤ 5 dropped frames per minute at 240p/360p.
  - **Memory Pressure:** Browser process memory must not trigger Android LMK (Low Memory Killer) crashes on 2GB RAM devices.
  - **Popup Latency:** Quiz overlay displays within **≤ 200ms** of video pause.

### Protocol 4: Offline Lesson Transcript Search (AI Tutor Fallback)
- **Objective:** Ensure student can query lesson topics when internet is unavailable.
- **Procedure:**
  1. With Airplane Mode enabled, open AI Tutor drawer.
  2. Type Sindhi search term *"روشني"* into input box and tap send.
  3. Type out-of-scope term *"سياست"* and tap send.
- **Pass / Fail Thresholds:**
  - **Relevant Query:** Returns matched STBB lesson transcript snippet with clickable video timestamp link in **≤ 500ms**. Tapping link jumps video to timestamp.
  - **Irrelevant Query:** Returns standardized refusal message in Sindhi: *"معاف ڪجو، مان رڳو سنڌ ٽيڪسٽ بڪ بورڊ جي نصابي سبقن بابت مدد ڪري سگهان ٿو."*
  - **Crash Prevention:** Zero uncaught JavaScript errors in console.

### Protocol 5: Local Storage Persistence across Browser Kills
- **Objective:** Ensure student progress and queued quiz attempts survive unexpected browser closure or battery shutdown.
- **Procedure:**
  1. Answer 2 quiz questions offline. Note current playback position (e.g. 180s).
  2. Force-kill the browser via Android task switcher (`Swipe to dismiss`) or trigger device reboot.
  3. Reopen SDC PWA in Airplane Mode.
  4. Inspect video playback bookmark and IndexedDB `sync_queue` table.
- **Pass / Fail Thresholds:**
  - **Bookmark Recovery:** Video playback resumes at the saved position (± 2 seconds).
  - **Queue Retention:** Unsynced attempts remain safely preserved in IndexedDB `sync_queue` partitioned by student ID.

### Protocol 6: Background Synchronization upon Network Reconnection
- **Objective:** Ensure queued offline attempts sync idempotently when connectivity returns.
- **Procedure:**
  1. Disable Airplane Mode (reconnect to Wi-Fi).
  2. Observe automatic synchronization triggered by `window.online` event.
  3. Verify toast notification confirms synced attempt count.
  4. Query server endpoint `/api/dashboards/student?user_id=usr-stu-101` to verify attempt records.
  5. Disconnect and reconnect Wi-Fi again to test retry handling.
- **Pass / Fail Thresholds:**
  - **Sync Duration:** Completed within **≤ 3 seconds** for queues of 10 items.
  - **Queue Cleared:** IndexedDB `sync_queue` store is emptied after successful 200 OK server response.
  - **Zero Duplicates:** Server SQLite `attempts` table contains exactly 1 row per attempt (enforced by primary key idempotency).
  - **Monotonic Progress:** Student playback progress does not rewind to earlier seconds.

### Protocol 7: Shared Device Account Switching & Privacy Protection
- **Objective:** Verify privacy isolation when multiple students share a single school tablet.
- **Procedure:**
  1. Student A (`STU-101`) solves quiz and queues progress offline.
  2. Tap *"اڪائونٽ تبديل ڪريو (Switch User)"* and switch to Student B (`STU-102`) or Teacher (`TCH-HYD-01`).
  3. Open IndexedDB inspector or student dashboard.
- **Pass / Fail Thresholds:**
  - Outgoing student's offline queue is flushed before account switch.
  - Student B cannot see Student A's scores, streak, or quiz answers.
  - Header user badge immediately updates to reflect the active identity.

### Protocol 8: Touch Target Usability & Sindhi Typography
- **Objective:** Validate accessibility and readability on small 6.5" displays.
- **Pass / Fail Thresholds:**
  - **Touch Targets:** All interactive buttons (`.btn-ctrl`, `.btn-send`, `.lesson-card`, quiz options) have a minimum clickable area of **48 x 48 px**.
  - **Sindhi Font Rendering:** Sindhi characters with unique diacritics (ڳ, ڱ, ڄ, ڃ, ڦ, ڇ, ڌ, ڍ, ٿ, ٽ) render cleanly without broken glyphs or overlapping diacritical marks.
  - **Directionality:** All layout containers maintain `direction: rtl` with proper alignment.

---

## 5. Physical Device Test Execution Sheet Template

When physical hardware becomes accessible during the pilot, field testers must complete the following record:

```text
================================================================================
SDC PHYSICAL ANDROID FIELD TEST RECORD
================================================================================
Test Date & Time:       ___________________________
Tester Name:            ___________________________
School Name & Code:     ___________________________

DEVICE UNDER TEST:
- Manufacturer & Model: ___________________________
- Android OS Version:   ___________________________ (e.g. Android 11 Go)
- Total RAM / Free RAM: ___________________________
- Browser & Version:    ___________________________ (e.g. Chrome 114.0)
- Screen Resolution:    ___________________________

TEST PROTOCOL RESULTS:
1. PWA Cold Launch Time (s):              [   ] s     (Threshold: <= 2.5s)
2. Unit Pack Download Time (s):           [   ] s     (Threshold: <= 45s)
3. Offline Unit Opening Time (s):         [   ] s     (Threshold: <= 1.5s)
4. Video 240p Playback Stability:         [ PASS / FAIL ] Drops: [   ]
5. Audio-Only Mode Toggle:                [ PASS / FAIL ]
6. Offline Video Quiz Popup & Answer:     [ PASS / FAIL ]
7. Offline Transcript Search:             [ PASS / FAIL ] Latency: [   ] ms
8. Browser Kill & Bookmark Recovery:      [ PASS / FAIL ] Position: [   ] s
9. Reconnection Auto-Sync Duration:       [   ] s     (Threshold: <= 3.0s)
10. Duplicate Ingestion Prevention:       [ PASS / FAIL ]
11. Shared-Device Account Isolation:      [ PASS / FAIL ]
12. Sindhi RTL Font Diacritics Quality:   [ PASS / FAIL ]

ANOMALIES & OBSERVATIONS:
________________________________________________________________________________
________________________________________________________________________________
```

---

## 6. Current Pilot Readiness Verdict regarding Physical Hardware

- **Physical Android Test Status:** **BLOCKED**
- **Rationale:** Physical low-end Android hardware is not connected to the current development runner. Fabricated benchmarks are strictly forbidden by audit protocol.
- **Mitigation:** The software has passed all 37 backend and offline integration unit tests. Once physical pilot devices are provided by SELD, field engineers will execute this document's protocol before open classroom release.
