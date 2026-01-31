# PlantUML CSA MCP Server Implementation Plan

## Executive Summary

**Recommendation: Yes, PlantUML is better than FreeCAD for CSA diagram generation.**

| Factor | FreeCAD CSA | PlantUML |
|--------|-------------|----------|
| Code complexity | 4,442 lines + FreeCAD runtime | ~500 lines + CLI subprocess |
| Version control | Binary .FCStd files | Plain text .puml files |
| Iteration speed | Slow (FreeCAD startup) | Fast (CLI) |
| Layout quality | NetworkX/ELK | Graphviz (built-in, excellent) |
| Documentation focus | CAD-oriented | Perfect for architecture docs |
| Existing ecosystem | Custom MCP | Multiple MCP servers exist |

**Keep FreeCAD CSA for:** CAD integration, DXF export, TechDraw title blocks
**Use PlantUML for:** Documentation, version-controlled diagrams, rapid iteration

---

## Integration with SKILLS Vision

The PlantUML approach consumes **equipment-list-skill** and **instrument-io-skill** outputs:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     SKILL → CSA DIAGRAM DATA FLOW                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  pid-digitization-skill → equipment-list-skill → instrument-io-skill   │
│                                                          │              │
│                                                          ▼              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  equipment-list-skill OUTPUT: equipment-list.qmd                 │   │
│  │  ├── tag: "200-B-01"           ← Equipment tag                   │   │
│  │  ├── feeder_type: "VFD"        ← DOL/VFD/Soft-Starter/Vendor    │   │
│  │  ├── power_kw: 110             ← Electrical load                 │   │
│  │  ├── area: 200                 ← Process area                    │   │
│  │  ├── control_responsibility: "plc"  ← PLC vs vendor vs manual   │   │
│  │  └── kind: "equipment"         ← equipment vs package            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                      │                                                  │
│                      ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  instrument-io-skill OUTPUT: database.yaml + io-list.xlsx        │   │
│  │  ├── equipment_tag: "200-B-01" ← Links to equipment              │   │
│  │  ├── io_signals:               ← Full IO definition              │   │
│  │  │   ├── io_type: DI (3x)     ← Digital Inputs                   │   │
│  │  │   ├── io_type: DO (1x)     ← Digital Outputs                  │   │
│  │  │   ├── io_type: AI (1x)     ← Analog Inputs (4-20mA)          │   │
│  │  │   └── io_type: AO (1x)     ← Analog Outputs                   │   │
│  │  └── io-summary per area:      ← Size IO modules                 │   │
│  │      Area 200: 45 DI, 12 DO, 28 AI, 8 AO                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                      │                                                  │
│                      ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  csa_bootstrap_from_io (NEW MCP TOOL)                           │   │
│  │                                                                  │   │
│  │  Input:                                                          │   │
│  │    - equipment_list_yaml (from equipment-list-skill)            │   │
│  │    - instrument_database_yaml (from instrument-io-skill)        │   │
│  │    - architecture_template: "centralized" | "distributed" | ... │   │
│  │                                                                  │   │
│  │  Output: draft CSA topology YAML                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                      │                                                  │
│                      ▼                                                  │
│             CSA TOPOLOGY (YAML)                                        │
│                      │                                                  │
│         ┌────────────┴───────────────────────┐                         │
│         ▼                                    ▼                         │
│  plantuml-csa-mcp                    freecad-csa-workbench            │
│         │                                    │                         │
│         ▼                                    ▼                         │
│  SVG/PNG/PDF + .puml                 TechDraw PDF                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Templates

Predefined templates for common control system configurations:

### Template 1: `centralized` (Central MCC + Central PLC)
```
All VFDs and IO modules in centralized MCC/PLC cabinet
├── Single PLC cabinet with local IO cards
├── All VFDs wired back to central MCC
├── Field instruments hardwired to marshalling panels
├── Protocols: Hardwired (4-20mA, 24V DC)
└── Use case: Small plants (<5 MLD), compact footprint
```

### Template 2: `central_mcc_distributed_io` (Central MCC + Distributed IO)
```
VFDs in central MCC, IO distributed via Profinet/Ethernet-IP
├── Central PLC in control room
├── VFDs in central MCC (wired to PLC via Profinet)
├── Distributed Remote IO panels at each process area
├── Protocols: Profinet/Ethernet-IP to RIOs, hardwired to MCC
└── Use case: Medium plants, moderate distances
```

### Template 3: `fully_distributed` (Remote Panels)
```
VFDs, starters, and IO in remote panels per area
├── Central PLC with Profinet/Ethernet-IP backbone
├── Remote panels per area with:
│   ├── VFDs
│   ├── Soft starters / DOL starters
│   ├── IO modules
│   └── Local power distribution
├── Single power + comms cable to each panel
├── Protocols: Profinet/Ethernet-IP
└── Use case: Large plants, long distances, modular expansion
```

### Template 4: `hybrid_safety` (Central Safety + Distributed Process)
```
Safety PLC centralized, process control distributed
├── Central Safety PLC for ESD/SIS functions
├── Distributed process PLCs per area
├── VFDs at remote panels
├── Profinet ring topology for redundancy
└── Use case: Plants with SIL requirements
```

### Template 5: `vendor_package_integration`
```
OEM packages with vendor PLCs integrated via OPC-UA
├── Main plant PLC for utilities/common systems
├── Vendor PLCs for packages (MBR, RO, DAF)
├── OPC-UA gateway for data exchange
├── Hardwired interlocks for safety
└── Use case: Plants with multiple vendor packages
```

**Template Selection Logic:**

| Criterion | centralized | central_mcc_dist_io | fully_distributed |
|-----------|-------------|---------------------|-------------------|
| Plant size | <5 MLD | 5-20 MLD | >20 MLD |
| Max distance | <100m | <500m | >500m |
| IO count | <200 | 200-1000 | >1000 |
| VFD count | <20 | 20-50 | >50 |

---

## Key Integration: Skill Outputs → CSA

| Skill Output | CSA Topology Usage |
|--------------|-------------------|
| `equipment-list.qmd` | `controller.equipment_tags[]` from PLC-controlled equipment |
| `feeder_type: "VFD"` | Create VFD device entries with Profinet links |
| `feeder_type: "DOL"/"Soft-Starter"` | IO allocation at MCC or remote panel |
| `control_responsibility: "vendor"` | Exclude from PLC, add as vendor package |
| `io_signals[]` from instrument DB | Calculate Remote IO module count per area |
| `io-summary.xlsx` (DI/DO/AI/AO counts) | Size IO cards per area |
| `area` codes | Group into PLCs: PLC-100, PLC-200, etc. |

**Traceability Chain:**
```
equipment-list.qmd → database.yaml → CSA topology → PlantUML
      ↓                    ↓              ↓
 feeder_type=VFD      io_signals[]    device: VFD-200-B-01
 power_kw=110        DI:3,DO:1,AI:1   parent: PLC-200
```

---

## Architecture: Python FastMCP

**Framework:** FastMCP (consistent with site-fit-mcp-server, freecad-mcp)

**Rationale:**
- Reuse CSATopology Pydantic models directly from freecad-csa-workbench
- Consistent patterns (structlog, response filtering, tool annotations)
- PlantUML invoked via subprocess (`java -jar plantuml.jar --pipe`)

---

## Codex Review Recommendations (Incorporated)

### Template Versioning & Overrides
- Add `template_version` field to all architecture templates
- Support an `overrides` block for customization:
  - Panel counts
  - Spare IO percentage
  - Protocol preferences
  - Redundancy settings
  - Vendor package handling

### MCP Tool Enhancements
- Add `layout_engine` parameter (Graphviz/Smetana/ELK) for deterministic outputs
- Add `font` and `theme` parameters for consistent styling
- Add `strict` vs `lenient` mode for `csa_bootstrap_from_io`
- Add `csa_list_templates` tool to enumerate available templates
- Add `csa_render_preview` tool for quick iteration

### Input Contract Precision
- Parse YAML frontmatter from `equipment-list.qmd` (not assume raw YAML)
- Preserve tag casing and enumerations (e.g., `SOFT-STARTER` not `Soft-Starter`)
- Include PI/PO signal types from instrument-io-skill (not just DI/DO/AI/AO)
- Model vendor packages as vendor PLC nodes with OPC-UA + hardwired interlocks

### Technical Risks to Address
- **Layout Engine**: PlantUML does NOT have "built-in Graphviz" - pin Graphviz version or explicitly use Smetana/ELK
- **PDF Output**: Official docs list PNG/SVG/LaTeX/EPS only - implement SVG→PDF conversion or verify `-tpdf` flag
- **Security**: Lock down `!include` behavior and remote includes to prevent file disclosure

### Schema Completeness
- Generate `networks` segments (not just links) for FreeCAD parity
- Optionally generate `ports` and channel mappings for detailed IO allocation

---

## File Structure

```
plantuml-csa-mcp-server/
├── src/
│   ├── __init__.py
│   ├── server.py                    # FastMCP server with MCP tools
│   ├── models/
│   │   └── csa_topology.py          # Symlink/copy from freecad-csa-workbench
│   ├── converter/
│   │   ├── topology_to_puml.py      # YAML topology → PlantUML source
│   │   ├── sprites.py               # ISA symbol sprite definitions
│   │   └── layout_hints.py          # Purdue-aware layout directives
│   ├── renderer/
│   │   └── plantuml_runner.py       # PlantUML CLI wrapper
│   └── encoder/
│       └── plantuml_encoder.py      # Text encoding for shareable URLs
├── resources/
│   ├── sprites/
│   │   ├── controllers/             # PLC, DCS, PAC, Safety_PLC sprites
│   │   ├── devices/                 # HMI, SCADA, VFD, RemoteIO sprites
│   │   ├── network/                 # Switch, Firewall, Router sprites
│   │   └── common.puml              # Shared sprite definitions
│   └── templates/
│       ├── csa_base.puml            # Base skinparam styling
│       └── purdue_zones.puml        # Zone color definitions
├── tests/
│   ├── test_topology_conversion.py
│   ├── test_sprite_generation.py
│   └── fixtures/                    # Sample YAML topologies
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

---

## MCP Tools

### 1. `csa_bootstrap_from_io` (Skill Integration - Core Tool)
```
Purpose: Bootstrap CSA topology from equipment-list-skill + instrument-io-skill outputs
Input:
  - equipment_list_qmd: str         # QMD file with YAML frontmatter (parse frontmatter)
  - instrument_database_yaml: str   # From instrument-io-skill
  - project_name: str
  - architecture_template: str      # Template name (see Architecture Templates)
  - template_version: str           # Template version for reproducibility (default: "1.0")
  - mode: "strict" | "lenient"      # Strict fails on ambiguity, lenient warns (default: "lenient")
  - overrides: dict | None          # Optional customizations:
      - spare_io_pct: int           # Spare IO percentage (default: 20)
      - panel_counts: dict          # Override panel allocation per area
      - protocol_preferences: list  # Preferred protocols ["Profinet", "Ethernet_IP"]
      - redundancy: dict            # Redundancy settings per controller type

Output:
  - topology_yaml: str              # Draft CSA topology for refinement
  - suggestions[]: list             # Human review items
  - io_summary: dict                # DI/DO/AI/AO/PI/PO counts per area (includes PI/PO)
  - equipment_mapping: dict         # Which equipment → which PLC
  - networks[]: list                # Generated network segments for FreeCAD parity

Logic:
  1. Parse equipment-list.qmd YAML frontmatter, extract:
     - Equipment tags with control_responsibility="plc"
     - feeder_type (VFD/DOL/SOFT-STARTER) - preserve exact casing
     - Area codes for PLC grouping
     - Vendor packages (control_responsibility="vendor") → create vendor PLC nodes
  2. Parse instrument database.yaml, extract:
     - io_signals[] for IO count calculation (DI/DO/AI/AO/PI/PO - all 6 types)
     - VFD equipment for device entries
  3. Apply architecture template with overrides:
     - Allocate PLCs (central vs per-area)
     - Allocate VFDs (MCC vs remote panels)
     - Allocate Remote IO modules based on IO counts + spare_io_pct
     - Create vendor PLC nodes with OPC-UA + hardwired interlocks
  4. Generate ISA-95 zones (Levels 0-2)
  5. Generate network segments AND links per template protocol preferences
  6. Return draft topology + suggestions for human refinement
```

### 2. `csa_generate_diagram`
```
Purpose: Generate CSA diagram from YAML topology
Input:
  - topology_yaml: str
  - format: "svg" | "png"           # Note: PDF via SVG→PDF conversion
  - layout: "hierarchical" | "left_to_right" | "top_to_bottom"
  - layout_engine: "graphviz" | "smetana" | "elk"  # For deterministic output
  - output_path: str | None
  - font: str                       # Font family (default: "Arial")
  - theme: str                      # Theme name (default: "csa_industrial")
Output:  {success, image_data (base64), plantuml_source, file_path}
```

### 3. `csa_get_plantuml_source`
```
Purpose: Convert topology to .puml source without rendering
Input:   topology_yaml, layout, show_zones, show_protocols, layout_engine
Output:  {plantuml_source, line_count, component_count}
Use:     Version control, manual editing, CI/CD pipelines
Security: Disables !include directives to prevent file disclosure
```

### 4. `csa_validate_topology`
```
Purpose: Validate YAML topology against schema
Input:   topology_yaml, strict
Output:  {valid, errors[], warnings[], summary}
```

### 5. `csa_list_symbols`
```
Purpose: List available ISA-style symbols
Input:   category (controllers/devices/network/all)
Output:  {symbols[{id, category, description, sprite_name}]}
```

### 6. `csa_encode_plantuml`
```
Purpose: Encode PlantUML source for shareable URL
Input:   plantuml_source, server_url
Output:  {encoded, svg_url, png_url, edit_url}
```

### 7. `csa_list_templates` (NEW - per Codex)
```
Purpose: List available architecture templates with versions
Input:   None
Output:  {templates[{name, version, description, use_case, default_overrides}]}
```

### 8. `csa_render_preview` (NEW - per Codex)
```
Purpose: Quick preview render without full validation (for iteration)
Input:   topology_yaml, layout_engine
Output:  {preview_svg (low-res), warnings[], render_time_ms}
```

---

## Topology → PlantUML Conversion

### Zone Rendering (Purdue Model)
```plantuml
package "Level 2 - Supervisory" as level_2 #FFF3E0 {
}
package "Level 1 - Control" as level_1 #E3F2FD {
}
package "Level 0 - Field" as level_0 #E8F5E9 {
}
```

### Controller/Device Rendering
```plantuml
level_1::<$plc> "PLC-101\nSiemens S7-1500" as PLC_101
level_0::<$remote_io> "RIO-101" as RIO_101
level_2::<$scada> "SCADA-001" as SCADA_001
```

### Link Rendering with Protocol Styles
```plantuml
PLC_101 -[#0066CC]-> RIO_101 : Ethernet_IP
PLC_101 -[#009933]-> HMI_001 : Profinet
PLC_101 -[#6600CC]-> SCADA_001 : OPC_UA
```

---

## Companion Skill Update

Update `/home/hvksh/skills/csa-diagram-skill/SKILL.md`:

1. Add PlantUML as alternative renderer
2. Document when to use PlantUML vs FreeCAD
3. Add `csa_generate_diagram` tool reference
4. Keep existing FreeCAD tools for CAD workflows

---

## Critical Files to Reference

| File | Purpose |
|------|---------|
| `freecad-csa-workbench/addon/CSAWorkbench/models/csa_topology.py` | Pydantic models (319 lines) - reuse directly |
| `site-fit-mcp-server/src/server.py` | FastMCP server pattern to follow |
| `skills/csa-diagram-skill/SKILL.md` | Existing skill to update |
| `skills/equipment-list-skill/SKILL.md` | Equipment list schema (feeder_type, control_responsibility) |
| `skills/instrument-io-skill/SKILL.md` | IO database schema (io_signals[]) |
| `skills/instrument-io-skill/templates/io-patterns.yaml` | IO patterns for VFD, DOL, valves |
| `skills/instrument-io-skill/schemas/instrument-database.schema.yaml` | Database schema |
| `freecad-csa-workbench/examples/sample_topology.yaml` | Test topology |
| `skills/shared/schemas/process-unit-taxonomy.yaml` | Equipment type definitions |

---

## Verification Plan

1. **Unit tests:**
   - YAML topology → PlantUML source conversion
   - Sprite rendering for all 34+ component types
   - Protocol line styles
   - Zone package generation
   - Equipment-list.qmd parsing (feeder_type, control_responsibility)
   - Instrument database.yaml parsing (io_signals[])

2. **Integration tests:**
   - PlantUML CLI renders valid SVG/PNG
   - Same topology produces identical output (idempotent)
   - Encoding produces decodable URLs
   - `csa_bootstrap_from_io` produces valid topology YAML

3. **Architecture template tests:**
   - Each template produces distinct network topology
   - `centralized`: All VFDs/IO at central location
   - `fully_distributed`: VFDs/IO at remote panels per area
   - IO counts correctly allocate RIO modules

4. **End-to-end (Skill → CSA):**
   - Input: Sample equipment-list.qmd + database.yaml from instrument-io-skill
   - Call `csa_bootstrap_from_io` with each architecture template
   - Call `csa_generate_diagram` → SVG output
   - Verify equipment_tags trace back to original equipment list

5. **Interoperability test:**
   - Generate topology with PlantUML MCP
   - Import same topology into FreeCAD CSA workbench
   - Verify both render equivalent diagrams

---

## Implementation Phases

### Phase 1: Core Server ✅ COMPLETE
- [x] Create project structure with pyproject.toml
- [x] Copy CSATopology Pydantic models from freecad-csa-workbench
- [x] Implement `topology_to_puml.py` converter
- [x] Implement PlantUML subprocess runner
- [x] Add `csa_generate_diagram` and `csa_get_plantuml_source` tools

### Phase 2: Skill Integration + Architecture Templates ✅ COMPLETE
- [x] Parse equipment-list.qmd schema (from equipment-list-skill)
- [x] Parse instrument database.yaml schema (from instrument-io-skill)
- [x] Define architecture template schemas:
  - [x] `centralized` - central MCC + central PLC
  - [x] `central_mcc_distributed_io` - central MCC + distributed RIO
  - [x] `fully_distributed` - remote panels per area
  - [x] `hybrid_safety` - central safety + distributed process
  - [x] `vendor_package_integration` - OEM packages via OPC-UA
- [x] Implement `csa_bootstrap_from_io` tool:
  - [x] Parse equipment list: feeder_type, control_responsibility, area
  - [x] Parse IO database: io_signals[], calculate DI/DO/AI/AO per area
  - [x] Apply template to allocate PLCs, VFDs, RIOs
  - [x] Generate network links per template protocol preferences
- [x] Add human review suggestions for ambiguous mappings

### Phase 3: Sprites & Styling ✅ COMPLETE
- [x] Create PlantUML sprite definitions for 34+ component types
- [x] Implement protocol line styles (12 protocols)
- [x] Implement Purdue zone coloring (Levels 0-4)

### Phase 4: Additional Tools ✅ COMPLETE
- [x] Implement `csa_validate_topology`
- [x] Implement `csa_list_symbols`
- [x] Implement `csa_encode_plantuml`
- [x] Implement `csa_list_templates`
- [x] Implement `csa_render_preview`
- [x] Implement `csa_check_plantuml`

### Phase 5: Skill Update & Documentation ✅ COMPLETE
- [x] Update csa-diagram-skill/SKILL.md with PlantUML workflow (standardized on PlantUML only per user request)
- [x] Document P&ID → CSA workflow in skill (Bootstrap from Skill Outputs section added)
- [x] Write CLAUDE.md and README.md
- [x] Add to .mcp.json configuration

### Phase 6: Testing ✅ COMPLETE
- [x] Unit tests for topology_to_puml converter (14 tests)
- [x] Unit tests for sprites and styling (13 tests)
- [x] Unit tests for encoder (7 tests)
- [x] Unit tests for bootstrap/templates (17 tests)
- [x] Unit tests for validation
- [x] Total: 56 tests passing

---

## Existing PlantUML MCP Servers (Reference)

Multiple implementations exist we could learn from:
- [infobip/plantuml-mcp-server](https://github.com/infobip/plantuml-mcp-server) - TypeScript
- [antoinebou12/uml-mcp](https://github.com/antoinebou12/uml-mcp) - Python, multi-format
- [sysam68/plantuml-mcp-server](https://github.com/sysam68/plantuml-mcp-server) - HTTP/SSE/STDIO

Our implementation is differentiated by:
1. ISA-95/Purdue model awareness
2. Same YAML schema as FreeCAD CSA (interoperability)
3. Integration with equipment_tags from P&ID digitization
4. Custom ISA-style sprites for industrial control components
