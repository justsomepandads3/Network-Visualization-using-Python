# config.py

# SNMP settings
SNMP_COMMUNITY = "netmon"
SNMP_PORT = 161
SNMP_VERSION = 2  # we use SNMPv2c

# Polling interval in seconds (used by collector)
POLL_INTERVAL = 10  # every 10 seconds

# List of network devices to monitor
DEVICES = [
    {"name": "Cisco-2901", "ip": "192.168.0.1", "role": "router"},
    {"name": "Catalyst-3560", "ip": "192.168.0.2", "role": "switch"},
]

# Thresholds for alerts (example: 80% of link speed)
# We'll estimate utilization in Flask using deltas in octets.
BANDWIDTH_THRESHOLD_PERCENT = 80

# Optional: default interface speed (in bps) if not available via SNMP
# e.g., 100 Mbps
DEFAULT_IF_SPEED_BPS = 100_000_000
