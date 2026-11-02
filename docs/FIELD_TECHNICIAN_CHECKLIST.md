# SDC Pilot — Field Technician Deployment & Operations Checklist
**Target Environment:** Rural Sindh School Lab (Offline Solar Powered Appliance)  
**Appliance:** Raspberry Pi 5 (8 GB RAM, ARM64)  
**Router:** Standalone Wi-Fi Router or Pi Internal Hotspot  

---

## 1. Pre-Deployment Kit Preparation (Before Leaving the City)

Ensure your deployment backpack contains:
- [ ] 1x Raspberry Pi 5 (8 GB RAM) with Active Cooler installed in metal chassis.
- [ ] 1x 32GB or 64GB SanDisk Extreme High-Endurance MicroSD card (pre-flashed with Raspberry Pi OS Bookworm ARM64 + SDC code).
- [ ] 1x Backup MicroSD card cloned with the exact same image.
- [ ] 1x 12V 100W/150W Monocrystalline Solar Panel + Mounting Brackets.
- [ ] 1x 12V 10A PWM or MPPT Solar Charge Controller.
- [ ] 1x 12V 20Ah–40Ah LiFePO4 or Deep-Cycle Gel Battery.
- [ ] 1x 12V-to-5V 5A (27W USB-PD) Buck Converter with USB-C termination.
- [ ] 1x Wi-Fi Router (TP-Link TL-WR840N or equivalent) + 12V DC power plug.
- [ ] 1x 1-meter Cat6 Ethernet patch cable.
- [ ] 1x Digital Multimeter (for solar panel & battery voltage verification).
- [ ] 1x Reference Android Tablet (1 GB or 2 GB RAM) for testing client connections.

---

## 2. On-Site Hardware Assembly & Solar Connection

Follow this strict sequence to prevent electrical damage to the controller or Pi:

```
[ Step 1: Connect Battery to Controller First ]
         |
         v
[ Step 2: Connect Solar Panel to Controller ]
         |
         v
[ Step 3: Connect 12V-to-5V Buck Converter to Battery/Load ]
         |
         v
[ Step 4: Connect USB-C Plug to Raspberry Pi 5 ]
```

> [!CAUTION]
> ALWAYS connect the 12V battery to the charge controller FIRST so the controller auto-detects 12V system voltage before you connect the high-voltage solar panel!

### Voltage Checks:
- Solar open-circuit voltage ($V_{oc}$): Expect $18\text{V} - 22\text{V}$ in sunlight.
- Battery terminal voltage: Expect $12.6\text{V} - 13.8\text{V}$ when charged.
- USB-C power output: Verify $5.1\text{V} \pm 0.1\text{V}$ before plugging into the Pi 5.

---

## 3. Wi-Fi Router & Network Configuration

### Option A: Using Standalone Wi-Fi Router (Recommended for 15+ Devices)
1. Power the router from the 12V battery line (most routers accept 9V–12V DC natively).
2. Connect Ethernet cable from Router LAN Port 1 to the Raspberry Pi 5 Ethernet port.
3. Access Router Settings (`192.168.1.1` or `192.168.0.1`):
   - **Wireless SSID:** `Sindhi_Digital_Classroom`
   - **Wireless Security:** WPA2-PSK (Passphrase: `sindhiclassroom`)
   - **LAN DHCP:** Reserve Static IP `192.168.1.100` for the Raspberry Pi MAC address.
   - **WAN Port:** Keep disconnected (No internet connection needed).

### Option B: Using Internal Pi 5 Hotspot (If no router available)
Run the automated hotspot setup script:
```bash
sudo bash deploy/setup_offline_hotspot.sh
```
The Pi 5 will broadcast SSID `Sindhi_Digital_Classroom` with IP `192.168.4.1`.

---

## 4. Software Deployment & System Verification

Open terminal on the Pi 5 and execute:

```bash
cd /home/pi/sdc-pilot
bash deploy/verify_installation.sh
```

### Verification Checklist:
- [ ] **Check 1:** `sdc-pilot.service` status is **ACTIVE**.
- [ ] **Check 2:** Port 8000 is **LISTENING** on all interfaces (`0.0.0.0:8000`).
- [ ] **Check 3:** SQLite journal mode is **WAL**.
- [ ] **Check 4:** Canonical row counts:
  - `sdc_chunks` = 90
  - `sdc_glossary` = 201
  - `sdc_exercises` = 39
  - `sdc_videos` = 113
- [ ] **Check 5:** `GET /api/health` returns `status: ok`.
- [ ] **Check 6:** `GET /classroom` returns `HTTP 200`.

---

## 5. Client Tablet Acceptance Testing

Take the reference Android test tablet:
1. Connect to Wi-Fi `Sindhi_Digital_Classroom`.
2. Open Chrome and enter: `http://192.168.1.100:8000/classroom` (or `http://192.168.4.1:8000/classroom`).
3. Verify that the **Classroom Dashboard** loads within 2 seconds.
4. Perform 3 test queries:
   - Query 1: `جيو گهرڙو` (Cell) $\to$ Verify grounded answer and `"PDF 5-6 (printed 1-2)"` citation appear.
   - Query 2: `اک` (Eye) $\to$ Verify eye sense-organ chunks appear.
   - Query 3: `سوليوشن` (Solution, Ch7) $\to$ Verify yellow blank-PDF warning banner appears.
5. Tap Chrome menu $\to$ **"Install App"** / **"Add to Home Screen"**.
6. Turn off Wi-Fi on the tablet momentarily and reopen the app $\to$ Verify the offline banner displays and cached screens remain responsive.

---

## 6. Field Troubleshooting Guide

| Problem / Symptom | Probable Cause | Action / Fix |
|---|---|---|
| **Pi 5 Red Power LED Blinking** | Insufficient power (< 4.8V or brownout) | Check battery voltage with multimeter; tighten buck converter terminals. |
| **PWA cannot open URL in Chrome** | Tablet connected to wrong Wi-Fi or DHCP conflict | Verify tablet is on `Sindhi_Digital_Classroom`; ping Pi IP from tablet. |
| **FastAPI service fails to start** | Port 8000 conflict or DB lock | Run `sudo journalctl -u sdc-pilot -n 50`; check `PRAGMA integrity_check;`. |
| **Search returns 0 results** | FTS5 index needs rebuild | Run `python3 -c "from src.services.sdc_rag_db import ensure_sdc_data_seeded; ensure_sdc_data_seeded()"`. |
| **Tablets run out of battery** | School charging lack | Instruct teacher on rotating tablet charging schedule from solar bank. |
