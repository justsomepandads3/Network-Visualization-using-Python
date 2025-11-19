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
    Perform a simple SNMP GET and return value as Python type (int/str/etc.).
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
    elif errorStatus:
        raise RuntimeError(
            f"SNMP GET error: {errorStatus.prettyPrint()} at {errorIndex}"
        )

    # varBinds is a list of (ObjectType(ObjectIdentity(oid)), value)
    for varBind in varBinds:
        return varBind[1]  # return value part

    return None


def snmp_walk(ip, oid_prefix):
    """
    Perform an SNMP WALK (nextCmd) under a given OID prefix.
    Returns a list of (oid, value) tuples.
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
        elif errorStatus:
            raise RuntimeError(
                f"SNMP WALK error: {errorStatus.prettyPrint()} at {errorIndex}"
            )

        for varBind in varBinds:
            oid_str = str(varBind[0])
            val = varBind[1]
            results.append((oid_str, val))

    return results
