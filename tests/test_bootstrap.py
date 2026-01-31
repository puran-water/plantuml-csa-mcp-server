"""Tests for CSA bootstrap from equipment/IO lists."""
import pytest
import yaml

from src.bootstrap.csa_bootstrap import (
    bootstrap_csa_topology,
    calculate_io_summary,
    extract_equipment_list,
    parse_instrument_database,
    parse_qmd_frontmatter,
)
from src.templates import get_template, list_templates


class TestQMDParsing:
    """Tests for QMD frontmatter parsing."""

    def test_parse_qmd_with_frontmatter(self):
        """Parse QMD file with YAML frontmatter."""
        qmd = """---
equipment:
  - tag: "200-P-001"
    feeder_type: VFD
    control_responsibility: plc
---

# Equipment List

This is the equipment list.
"""
        result = parse_qmd_frontmatter(qmd)
        assert "equipment" in result
        assert len(result["equipment"]) == 1
        assert result["equipment"][0]["tag"] == "200-P-001"

    def test_parse_raw_yaml(self):
        """Parse raw YAML without frontmatter markers."""
        yaml_content = """
equipment:
  - tag: "200-B-001"
    feeder_type: DOL
"""
        result = parse_qmd_frontmatter(yaml_content)
        assert "equipment" in result

    def test_extract_equipment_list(self):
        """Extract equipment list from QMD."""
        qmd = """---
equipment:
  - tag: "200-P-001"
    feeder_type: VFD
  - tag: "200-B-001"
    feeder_type: SOFT-STARTER
---
"""
        equip = extract_equipment_list(qmd)
        assert len(equip) == 2
        assert equip[0]["tag"] == "200-P-001"


class TestInstrumentDatabaseParsing:
    """Tests for instrument database parsing."""

    def test_parse_instrument_database(self):
        """Parse instrument database YAML."""
        db_yaml = """
instruments:
  - tag: "200-FT-001"
    equipment_tag: "200-P-001"
    io_signals:
      - io_type: AI
      - io_type: DI
      - io_type: DI
"""
        result = parse_instrument_database(db_yaml)
        assert "instruments" in result
        assert len(result["instruments"]) == 1

    def test_calculate_io_summary(self):
        """Calculate IO counts per area."""
        db = {
            "instruments": [
                {
                    "tag": "200-FT-001",
                    "io_signals": [
                        {"io_type": "AI"},
                        {"io_type": "DI"},
                        {"io_type": "DI"},
                    ],
                },
                {
                    "tag": "200-PT-001",
                    "io_signals": [
                        {"io_type": "AI"},
                        {"io_type": "AO"},
                    ],
                },
                {
                    "tag": "300-LT-001",
                    "io_signals": [
                        {"io_type": "AI"},
                    ],
                },
            ]
        }

        summary = calculate_io_summary(db)

        assert "200" in summary
        assert summary["200"]["DI"] == 2
        assert summary["200"]["AI"] == 2
        assert summary["200"]["AO"] == 1

        assert "300" in summary
        assert summary["300"]["AI"] == 1


class TestArchitectureTemplates:
    """Tests for architecture templates."""

    def test_list_templates(self):
        """List all available templates."""
        templates = list_templates()

        assert len(templates) >= 5
        names = [t["name"] for t in templates]
        assert "centralized" in names
        assert "fully_distributed" in names
        assert "hybrid_safety" in names

    def test_get_centralized_template(self):
        """Get centralized template."""
        template = get_template("centralized")

        assert template is not None
        assert template.plc_allocation == "central"
        assert template.vfd_location == "mcc"
        assert template.io_location == "central"

    def test_get_fully_distributed_template(self):
        """Get fully distributed template."""
        template = get_template("fully_distributed")

        assert template is not None
        assert template.plc_allocation == "per_area"
        assert template.vfd_location == "remote_panel"
        assert template.io_location == "distributed"

    def test_get_hybrid_safety_template(self):
        """Get hybrid safety template."""
        template = get_template("hybrid_safety")

        assert template is not None
        assert template.safety_plc == "central"
        assert template.redundancy_type == "Dual_Redundant"


class TestBootstrapTopology:
    """Tests for bootstrap_csa_topology."""

    @pytest.fixture
    def sample_equipment_qmd(self):
        return """---
equipment:
  - tag: "200-P-001"
    feeder_type: VFD
    control_responsibility: plc
    power_kw: 110
  - tag: "200-B-001"
    feeder_type: SOFT-STARTER
    control_responsibility: plc
    power_kw: 75
  - tag: "200-MBR-001"
    feeder_type: VFD
    control_responsibility: vendor
---
"""

    @pytest.fixture
    def sample_instrument_yaml(self):
        return """
instruments:
  - tag: "200-FT-001"
    equipment_tag: "200-P-001"
    io_signals:
      - io_type: AI
      - io_type: DI
      - io_type: DI
  - tag: "200-PT-001"
    equipment_tag: "200-P-001"
    io_signals:
      - io_type: AI
      - io_type: AO
"""

    def test_bootstrap_centralized(self, sample_equipment_qmd, sample_instrument_yaml):
        """Bootstrap with centralized template."""
        result = bootstrap_csa_topology(
            equipment_list_qmd=sample_equipment_qmd,
            instrument_database_yaml=sample_instrument_yaml,
            project_name="Test WWTP",
            architecture_template="centralized",
        )

        assert "topology_yaml" in result
        assert "suggestions" in result
        assert "io_summary" in result
        assert "equipment_mapping" in result

        # Parse the generated topology
        topology = yaml.safe_load(result["topology_yaml"])

        # Should have one central PLC
        assert any(c["id"] == "PLC-001" for c in topology["controllers"])

        # VFDs should be created for VFD feeder_type
        vfds = [d for d in topology["devices"] if "VFD" in d["type"]]
        assert len(vfds) >= 1

    def test_bootstrap_fully_distributed(self, sample_equipment_qmd, sample_instrument_yaml):
        """Bootstrap with fully_distributed template."""
        result = bootstrap_csa_topology(
            equipment_list_qmd=sample_equipment_qmd,
            instrument_database_yaml=sample_instrument_yaml,
            project_name="Large WWTP",
            architecture_template="fully_distributed",
        )

        topology = yaml.safe_load(result["topology_yaml"])

        # Should have PLC per area
        assert any("PLC-200" in c["id"] for c in topology["controllers"])

    def test_bootstrap_with_vendor_packages(self, sample_equipment_qmd, sample_instrument_yaml):
        """Bootstrap handles vendor packages correctly."""
        result = bootstrap_csa_topology(
            equipment_list_qmd=sample_equipment_qmd,
            instrument_database_yaml=sample_instrument_yaml,
            project_name="Test WWTP",
            architecture_template="vendor_package_integration",
        )

        # Should have suggestion about vendor package
        assert any("vendor" in s.lower() for s in result["suggestions"])

    def test_bootstrap_generates_valid_yaml(self, sample_equipment_qmd, sample_instrument_yaml):
        """Generated topology YAML is valid."""
        result = bootstrap_csa_topology(
            equipment_list_qmd=sample_equipment_qmd,
            instrument_database_yaml=sample_instrument_yaml,
            project_name="Test WWTP",
            architecture_template="centralized",
        )

        # Should parse without error
        topology = yaml.safe_load(result["topology_yaml"])

        assert topology["metadata"]["project_name"] == "Test WWTP"
        assert len(topology["zones"]) == 3  # Level 0, 1, 2
        assert len(topology["controllers"]) > 0
        assert len(topology["links"]) > 0

    def test_bootstrap_io_summary(self, sample_equipment_qmd, sample_instrument_yaml):
        """IO summary is calculated correctly."""
        result = bootstrap_csa_topology(
            equipment_list_qmd=sample_equipment_qmd,
            instrument_database_yaml=sample_instrument_yaml,
            project_name="Test WWTP",
            architecture_template="centralized",
        )

        io_summary = result["io_summary"]
        assert "200" in io_summary
        assert io_summary["200"]["AI"] == 2
        assert io_summary["200"]["DI"] == 2

    def test_bootstrap_equipment_mapping(self, sample_equipment_qmd, sample_instrument_yaml):
        """Equipment mapping tracks PLC assignments."""
        result = bootstrap_csa_topology(
            equipment_list_qmd=sample_equipment_qmd,
            instrument_database_yaml=sample_instrument_yaml,
            project_name="Test WWTP",
            architecture_template="centralized",
        )

        mapping = result["equipment_mapping"]
        assert "200-P-001" in mapping
        assert mapping["200-P-001"] == "PLC-001"

    def test_bootstrap_lenient_mode(self):
        """Lenient mode handles malformed input gracefully."""
        result = bootstrap_csa_topology(
            equipment_list_qmd="not valid yaml {{",
            instrument_database_yaml="",
            project_name="Test",
            architecture_template="centralized",
            mode="lenient",
        )

        # Should succeed with warnings
        assert "topology_yaml" in result
        assert "warnings" in result

    def test_bootstrap_unknown_template_lenient(self, sample_equipment_qmd, sample_instrument_yaml):
        """Unknown template falls back to centralized in lenient mode."""
        result = bootstrap_csa_topology(
            equipment_list_qmd=sample_equipment_qmd,
            instrument_database_yaml=sample_instrument_yaml,
            project_name="Test",
            architecture_template="nonexistent_template",
            mode="lenient",
        )

        assert "topology_yaml" in result
        assert any("Unknown template" in w for w in result.get("warnings", []))
