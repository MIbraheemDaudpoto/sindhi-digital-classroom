# SDC Pilot — Raspberry Pi 5 Field Deployment & Operations Guide
**Target Hardware:** Raspberry Pi 5 (8 GB RAM, ARM64, Debian Bookworm)  
**Power Infrastructure:** 12V Solar panel array + Charge Controller + Battery + 5V/5A Buck Converter / UPS Hat  
**Network Architecture:** Zero-internet local Wi-Fi router (or internal hostapd Wi-Fi Access Point)  
**Curriculum Scope:** Class 6 General Science (Sindhi Medium, Sindh Textbook Board curriculum)  
**Client Target:** Low-cost 1–2 GB RAM Android tablets/smartphones accessing the offline PWA  

---

## 1. System Architecture & Zero-Cloud Principles
The Sindhi Digital Classroom (SDC) Pilot server is an ultra-reliable, zero-internet classroom appliance:
- **FastAPI Core**: Lightweight ASGI server running on Python 3.11+ ARM64, bound to `0.0.0.0:8000`.
- **SQLite Engine (WAL Mode)**: Full-text BM25 index over 90 curriculum chunks and 201 science glossary terms using SQLite FTS5 (`unicode61` tokenizer). Consumes only ~3.34 MB storage and < 90 MB RAM.
- **Client PWA Shell**: Vanilla HTML5/CSS3/ES6+ JavaScript with Service Worker caching and client-side IndexedDB caching.
- **YouTube Media Strategy**: SOS educational video titles and durations are indexed offline. When local school Wi-Fi has upstream internet, students can watch videos embedded directly in the classroom. When offline, video players degrade gracefully to title-only with an explicit `"Watch when online"` notification.

---

## 2. Hardware Assembly & Solar Power Management

### 2.1 Bill of Materials
1. **Server Unit:** Raspberry Pi 5 (8 GB or 4 GB RAM) with Active Cooler and aluminum case.
2. **Storage:** 32 GB or 64 GB SanDisk Extreme / High Endurance MicroSD card.
3. **Power Source:**
   - Option A: 12V 100W/150W Solar Panel + 12V 10A PWM/MPPT Charge Controller + 12V 20Ah–50Ah Lead-Acid/LiFePO4 Deep-Cycle Battery + 12V-to-5V 5A (27W USB-C PD) Step-Down Buck Converter.
   - Option B: Official Raspberry Pi 27W USB-C Power Supply connected to a commercial line UPS.
4. **Local Network:**
   - Option A (Recommended): TP-Link TL-WR840N or Mercusys Wi-Fi router (WAN disconnected).
   - Option B: Raspberry Pi 5 Internal Wi-Fi configured via `deploy/setup_offline_hotspot.sh`.

### 2.2 Solar Power & Brownout Protection
- The Pi 5 consumes ~5W–12W under load. In rural Sindh schools, power cuts occur during dusk and battery depletion.
- `deploy/solar_power_monitor.py` runs as `sdc-power-guard.service`. When a low-voltage signal is received on GPIO pin 4 (or low battery threshold), it executes:
  1. `PRAGMA wal_checkpoint(TRUNCATE);` to flush all pending SQLite writes.
  2. Stops the FastAPI service cleanly.
  3. Executes `sync` and powers down the Pi safely (`shutdown -h now`).

---

## 3. Automated One-Command Installation

On the Raspberry Pi 5 terminal (logged in as user `pi`):

```bash
cd /home/pi
git clone https://github.com/your-org/sindhi-digital-classroom.git sdc-pilot
cd sdc-pilot
chmod +x deploy/install_pi5.sh
sudo bash deploy/install_pi5.sh
```

---

## 4. Standalone Hotspot Setup (No External Router)

If an external router is not available in the rural school, run the automated hotspot configurator:

```bash
sudo bash deploy/setup_offline_hotspot.sh
```
- **Wi-Fi SSID:** `Sindhi_Digital_Classroom`
- **Wi-Fi Password:** `sindhiclassroom`
- **Gateway IP:** `192.168.4.1`
- **Classroom URL:** `http://192.168.4.1:8000/classroom`

---

## 5. Field Technician Diagnostics

To verify the system at any time, run:

```bash
bash deploy/verify_installation.sh
```

Sample output:
```
[1/6] Checking sdc-pilot.service status... ACTIVE (OK)
[2/6] Checking Port 8000 listening... LISTENING (OK)
[3/6] Checking SQLite WAL mode... WAL MODE (OK)
[4/6] Verifying canonical data tables... CHUNKS=90, GLOSSARY=201, EXERCISES=39, VIDEOS=113 (OK)
[5/6] Testing GET http://127.0.0.1:8000/api/health... HEALTHY (OK)
[6/6] Testing GET http://127.0.0.1:8000/classroom... HTTP 200 (OK)
ALL DIAGNOSTIC CHECKS PASSED! System is ready for class.
```

---

## 6. Client Tablet Connection (Android 1–2 GB RAM)

1. Turn on the student tablet / phone and connect to Wi-Fi `Sindhi_Digital_Classroom`.
2. Open Chrome and browse to `http://<pi-ip>:8000/classroom` (or `http://192.168.4.1:8000/classroom`).
3. Tap **Menu (⋮) $\to$ Add to Home Screen / Install App**.
4. The icon **SDC سنڌي** will appear on the Android home screen and work offline even during temporary Wi-Fi disconnects.

---

## 7. Performance Benchmarks on Raspberry Pi 5 (ARM64)

- **Total Ingested Data:**
  - 90 Curriculum Chunks (Chapters 1–12)
  - 201 Science Glossary Terms
  - 39 Exercises, SLOs & Review Questions
  - 113 Sindh Online School Video Lectures
- **Database Size:** ~3.34 MB (Zero-bloat SQLite in WAL mode)
- **BM25 Search Latency:**
  - p50: ~7.59 ms
  - p95: ~24.07 ms
  - p99: ~45.75 ms
- **FastAPI Memory Footprint:** < 90 MB RAM.
- **Pi 5 CPU Utilization:** < 5% during concurrent 15-student search bursts.
