import logging
import random
import time
from datetime import datetime, timezone

import requests

# =========================
# ИНСТРУКЦИЯ
# 1. При необходимости измени BACKEND_BASE_URL и API_PATH.
# 2. Запусти файл командой: py emulator.py
# 3. Эмулятор будет отправлять телеметрию на:
#    {BACKEND_BASE_URL}{API_PATH}
# 4. Все комнаты, датчики, интервалы и сценарии задаются константами ниже.
# =========================

BACKEND_BASE_URL = "http://localhost:5000"
API_PATH = "/api/latest"
REQUEST_TIMEOUT = 5
RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 2
SLEEP_SECONDS = 3

ROOMS = {
    "room_101": {
        "name": "Conference room",
    },
    "room_102": {
        "name": "Office",
    },
}

SENSORS = [
    {
        "room_id": "room_101",
        "sensor_type": "temperature",
        "value": 22.0,
        "unit": "C",
        "status": "ok",
        "min_value": 18.0,
        "max_value": 28.0,
        "delta": 0.4,
    },
    {
        "room_id": "room_101",
        "sensor_type": "humidity",
        "value": 45.0,
        "unit": "%",
        "status": "ok",
        "min_value": 35.0,
        "max_value": 60.0,
        "delta": 1.5,
    },
    {
        "room_id": "room_102",
        "sensor_type": "temperature",
        "value": 23.5,
        "unit": "C",
        "status": "ok",
        "min_value": 19.0,
        "max_value": 29.0,
        "delta": 0.5,
    },
    {
        "room_id": "room_102",
        "sensor_type": "pressure",
        "value": 1008.0,
        "unit": "hPa",
        "status": "ok",
        "min_value": 995.0,
        "max_value": 1025.0,
        "delta": 0.8,
    },
]

# Тестовый сценарий:
# начиная с 5-го цикла температура в room_101 начинает расти быстрее,
# а после 10-го цикла статус датчика становится warning.
SCENARIO = {
    "enabled": True,
    "target_room_id": "room_101",
    "target_sensor_type": "temperature",
    "heat_start_cycle": 5,
    "warning_cycle": 10,
    "extra_growth": 0.8,
}


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def get_timestamp():
    return datetime.now(timezone.utc).isoformat()


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def update_sensor_value(sensor, cycle_number):
    current_value = sensor["value"]
    delta = random.uniform(-sensor["delta"], sensor["delta"])

    if SCENARIO["enabled"]:
        if (
            sensor["room_id"] == SCENARIO["target_room_id"]
            and sensor["sensor_type"] == SCENARIO["target_sensor_type"]
        ):
            if cycle_number >= SCENARIO["heat_start_cycle"]:
                delta += SCENARIO["extra_growth"]

            if cycle_number >= SCENARIO["warning_cycle"]:
                sensor["status"] = "warning"

    new_value = current_value + delta
    new_value = clamp(new_value, sensor["min_value"], sensor["max_value"])
    sensor["value"] = round(new_value, 2)


def build_payload(sensor):
    return {
        "room_id": sensor["room_id"],
        "sensor_type": sensor["sensor_type"],
        "value": sensor["value"],
        "unit": sensor["unit"],
        "status": sensor["status"],
        "timestamp": get_timestamp(),
    }


def send_payload(payload):
    url = f"{BACKEND_BASE_URL}{API_PATH}"

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            logging.info(
                "Telemetry sent | attempt=%s | status_code=%s | payload=%s",
                attempt,
                response.status_code,
                payload,
            )
            return True

        except requests.RequestException as error:
            logging.error(
                "Send failed | attempt=%s/%s | error=%s | payload=%s",
                attempt,
                RETRY_COUNT,
                error,
                payload,
            )

            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY_SECONDS)

    return False


def emulate():
    cycle_number = 0
    logging.info("Emulator started")
    logging.info("Rooms: %s", list(ROOMS.keys()))
    logging.info("POST URL: %s%s", BACKEND_BASE_URL, API_PATH)

    while True:
        cycle_number += 1
        logging.info("Cycle %s started", cycle_number)

        for sensor in SENSORS:
            update_sensor_value(sensor, cycle_number)
            payload = build_payload(sensor)
            send_payload(payload)

        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    setup_logging()
    emulate()
