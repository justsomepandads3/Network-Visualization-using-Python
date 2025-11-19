# config.py

# SNMP settings
SNMP_COMMUNITY = "netmon"
SNMP_PORT = 161
SNMP_VERSION = 2  # we use SNMPv2c

# Polling interval in seconds (used by collector)
POLL_INTERVAL = 10  # every 10 seconds

# List of network devices to monitor
DEVICES = [
    {"name": "R1", "ip": "192.168.10.1", "role": "router"},
    {"name": "R2", "ip": "192.168.20.1", "role": "router"},
    {"name": "SW1", "ip": "192.168.10.2", "role": "switch"},
    {"name": "SW2", "ip": "192.168.20.2", "role": "switch"},
]

# Thresholds for alerts (example: 80% of link speed)
# We'll estimate utilization in Flask using deltas in octets.
BANDWIDTH_THRESHOLD_PERCENT = 80

# Optional: default interface speed (in bps) if not available via SNMP
# e.g., 100 Mbps
DEFAULT_IF_SPEED_BPS = 100_000_000
