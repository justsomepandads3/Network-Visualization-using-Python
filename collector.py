# collector.py

import time
import csv
import os
from datetime import datetime

from config import DEVICES, POLL_INTERVAL, METRICS_FILE, ALERTS_FILE
from snmp_utils import snmp_walk, snmp_get

# OIDs (IF-MIB + sysUpTime)
OID_IFDESCR = "1.3.6.1.2.1.2.2.1.2"      # ifDescr
OID_IFINOCTETS = "1.3.6.1.2.1.2.2.1.10"  # ifInOctets
OID_IFOUTOCTETS = "1.3.6.1.2.1.2.2.1.16" # ifOutOctets
OID_IFOPERSTATUS = "1.3.6.1.2.1.2.2.1.8" # ifOperStatus
OID_SYSUPTIME = "1.3.6.1.2.1.1.3.0"      # sysUpTime.0

METRICS_HEADER = [
    "timestamp",
    "device",
    "ip",
    "ifIndex",
    "ifDescr",
    "inOctets",
    "outOctets",
    "operStatus",
    "sysUpTimeCentisecs",
]


def ensure_csv_headers():
    if not os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "w", newline="") as f:
            csv.writer(f).writerow(METRICS_HEADER)

    if not os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp", "device", "ip", "severity", "message"]
            )


def log_metric(ts, dev, ip, idx, descr, in_oct, out_oct, status, uptime):
    with open(METRICS_FILE, "a", newline="") as f:
        csv.writer(f).writerow(
            [ts, dev, ip, idx, descr, in_oct, out_oct, status, uptime]
        )


def log_alert(ts, dev, ip, severity, msg):
    print(f"[{ts}] ALERT {severity} on {dev} ({ip}): {msg}")
    with open(ALERTS_FILE, "a", newline="") as f:
        csv.writer(f).writerow([ts, dev, ip, severity, msg])


def extract_index(oid_str, base_oid):
    # base_oid like "1.3.6.1.2.1.2.2.1.2"
    # oid_str like "1.3.6.1.2.1.2.2.1.2.1"
    if not oid_str.startswith(base_oid + "."):
        raise ValueError(f"OID {oid_str} does not start with {base_oid}")
    return oid_str[len(base_oid) + 1:]


def collect_for_device(device):
    name = device["name"]
    ip = device["ip"]
    ts = datetime.utcnow().isoformat()

    print(f"Collecting from {name} ({ip}) ...")

    try:
        descrs = snmp_walk(ip, OID_IFDESCR)
        in_octets = snmp_walk(ip, OID_IFINOCTETS)
        out_octets = snmp_walk(ip, OID_IFOUTOCTETS)
        oper_statuses = snmp_walk(ip, OID_IFOPERSTATUS)
        sys_uptime = snmp_get(ip, OID_SYSUPTIME)
    except Exception as e:
        log_alert(ts, name, ip, "CRITICAL", f"SNMP error: {e}")
        return

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

    all_indexes = sorted(descr_map.keys())

    for idx in all_indexes:
        descr = descr_map.get(idx, "unknown")
        in_oct = in_map.get(idx, 0)
        out_oct = out_map.get(idx, 0)
        status = oper_map.get(idx, 0)  # 1=up, 2=down

        log_metric(ts, name, ip, idx, descr, in_oct, out_oct, status, int(sys_uptime))

        if status != 1:
            log_alert(
                ts,
                name,
                ip,
                "WARNING",
                f"Interface {idx} ({descr}) is DOWN (status={status})",
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
