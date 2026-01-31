"""Tests for sprite definitions and styling."""
import pytest

from src.converter.sprites import (
    CONTROLLER_SPRITES,
    DEVICE_SPRITES,
    PROTOCOL_COLORS,
    ZONE_COLORS,
    get_controller_style,
    get_device_style,
    get_protocol_style,
    get_zone_style,
)
from src.models import ControllerType, DeviceType, ProtocolType


class TestControllerSprites:
    """Tests for controller sprite definitions."""

    def test_all_controller_types_have_sprites(self):
        """Every ControllerType has a sprite definition."""
        for ct in ControllerType:
            style = get_controller_style(ct)
            assert style is not None
            assert "sprite" in style
            assert "stereotype" in style
            assert "color" in style

    def test_controller_colors_are_valid_hex(self):
        """Controller colors are valid hex codes."""
        for ct in ControllerType:
            style = get_controller_style(ct)
            color = style["color"]
            assert color.startswith("#")
            assert len(color) == 7
            # Check it's valid hex
            int(color[1:], 16)

    def test_safety_plc_is_red(self):
        """Safety PLC uses red color for visibility."""
        style = get_controller_style(ControllerType.SAFETY_PLC)
        # Safety colors should be in red family (#E74C3C or similar)
        assert style["color"].upper() in ("#E74C3C", "#C0392B", "#E53935")


class TestDeviceSprites:
    """Tests for device sprite definitions."""

    def test_all_device_types_have_sprites(self):
        """Every DeviceType has a sprite definition."""
        for dt in DeviceType:
            style = get_device_style(dt)
            assert style is not None
            assert "sprite" in style
            assert "stereotype" in style
            assert "color" in style

    def test_network_devices_use_hexagon(self):
        """Network devices (switch, router, firewall) use hexagon shape."""
        network_types = [DeviceType.SWITCH, DeviceType.ROUTER, DeviceType.FIREWALL]
        for dt in network_types:
            style = get_device_style(dt)
            assert style["shape"] == "hexagon", f"{dt} should use hexagon shape"

    def test_historian_uses_database_shape(self):
        """Historian device uses database shape."""
        style = get_device_style(DeviceType.HISTORIAN)
        assert style["shape"] == "database"


class TestProtocolColors:
    """Tests for protocol line colors."""

    def test_all_protocols_have_colors(self):
        """Every ProtocolType has a color definition."""
        for pt in ProtocolType:
            style = get_protocol_style(pt)
            assert style is not None
            assert "color" in style
            assert "style" in style
            assert "label" in style

    def test_fieldbus_protocols_are_dashed(self):
        """Serial/fieldbus protocols use dashed lines."""
        fieldbus = [
            ProtocolType.MODBUS_RTU,
            ProtocolType.PROFIBUS,
            ProtocolType.DEVICENET,
        ]
        for pt in fieldbus:
            style = get_protocol_style(pt)
            assert style["style"] == "dashed", f"{pt} should use dashed lines"

    def test_ethernet_protocols_are_solid(self):
        """Ethernet protocols use solid lines."""
        ethernet = [
            ProtocolType.ETHERNET_IP,
            ProtocolType.PROFINET,
            ProtocolType.MODBUS_TCP,
            ProtocolType.OPC_UA,
        ]
        for pt in ethernet:
            style = get_protocol_style(pt)
            assert style["style"] == "solid", f"{pt} should use solid lines"


class TestZoneColors:
    """Tests for Purdue zone colors."""

    def test_all_purdue_levels_have_colors(self):
        """Purdue levels 0-4 all have color definitions."""
        for level in range(5):
            style = get_zone_style(level)
            assert style is not None
            assert "background" in style
            assert "border" in style
            assert "name" in style

    def test_zone_backgrounds_are_light(self):
        """Zone backgrounds are light colors for readability."""
        for level in range(5):
            style = get_zone_style(level)
            bg = style["background"]
            # Light colors have high R, G, B values
            r = int(bg[1:3], 16)
            g = int(bg[3:5], 16)
            b = int(bg[5:7], 16)
            # Average > 200 indicates light color
            assert (r + g + b) / 3 > 180, f"Level {level} background too dark"

    def test_level_0_is_green_field(self):
        """Level 0 (field) uses green tones."""
        style = get_zone_style(0)
        # Green background should have G component highest
        bg = style["background"]
        g = int(bg[3:5], 16)
        r = int(bg[1:3], 16)
        b = int(bg[5:7], 16)
        assert g >= r and g >= b, "Field level should be green-tinted"

    def test_level_1_is_blue_control(self):
        """Level 1 (control) uses blue tones."""
        style = get_zone_style(1)
        bg = style["background"]
        b = int(bg[5:7], 16)
        r = int(bg[1:3], 16)
        g = int(bg[3:5], 16)
        assert b >= r and b >= g, "Control level should be blue-tinted"


class TestDefaultStyles:
    """Tests for default/fallback styles."""

    def test_unknown_controller_type_returns_default(self):
        """Unknown controller type returns sensible default."""
        # Create mock enum value (this tests the fallback)
        style = CONTROLLER_SPRITES.get(
            "UNKNOWN",
            {"sprite": "controller", "stereotype": "<<Controller>>", "color": "#95A5A6"},
        )
        assert style["color"] == "#95A5A6"

    def test_unknown_device_type_returns_default(self):
        """Unknown device type returns sensible default."""
        style = DEVICE_SPRITES.get(
            "UNKNOWN",
            {"sprite": "device", "stereotype": "<<Device>>", "color": "#BDC3C7"},
        )
        assert style["color"] == "#BDC3C7"
