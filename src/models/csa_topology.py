"""CSA Topology Pydantic models.

Provides schema validation for Control System Architecture topology definitions.
Uses Pydantic for automatic validation and serialization.

NOTE: This is a copy from freecad-csa-workbench/addon/CSAWorkbench/models/csa_topology.py
to maintain schema compatibility between FreeCAD and PlantUML renderers.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ControllerType(str, Enum):
    """Controller types following industry standards."""

    PLC = "PLC"
    DCS = "DCS"
    PAC = "PAC"
    SAFETY_PLC = "Safety_PLC"
    SOFT_PLC = "Soft_PLC"
    EDGE_CONTROLLER = "Edge_Controller"
    MOTION_CONTROLLER = "Motion_Controller"
    REDUNDANT_PLC = "Redundant_PLC"
    RTU = "RTU"
    SIS = "SIS"


class DeviceType(str, Enum):
    """Device types for CSA diagrams."""

    REMOTE_IO = "RemoteIO"
    HMI = "HMI"
    SCADA = "SCADA"
    HISTORIAN = "Historian"
    OPC_UA_SERVER = "OPC_UA_Server"
    GATEWAY = "Gateway"
    VFD = "VFD"
    SOFT_STARTER = "Soft_Starter"
    MCC = "MCC"
    INDUSTRIAL_PC = "Industrial_PC"
    SWITCH = "Switch"
    MANAGED_SWITCH = "Managed_Switch"
    ROUTER = "Router"
    FIREWALL = "Firewall"
    WIRELESS_AP = "Wireless_AP"
    MEDIA_CONVERTER = "Media_Converter"
    NETWORK_TAP = "Network_TAP"
    MOTOR_STARTER = "Motor_Starter"
    ENGINEERING_WS = "Engineering_WS"
    PANEL_PC = "Panel_PC"
    DATA_LOGGER = "Data_Logger"
    JUNCTION_BOX = "Junction_Box"
    MARSHALLING_CABINET = "Marshalling_Cabinet"
    LOCAL_PANEL = "Local_Panel"
    REMOTE_PANEL = "Remote_Panel"
    INSTRUMENT_RACK = "Instrument_Rack"


class ProtocolType(str, Enum):
    """Industrial network protocols."""

    ETHERNET_IP = "Ethernet_IP"
    PROFINET = "Profinet"
    MODBUS_TCP = "Modbus_TCP"
    MODBUS_RTU = "Modbus_RTU"
    PROFIBUS = "Profibus"
    DEVICENET = "DeviceNet"
    CONTROLNET = "ControlNet"
    HART = "HART"
    FOUNDATION_FIELDBUS = "Foundation_Fieldbus"
    OPC_UA = "OPC_UA"
    MQTT = "MQTT"
    BACNET = "BACnet"


class RedundancyType(str, Enum):
    """Controller redundancy configurations."""

    NONE = "None"
    HOT_STANDBY = "Hot_Standby"
    WARM_STANDBY = "Warm_Standby"
    COLD_STANDBY = "Cold_Standby"
    DUAL_REDUNDANT = "Dual_Redundant"
    TRIPLE_MODULAR = "Triple_Modular"


class CSAMetadata(BaseModel):
    """Project metadata for CSA topology."""

    project_name: str
    site: str = ""
    revision: str = "A"
    date: str = ""
    author: str = ""
    client: str = ""
    description: str = ""


class CSAZone(BaseModel):
    """Network zone following ISA-95 Purdue model."""

    id: str
    name: str = ""
    purdue_level: int = Field(default=1, ge=0, le=4)

    @field_validator("name", mode="before")
    @classmethod
    def default_name_from_id(cls, v: str, info) -> str:
        if not v and info.data.get("id"):
            return info.data["id"]
        return v


class CSAPort(BaseModel):
    """Connection port on a controller or device."""

    model_config = {"populate_by_name": True}

    id: str
    x: float = 0.0
    y: float = 0.0
    direction: str = "N"  # N, S, E, W
    type: str = Field(default="ethernet", alias="port_type")


class CSAControllerDef(BaseModel):
    """Controller definition in CSA topology."""

    id: str
    type: ControllerType
    manufacturer: str = ""
    model: str = ""
    redundancy: RedundancyType = RedundancyType.NONE
    zone: str = ""
    equipment_tags: list[str] = Field(default_factory=list)
    ip_address: str = ""
    description: str = ""
    ports: list[CSAPort] = Field(default_factory=list)
    position_x: float = 0.0
    position_y: float = 0.0
    width: float = 60.0
    height: float = 40.0


class CSADeviceDef(BaseModel):
    """Device definition in CSA topology."""

    id: str
    type: DeviceType
    model: str = ""
    parent_controller: str = ""
    zone: str = ""
    ip_address: str = ""
    description: str = ""
    ports: list[CSAPort] = Field(default_factory=list)
    position_x: float = 0.0
    position_y: float = 0.0
    width: float = 40.0
    height: float = 30.0


class CSANetworkDef(BaseModel):
    """Network definition in CSA topology."""

    id: str
    name: str = ""
    protocol: ProtocolType
    zone: str = ""
    subnet: str = ""
    description: str = ""

    @field_validator("name", mode="before")
    @classmethod
    def default_name_from_id(cls, v: str, info) -> str:
        if not v and info.data.get("id"):
            return info.data["id"]
        return v


class CSAWaypoint(BaseModel):
    """Waypoint for link routing."""

    x: float
    y: float


class CSALinkDef(BaseModel):
    """Network link definition in CSA topology."""

    source: str
    target: str
    protocol: ProtocolType
    network: str = ""
    cable_type: str = ""
    source_port: str = ""
    target_port: str = ""
    description: str = ""
    waypoints: list[CSAWaypoint] = Field(default_factory=list)


class CSATopology(BaseModel):
    """Complete CSA topology definition."""

    schema_version: str = "1.0"
    metadata: CSAMetadata = Field(default_factory=lambda: CSAMetadata(project_name="Untitled"))
    zones: list[CSAZone] = Field(default_factory=list)
    controllers: list[CSAControllerDef] = Field(default_factory=list)
    devices: list[CSADeviceDef] = Field(default_factory=list)
    networks: list[CSANetworkDef] = Field(default_factory=list)
    links: list[CSALinkDef] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> "CSATopology":
        """Validate that all references are valid."""
        controller_ids = {c.id for c in self.controllers}
        device_ids = {d.id for d in self.devices}
        zone_ids = {z.id for z in self.zones}
        network_ids = {n.id for n in self.networks}
        all_node_ids = controller_ids | device_ids

        # Validate controller zones
        for controller in self.controllers:
            if controller.zone and controller.zone not in zone_ids:
                raise ValueError(
                    f"Controller '{controller.id}' references unknown zone '{controller.zone}'"
                )

        # Validate device parent controllers
        for device in self.devices:
            if device.parent_controller and device.parent_controller not in controller_ids:
                raise ValueError(
                    f"Device '{device.id}' references unknown parent_controller "
                    f"'{device.parent_controller}'"
                )

        # Validate links
        for link in self.links:
            if link.source not in all_node_ids:
                raise ValueError(f"Link source '{link.source}' not found in controllers or devices")
            if link.target not in all_node_ids:
                raise ValueError(f"Link target '{link.target}' not found in controllers or devices")
            if link.network and link.network not in network_ids:
                raise ValueError(f"Link references unknown network '{link.network}'")

        return self

    def get_controller(self, controller_id: str) -> Optional[CSAControllerDef]:
        """Get controller by ID."""
        for c in self.controllers:
            if c.id == controller_id:
                return c
        return None

    def get_device(self, device_id: str) -> Optional[CSADeviceDef]:
        """Get device by ID."""
        for d in self.devices:
            if d.id == device_id:
                return d
        return None

    def get_zone(self, zone_id: str) -> Optional[CSAZone]:
        """Get zone by ID."""
        for z in self.zones:
            if z.id == zone_id:
                return z
        return None

    def get_nodes_in_zone(self, zone_id: str) -> list[str]:
        """Get all node IDs in a zone."""
        nodes = []
        for c in self.controllers:
            if c.zone == zone_id:
                nodes.append(c.id)
        for d in self.devices:
            if d.zone == zone_id:
                nodes.append(d.id)
        return nodes

    def get_links_for_node(self, node_id: str) -> list[CSALinkDef]:
        """Get all links connected to a node."""
        return [link for link in self.links if link.source == node_id or link.target == node_id]

    def add_controller(self, controller: CSAControllerDef) -> None:
        """Add a controller to the topology."""
        if any(c.id == controller.id for c in self.controllers):
            raise ValueError(f"Controller with ID '{controller.id}' already exists")
        self.controllers.append(controller)

    def add_device(self, device: CSADeviceDef) -> None:
        """Add a device to the topology."""
        if any(d.id == device.id for d in self.devices):
            raise ValueError(f"Device with ID '{device.id}' already exists")
        self.devices.append(device)

    def add_link(self, link: CSALinkDef) -> None:
        """Add a link to the topology."""
        all_ids = {c.id for c in self.controllers} | {d.id for d in self.devices}
        if link.source not in all_ids:
            raise ValueError(f"Link source '{link.source}' not found")
        if link.target not in all_ids:
            raise ValueError(f"Link target '{link.target}' not found")
        self.links.append(link)

    def to_dict(self) -> dict[str, Any]:
        """Convert topology to dictionary for serialization."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CSATopology":
        """Create topology from dictionary."""
        return cls.model_validate(data)
