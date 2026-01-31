# PlantUML CSA MCP Server

PlantUML-based Control System Architecture diagram generation via MCP.

## Architecture

```
plantuml-csa-mcp-server/
├── src/
│   ├── server.py                    # FastMCP server with MCP tools
│   ├── models/
│   │   └── csa_topology.py          # Pydantic models (same as FreeCAD CSA)
│   ├── converter/
│   │   ├── topology_to_puml.py      # YAML topology → PlantUML source
│   │   ├── sprites.py               # ISA symbol sprite definitions
│   │   └── layout_hints.py          # Purdue-aware layout directives
│   ├── renderer/
│   │   └── plantuml_runner.py       # PlantUML CLI wrapper
│   └── encoder/
│       └── plantuml_encoder.py      # Text encoding for shareable URLs
├── resources/
│   ├── sprites/                     # PlantUML sprite definitions
│   └── templates/                   # Base styling templates
└── tests/
    ├── test_topology_conversion.py  # Converter tests
    ├── test_encoder.py              # Encoding tests
    └── fixtures/                    # Sample YAML topologies
```

## Key Design Decisions

### Same Schema as FreeCAD CSA

The CSATopology Pydantic model is copied from freecad-csa-workbench to ensure:
- Identical YAML schema for both renderers
- Topology files work with both PlantUML and FreeCAD
- No translation layer needed between systems

### PlantUML Backend Detection

The renderer auto-detects available PlantUML backends in priority order:
1. Java JAR (PLANTUML_JAR env var or explicit path)
2. Native binary (`plantuml` in PATH)
3. Docker container (plantuml/plantuml)

### Security: !include Disabled

All generated PlantUML source includes `!pragma teoz false` to disable file includes
and prevent potential file disclosure through crafted topology YAML.

## MCP Tools

### Core Rendering Tools

| Tool | Purpose |
|------|---------|
| `csa_generate_diagram` | Render topology YAML to SVG/PNG |
| `csa_get_plantuml_source` | Get .puml source for version control |
| `csa_validate_topology` | Validate YAML against schema |
| `csa_list_symbols` | List available component symbols |
| `csa_encode_plantuml` | Generate shareable PlantUML URLs |
| `csa_render_preview` | Quick preview for iteration |
| `csa_check_plantuml` | Check PlantUML availability |

### Skill Integration Tools (Phase 2)

| Tool | Purpose |
|------|---------|
| `csa_list_templates` | List available architecture templates |
| `csa_bootstrap_from_io` | Bootstrap topology from equipment-list + instrument-io skills |

### Architecture Templates

Pre-defined templates for common control system configurations:

| Template | Description | Use Case |
|----------|-------------|----------|
| `centralized` | Central MCC + Central PLC | Small plants (<5 MLD) |
| `central_mcc_distributed_io` | Central MCC + Distributed IO | Medium plants (5-20 MLD) |
| `fully_distributed` | Remote panels per area | Large plants (>20 MLD) |
| `hybrid_safety` | Central Safety + Distributed Process | SIL/SIS requirements |
| `vendor_package_integration` | OEM packages via OPC-UA | Multiple vendor packages |

### Bootstrap Workflow

```
equipment-list-skill      instrument-io-skill
        │                        │
        ▼                        ▼
  equipment-list.qmd       database.yaml
        │                        │
        └────────┬───────────────┘
                 │
                 ▼
      csa_bootstrap_from_io()
                 │
                 ▼
         Draft CSA Topology YAML
                 │
         ┌───────┴──────┐
         ▼              ▼
  csa_generate_diagram  FreeCAD CSA
         │              │
         ▼              ▼
    SVG/PNG         TechDraw PDF
```

## Running the Server

```bash
# Install dependencies
uv sync

# Run MCP server
uv run python -m src
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `PLANTUML_JAR` | Path to plantuml.jar (optional) |

## Integration with FreeCAD CSA

This server produces diagrams from the same YAML topology format as FreeCAD CSA:

```
CSA Topology YAML
       │
       ├──► plantuml-csa-mcp ──► SVG/PNG (documentation)
       │
       └──► freecad-csa-workbench ──► TechDraw PDF (CAD deliverable)
```

## Layout Engines

- **graphviz** (default): Best quality, requires Graphviz installed
- **smetana**: Built-in, no external dependencies, faster
- **elk**: Best for large hierarchical diagrams, requires elkjs

## PlantUML Installation

### Option 1: Native Binary (Recommended)
```bash
# Ubuntu/Debian
sudo apt install plantuml

# macOS
brew install plantuml
```

### Option 2: Java JAR
```bash
# Download JAR
wget https://github.com/plantuml/plantuml/releases/download/v1.2024.8/plantuml-1.2024.8.jar
export PLANTUML_JAR=/path/to/plantuml.jar
```

### Option 3: Docker
```bash
docker pull plantuml/plantuml
```

## Testing

```bash
# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src
```
