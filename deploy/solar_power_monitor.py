#!/usr/bin/env python3
"""SDC Solar & UPS Power Monitor for Raspberry Pi 5.
Monitors battery voltage or low-battery GPIO signals from a 12V solar charge controller / UPS hat.
Initiates safe shutdown to prevent SD card corruption during dusk/dawn brownouts or low-battery conditions.
Authored under agency-ai-engineer and agency-devops-automator.
"""

import logging
import os
import signal
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SDC-PowerGuard] %(message)s"
)
logger = logging.getLogger("sdc.power_guard")

# Default GPIO pin for Low Battery Signal from UPS / Solar Charge Controller (Active LOW)
LOW_BATTERY_GPIO_PIN = int(os.environ.get("SDC_POWER_GPIO_PIN", "4"))
CHECK_INTERVAL_SECONDS = int(os.environ.get("SDC_POWER_CHECK_INTERVAL", "5"))
GRACE_PERIOD_SECONDS = 15


def safe_shutdown():
    """Flush SQLite WAL checkpoints and shut down the Raspberry Pi 5 safely."""
    logger.warning("Low battery condition detected! Preparing system for emergency safe shutdown...")
    
    # 1. Checkpoint SQLite database to prevent WAL corruption
    try:
        import sqlite3
        db_path = os.environ.get("DATABASE_PATH", "/home/pi/sdc-pilot/data/sdc_platform.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conn.close()
            logger.info("SQLite WAL successfully checkpointed to disk.")
    except Exception as e:
        logger.error(f"Error during SQLite flush: {e}")

    # 2. Stop application service
    try:
        os.system("systemctl stop sdc-pilot.service")
    except Exception:
        pass

    # 3. Synchronize file system cache
    os.system("sync")
    logger.info(f"System will power off in {GRACE_PERIOD_SECONDS} seconds.")
    time.sleep(GRACE_PERIOD_SECONDS)
    os.system("shutdown -h now 'SDC Solar Guard: Battery exhausted'")
    sys.exit(0)


def main():
    logger.info("SDC Solar Power Monitor started.")
    logger.info(f"Monitoring GPIO Pin {LOW_BATTERY_GPIO_PIN} at {CHECK_INTERVAL_SECONDS}s interval.")

    # Try importing RPi.GPIO or gpiod if available on Raspberry Pi OS
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LOW_BATTERY_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        has_gpio = True
    except (ImportError, RuntimeError):
        logger.info("RPi.GPIO not available or running outside Pi hardware. Falling back to passive watcher.")
        has_gpio = False

    while True:
        try:
            if has_gpio:
                # Active low: 0 indicates battery depleted signal
                pin_val = GPIO.input(LOW_BATTERY_GPIO_PIN)
                if pin_val == 0:
                    safe_shutdown()
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Power monitor stopped by operator.")
            break
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
