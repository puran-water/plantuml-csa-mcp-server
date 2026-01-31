"""Convert CSA Topology YAML to PlantUML source.

This module transforms CSATopology Pydantic models into PlantUML diagram source
with ISA-95 Purdue model awareness and industrial component styling.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .layout_hints import (
    LayoutDirection,
    LayoutEngine,
    get_layout_directive,
    get_layout_engine_config,
    get_legend_block,
    get_skinparam_base,
)
from .sprites import (
    get_controller_style,
    get_device_style,
    get_protocol_style,
    get_zone_style,
)

if TYPE_CHECKING:
    from ..models import (
        CSAControllerDef,
        CSADeviceDef,
        CSALinkDef,
        CSATopology,
        CSAZone,
    )


class TopologyToPumlConverter:
    """Converts CSA topology to PlantUML source code.

    Features:
    - Purdue model zone packages with color coding
    - ISA-style component stereotypes
    - Protocol-colored network links
    - Multiple layout options
    - Configurable layout engines for deterministic output
    """

    def __init__(
        self,
        topology: CSATopology,
        layout: LayoutDirection = "hierarchical",
        layout_engine: LayoutEngine = "graphviz",
        show_zones: bool = True,
        show_protocols: bool = True,
        show_legend: bool = True,
        font: str = "Arial",
        theme: str = "csa_industrial",
    ):
        """Initialize converter.

        Args:
            topology: CSA topology to convert
            layout: Layout direction (top_to_bottom, left_to_right, hierarchical)
            layout_engine: Layout engine (graphviz, smetana, elk)
            show_zones: Whether to render Purdue zone packages
            show_protocols: Whether to show protocol labels on links
            show_legend: Whether to include protocol legend
            font: Font family name
            theme: Theme name for styling
        """
        self.topology = topology
        self.layout = layout
        self.layout_engine = layout_engine
        self.show_zones = show_zones
        self.show_protocols = show_protocols
        self.show_legend = show_legend
        self.font = font
        self.theme = theme

        # Build lookup maps
        self._zone_map: dict[str, CSAZone] = {z.id: z for z in topology.zones}
        self._controller_map: dict[str, CSAControllerDef] = {
            c.id: c for c in topology.controllers
        }
        self._device_map: dict[str, CSADeviceDef] = {d.id: d for d in topology.devices}

    def convert(self) -> str:
        """Convert topology to PlantUML source.

        Returns:
            Complete PlantUML diagram source
        """
        lines: list[str] = []

        # Header
        lines.append("@startuml")
        lines.append("")

        # Security: disable !include to prevent file disclosure
        lines.append("' Security: disable file includes")
        lines.append("!pragma teoz false")
        lines.append("")

        # Layout engine pragma (if not graphviz default)
        engine_config = get_layout_engine_config(self.layout_engine)
        if engine_config:
            lines.append(engine_config)
            lines.append("")

        # Title
        title = self.topology.metadata.project_name
        if self.topology.metadata.revision:
            title += f" (Rev {self.topology.metadata.revision})"
        lines.append(f"title {title}")
        lines.append("")

        # Layout direction
        lines.append(get_layout_directive(self.layout))
        lines.append("")

        # Skinparam styling
        lines.append(get_skinparam_base(self.theme, self.font))
        lines.append("")

        # Render zones with components
        if self.show_zones and self.topology.zones:
            lines.extend(self._render_zones())
        else:
            # Render components without zone packages
            lines.extend(self._render_controllers_flat())
            lines.extend(self._render_devices_flat())

        lines.append("")

        # Render links
        lines.extend(self._render_links())
        lines.append("")

        # Legend
        if self.show_legend:
            legend = get_legend_block(self.show_protocols)
            if legend:
                lines.append(legend)
                lines.append("")

        # Footer
        lines.append("@enduml")

        return "\n".join(lines)

    def _render_zones(self) -> list[str]:
        """Render Purdue zone packages with components inside."""
        lines: list[str] = []

        # Sort zones by Purdue level (highest first for visual hierarchy)
        sorted_zones = sorted(
            self.topology.zones, key=lambda z: z.purdue_level, reverse=True
        )

        for zone in sorted_zones:
            style = get_zone_style(zone.purdue_level)
            zone_name = zone.name or style["name"]

            lines.append(
                f'package "{zone_name}" as {self._sanitize_id(zone.id)} {style["background"]} {{'
            )

            # Controllers in this zone
            for controller in self.topology.controllers:
                if controller.zone == zone.id:
                    lines.extend(self._render_controller(controller, indent=2))

            # Devices in this zone
            for device in self.topology.devices:
                if device.zone == zone.id:
                    lines.extend(self._render_device(device, indent=2))

            lines.append("}")
            lines.append("")

        # Render orphan components (no zone assigned)
        orphan_controllers = [c for c in self.topology.controllers if not c.zone]
        orphan_devices = [d for d in self.topology.devices if not d.zone]

        if orphan_controllers or orphan_devices:
            lines.append('package "Unassigned" as unassigned #ECEFF1 {')
            for controller in orphan_controllers:
                lines.extend(self._render_controller(controller, indent=2))
            for device in orphan_devices:
                lines.extend(self._render_device(device, indent=2))
            lines.append("}")
            lines.append("")

        return lines

    def _render_controllers_flat(self) -> list[str]:
        """Render controllers without zone packages."""
        lines: list[str] = []
        for controller in self.topology.controllers:
            lines.extend(self._render_controller(controller, indent=0))
        return lines

    def _render_devices_flat(self) -> list[str]:
        """Render devices without zone packages."""
        lines: list[str] = []
        for device in self.topology.devices:
            lines.extend(self._render_device(device, indent=0))
        return lines

    def _render_controller(
        self, controller: CSAControllerDef, indent: int = 0
    ) -> list[str]:
        """Render a single controller component."""
        lines: list[str] = []
        prefix = "  " * indent

        style = get_controller_style(controller.type)
        safe_id = self._sanitize_id(controller.id)

        # Build label with details
        label_parts = [controller.id]
        if controller.model:
            label_parts.append(controller.model)
        if controller.ip_address:
            label_parts.append(controller.ip_address)

        label = "\\n".join(label_parts)

        # Render based on shape
        if style["shape"] == "database":
            lines.append(
                f'{prefix}database "{label}" as {safe_id} {style["stereotype"]} {style["color"]}'
            )
        elif style["shape"] == "hexagon":
            lines.append(
                f'{prefix}hexagon "{label}" as {safe_id} {style["stereotype"]} {style["color"]}'
            )
        else:
            lines.append(
                f'{prefix}rectangle "{label}" as {safe_id} {style["stereotype"]} {style["color"]}'
            )

        return lines

    def _render_device(self, device: CSADeviceDef, indent: int = 0) -> list[str]:
        """Render a single device component."""
        lines: list[str] = []
        prefix = "  " * indent

        style = get_device_style(device.type)
        safe_id = self._sanitize_id(device.id)

        # Build label
        label_parts = [device.id]
        if device.model:
            label_parts.append(device.model)
        if device.ip_address:
            label_parts.append(device.ip_address)

        label = "\\n".join(label_parts)

        # Render based on shape
        if style["shape"] == "database":
            lines.append(
                f'{prefix}database "{label}" as {safe_id} {style["stereotype"]} {style["color"]}'
            )
        elif style["shape"] == "hexagon":
            lines.append(
                f'{prefix}hexagon "{label}" as {safe_id} {style["stereotype"]} {style["color"]}'
            )
        else:
            lines.append(
                f'{prefix}rectangle "{label}" as {safe_id} {style["stereotype"]} {style["color"]}'
            )

        return lines

    def _render_links(self) -> list[str]:
        """Render network links with protocol styling."""
        lines: list[str] = []
        lines.append("' Network Links")

        for link in self.topology.links:
            style = get_protocol_style(link.protocol)
            source_id = self._sanitize_id(link.source)
            target_id = self._sanitize_id(link.target)

            # Build link style
            link_style = f'[{style["color"]}'
            if style["style"] == "dashed":
                link_style += ",dashed"
            elif style["style"] == "dotted":
                link_style += ",dotted"
            link_style += "]"

            # Build link with optional label
            if self.show_protocols:
                label = style["label"]
                if link.cable_type:
                    label += f"\\n{link.cable_type}"
                lines.append(f'{source_id} -{link_style}-> {target_id} : "{label}"')
            else:
                lines.append(f"{source_id} -{link_style}-> {target_id}")

        return lines

    def _sanitize_id(self, component_id: str) -> str:
        """Sanitize component ID for PlantUML compatibility.

        PlantUML IDs cannot contain hyphens or special characters.
        """
        return component_id.replace("-", "_").replace(".", "_").replace(" ", "_")

    def get_component_count(self) -> int:
        """Get total number of components (controllers + devices)."""
        return len(self.topology.controllers) + len(self.topology.devices)

    def get_line_count(self) -> int:
        """Estimate line count of generated PlantUML source."""
        # Rough estimate: header + zones + components + links + footer
        base_lines = 30  # Header, skinparam, footer
        zone_lines = len(self.topology.zones) * 3
        controller_lines = len(self.topology.controllers) * 2
        device_lines = len(self.topology.devices) * 2
        link_lines = len(self.topology.links) * 2
        legend_lines = 10 if self.show_legend else 0

        return (
            base_lines
            + zone_lines
            + controller_lines
            + device_lines
            + link_lines
            + legend_lines
        )
