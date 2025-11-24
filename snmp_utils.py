# snmp_utils.py

from pysnmp.hlapi import (
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    getCmd,
    nextCmd,
)
from config import SNMP_COMMUNITY, SNMP_PORT


def snmp_get(ip, oid):
    """
    Simple SNMP GET, returns the value of the OID.
    Raises RuntimeError on SNMP errors.
    """
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(SNMP_COMMUNITY, mpModel=1),  # SNMPv2c
        UdpTransportTarget((ip, SNMP_PORT), timeout=1, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication:
        raise RuntimeError(f"SNMP GET error: {errorIndication}")
    if errorStatus:
        raise RuntimeError(
            f"SNMP GET error: {errorStatus.prettyPrint()} at {errorIndex}"
        )

    for varBind in varBinds:
        # varBind[1] is the value
        return varBind[1]

    return None


def snmp_walk(ip, oid_prefix):
    """
    Simple SNMP WALK, returns list of (oid_str, value) tuples.
    Raises RuntimeError on SNMP errors.
    """
    results = []

    for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
        SnmpEngine(),
        CommunityData(SNMP_COMMUNITY, mpModel=1),
        UdpTransportTarget((ip, SNMP_PORT), timeout=1, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity(oid_prefix)),
        lexicographicMode=False,
    ):
        if errorIndication:
            raise RuntimeError(f"SNMP WALK error: {errorIndication}")
        if errorStatus:
            raise RuntimeError(
                f"SNMP WALK error: {errorStatus.prettyPrint()} at {errorIndex}"
            )

        for varBind in varBinds:
            oid_str = str(varBind[0])
            val = varBind[1]
            results.append((oid_str, val))

    return results
