# snmp_utils.py

from pysnmp_sync_adapter import get_cmd_sync, next_cmd_sync
from pysnmp.hlapi.v3arch.asyncio import SnmpEngine, CommunityData, UdpTransportTarget, ContextData
from pysnmp.smi.rfc1902 import ObjectIdentity, ObjectType
from pysnmp_sync_adapter import create_transport
from config import SNMP_COMMUNITY, SNMP_PORT


def snmp_get(ip, oid):
    """
    Perform SNMP GET and return value as Python type.
    """
    errorIndication, errorStatus, errorIndex, varBinds = get_cmd_sync(
        SnmpEngine(),
        CommunityData(SNMP_COMMUNITY, mpModel=1),
        create_transport(UdpTransportTarget, (ip, SNMP_PORT), timeout=1, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )

    if errorIndication:
        raise RuntimeError(f"SNMP GET error: {errorIndication}")
    elif errorStatus:
        raise RuntimeError(f"SNMP GET error: {errorStatus.prettyPrint()} at {errorIndex}")

    for varBind in varBinds:
        return varBind[1]
    return None


def snmp_walk(ip, oid_prefix):
    """
    Perform SNMP WALK and return list of (oid, value) tuples.
    """
    results = []
    for errorIndication, errorStatus, errorIndex, varBinds in next_cmd_sync(
        SnmpEngine(),
        CommunityData(SNMP_COMMUNITY, mpModel=1),
        create_transport(UdpTransportTarget, (ip, SNMP_PORT), timeout=1, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity(oid_prefix)),
        lexicographicMode=False
    ):
        if errorIndication:
            raise RuntimeError(f"SNMP WALK error: {errorIndication}")
        elif errorStatus:
            raise RuntimeError(f"SNMP WALK error: {errorStatus.prettyPrint()} at {errorIndex}")

        for varBind in varBinds:
            results.append((str(varBind[0]), varBind[1]))
    return results   