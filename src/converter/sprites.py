"""ISA-style sprite definitions for PlantUML CSA diagrams.

Provides sprite mappings and color schemes for industrial control components.
"""
from ..models import ControllerType, DeviceType, ProtocolType

# Controller type to sprite/stereotype mapping
CONTROLLER_SPRITES: dict[ControllerType, dict[str, str]] = {
    ControllerType.PLC: {
        "sprite": "plc",
        "stereotype": "<<PLC>>",
        "color": "#4A90D9",
        "shape": "rectangle",
    },
    ControllerType.DCS: {
        "sprite": "dcs",
        "stereotype": "<<DCS>>",
        "color": "#8E44AD",
        "shape": "rectangle",
    },
    ControllerType.PAC: {
        "sprite": "pac",
        "stereotype": "<<PAC>>",
        "color": "#2980B9",
        "shape": "rectangle",
    },
    ControllerType.SAFETY_PLC: {
        "sprite": "safety_plc",
        "stereotype": "<<Safety PLC>>",
        "color": "#E74C3C",
        "shape": "rectangle",
    },
    ControllerType.SOFT_PLC: {
        "sprite": "soft_plc",
        "stereotype": "<<Soft PLC>>",
        "color": "#3498DB",
        "shape": "rectangle",
    },
    ControllerType.EDGE_CONTROLLER: {
        "sprite": "edge",
        "stereotype": "<<Edge>>",
        "color": "#1ABC9C",
        "shape": "rectangle",
    },
    ControllerType.MOTION_CONTROLLER: {
        "sprite": "motion",
        "stereotype": "<<Motion>>",
        "color": "#F39C12",
        "shape": "rectangle",
    },
    ControllerType.REDUNDANT_PLC: {
        "sprite": "redundant_plc",
        "stereotype": "<<Redundant>>",
        "color": "#27AE60",
        "shape": "rectangle",
    },
    ControllerType.RTU: {
        "sprite": "rtu",
        "stereotype": "<<RTU>>",
        "color": "#95A5A6",
        "shape": "rectangle",
    },
    ControllerType.SIS: {
        "sprite": "sis",
        "stereotype": "<<SIS>>",
        "color": "#C0392B",
        "shape": "rectangle",
    },
}

# Device type to sprite/stereotype mapping
DEVICE_SPRITES: dict[DeviceType, dict[str, str]] = {
    DeviceType.REMOTE_IO: {
        "sprite": "remote_io",
        "stereotype": "<<Remote IO>>",
        "color": "#7F8C8D",
        "shape": "rectangle",
    },
    DeviceType.HMI: {
        "sprite": "hmi",
        "stereotype": "<<HMI>>",
        "color": "#2ECC71",
        "shape": "rectangle",
    },
    DeviceType.SCADA: {
        "sprite": "scada",
        "stereotype": "<<SCADA>>",
        "color": "#9B59B6",
        "shape": "rectangle",
    },
    DeviceType.HISTORIAN: {
        "sprite": "historian",
        "stereotype": "<<Historian>>",
        "color": "#E67E22",
        "shape": "database",
    },
    DeviceType.OPC_UA_SERVER: {
        "sprite": "opc_ua",
        "stereotype": "<<OPC-UA>>",
        "color": "#1ABC9C",
        "shape": "rectangle",
    },
    DeviceType.GATEWAY: {
        "sprite": "gateway",
        "stereotype": "<<Gateway>>",
        "color": "#34495E",
        "shape": "rectangle",
    },
    DeviceType.VFD: {
        "sprite": "vfd",
        "stereotype": "<<VFD>>",
        "color": "#F1C40F",
        "shape": "rectangle",
    },
    DeviceType.SOFT_STARTER: {
        "sprite": "soft_starter",
        "stereotype": "<<Soft Starter>>",
        "color": "#D4AC0D",
        "shape": "rectangle",
    },
    DeviceType.MCC: {
        "sprite": "mcc",
        "stereotype": "<<MCC>>",
        "color": "#566573",
        "shape": "rectangle",
    },
    DeviceType.INDUSTRIAL_PC: {
        "sprite": "ipc",
        "stereotype": "<<IPC>>",
        "color": "#2C3E50",
        "shape": "rectangle",
    },
    DeviceType.SWITCH: {
        "sprite": "switch",
        "stereotype": "<<Switch>>",
        "color": "#3498DB",
        "shape": "hexagon",
    },
    DeviceType.MANAGED_SWITCH: {
        "sprite": "managed_switch",
        "stereotype": "<<Managed Switch>>",
        "color": "#2980B9",
        "shape": "hexagon",
    },
    DeviceType.ROUTER: {
        "sprite": "router",
        "stereotype": "<<Router>>",
        "color": "#8E44AD",
        "shape": "hexagon",
    },
    DeviceType.FIREWALL: {
        "sprite": "firewall",
        "stereotype": "<<Firewall>>",
        "color": "#E74C3C",
        "shape": "hexagon",
    },
    DeviceType.WIRELESS_AP: {
        "sprite": "wireless",
        "stereotype": "<<Wireless AP>>",
        "color": "#9B59B6",
        "shape": "rectangle",
    },
    DeviceType.MEDIA_CONVERTER: {
        "sprite": "media_conv",
        "stereotype": "<<Media Conv>>",
        "color": "#7F8C8D",
        "shape": "rectangle",
    },
    DeviceType.NETWORK_TAP: {
        "sprite": "network_tap",
        "stereotype": "<<TAP>>",
        "color": "#95A5A6",
        "shape": "rectangle",
    },
    DeviceType.MOTOR_STARTER: {
        "sprite": "motor_starter",
        "stereotype": "<<Starter>>",
        "color": "#D68910",
        "shape": "rectangle",
    },
    DeviceType.ENGINEERING_WS: {
        "sprite": "eng_ws",
        "stereotype": "<<Eng WS>>",
        "color": "#2C3E50",
        "shape": "rectangle",
    },
    DeviceType.PANEL_PC: {
        "sprite": "panel_pc",
        "stereotype": "<<Panel PC>>",
        "color": "#34495E",
        "shape": "rectangle",
    },
    DeviceType.DATA_LOGGER: {
        "sprite": "data_logger",
        "stereotype": "<<Logger>>",
        "color": "#E67E22",
        "shape": "rectangle",
    },
    DeviceType.JUNCTION_BOX: {
        "sprite": "jbox",
        "stereotype": "<<JB>>",
        "color": "#BDC3C7",
        "shape": "rectangle",
    },
    DeviceType.MARSHALLING_CABINET: {
        "sprite": "marsh_cab",
        "stereotype": "<<Marshalling>>",
        "color": "#95A5A6",
        "shape": "rectangle",
    },
    DeviceType.LOCAL_PANEL: {
        "sprite": "local_panel",
        "stereotype": "<<Local Panel>>",
        "color": "#7F8C8D",
        "shape": "rectangle",
    },
    DeviceType.REMOTE_PANEL: {
        "sprite": "remote_panel",
        "stereotype": "<<Remote Panel>>",
        "color": "#566573",
        "shape": "rectangle",
    },
    DeviceType.INSTRUMENT_RACK: {
        "sprite": "inst_rack",
        "stereotype": "<<Inst Rack>>",
        "color": "#ABB2B9",
        "shape": "rectangle",
    },
}

# Protocol colors for link styling
PROTOCOL_COLORS: dict[ProtocolType, dict[str, str]] = {
    ProtocolType.ETHERNET_IP: {
        "color": "#0066CC",
        "style": "solid",
        "label": "EtherNet/IP",
    },
    ProtocolType.PROFINET: {
        "color": "#009933",
        "style": "solid",
        "label": "PROFINET",
    },
    ProtocolType.MODBUS_TCP: {
        "color": "#FF6600",
        "style": "solid",
        "label": "Modbus TCP",
    },
    ProtocolType.MODBUS_RTU: {
        "color": "#CC6600",
        "style": "dashed",
        "label": "Modbus RTU",
    },
    ProtocolType.PROFIBUS: {
        "color": "#660099",
        "style": "dashed",
        "label": "PROFIBUS",
    },
    ProtocolType.DEVICENET: {
        "color": "#993366",
        "style": "dashed",
        "label": "DeviceNet",
    },
    ProtocolType.CONTROLNET: {
        "color": "#336699",
        "style": "dashed",
        "label": "ControlNet",
    },
    ProtocolType.HART: {
        "color": "#996633",
        "style": "dotted",
        "label": "HART",
    },
    ProtocolType.FOUNDATION_FIELDBUS: {
        "color": "#339966",
        "style": "dashed",
        "label": "FF",
    },
    ProtocolType.OPC_UA: {
        "color": "#6600CC",
        "style": "solid",
        "label": "OPC-UA",
    },
    ProtocolType.MQTT: {
        "color": "#00CC99",
        "style": "solid",
        "label": "MQTT",
    },
    ProtocolType.BACNET: {
        "color": "#3399CC",
        "style": "solid",
        "label": "BACnet",
    },
}

# Purdue level zone colors (ISA-95)
ZONE_COLORS: dict[int, dict[str, str]] = {
    0: {
        "background": "#E8F5E9",  # Light green - Field Level
        "border": "#4CAF50",
        "name": "Level 0 - Field",
    },
    1: {
        "background": "#E3F2FD",  # Light blue - Control Level
        "border": "#2196F3",
        "name": "Level 1 - Control",
    },
    2: {
        "background": "#FFF3E0",  # Light orange - Supervisory Level
        "border": "#FF9800",
        "name": "Level 2 - Supervisory",
    },
    3: {
        "background": "#F3E5F5",  # Light purple - Operations Level
        "border": "#9C27B0",
        "name": "Level 3 - Operations",
    },
    4: {
        "background": "#FFEBEE",  # Light red - Enterprise Level
        "border": "#F44336",
        "name": "Level 4 - Enterprise",
    },
}


def get_controller_style(controller_type: ControllerType) -> dict[str, str]:
    """Get sprite/style info for a controller type."""
    return CONTROLLER_SPRITES.get(
        controller_type,
        {
            "sprite": "controller",
            "stereotype": "<<Controller>>",
            "color": "#95A5A6",
            "shape": "rectangle",
        },
    )


def get_device_style(device_type: DeviceType) -> dict[str, str]:
    """Get sprite/style info for a device type."""
    return DEVICE_SPRITES.get(
        device_type,
        {
            "sprite": "device",
            "stereotype": "<<Device>>",
            "color": "#BDC3C7",
            "shape": "rectangle",
        },
    )


def get_protocol_style(protocol: ProtocolType) -> dict[str, str]:
    """Get line style for a protocol."""
    return PROTOCOL_COLORS.get(
        protocol,
        {
            "color": "#7F8C8D",
            "style": "solid",
            "label": str(protocol.value),
        },
    )


def get_zone_style(purdue_level: int) -> dict[str, str]:
    """Get zone styling for a Purdue level."""
    return ZONE_COLORS.get(
        purdue_level,
        {
            "background": "#FAFAFA",
            "border": "#BDBDBD",
            "name": f"Level {purdue_level}",
        },
    )
