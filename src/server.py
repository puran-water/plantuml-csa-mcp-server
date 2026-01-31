"""FastMCP server for PlantUML CSA diagram generation.

Exposes MCP tools for generating Control System Architecture diagrams
using PlantUML, with same YAML schema as FreeCAD CSA for interoperability.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Literal

import structlog
import yaml
from mcp.server.fastmcp import FastMCP

from .converter import TopologyToPumlConverter
from .converter.layout_hints import LayoutDirection, LayoutEngine
from .encoder import encode_plantuml, get_plantuml_urls
from .models import CSATopology
from .renderer import PlantUMLError, PlantUMLRunner

# Configure structured logging (JSON to stderr for MCP compatibility)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Ensure stdlib logging goes to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stderr,
)

logger = structlog.get_logger(__name__)

# Response detail level type
DetailLevel = Literal["compact", "full"]

# Create MCP server
mcp = FastMCP(
    name="plantuml_csa_mcp",
    instructions="Generate Control System Architecture (CSA) diagrams using PlantUML. "
    "Use csa_generate_diagram to render topology YAML to SVG/PNG, "
    "csa_get_plantuml_source to get .puml source for version control, "
    "and csa_encode_plantuml to get shareable URLs.",
)

# PlantUML runner instance
_runner: PlantUMLRunner | None = None


def _get_runner() -> PlantUMLRunner:
    """Get or create PlantUML runner instance."""
    global _runner
    if _runner is None:
        _runner = PlantUMLRunner()
    return _runner


def _parse_topology(topology_yaml: str) -> CSATopology:
    """Parse YAML string to CSATopology model.

    Args:
        topology_yaml: YAML topology string

    Returns:
        Validated CSATopology model

    Raises:
        ValueError: If YAML is invalid or doesn't match schema
    """
    try:
        data = yaml.safe_load(topology_yaml)
        if not isinstance(data, dict):
            raise ValueError("Topology YAML must be a dictionary")
        return CSATopology.model_validate(data)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}") from e


@mcp.tool(
    annotations={
        "readOnlyHint": False,  # May create output file
        "destructiveHint": False,
        "idempotentHint": True,  # Same input produces same output
        "openWorldHint": False,
    }
)
async def csa_generate_diagram(
    topology_yaml: str,
    format: Literal["svg", "png"] = "svg",
    layout: LayoutDirection = "hierarchical",
    layout_engine: LayoutEngine = "graphviz",
    output_path: str | None = None,
    font: str = "Arial",
    theme: str = "csa_industrial",
    show_zones: bool = True,
    show_protocols: bool = True,
    show_legend: bool = True,
) -> dict[str, Any]:
    """Generate CSA diagram from YAML topology.

    Renders a Control System Architecture diagram using PlantUML with
    ISA-95 Purdue model awareness and industrial component styling.

    Args:
        topology_yaml: YAML topology string (same schema as FreeCAD CSA)
        format: Output format - 'svg' (default) or 'png'
        layout: Layout direction - 'hierarchical', 'top_to_bottom', or 'left_to_right'
        layout_engine: Layout engine - 'graphviz' (default), 'smetana', or 'elk'
        output_path: Optional path to save output file
        font: Font family name (default: 'Arial')
        theme: Theme name (default: 'csa_industrial')
        show_zones: Render Purdue zone packages (default: True)
        show_protocols: Show protocol labels on links (default: True)
        show_legend: Include protocol legend (default: True)

    Returns:
        Dict with success, image_data (base64), plantuml_source, file_path (if saved)
    """
    logger.info(
        "csa_generate_diagram_started",
        format=format,
        layout=layout,
        layout_engine=layout_engine,
    )

    try:
        # Parse and validate topology
        topology = _parse_topology(topology_yaml)

        # Convert to PlantUML source
        converter = TopologyToPumlConverter(
            topology=topology,
            layout=layout,
            layout_engine=layout_engine,
            show_zones=show_zones,
            show_protocols=show_protocols,
            show_legend=show_legend,
            font=font,
            theme=theme,
        )
        puml_source = converter.convert()

        # Render diagram
        runner = _get_runner()
        image_data_b64 = runner.render_base64(puml_source, format)

        # Save to file if requested
        file_path = None
        if output_path:
            image_bytes, file_path = runner.render(puml_source, format, output_path)

        result = {
            "success": True,
            "format": format,
            "image_data": image_data_b64,
            "plantuml_source": puml_source,
            "component_count": converter.get_component_count(),
            "line_count": len(puml_source.splitlines()),
        }

        if file_path:
            result["file_path"] = file_path

        logger.info(
            "csa_generate_diagram_complete",
            format=format,
            component_count=result["component_count"],
        )

        return result

    except ValueError as e:
        logger.warning("csa_generate_diagram_validation_error", error=str(e))
        return {
            "success": False,
            "isError": True,
            "error": str(e),
            "suggestion": "Validate topology YAML with csa_validate_topology first",
        }
    except PlantUMLError as e:
        logger.error("csa_generate_diagram_render_error", error=str(e))
        return {
            "success": False,
            "isError": True,
            "error": str(e),
            "suggestion": "Check PlantUML installation or use csa_get_plantuml_source for manual rendering",
        }
    except Exception as e:
        logger.exception("csa_generate_diagram_failed", error=str(e))
        return {
            "success": False,
            "isError": True,
            "error": str(e),
        }


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def csa_get_plantuml_source(
    topology_yaml: str,
    layout: LayoutDirection = "hierarchical",
    layout_engine: LayoutEngine = "graphviz",
    show_zones: bool = True,
    show_protocols: bool = True,
    show_legend: bool = True,
) -> dict[str, Any]:
    """Convert CSA topology to PlantUML source without rendering.

    Returns the .puml source code for version control, manual editing,
    or CI/CD pipelines. Does NOT require PlantUML installation.

    Security: Disables !include directives to prevent file disclosure.

    Args:
        topology_yaml: YAML topology string
        layout: Layout direction
        layout_engine: Layout engine pragma
        show_zones: Render Purdue zone packages
        show_protocols: Show protocol labels on links
        show_legend: Include protocol legend

    Returns:
        Dict with plantuml_source, line_count, component_count
    """
    logger.info("csa_get_plantuml_source_started", layout=layout)

    try:
        topology = _parse_topology(topology_yaml)

        converter = TopologyToPumlConverter(
            topology=topology,
            layout=layout,
            layout_engine=layout_engine,
            show_zones=show_zones,
            show_protocols=show_protocols,
            show_legend=show_legend,
        )
        puml_source = converter.convert()

        return {
            "success": True,
            "plantuml_source": puml_source,
            "line_count": len(puml_source.splitlines()),
            "component_count": converter.get_component_count(),
        }

    except ValueError as e:
        return {
            "success": False,
            "isError": True,
            "error": str(e),
            "suggestion": "Validate topology YAML with csa_validate_topology first",
        }
    except Exception as e:
        logger.exception("csa_get_plantuml_source_failed", error=str(e))
        return {
            "success": False,
            "isError": True,
            "error": str(e),
        }


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def csa_validate_topology(
    topology_yaml: str,
    strict: bool = False,
) -> dict[str, Any]:
    """Validate YAML topology against CSA schema.

    Checks:
    - YAML syntax validity
    - Required fields present
    - Reference integrity (zones, controllers, devices, links)
    - Enum values (controller types, device types, protocols)

    Args:
        topology_yaml: YAML topology string to validate
        strict: If True, treat warnings as errors

    Returns:
        Dict with valid (bool), errors[], warnings[], summary
    """
    logger.info("csa_validate_topology_started", strict=strict)

    errors: list[str] = []
    warnings: list[str] = []

    try:
        # Parse YAML
        data = yaml.safe_load(topology_yaml)
        if not isinstance(data, dict):
            errors.append("Topology must be a YAML dictionary/object")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "summary": "Invalid YAML structure",
            }

        # Validate against Pydantic model
        topology = CSATopology.model_validate(data)

        # Additional checks
        if not topology.controllers and not topology.devices:
            warnings.append("Topology has no controllers or devices")

        if not topology.zones:
            warnings.append("No Purdue zones defined - components will render flat")

        if not topology.links:
            warnings.append("No network links defined")

        # Check for orphan components (no zone)
        for controller in topology.controllers:
            if not controller.zone:
                warnings.append(f"Controller '{controller.id}' has no zone assigned")
        for device in topology.devices:
            if not device.zone:
                warnings.append(f"Device '{device.id}' has no zone assigned")

        # Check for devices without parent controller
        for device in topology.devices:
            if (
                device.type.value
                in ["RemoteIO", "VFD", "Soft_Starter", "Motor_Starter"]
                and not device.parent_controller
            ):
                warnings.append(
                    f"Device '{device.id}' ({device.type.value}) has no parent_controller"
                )

        valid = len(errors) == 0 and (not strict or len(warnings) == 0)

        summary_parts = []
        summary_parts.append(f"{len(topology.controllers)} controller(s)")
        summary_parts.append(f"{len(topology.devices)} device(s)")
        summary_parts.append(f"{len(topology.links)} link(s)")
        summary_parts.append(f"{len(topology.zones)} zone(s)")

        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "summary": ", ".join(summary_parts),
            "counts": {
                "controllers": len(topology.controllers),
                "devices": len(topology.devices),
                "links": len(topology.links),
                "zones": len(topology.zones),
                "networks": len(topology.networks),
            },
        }

    except yaml.YAMLError as e:
        errors.append(f"YAML syntax error: {e}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "summary": "YAML parse failed",
        }
    except ValueError as e:
        errors.append(f"Schema validation error: {e}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "summary": "Schema validation failed",
        }
    except Exception as e:
        logger.exception("csa_validate_topology_failed", error=str(e))
        errors.append(f"Unexpected error: {e}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "summary": "Validation failed",
        }


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def csa_list_symbols(
    category: Literal["controllers", "devices", "network", "protocols", "all"] = "all",
) -> dict[str, Any]:
    """List available ISA-style symbols for CSA diagrams.

    Returns the symbols available for each category with their
    stereotypes and default colors.

    Args:
        category: Filter by category - 'controllers', 'devices', 'network',
                 'protocols', or 'all' (default)

    Returns:
        Dict with symbols array containing id, category, stereotype, color
    """
    from .converter.sprites import (
        CONTROLLER_SPRITES,
        DEVICE_SPRITES,
        PROTOCOL_COLORS,
        ZONE_COLORS,
    )
    from .models import ControllerType, DeviceType, ProtocolType

    symbols: list[dict[str, str]] = []

    if category in ("controllers", "all"):
        for ct in ControllerType:
            style = CONTROLLER_SPRITES.get(ct, {})
            symbols.append(
                {
                    "id": ct.value,
                    "category": "controller",
                    "stereotype": style.get("stereotype", f"<<{ct.value}>>"),
                    "color": style.get("color", "#95A5A6"),
                    "shape": style.get("shape", "rectangle"),
                }
            )

    if category in ("devices", "network", "all"):
        network_types = {"Switch", "Managed_Switch", "Router", "Firewall", "Wireless_AP"}
        for dt in DeviceType:
            is_network = dt.value in network_types
            if category == "network" and not is_network:
                continue
            if category == "devices" and is_network:
                continue

            style = DEVICE_SPRITES.get(dt, {})
            symbols.append(
                {
                    "id": dt.value,
                    "category": "network" if is_network else "device",
                    "stereotype": style.get("stereotype", f"<<{dt.value}>>"),
                    "color": style.get("color", "#BDC3C7"),
                    "shape": style.get("shape", "rectangle"),
                }
            )

    if category in ("protocols", "all"):
        for pt in ProtocolType:
            style = PROTOCOL_COLORS.get(pt, {})
            symbols.append(
                {
                    "id": pt.value,
                    "category": "protocol",
                    "label": style.get("label", pt.value),
                    "color": style.get("color", "#7F8C8D"),
                    "style": style.get("style", "solid"),
                }
            )

    return {
        "symbols": symbols,
        "count": len(symbols),
        "category_filter": category,
    }


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def csa_encode_plantuml(
    plantuml_source: str,
    server_url: str = "https://www.plantuml.com/plantuml",
) -> dict[str, Any]:
    """Encode PlantUML source for shareable URL.

    Generates URLs for PlantUML server that can render the diagram
    without requiring local PlantUML installation.

    Args:
        plantuml_source: PlantUML source text (from csa_get_plantuml_source)
        server_url: PlantUML server URL (default: plantuml.com)

    Returns:
        Dict with encoded string, svg_url, png_url, edit_url
    """
    logger.info("csa_encode_plantuml_started", source_length=len(plantuml_source))

    try:
        encoded = encode_plantuml(plantuml_source)
        urls = get_plantuml_urls(encoded, server_url)

        return {
            "success": True,
            "encoded": encoded,
            "svg_url": urls["svg_url"],
            "png_url": urls["png_url"],
            "edit_url": urls["edit_url"],
        }

    except Exception as e:
        logger.exception("csa_encode_plantuml_failed", error=str(e))
        return {
            "success": False,
            "isError": True,
            "error": str(e),
        }


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def csa_render_preview(
    topology_yaml: str,
    layout_engine: LayoutEngine = "smetana",
) -> dict[str, Any]:
    """Quick preview render without full validation (for iteration).

    Uses Smetana layout engine by default for faster rendering without
    external Graphviz dependency.

    Args:
        topology_yaml: YAML topology string
        layout_engine: Layout engine (default: 'smetana' for speed)

    Returns:
        Dict with preview_svg (low-res), warnings[], render_time_ms
    """
    import time

    logger.info("csa_render_preview_started", layout_engine=layout_engine)
    start_time = time.monotonic()

    warnings: list[str] = []

    try:
        # Quick parse without full validation
        data = yaml.safe_load(topology_yaml)
        if not isinstance(data, dict):
            return {
                "success": False,
                "isError": True,
                "error": "Invalid YAML structure",
            }

        # Try to create topology, collect warnings instead of failing
        try:
            topology = CSATopology.model_validate(data)
        except ValueError as e:
            warnings.append(f"Validation warning: {e}")
            # Create minimal topology for preview
            topology = CSATopology(
                metadata=data.get("metadata", {}),
                zones=data.get("zones", []),
                controllers=data.get("controllers", []),
                devices=data.get("devices", []),
                links=[],  # Skip links to avoid validation errors
            )

        # Convert with minimal options
        converter = TopologyToPumlConverter(
            topology=topology,
            layout="hierarchical",
            layout_engine=layout_engine,
            show_zones=True,
            show_protocols=False,  # Faster without protocol labels
            show_legend=False,  # Skip legend for speed
        )
        puml_source = converter.convert()

        # Render preview
        runner = _get_runner()
        preview_svg_b64 = runner.render_base64(puml_source, "svg")

        render_time_ms = int((time.monotonic() - start_time) * 1000)

        return {
            "success": True,
            "preview_svg": preview_svg_b64,
            "warnings": warnings,
            "render_time_ms": render_time_ms,
            "component_count": converter.get_component_count(),
        }

    except PlantUMLError as e:
        return {
            "success": False,
            "isError": True,
            "error": str(e),
            "warnings": warnings,
            "suggestion": "PlantUML not available - use csa_encode_plantuml for server-side rendering",
        }
    except Exception as e:
        logger.exception("csa_render_preview_failed", error=str(e))
        return {
            "success": False,
            "isError": True,
            "error": str(e),
            "warnings": warnings,
        }


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def csa_check_plantuml() -> dict[str, Any]:
    """Check PlantUML availability and backend.

    Returns status of PlantUML installation for diagnostics.

    Returns:
        Dict with available (bool), backend type, or error message
    """
    runner = _get_runner()
    status = runner.check_available()

    return {
        "available": status.get("available", False),
        "backend": status.get("backend"),
        "error": status.get("error"),
    }


# =============================================================================
# Phase 2: Architecture Templates & Bootstrap Tools
# =============================================================================


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def csa_list_templates() -> dict[str, Any]:
    """List available architecture templates with versions.

    Returns predefined templates for common control system configurations:
    - centralized: Central MCC + Central PLC
    - central_mcc_distributed_io: Central MCC + Distributed IO
    - fully_distributed: Remote panels per area
    - hybrid_safety: Central Safety + Distributed Process
    - vendor_package_integration: OEM packages via OPC-UA

    Returns:
        Dict with templates array containing name, version, description, use_case
    """
    from .templates import list_templates

    templates = list_templates()

    return {
        "templates": templates,
        "count": len(templates),
    }


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def csa_bootstrap_from_io(
    equipment_list_qmd: str,
    instrument_database_yaml: str,
    project_name: str,
    architecture_template: str = "centralized",
    template_version: str = "1.0",
    mode: Literal["strict", "lenient"] = "lenient",
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bootstrap CSA topology from equipment-list-skill + instrument-io-skill outputs.

    This is the core integration tool for generating CSA diagrams from P&ID-derived data.
    Parses equipment list (feeder_type, control_responsibility) and instrument database
    (io_signals) to auto-generate a draft CSA topology.

    Args:
        equipment_list_qmd: QMD file content with YAML frontmatter (from equipment-list-skill)
        instrument_database_yaml: YAML content from instrument-io-skill database.yaml
        project_name: Project name for CSA topology
        architecture_template: Template name - 'centralized', 'central_mcc_distributed_io',
            'fully_distributed', 'hybrid_safety', 'vendor_package_integration'
        template_version: Template version for reproducibility (default: "1.0")
        mode: "strict" fails on ambiguity, "lenient" warns (default: "lenient")
        overrides: Optional customizations:
            - spare_io_pct: Spare IO percentage (default: 20)
            - panel_counts: Override panel allocation per area
            - protocol_preferences: Preferred protocols ["Profinet", "Ethernet_IP"]
            - redundancy: Redundancy settings per controller type

    Returns:
        Dict with:
        - topology_yaml: Draft CSA topology YAML for refinement
        - suggestions: Human review items
        - io_summary: DI/DO/AI/AO/PI/PO counts per area
        - equipment_mapping: Which equipment -> which PLC
        - networks: Generated network segments for FreeCAD parity
        - template_used: Template name applied
    """
    from .bootstrap import bootstrap_csa_topology

    logger.info(
        "csa_bootstrap_from_io_started",
        project_name=project_name,
        template=architecture_template,
        mode=mode,
    )

    try:
        result = bootstrap_csa_topology(
            equipment_list_qmd=equipment_list_qmd,
            instrument_database_yaml=instrument_database_yaml,
            project_name=project_name,
            architecture_template=architecture_template,
            template_version=template_version,
            mode=mode,
            overrides=overrides,
        )

        result["success"] = True
        return result

    except ValueError as e:
        logger.warning("csa_bootstrap_from_io_validation_error", error=str(e))
        return {
            "success": False,
            "isError": True,
            "error": str(e),
            "suggestion": "Check equipment_list_qmd and instrument_database_yaml formats",
        }
    except Exception as e:
        logger.exception("csa_bootstrap_from_io_failed", error=str(e))
        return {
            "success": False,
            "isError": True,
            "error": str(e),
        }


def run_server():
    """Run the MCP server (MCP transport only)."""
    logger.info("plantuml_csa_mcp_server_starting")
    mcp.run()


def main():
    """Main entry point."""
    run_server()


if __name__ == "__main__":
    main()
