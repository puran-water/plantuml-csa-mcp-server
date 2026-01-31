"""Tests for PlantUML text encoder."""
import pytest

from src.encoder import decode_plantuml, encode_plantuml, get_plantuml_urls


class TestPlantUMLEncoder:
    """Tests for PlantUML encoding/decoding."""

    def test_encode_simple_diagram(self):
        """Simple diagram encodes to non-empty string."""
        source = "@startuml\nA -> B\n@enduml"
        encoded = encode_plantuml(source)

        assert encoded
        assert len(encoded) > 0
        # PlantUML encoding uses alphanumeric + - _
        assert all(c.isalnum() or c in "-_" for c in encoded)

    def test_encode_decode_roundtrip(self):
        """Encode then decode returns original source."""
        source = "@startuml\ntitle Test Diagram\nA -> B : message\n@enduml"
        encoded = encode_plantuml(source)
        decoded = decode_plantuml(encoded)

        assert decoded == source

    def test_encode_unicode(self):
        """Unicode characters encode correctly."""
        source = "@startuml\ntitle Tëst Dïàgräm\nA -> B\n@enduml"
        encoded = encode_plantuml(source)
        decoded = decode_plantuml(encoded)

        assert decoded == source

    def test_encode_large_diagram(self):
        """Large diagram encodes successfully."""
        lines = ["@startuml", "title Large Diagram"]
        for i in range(100):
            lines.append(f"A{i} -> B{i} : message {i}")
        lines.append("@enduml")
        source = "\n".join(lines)

        encoded = encode_plantuml(source)
        decoded = decode_plantuml(encoded)

        assert decoded == source


class TestPlantUMLURLs:
    """Tests for PlantUML URL generation."""

    def test_get_urls_default_server(self):
        """URLs generated for default PlantUML server."""
        encoded = "SoWkIImgAStDuNBAJrBGjLDmpCbCJbMmKiX8pSd9vt98pKi1IW80"
        urls = get_plantuml_urls(encoded)

        assert urls["svg_url"] == f"https://www.plantuml.com/plantuml/svg/{encoded}"
        assert urls["png_url"] == f"https://www.plantuml.com/plantuml/png/{encoded}"
        assert urls["edit_url"] == f"https://www.plantuml.com/plantuml/uml/{encoded}"

    def test_get_urls_custom_server(self):
        """URLs generated for custom server."""
        encoded = "abc123"
        urls = get_plantuml_urls(encoded, "http://localhost:8080")

        assert urls["svg_url"] == "http://localhost:8080/svg/abc123"
        assert urls["png_url"] == "http://localhost:8080/png/abc123"
        assert urls["edit_url"] == "http://localhost:8080/uml/abc123"

    def test_get_urls_strips_trailing_slash(self):
        """Trailing slash on server URL is handled."""
        encoded = "test"
        urls = get_plantuml_urls(encoded, "https://server.com/plantuml/")

        assert "plantuml//svg" not in urls["svg_url"]
        assert urls["svg_url"] == "https://server.com/plantuml/svg/test"
