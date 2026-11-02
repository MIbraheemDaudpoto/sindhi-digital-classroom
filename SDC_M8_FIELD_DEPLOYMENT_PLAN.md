# SDC Pilot — M8 Field Deployment & Pilot Evaluation: Implementation Plan

## Executive Overview
Following the successful build and verification of the M5/M6 offline RAG system (where all 6 acceptance tests passed), **M8: Raspberry Pi 5 Field Deployment & Pilot Evaluation** prepares the entire platform for real-world field pilot testing in rural Sindh school labs.

The field environment has unique physical and technical constraints:
- **Server:** Raspberry Pi 5 (8 GB RAM, ARM64, Debian Bookworm).
- **Power:** 12V Solar panel array + Charge Controller + Battery / 12V-to-5V 5A step-down or USB-PD UPS, prone to dusk/dawn power fluctuations.
- **Connectivity:** 100% zero internet; local standalone Wi-Fi AP (TP-Link/D-Link or Pi internal hotspot `hostapd` + `dnsmasq`).
- **Clients:** Low-cost 1–2 GB RAM Android tablets and phones accessing the offline PWA.

---

## Detailed Gap Analysis & Plan of Work

### Phase 1: Deployment Hardening & Package Correction
#### 1.1 Gaps in Current Deployment Artifacts
- **Missing OS Dependencies in `install_pi5.sh`:**
  - Need `python3-dev`, `build-essential`, `libsqlite3-dev` (ensures FTS5 compile features are standard on minimal ARM64 images).
  - Need `dnsmasq`, `hostapd`, `iptables` for automated captive hotspot mode if external router is absent.
  - Need `jq`, `ufw`, `logrotate`.
- **Systemd Service Hardening (`deploy/sdc-pilot.service`):**
  - Add explicit memory resource limits (`MemoryMax=2G`, `MemoryHigh=1.5G`, `CPUQuota=200%`) so the application never exceeds budget or starves the OS.
  - Add `Restart=on-failure`, `RestartSec=3s`, `WatchdogSec=30s`.
  - Add environment overrides (`DATABASE_PATH=/home/pi/sdc-pilot/data/sdc_platform.db`, `PORT=8000`, `HOST=0.0.0.0`).
  - Add syslog identifier and standard output/error logging configuration.
- **Solar Power Management & Battery Safe Shutdown:**
  - Provide `deploy/solar_power_monitor.py` & systemd service `deploy/sdc-power-guard.service` that monitors battery/UPS voltage via GPIO / INA219 / NUT / serial ADC or gracefully shuts down when low-battery signal is triggered.
  - Prevent SD card corruption by enabling overlayfs / read-only root or SQLite WAL with safe flush triggers.
- **Field Technician Tooling:**
  - Provide `deploy/verify_installation.sh` that checks system health, WAL mode, port binding, and runs the acceptance test suite in one keystroke.
  - Provide `deploy/setup_offline_hotspot.sh` for optional direct Pi 5 Wi-Fi Access Point deployment without an external router.

### Phase 2: RAG Accuracy Evaluation Harness
#### 2.1 Synthetic Test Dataset (40 Grounded Questions)
Grounding in the 90 canonical chunks and covering all 12 curriculum chapters:
- **Chapter 1 (Cells & Microscope):** 4 questions (cell structure, microscope parts, unicellular vs multicellular, tissues to organs) + Heh variants (`گهرڙو` vs `گھرڙو`).
- **Chapter 2 (Sense Organs):** 4 questions (five senses, eye parts `ڪورنيا / بلور / تارو`, ear structure, skin/smell) + `اک` vs `اڪ` edge cases.
- **Chapter 3 (Photosynthesis & Respiration):** 3 questions (chlorophyll, stomata, oxygen cycle).
- **Chapter 4 (Environment & Interactions):** 3 questions (ecosystem, food chain, predators/prey).
- **Chapter 5 (Matter, Atoms & Molecules):** 3 questions (matter states, atom structure, elements vs compounds).
- **Chapter 6 (Air):** 3 questions (composition of air, oxygen, nitrogen importance).
- **Chapter 7 (Solutions - Blank PDF Provenance):** 3 questions (solute vs solvent, suspension, saturated solutions) checking for mandatory blank-PDF warning banner and provenance citation.
- **Chapter 8 (Energy):** 3 questions (forms of energy, kinetic vs potential, law of conservation of energy).
- **Chapter 9 (Light):** 3 questions (reflection, shadows, speed of light, pinhole camera).
- **Chapter 10 (Sound):** 3 questions (sound waves, vibration, speed of sound in mediums).
- **Chapter 11 (Magnetism):** 3 questions (magnetic poles, magnetic field, electromagnets).
- **Chapter 12 (Space & Solar System):** 3 questions (planets, asteroids, solar system orbit).
- **English & Cross-lingual Queries:** 4 bilingual queries verifying English query parsing and retrieval.

#### 2.2 Evaluation Metrics & Automated Script (`tests/evaluate_rag_accuracy.py`)
- **Metrics Computed:**
  1. **Retrieval Recall@3:** Whether the gold-standard chunk ID is among the top 3 retrieved chunks.
  2. **Citation Accuracy Rate:** Percentage of responses with correctly formatted `"PDF X (printed Y)"` citations matching the ground truth.
  3. **Faithfulness & Groundedness Score:** Percentage of generated claims supported by retrieved context without hallucination.
  4. **Sindhi Script Language Consistency:** Ensuring Sindhi queries receive valid Sindhi answers.
  5. **Chapter 7 Provenance Compliance Rate:** 100% adherence to displaying the blank-PDF warning when Ch7 is queried.
- **Reporting:** Tabulated Markdown report and JSON benchmark artifacts.

### Phase 3: Field Pilot Preparation & Documentation
#### 3.1 Pilot Evaluation Protocol (`docs/PILOT_EVALUATION_PROTOCOL.md`)
- Target success criteria (RAG accuracy $\ge$ 80%, offline uptime 100%, p95 latency < 50ms).
- 4-week timeline (Week 1: Baseline & Onboarding; Week 2: Student independent exploration; Week 3: Teacher-guided review; Week 4: Summative assessment & feedback).
- Privacy-first anonymized local search logging schema (no student names or phone numbers stored).
- Standard Operating Procedure (SOP) for teacher fallback/rollback.

#### 3.2 Field Technician Checklist (`docs/FIELD_TECHNICIAN_CHECKLIST.md`)
- Step-by-step physical hardware assembly (Pi 5, active cooler, aluminum case, 12V solar charge controller, DC-DC converter).
- MicroSD card preparation, static IP assignment, and router SSID setup.
- Verification checklist with terminal commands and expected outputs.
- Field diagnostic decision tree (e.g., LED code interpretations, power cut recoveries, client connection troubleshooting).

#### 3.3 Teacher Training Guide (`docs/TEACHER_TRAINING_GUIDE.md`)
- Bilingual (Simple English + Sindhi educational phrases: سنڌي هدايتون).
- How to power on/off the appliance with one button.
- Walkthrough of the 4 screens (Search/Ask, Glossary, Exercises, Video Classroom).
- Interpreting the dual citations ("PDF X (printed Y)") so teachers can map answers directly to physical textbooks distributed by the Sindh Textbook Board (Jamshoro).
- Troubleshooting simple issues (clearing browser cache, reconnecting Wi-Fi).

---

## Deliverables Summary

| Artifact | File Path | Status |
|---|---|---|
| Hardened systemd Service | `deploy/sdc-pilot.service` | Update / Harden |
| Corrected Pi 5 Installer | `deploy/install_pi5.sh` | Update / Expand |
| Automated Health Verification | `deploy/verify_installation.sh` | New Script |
| Standalone Hotspot Configurator | `deploy/setup_offline_hotspot.sh` | New Script |
| Solar Power Guard Service | `deploy/solar_power_monitor.py` | New Service |
| Comprehensive Deployment Guide | `README_PI5_SDC_PILOT.md` | Update / Enrich |
| RAG Accuracy Evaluation Harness | `tests/evaluate_rag_accuracy.py` | New Benchmark |
| Synthetic Evaluation Dataset | `data/eval/rag_synthetic_eval_set.json` | New Dataset |
| Pilot Evaluation Protocol | `docs/PILOT_EVALUATION_PROTOCOL.md` | New Doc |
| Field Technician Checklist | `docs/FIELD_TECHNICIAN_CHECKLIST.md` | New Doc |
| Teacher Training Guide | `docs/TEACHER_TRAINING_GUIDE.md` | New Doc |

---

## Verification & Execution Steps
1. Create the evaluation dataset and run `tests/evaluate_rag_accuracy.py`.
2. Inspect the per-chapter retrieval recall, citation formatting, and faithfulness scores.
3. Update and validate deployment scripts and systemd units for POSIX compliance and ARM64 readiness.
4. Verify all existing acceptance tests continue passing without regression.
5. Compile comprehensive M8 deployment and evaluation report.
