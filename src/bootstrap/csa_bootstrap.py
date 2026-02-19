"""Bootstrap CSA topology from equipment-list-skill and instrument-io-skill outputs.

This module transforms skill outputs into draft CSA topology YAML for refinement.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Literal

import structlog
import yaml

from ..models import (
    ControllerType,
    CSAControllerDef,
    CSADeviceDef,
    CSALinkDef,
    CSAMetadata,
    CSANetworkDef,
    CSATopology,
    CSAZone,
    DeviceType,
    ProtocolType,
    RedundancyType,
)
from ..templates import ArchitectureTemplate, TemplateOverrides, get_template

logger = structlog.get_logger(__name__)


def _extract_area(tag: str) -> str:
    """Extract area code from equipment or instrument tag. Consistent across all paths."""
    # Try leading digits (standard: 200-P-01)
    m = re.match(r"(\d{3,4})", tag)
    if m:
        return m.group(1)
    # Try embedded (ISA: PIT-200-01)
    m = re.search(r"[A-Z]+-(\d{3,4})-", tag)
    if m:
        return m.group(1)
    return "000"

# IO module sizing (typical Allen-Bradley 1756 modules)
IO_MODULE_SIZES = {
    "DI": 32,  # Points per module
    "DO": 32,
    "AI": 8,
    "AO": 8,
    "PI": 4,  # Pulse input
    "PO": 4,  # Pulse output
}


def parse_qmd_frontmatter(qmd_content: str) -> dict[str, Any]:
    """Parse YAML frontmatter from QMD file.

    QMD files have YAML frontmatter between --- markers at the start.

    Args:
        qmd_content: QMD file content

    Returns:
        Parsed YAML frontmatter as dict
    """
    # Match YAML frontmatter between --- markers
    match = re.match(r"^---\s*\n(.*?)\n---", qmd_content, re.DOTALL)
    if match:
        return yaml.safe_load(match.group(1)) or {}

    # If no frontmatter, try parsing entire content as YAML
    try:
        return yaml.safe_load(qmd_content) or {}
    except yaml.YAMLError:
        return {}


def extract_equipment_list(qmd_content: str) -> list[dict[str, Any]]:
    """Extract equipment list from equipment-list.qmd content.

    Args:
        qmd_content: QMD file content (with YAML frontmatter or direct YAML)

    Returns:
        List of equipment dictionaries
    """
    data = parse_qmd_frontmatter(qmd_content)

    # Equipment list might be at top level or under 'equipment' key
    if "equipment" in data:
        return data["equipment"]
    if isinstance(data, list):
        return data

    # Might be a dict where each key is an equipment entry
    return list(data.values()) if isinstance(data, dict) else []


def parse_instrument_database(yaml_content: str) -> dict[str, Any]:
    """Parse instrument database YAML from instrument-io-skill.

    Args:
        yaml_content: YAML content from database.yaml

    Returns:
        Parsed database dict with instruments/signals
    """
    return yaml.safe_load(yaml_content) or {}


def calculate_io_summary(
    instrument_db: dict[str, Any],
) -> dict[str, dict[str, int]]:
    """Calculate IO counts per area from instrument database.

    Args:
        instrument_db: Parsed instrument database

    Returns:
        Dict mapping area code to IO type counts
        e.g., {"200": {"DI": 45, "DO": 12, "AI": 28, "AO": 8}}
    """
    io_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"DI": 0, "DO": 0, "AI": 0, "AO": 0, "PI": 0, "PO": 0}
    )

    instruments = instrument_db.get("instruments", [])
    if not instruments:
        instruments = instrument_db.get("database", [])

    for inst in instruments:
        # Extract area from equipment_tag first (ISA format: "200-TK-03" → "200"),
        # then fall back to instrument tag (which may start with letters: "LIT-200-03")
        area = "000"

        # Strategy 1: equipment_tag field (most reliable — direct ISA equipment ref)
        eq_tag = inst.get("equipment_tag", "") or ""
        extracted = _extract_area(eq_tag)
        if extracted != "000":
            area = extracted
        else:
            # Strategy 2: instrument tag — handle nested tag dict
            raw_tag = inst.get("tag", "")
            if isinstance(raw_tag, dict):
                tag = raw_tag.get("full_tag", "") or ""
            else:
                tag = raw_tag or ""
            area = _extract_area(tag)

        # Count IO signals
        signals = inst.get("io_signals") or inst.get("signals") or []
        for signal in signals:
            io_type = (signal.get("io_type") or signal.get("type") or "").upper()
            if io_type in io_counts[area]:
                io_counts[area][io_type] += 1

    return dict(io_counts)


def calculate_rio_modules(
    io_counts: dict[str, int],
    spare_pct: int = 20,
) -> dict[str, int]:
    """Calculate Remote IO module requirements.

    Args:
        io_counts: IO type counts (DI, DO, AI, AO, PI, PO)
        spare_pct: Spare capacity percentage

    Returns:
        Dict mapping IO type to module count
    """
    modules = {}
    for io_type, count in io_counts.items():
        if count == 0:
            continue
        module_size = IO_MODULE_SIZES.get(io_type, 16)
        # Add spare capacity
        required = int(count * (1 + spare_pct / 100))
        modules[io_type] = (required + module_size - 1) // module_size

    return modules


def bootstrap_csa_topology(
    equipment_list_qmd: str,
    instrument_database_yaml: str,
    project_name: str,
    architecture_template: str = "centralized",
    template_version: str = "1.0",
    mode: Literal["strict", "lenient"] = "lenient",
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bootstrap CSA topology from skill outputs.

    Args:
        equipment_list_qmd: QMD content from equipment-list-skill
        instrument_database_yaml: YAML content from instrument-io-skill
        project_name: Project name for CSA
        architecture_template: Template name (centralized, fully_distributed, etc.)
        template_version: Template version for reproducibility
        mode: "strict" fails on ambiguity, "lenient" warns
        overrides: Optional template customizations

    Returns:
        Dict with:
        - topology_yaml: Draft CSA topology YAML string
        - suggestions: Human review items
        - io_summary: DI/DO/AI/AO counts per area
        - equipment_mapping: Equipment -> PLC mapping
        - networks: Generated network segments
    """
    logger.info(
        "bootstrap_csa_started",
        project_name=project_name,
        template=architecture_template,
    )

    suggestions: list[str] = []
    warnings: list[str] = []

    # Get template
    template = get_template(architecture_template)
    if not template:
        if mode == "strict":
            raise ValueError(f"Unknown template: {architecture_template}")
        warnings.append(f"Unknown template '{architecture_template}', using 'centralized'")
        template = get_template("centralized")

    # Apply overrides
    template_overrides = TemplateOverrides(**(overrides or {}))

    # Parse inputs
    equipment_list = extract_equipment_list(equipment_list_qmd)
    instrument_db = parse_instrument_database(instrument_database_yaml)

    if not equipment_list:
        warnings.append("No equipment found in equipment list")
    if not instrument_db:
        warnings.append("No instruments found in database")

    # Calculate IO summary
    io_summary = calculate_io_summary(instrument_db)

    # Build topology
    zones = _create_zones()
    controllers: list[CSAControllerDef] = []
    devices: list[CSADeviceDef] = []
    links: list[CSALinkDef] = []
    networks: list[CSANetworkDef] = []
    equipment_mapping: dict[str, str] = {}

    # Group equipment by area
    equipment_by_area: dict[str, list[dict]] = defaultdict(list)
    vendor_packages: list[dict] = []

    for equip in equipment_list:
        tag = equip.get("tag", equip.get("equipment_tag", ""))
        area = _extract_area(tag)

        control_resp = (equip.get("control_responsibility") or "plc").lower()
        if control_resp == "vendor":
            vendor_packages.append(equip)
        else:
            equipment_by_area[area].append(equip)

    areas = sorted(equipment_by_area.keys())

    # Create networks
    control_net = CSANetworkDef(
        id="control_net",
        name="Control Network",
        protocol=ProtocolType(template.primary_protocol),
        zone="level_1",
        subnet="192.168.1.0/24",
    )
    networks.append(control_net)

    device_net = CSANetworkDef(
        id="device_net",
        name="Device Network",
        protocol=ProtocolType(template.primary_protocol),
        zone="level_0",
        subnet="192.168.2.0/24",
    )
    networks.append(device_net)

    # Create PLCs based on template
    if template.plc_allocation == "central":
        # Single central PLC
        main_plc = CSAControllerDef(
            id="PLC-001",
            type=ControllerType.PLC,
            zone="level_1",
            redundancy=RedundancyType(template.redundancy_type),
            ip_address="192.168.1.10",
            description="Main Process PLC",
            equipment_tags=[],
        )
        controllers.append(main_plc)

        # Map all equipment to main PLC
        for area, equip_list in equipment_by_area.items():
            for equip in equip_list:
                tag = equip.get("tag", equip.get("equipment_tag", ""))
                if tag:
                    main_plc.equipment_tags.append(tag)
                    equipment_mapping[tag] = "PLC-001"

    else:
        # PLC per area — enumerate unique areas for collision-free IPs
        area_ip_map = {a: f"192.168.1.{10 + i}" for i, a in enumerate(areas)}
        for area in areas:
            plc_id = f"PLC-{area}"
            plc = CSAControllerDef(
                id=plc_id,
                type=ControllerType.PLC,
                zone="level_1",
                redundancy=RedundancyType(template.redundancy_type),
                ip_address=area_ip_map[area],
                description=f"Area {area} PLC",
                equipment_tags=[],
            )

            for equip in equipment_by_area[area]:
                tag = equip.get("tag", equip.get("equipment_tag", ""))
                if tag:
                    plc.equipment_tags.append(tag)
                    equipment_mapping[tag] = plc_id

            controllers.append(plc)

    # Add Safety PLC if required
    if template.safety_plc == "central":
        safety_plc = CSAControllerDef(
            id="SIS-001",
            type=ControllerType.SAFETY_PLC,
            zone="level_1",
            redundancy=RedundancyType.DUAL_REDUNDANT,
            ip_address="192.168.1.100",
            description="Safety Instrumented System",
        )
        controllers.append(safety_plc)

    # Create Remote IO / VFDs based on template
    device_ip_counter = 100
    rio_node_ids: set[str] = set()

    for area in areas:
        area_equip = equipment_by_area[area]
        area_io = io_summary.get(area, {})

        # Determine parent PLC
        if template.plc_allocation == "central":
            parent_plc = "PLC-001"
        else:
            parent_plc = f"PLC-{area}"

        # Create Remote IO panel if distributed
        if template.io_location == "distributed" and any(area_io.values()):
            rio_id = f"RIO-{area}"
            rio = CSADeviceDef(
                id=rio_id,
                type=DeviceType.REMOTE_IO,
                parent_controller=parent_plc,
                zone="level_0",
                ip_address=f"192.168.2.{device_ip_counter}",
                description=f"Area {area} Remote IO",
            )
            devices.append(rio)
            rio_node_ids.add(rio_id)
            device_ip_counter += 1

            # Link to parent PLC
            links.append(
                CSALinkDef(
                    source=parent_plc,
                    target=rio_id,
                    protocol=ProtocolType(template.primary_protocol),
                    network="device_net",
                )
            )

            # Calculate module requirements
            modules = calculate_rio_modules(area_io, template_overrides.spare_io_pct)
            suggestions.append(
                f"Area {area} RIO modules: {modules} (based on {area_io})"
            )

        # Create VFDs
        for equip in area_equip:
            feeder_type = (equip.get("feeder_type") or "").upper()
            tag = equip.get("tag", equip.get("equipment_tag", ""))

            if feeder_type == "VFD":
                vfd_id = f"VFD-{tag}"
                vfd = CSADeviceDef(
                    id=vfd_id,
                    type=DeviceType.VFD,
                    parent_controller=parent_plc,
                    zone="level_0",
                    ip_address=f"192.168.2.{device_ip_counter}",
                    description=f"VFD for {tag}",
                )
                devices.append(vfd)
                device_ip_counter += 1

                # Determine link source: RIO if distributed, PLC if centralized
                if template.io_location == "distributed":
                    rio_id = f"RIO-{area}"
                    vfd_link_source = rio_id if rio_id in rio_node_ids else parent_plc
                else:
                    vfd_link_source = parent_plc

                links.append(
                    CSALinkDef(
                        source=vfd_link_source,
                        target=vfd_id,
                        protocol=ProtocolType(template.primary_protocol),
                        network="device_net",
                    )
                )

            elif feeder_type in ("SOFT-STARTER", "SOFT_STARTER"):
                ss_id = f"SS-{tag}"
                ss = CSADeviceDef(
                    id=ss_id,
                    type=DeviceType.SOFT_STARTER,
                    parent_controller=parent_plc,
                    zone="level_0",
                    description=f"Soft Starter for {tag}",
                )
                devices.append(ss)

                # Determine link source: RIO if distributed, PLC if centralized
                if template.io_location == "distributed":
                    rio_id = f"RIO-{area}"
                    ss_link_source = rio_id if rio_id in rio_node_ids else parent_plc
                else:
                    ss_link_source = parent_plc

                links.append(
                    CSALinkDef(
                        source=ss_link_source,
                        target=ss_id,
                        protocol=ProtocolType(template.primary_protocol),
                        network="device_net",
                    )
                )

    # Handle vendor packages
    for pkg in vendor_packages:
        tag = pkg.get("tag", pkg.get("equipment_tag", ""))
        pkg_id = f"PKG-{tag}"

        # Create vendor PLC node
        vendor_plc = CSAControllerDef(
            id=pkg_id,
            type=ControllerType.PLC,
            zone="level_1",
            ip_address=f"192.168.1.{device_ip_counter}",
            description=f"Vendor PLC - {tag}",
        )
        controllers.append(vendor_plc)
        device_ip_counter += 1

        suggestions.append(
            f"Vendor package '{tag}': Create OPC-UA gateway and hardwired interlocks"
        )

        # Add OPC-UA link to main PLC if using OPC-UA integration
        if template.vendor_integration == "opc_ua" and controllers:
            main_plc_id = controllers[0].id
            links.append(
                CSALinkDef(
                    source=main_plc_id,
                    target=pkg_id,
                    protocol=ProtocolType.OPC_UA,
                    description="Vendor package integration",
                )
            )

    # Add network switches
    sw_id = "SW-001"
    switch = CSADeviceDef(
        id=sw_id,
        type=DeviceType.MANAGED_SWITCH,
        zone="level_1",
        ip_address="192.168.1.1",
        description="Control Network Switch",
    )
    devices.append(switch)

    # Link all PLCs to switch
    for ctrl in controllers:
        links.append(
            CSALinkDef(
                source=ctrl.id,
                target=sw_id,
                protocol=ProtocolType(template.primary_protocol),
                network="control_net",
            )
        )

    # Add SCADA
    scada = CSADeviceDef(
        id="SCADA-001",
        type=DeviceType.SCADA,
        zone="level_2",
        ip_address="192.168.2.10",
        description="SCADA Server",
    )
    devices.append(scada)

    # Link switch to SCADA
    links.append(
        CSALinkDef(
            source=sw_id,
            target="SCADA-001",
            protocol=ProtocolType(template.primary_protocol),
        )
    )

    # Build topology
    topology = CSATopology(
        schema_version="1.0",
        metadata=CSAMetadata(
            project_name=project_name,
            description=f"Generated from {architecture_template} template",
        ),
        zones=zones,
        controllers=controllers,
        devices=devices,
        networks=networks,
        links=links,
    )

    # Add review suggestions
    if not equipment_list:
        suggestions.append("No equipment parsed - verify equipment-list.qmd format")
    if not io_summary:
        suggestions.append("No IO signals parsed - verify database.yaml format")

    for area, counts in io_summary.items():
        total = sum(counts.values())
        if total > 500:
            suggestions.append(
                f"Area {area} has {total} IO points - consider additional RIO panels"
            )

    logger.info(
        "bootstrap_csa_complete",
        controllers=len(controllers),
        devices=len(devices),
        links=len(links),
        suggestions=len(suggestions),
    )

    return {
        "topology_yaml": yaml.dump(
            topology.model_dump(mode="json", exclude_none=True),
            sort_keys=False,
            default_flow_style=False,
        ),
        "suggestions": suggestions,
        "warnings": warnings,
        "io_summary": io_summary,
        "equipment_mapping": equipment_mapping,
        "networks": [n.model_dump(mode="json") for n in networks],
        "template_used": architecture_template,
        "template_version": template_version,
    }


def _create_zones() -> list[CSAZone]:
    """Create standard Purdue model zones."""
    return [
        CSAZone(id="level_0", name="Field Level", purdue_level=0),
        CSAZone(id="level_1", name="Control Level", purdue_level=1),
        CSAZone(id="level_2", name="Supervisory Level", purdue_level=2),
    ]
