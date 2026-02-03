# PlantUML CSA MCP Server

Generate Control System Architecture (CSA) diagrams using PlantUML via the Model Context Protocol (MCP).

## Features

- **ISA-95 Purdue Model** - Zone packages with color-coded levels (0-4)
- **Industrial Symbols** - 36+ component types (10 controllers, 26 devices)
- **Protocol Visualization** - 12 protocols with distinct line colors
- **Architecture Templates** - 5 pre-defined templates for common configurations
- **Bootstrap from Skills** - Generate topology from equipment-list + instrument-io skills
- **Multiple Layout Engines** - Graphviz, Smetana, ELK
- **Shareable URLs** - Generate PlantUML server links
- **Same Schema as FreeCAD** - Interoperable YAML topology format

## Project Structure

```
plantuml-csa-mcp-server/
├── src/
│   ├── __init__.py              # Package entry point
│   ├── __main__.py              # Module runner (python -m src)
│   ├── server.py                # FastMCP server with 8 MCP tools
│   ├── models/
│   │   └── csa_topology.py      # Pydantic models (same as FreeCAD CSA)
│   ├── converter/
│   │   ├── topology_to_puml.py  # YAML topology → PlantUML source
│   │   ├── sprites.py           # ISA symbol definitions (36+ types)
│   │   └── layout_hints.py      # Purdue-aware layout directives
│   ├── renderer/
│   │   └── plantuml_runner.py   # PlantUML CLI wrapper (JAR/native/Docker)
│   ├── encoder/
│   │   └── plantuml_encoder.py  # Text encoding for shareable URLs
│   ├── templates/
│   │   └── architecture_templates.py  # 5 architecture templates
│   └── bootstrap/
│       └── csa_bootstrap.py     # Bootstrap from equipment/IO lists
├── tests/                       # 56 tests
├── docs/
│   └── completed-plans/         # Implementation plan
├── pyproject.toml
├── CLAUDE.md                    # Development guide
└── README.md
```

## Installation

```bash
# Clone and install
cd plantuml-csa-mcp-server
uv sync

# Verify PlantUML is available
uv run python -c "from src.renderer import PlantUMLRunner; print(PlantUMLRunner().check_available())"
```

## Quick Start

### 1. Add to MCP Configuration

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "plantuml-csa-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "/path/to/plantuml-csa-mcp-server", "run", "python", "-m", "src"],
      "description": "PlantUML CSA diagram generation (ISA-95 Purdue model)"
    }
  }
}
```

### 2. Generate a Diagram

```yaml
# topology.yaml
schema_version: "1.0"
metadata:
  project_name: "Sample WWTP CSA"
zones:
  - id: "level_0"
    purdue_level: 0
  - id: "level_1"
    purdue_level: 1
controllers:
  - id: "PLC-101"
    type: PLC
    zone: "level_1"
devices:
  - id: "RIO-101"
    type: RemoteIO
    parent_controller: "PLC-101"
    zone: "level_0"
links:
  - source: "PLC-101"
    target: "RIO-101"
    protocol: "Ethernet_IP"
```

Then use the MCP tools:

```python
# Get PlantUML source for version control
csa_get_plantuml_source(topology_yaml=yaml_content)

# Generate SVG diagram
csa_generate_diagram(topology_yaml=yaml_content, format="svg")

# Get shareable URL
csa_encode_plantuml(plantuml_source=puml_source)
```

## MCP Tools Reference

| Tool | Purpose |
|------|---------|
| `csa_generate_diagram` | Render topology YAML to SVG/PNG |
| `csa_get_plantuml_source` | Get .puml source for version control |
| `csa_validate_topology` | Validate YAML against schema |
| `csa_list_symbols` | List available ISA-style symbols |
| `csa_encode_plantuml` | Generate shareable PlantUML URLs |
| `csa_list_templates` | List architecture templates |
| `csa_render_preview` | Quick preview for iteration |
| `csa_check_plantuml` | Check PlantUML availability |
| `csa_bootstrap_from_io` | Bootstrap topology from equipment/IO lists |

## Architecture Templates

Pre-defined templates for common control system configurations:

| Template | Description | Use Case |
|----------|-------------|----------|
| `centralized` | Central MCC + Central PLC | Small plants (<5 MLD) |
| `central_mcc_distributed_io` | Central MCC + Distributed IO | Medium plants (5-20 MLD) |
| `fully_distributed` | Remote panels per area | Large plants (>20 MLD) |
| `hybrid_safety` | Central Safety + Distributed Process | SIL/SIS requirements |
| `vendor_package_integration` | OEM packages via OPC-UA | Multiple vendor packages |

## Bootstrap from Skill Outputs

Generate CSA topology from equipment-list-skill and instrument-io-skill outputs:

```python
csa_bootstrap_from_io(
    equipment_list_qmd=equipment_qmd_content,
    instrument_database_yaml=io_database_yaml,
    project_name="WWTP Control System",
    architecture_template="fully_distributed"
)
# Returns: {topology_yaml, suggestions, io_summary, equipment_mapping}
```

## Supported Components

### Controllers (10 types)
PLC, DCS, PAC, Safety_PLC, Soft_PLC, Edge_Controller, Motion_Controller, Redundant_PLC, RTU, SIS

### Devices (26 types)
RemoteIO, HMI, SCADA, Historian, OPC_UA_Server, Gateway, VFD, Soft_Starter, MCC, Industrial_PC, Switch, Managed_Switch, Router, Firewall, Wireless_AP, Media_Converter, Network_TAP, Motor_Starter, Engineering_WS, Panel_PC, Data_Logger, Junction_Box, Marshalling_Cabinet, Local_Panel, Remote_Panel, Instrument_Rack

### Protocols (12 types)
Ethernet_IP, Profinet, Modbus_TCP, Modbus_RTU, Profibus, DeviceNet, ControlNet, HART, Foundation_Fieldbus, OPC_UA, MQTT, BACnet

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src
```

## vs FreeCAD CSA

| Aspect | PlantUML CSA | FreeCAD CSA |
|--------|-------------|-------------|
| Output | SVG/PNG | TechDraw PDF |
| Version Control | Plain text .puml | Binary .FCStd |
| Dependencies | Java/PlantUML | FreeCAD runtime |
| Best For | Documentation | CAD deliverables |

**Use Both**: Same YAML topology works with both renderers. Use PlantUML for rapid iteration and documentation, FreeCAD for final engineering drawings.

## Workflow Integration

This server is part of the puran-water control system architecture workflow:

```
┌─────────────────────────┐     ┌──────────────────────────┐     ┌─────────────────────┐
│  equipment-list-skill   │ ──► │  instrument-io-skill     │ ──► │  csa-diagram-skill  │
│  (equipment + feeder)   │     │  (IO lists, patterns)    │     │  (CSA generation)   │
└─────────────────────────┘     └──────────────────────────┘     └─────────────────────┘
                                                                            │
                                                                            ▼
                                                                 ┌─────────────────────┐
                                                                 │ plantuml-csa-mcp    │
                                                                 │ (this server)       │
                                                                 └─────────────────────┘
                                                                            │
                                                                            ▼
                                                                 ┌─────────────────────┐
                                                                 │ CSA Topology YAML   │
                                                                 │ PlantUML PNG/SVG    │
                                                                 │ Shareable URLs      │
                                                                 └─────────────────────┘
```

## Related Projects

### Upstream (Data Sources)
- [equipment-list-skill](https://github.com/puran-water/equipment-list-skill) - Equipment lists with feeder types
- [instrument-io-skill](https://github.com/puran-water/instrument-io-skill) - IO lists with DI/DO/AI/AO patterns

### Companion Skill
- [csa-diagram-skill](https://github.com/puran-water/csa-diagram-skill) - Claude Code skill that orchestrates this MCP server

### Similar Pattern (Electrical)
- [plantuml-sld-mcp-server](https://github.com/puran-water/plantuml-sld-mcp-server) - Single-Line Diagram generation (same YAML → PlantUML pattern)
- [electrical-distribution-skill](https://github.com/puran-water/electrical-distribution-skill) - SLD skill using plantuml-sld-mcp-server

### Alternative Renderer
- [freecad-csa-workbench](https://github.com/puran-water/freecad-csa-workbench) - Same YAML topology rendered in FreeCAD for CAD deliverables

## License

MIT
