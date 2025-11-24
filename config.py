
# SNMP settings
SNMP_COMMUNITY = "netmon"
SNMP_PORT = 161
SNMP_VERSION = 2  # we use SNMPv2c

# Polling interval in seconds 
POLL_INTERVAL = 4  # every 4 seconds

# List of network devices to monitor
DEVICES = [
    {"name": "R1", "ip": "192.168.10.1", "role": "router"},
    {"name": "R2", "ip": "192.168.20.1", "role": "router"},
]

# Thresholds for alerts 
# We'll estimate utilization in Flask using deltas in octets.
BANDWIDTH_THRESHOLD_PERCENT = 80

#default interface speed (in bps) if not available via SNMP
DEFAULT_IF_SPEED_BPS = 100_000_000

#Files to save the performance metrics and alerts
METRICS_FILE = "metrics.csv"
ALERTS_FILE = "alerts.csv"
