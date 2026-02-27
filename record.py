#!/usr/bin/env python3
"""
record.py — Read NMEA sentences from a BU-353N GPS and append fixes to a YAML file.

Usage:
    uv run python record.py                         # auto-detect port
    uv run python record.py --port /dev/cu.usbserial-0001
    uv run python record.py --port /dev/cu.usbserial-0001 --output track.yaml
    uv run python record.py --count 50              # stop after 50 fixes

The BU-353N transmits NMEA 0183 at 4800 baud. This script uses $GPRMC and
$GNRMC sentences for position/speed/heading, supplemented by $GPGGA/$GNGGA
for altitude and satellite count.
"""

import argparse
import datetime
import glob
import sys
import time

import pynmea2
import serial
import yaml

DEFAULT_BAUD = 4800
DEFAULT_OUTPUT = "gps_track.yaml"


def find_gps_port() -> str:
    """Return the first likely GPS serial port, or raise if none found."""
    candidates = (
        glob.glob("/dev/cu.PL2303*")
        + glob.glob("/dev/cu.usbserial*")
        + glob.glob("/dev/cu.usbmodem*")
        + glob.glob("/dev/tty.PL2303*")
        + glob.glob("/dev/tty.usbserial*")
        + glob.glob("/dev/tty.usbmodem*")
    )
    if candidates:
        return candidates[0]
    raise RuntimeError(
        "No USB serial port found. Is the BU-353N plugged in and its driver installed?\n"
        "  Prolific driver for macOS: https://www.prolific.com.tw/US/ShowProduct.aspx?p_id=229&pcid=41\n"
        "  After installing, replug the device and check: ls /dev/cu.usbserial*"
    )


def load_existing(path: str) -> list:
    """Load existing YAML track file, returning a list of point dicts."""
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []


def save_points(path: str, points: list) -> None:
    with open(path, "w") as f:
        yaml.dump(points, f, default_flow_style=False, sort_keys=False)


def parse_args():
    p = argparse.ArgumentParser(description="Record GPS fixes to a YAML file.")
    p.add_argument("--port", help="Serial port (auto-detected if omitted)")
    p.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    p.add_argument("--output", default=DEFAULT_OUTPUT, help=f"Output YAML file (default: {DEFAULT_OUTPUT})")
    p.add_argument("--count", type=int, default=0, help="Stop after N fixes (0 = run forever, Ctrl-C to stop)")
    return p.parse_args()


def main():
    args = parse_args()

    port = args.port or find_gps_port()
    print(f"Opening {port} at {args.baud} baud …")

    points = load_existing(args.output)
    print(f"Loaded {len(points)} existing points from {args.output!r}")

    try:
        ser = serial.Serial(port, args.baud, timeout=2)
    except serial.SerialException as e:
        sys.exit(f"Cannot open {port}: {e}")

    fixes_recorded = 0
    pending_gga: dict | None = None  # last $GPGGA/$GNGGA extras

    print("Waiting for GPS fix … (Ctrl-C to stop)")
    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue
            try:
                line = raw.decode("ascii", errors="replace").strip()
            except Exception:
                continue

            if not line.startswith("$"):
                continue

            try:
                msg = pynmea2.parse(line)
            except pynmea2.ParseError:
                continue

            # Collect altitude + sat count from GGA sentences
            if isinstance(msg, (pynmea2.types.talker.GGA,)):
                if msg.latitude and msg.longitude:
                    pending_gga = {
                        "altitude_m": float(msg.altitude) if msg.altitude else None,
                        "num_sats": int(msg.num_sats) if msg.num_sats else None,
                    }
                continue

            # Use RMC for the primary fix (has date + time + speed + course)
            if not isinstance(msg, (pynmea2.types.talker.RMC,)):
                continue

            if not msg.status or msg.status != "A":
                # 'A' = Active (valid fix); 'V' = Void
                continue

            lat = msg.latitude   # decimal degrees, positive = N
            lon = msg.longitude  # decimal degrees, positive = E

            if lat == 0.0 and lon == 0.0:
                continue

            # Build timestamp
            try:
                dt = datetime.datetime.combine(msg.datestamp, msg.timestamp.replace(tzinfo=None))
                ts = dt.isoformat() + "Z"
            except Exception:
                ts = datetime.datetime.utcnow().isoformat() + "Z"

            point = {
                "timestamp": ts,
                "lat": round(lat, 8),
                "lon": round(lon, 8),
                "speed_knots": round(float(msg.spd_over_grnd), 3) if msg.spd_over_grnd else None,
                "course_deg": round(float(msg.true_course), 2) if msg.true_course else None,
            }

            if pending_gga:
                point.update(pending_gga)
                pending_gga = None

            points.append(point)
            save_points(args.output, points)

            fixes_recorded += 1
            print(
                f"[{fixes_recorded:>4}] {ts}  lat={lat:>11.6f}  lon={lon:>12.6f}"
                + (f"  {point['speed_knots']:.1f} kn" if point.get("speed_knots") is not None else "")
            )

            if args.count and fixes_recorded >= args.count:
                print(f"Reached {args.count} fixes — stopping.")
                break

    except KeyboardInterrupt:
        print(f"\nStopped. {fixes_recorded} new fixes recorded to {args.output!r}")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
