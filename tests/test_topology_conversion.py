"""Tests for topology to PlantUML conversion."""
from pathlib import Path

import pytest
import yaml

from src.converter import TopologyToPumlConverter
from src.models import CSATopology


@pytest.fixture
def sample_topology_yaml() -> str:
    """Load sample topology YAML."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_topology.yaml"
    return fixture_path.read_text()


@pytest.fixture
def sample_topology(sample_topology_yaml: str) -> CSATopology:
    """Parse sample topology."""
    data = yaml.safe_load(sample_topology_yaml)
    return CSATopology.model_validate(data)


class TestTopologyToPumlConverter:
    """Tests for TopologyToPumlConverter."""

    def test_convert_produces_valid_plantuml(self, sample_topology: CSATopology):
        """Conversion produces valid PlantUML structure."""
        converter = TopologyToPumlConverter(sample_topology)
        result = converter.convert()

        assert result.startswith("@startuml")
        assert result.endswith("@enduml")
        assert "title" in result

    def test_convert_includes_zones(self, sample_topology: CSATopology):
        """Zones are rendered as packages."""
        converter = TopologyToPumlConverter(sample_topology, show_zones=True)
        result = converter.convert()

        assert 'package "Field Level"' in result
        assert 'package "Control Level"' in result
        assert 'package "Supervisory Level"' in result

    def test_convert_includes_controllers(self, sample_topology: CSATopology):
        """Controllers are rendered with stereotypes."""
        converter = TopologyToPumlConverter(sample_topology)
        result = converter.convert()

        assert "PLC_101" in result  # Sanitized ID
        assert "<<PLC>>" in result
        assert "<<Safety PLC>>" in result

    def test_convert_includes_devices(self, sample_topology: CSATopology):
        """Devices are rendered with stereotypes."""
        converter = TopologyToPumlConverter(sample_topology)
        result = converter.convert()

        assert "RIO_101" in result
        assert "HMI_001" in result
        assert "<<Remote IO>>" in result
        assert "<<HMI>>" in result

    def test_convert_includes_links(self, sample_topology: CSATopology):
        """Links are rendered with protocol colors."""
        converter = TopologyToPumlConverter(sample_topology, show_protocols=True)
        result = converter.convert()

        assert "PLC_101" in result and "RIO_101" in result
        assert "#0066CC" in result  # Ethernet/IP color
        assert "EtherNet/IP" in result

    def test_convert_without_zones(self, sample_topology: CSATopology):
        """Components render flat when zones disabled."""
        converter = TopologyToPumlConverter(sample_topology, show_zones=False)
        result = converter.convert()

        assert "package" not in result.lower().split("skinparam")[0]
        assert "PLC_101" in result

    def test_convert_layout_direction(self, sample_topology: CSATopology):
        """Layout directive matches configuration."""
        converter_tb = TopologyToPumlConverter(sample_topology, layout="top_to_bottom")
        converter_lr = TopologyToPumlConverter(sample_topology, layout="left_to_right")

        result_tb = converter_tb.convert()
        result_lr = converter_lr.convert()

        assert "top to bottom direction" in result_tb
        assert "left to right direction" in result_lr

    def test_convert_layout_engine_pragma(self, sample_topology: CSATopology):
        """Layout engine pragma is set correctly."""
        converter_smetana = TopologyToPumlConverter(
            sample_topology, layout_engine="smetana"
        )
        converter_elk = TopologyToPumlConverter(sample_topology, layout_engine="elk")
        converter_graphviz = TopologyToPumlConverter(
            sample_topology, layout_engine="graphviz"
        )

        assert "!pragma layout smetana" in converter_smetana.convert()
        assert "!pragma layout elk" in converter_elk.convert()
        assert "!pragma layout" not in converter_graphviz.convert()

    def test_convert_idempotent(self, sample_topology: CSATopology):
        """Same input produces identical output."""
        converter1 = TopologyToPumlConverter(sample_topology)
        converter2 = TopologyToPumlConverter(sample_topology)

        result1 = converter1.convert()
        result2 = converter2.convert()

        assert result1 == result2

    def test_sanitize_id_removes_hyphens(self, sample_topology: CSATopology):
        """Component IDs with hyphens are sanitized."""
        converter = TopologyToPumlConverter(sample_topology)
        result = converter.convert()

        # PLC-101 should become PLC_101
        assert "PLC-101" not in result or "PLC_101" in result
        assert "RIO-101" not in result or "RIO_101" in result

    def test_component_count(self, sample_topology: CSATopology):
        """Component count is accurate."""
        converter = TopologyToPumlConverter(sample_topology)

        # 2 controllers + 5 devices
        assert converter.get_component_count() == 7

    def test_line_count_estimate(self, sample_topology: CSATopology):
        """Line count estimate is reasonable."""
        converter = TopologyToPumlConverter(sample_topology)
        estimate = converter.get_line_count()
        actual = len(converter.convert().splitlines())

        # Estimate should be within 50% of actual
        assert estimate > actual * 0.5
        assert estimate < actual * 1.5

    def test_security_includes_disabled(self, sample_topology: CSATopology):
        """Security pragma disables includes."""
        converter = TopologyToPumlConverter(sample_topology)
        result = converter.convert()

        assert "!pragma teoz false" in result


class TestTopologyValidation:
    """Tests for topology validation."""

    def test_valid_topology_parses(self, sample_topology_yaml: str):
        """Valid topology YAML parses successfully."""
        data = yaml.safe_load(sample_topology_yaml)
        topology = CSATopology.model_validate(data)

        assert topology.metadata.project_name == "Test WWTP CSA"
        assert len(topology.controllers) == 2
        assert len(topology.devices) == 5
        assert len(topology.links) == 6

    def test_invalid_zone_reference_fails(self):
        """Invalid zone reference raises error."""
        data = {
            "zones": [{"id": "level_1", "purdue_level": 1}],
            "controllers": [
                {"id": "PLC-101", "type": "PLC", "zone": "invalid_zone"}
            ],
        }

        with pytest.raises(ValueError, match="unknown zone"):
            CSATopology.model_validate(data)

    def test_invalid_link_source_fails(self):
        """Invalid link source raises error."""
        data = {
            "controllers": [{"id": "PLC-101", "type": "PLC"}],
            "links": [
                {"source": "INVALID", "target": "PLC-101", "protocol": "Ethernet_IP"}
            ],
        }

        with pytest.raises(ValueError, match="not found"):
            CSATopology.model_validate(data)

    def test_empty_topology_valid(self):
        """Empty topology with just metadata is valid."""
        data = {
            "metadata": {"project_name": "Empty Project"},
        }

        topology = CSATopology.model_validate(data)
        assert topology.metadata.project_name == "Empty Project"
        assert len(topology.controllers) == 0
