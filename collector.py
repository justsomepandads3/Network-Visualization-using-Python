# collector.py

import time
import csv
import os
from datetime import datetime

from config import DEVICES, POLL_INTERVAL
from snmp_utils import snmp_walk

# OIDs for interfaces from IF-MIB
OID_IFDESCR = "1.3.6.1.2.1.2.2.1.2"      # ifDescr
OID_IFINOCTETS = "1.3.6.1.2.1.2.2.1.10"  # ifInOctets
OID_IFOUTOCTETS = "1.3.6.1.2.1.2.2.1.16" # ifOutOctets
OID_IFOPERSTATUS = "1.3.6.1.2.1.2.2.1.8" # ifOperStatus


METRICS_FILE = "metrics.csv"
ALERTS_FILE = "alerts.csv"


def ensure_csv_headers():
    """
    Create CSV files with headers if they don't exist.
    """
    if not os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "device",
                "ip",
                "ifIndex",
                "ifDescr",
                "inOctets",
                "outOctets",
                "operStatus"
            ])

    if not os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "device",
                "ip",
                "severity",
                "message"
            ])


def log_metric(timestamp, device_name, ip, if_index, if_descr,
               in_octets, out_octets, oper_status):
    with open(METRICS_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            device_name,
            ip,
            if_index,
            if_descr,
            in_octets,
            out_octets,
            oper_status
        ])


def log_alert(timestamp, device_name, ip, severity, message):
    print(f"[{timestamp}] ALERT {severity} on {device_name} ({ip}): {message}")
    with open(ALERTS_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            device_name,
            ip,
            severity,
            message
        ])


def collect_for_device(device):
    """
    Collect interface metrics for a single device using SNMP.
    """
    name = device["name"]
    ip = device["ip"]

    print(f"Collecting from {name} ({ip}) ...")

    timestamp = datetime.utcnow().isoformat()

    try:
        # Walk each OID table: they share the same index (.ifIndex)
        descrs = snmp_walk(ip, OID_IFDESCR)
        in_octets = snmp_walk(ip, OID_IFINOCTETS)
        out_octets = snmp_walk(ip, OID_IFOUTOCTETS)
        oper_statuses = snmp_walk(ip, OID_IFOPERSTATUS)
    except Exception as e:
        log_alert(timestamp, name, ip, "CRITICAL", f"SNMP error: {e}")
        return

    # Convert to dictionaries indexed by interface index
    # OIDs look like: 1.3.6.1.2.1.2.2.1.2.<ifIndex>
    def extract_index(oid_str, base_oid):
        return oid_str[len(base_oid) + 1 :]

    descr_map = {}
    in_map = {}
    out_map = {}
    oper_map = {}

    for oid_str, val in descrs:
        idx = extract_index(oid_str, OID_IFDESCR)
        descr_map[idx] = str(val)

    for oid_str, val in in_octets:
        idx = extract_index(oid_str, OID_IFINOCTETS)
        in_map[idx] = int(val)

    for oid_str, val in out_octets:
        idx = extract_index(oid_str, OID_IFOUTOCTETS)
        out_map[idx] = int(val)

    for oid_str, val in oper_statuses:
        idx = extract_index(oid_str, OID_IFOPERSTATUS)
        oper_map[idx] = int(val)

    # Merge per interface index
    all_indexes = sorted(descr_map.keys())

    for idx in all_indexes:
        if_descr = descr_map.get(idx, "unknown")
        in_oct = in_map.get(idx, 0)
        out_oct = out_map.get(idx, 0)
        oper_status = oper_map.get(idx, 0)  # 1=up, 2=down, etc.

        log_metric(timestamp, name, ip, idx, if_descr, in_oct, out_oct, oper_status)

        # Simple alert if interface is down
        if oper_status != 1:
            log_alert(
                timestamp,
                name,
                ip,
                "WARNING",
                f"Interface {idx} ({if_descr}) is DOWN (status={oper_status})",
            )


def main():
    ensure_csv_headers()
    print("Starting collector loop...")
    while True:
        for dev in DEVICES:
            collect_for_device(dev)
        print(f"Sleeping for {POLL_INTERVAL} seconds...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
