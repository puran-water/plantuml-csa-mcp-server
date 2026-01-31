"""Architecture templates for CSA bootstrap from equipment/IO lists.

Provides predefined templates for common control system configurations:
- centralized: Central MCC + Central PLC
- central_mcc_distributed_io: Central MCC + Distributed IO
- fully_distributed: Remote panels per area
- hybrid_safety: Central Safety + Distributed Process
- vendor_package_integration: OEM packages via OPC-UA
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TemplateOverrides(BaseModel):
    """Optional overrides for architecture template customization."""

    spare_io_pct: int = Field(default=20, ge=0, le=100)
    panel_counts: dict[str, int] = Field(default_factory=dict)
    protocol_preferences: list[str] = Field(
        default_factory=lambda: ["Ethernet_IP", "Profinet"]
    )
    redundancy: dict[str, str] = Field(default_factory=dict)
    plc_per_area: bool = False
    central_safety_plc: bool = False
    vfd_at_mcc: bool = True


class ArchitectureTemplate(BaseModel):
    """Architecture template definition."""

    name: str
    version: str = "1.0"
    description: str
    use_case: str
    default_overrides: TemplateOverrides = Field(default_factory=TemplateOverrides)

    # Template configuration
    plc_allocation: Literal["central", "per_area"] = "central"
    vfd_location: Literal["mcc", "remote_panel"] = "mcc"
    io_location: Literal["central", "distributed"] = "central"
    safety_plc: Literal["none", "central", "per_area"] = "none"
    vendor_integration: Literal["none", "opc_ua", "hardwired"] = "none"

    # Sizing thresholds (plant size triggers)
    max_distance_m: int = 100
    max_io_count: int = 200
    max_vfd_count: int = 20

    # Network topology
    primary_protocol: str = "Ethernet_IP"
    fieldbus_protocol: str | None = None
    redundancy_type: str = "None"


# Pre-defined architecture templates
ARCHITECTURE_TEMPLATES: dict[str, ArchitectureTemplate] = {
    "centralized": ArchitectureTemplate(
        name="centralized",
        version="1.0",
        description="Central MCC + Central PLC - all VFDs and IO in central location",
        use_case="Small plants (<5 MLD), compact footprint, short cable runs",
        plc_allocation="central",
        vfd_location="mcc",
        io_location="central",
        safety_plc="none",
        vendor_integration="none",
        max_distance_m=100,
        max_io_count=200,
        max_vfd_count=20,
        primary_protocol="Ethernet_IP",
        redundancy_type="None",
        default_overrides=TemplateOverrides(
            spare_io_pct=20,
            vfd_at_mcc=True,
            plc_per_area=False,
        ),
    ),
    "central_mcc_distributed_io": ArchitectureTemplate(
        name="central_mcc_distributed_io",
        version="1.0",
        description="Central MCC + Distributed IO - VFDs in MCC, Remote IO panels at process areas",
        use_case="Medium plants (5-20 MLD), moderate distances",
        plc_allocation="central",
        vfd_location="mcc",
        io_location="distributed",
        safety_plc="none",
        vendor_integration="none",
        max_distance_m=500,
        max_io_count=1000,
        max_vfd_count=50,
        primary_protocol="Ethernet_IP",
        redundancy_type="Hot_Standby",
        default_overrides=TemplateOverrides(
            spare_io_pct=20,
            vfd_at_mcc=True,
            plc_per_area=False,
            protocol_preferences=["Ethernet_IP", "Profinet"],
        ),
    ),
    "fully_distributed": ArchitectureTemplate(
        name="fully_distributed",
        version="1.0",
        description="Remote panels per area with VFDs, starters, and IO",
        use_case="Large plants (>20 MLD), long distances, modular expansion",
        plc_allocation="per_area",
        vfd_location="remote_panel",
        io_location="distributed",
        safety_plc="none",
        vendor_integration="none",
        max_distance_m=1000,
        max_io_count=5000,
        max_vfd_count=200,
        primary_protocol="Profinet",
        redundancy_type="Hot_Standby",
        default_overrides=TemplateOverrides(
            spare_io_pct=25,
            vfd_at_mcc=False,
            plc_per_area=True,
            protocol_preferences=["Profinet", "Ethernet_IP"],
        ),
    ),
    "hybrid_safety": ArchitectureTemplate(
        name="hybrid_safety",
        version="1.0",
        description="Central Safety PLC + Distributed process control",
        use_case="Plants with SIL requirements, ESD/SIS functions",
        plc_allocation="per_area",
        vfd_location="remote_panel",
        io_location="distributed",
        safety_plc="central",
        vendor_integration="none",
        max_distance_m=1000,
        max_io_count=5000,
        max_vfd_count=200,
        primary_protocol="Profinet",
        redundancy_type="Dual_Redundant",
        default_overrides=TemplateOverrides(
            spare_io_pct=25,
            vfd_at_mcc=False,
            plc_per_area=True,
            central_safety_plc=True,
            protocol_preferences=["Profinet"],
        ),
    ),
    "vendor_package_integration": ArchitectureTemplate(
        name="vendor_package_integration",
        version="1.0",
        description="OEM packages with vendor PLCs integrated via OPC-UA",
        use_case="Plants with multiple vendor packages (MBR, RO, DAF)",
        plc_allocation="per_area",
        vfd_location="remote_panel",
        io_location="distributed",
        safety_plc="none",
        vendor_integration="opc_ua",
        max_distance_m=1000,
        max_io_count=3000,
        max_vfd_count=100,
        primary_protocol="Ethernet_IP",
        redundancy_type="Hot_Standby",
        default_overrides=TemplateOverrides(
            spare_io_pct=20,
            vfd_at_mcc=False,
            plc_per_area=True,
            protocol_preferences=["Ethernet_IP", "OPC_UA"],
        ),
    ),
}


def get_template(name: str) -> ArchitectureTemplate | None:
    """Get architecture template by name.

    Args:
        name: Template name

    Returns:
        ArchitectureTemplate or None if not found
    """
    return ARCHITECTURE_TEMPLATES.get(name)


def list_templates() -> list[dict[str, Any]]:
    """List all available architecture templates.

    Returns:
        List of template summaries with name, version, description, use_case
    """
    return [
        {
            "name": t.name,
            "version": t.version,
            "description": t.description,
            "use_case": t.use_case,
            "plc_allocation": t.plc_allocation,
            "io_location": t.io_location,
            "vfd_location": t.vfd_location,
            "primary_protocol": t.primary_protocol,
        }
        for t in ARCHITECTURE_TEMPLATES.values()
    ]


def select_template_for_plant(
    io_count: int,
    vfd_count: int,
    max_distance_m: int,
    has_safety_requirements: bool = False,
    has_vendor_packages: bool = False,
) -> str:
    """Auto-select best template based on plant characteristics.

    Args:
        io_count: Total IO point count
        vfd_count: Total VFD count
        max_distance_m: Maximum cable run distance
        has_safety_requirements: Whether SIL/SIS is required
        has_vendor_packages: Whether vendor packages exist

    Returns:
        Recommended template name
    """
    if has_safety_requirements:
        return "hybrid_safety"

    if has_vendor_packages:
        return "vendor_package_integration"

    if io_count <= 200 and vfd_count <= 20 and max_distance_m <= 100:
        return "centralized"

    if io_count <= 1000 and vfd_count <= 50 and max_distance_m <= 500:
        return "central_mcc_distributed_io"

    return "fully_distributed"
