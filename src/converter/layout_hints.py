"""Layout hints and directives for PlantUML CSA diagrams.

Provides Purdue-aware layout configuration for hierarchical diagrams.
"""
from typing import Literal

LayoutDirection = Literal["top_to_bottom", "left_to_right", "hierarchical"]
LayoutEngine = Literal["graphviz", "smetana", "elk"]


def get_layout_directive(layout: LayoutDirection) -> str:
    """Get PlantUML layout directive for diagram direction."""
    directives = {
        "top_to_bottom": "top to bottom direction",
        "left_to_right": "left to right direction",
        "hierarchical": "top to bottom direction",  # Purdue levels flow top-down
    }
    return directives.get(layout, "top to bottom direction")


def get_skinparam_base(theme: str = "csa_industrial", font: str = "Arial") -> str:
    """Get base skinparam styling for CSA diagrams.

    Args:
        theme: Theme name (currently supports 'csa_industrial')
        font: Font family name

    Returns:
        PlantUML skinparam block
    """
    return f"""
skinparam defaultFontName {font}
skinparam defaultFontSize 11
skinparam dpi 150
skinparam shadowing false
skinparam roundcorner 8

skinparam package {{
    BackgroundColor #FAFAFA
    BorderColor #BDBDBD
    FontStyle bold
    FontSize 12
}}

skinparam rectangle {{
    BackgroundColor #FFFFFF
    BorderColor #37474F
    FontSize 10
    Padding 8
}}

skinparam database {{
    BackgroundColor #FFFFFF
    BorderColor #37474F
}}

skinparam hexagon {{
    BackgroundColor #FFFFFF
    BorderColor #37474F
}}

skinparam arrow {{
    Color #546E7A
    FontSize 9
}}

skinparam legend {{
    BackgroundColor #FAFAFA
    BorderColor #E0E0E0
    FontSize 9
}}
""".strip()


def get_layout_engine_config(engine: LayoutEngine) -> str:
    """Get PlantUML pragma for specific layout engine.

    Args:
        engine: Layout engine (graphviz, smetana, elk)

    Returns:
        PlantUML pragma directive (empty for graphviz as it's default)
    """
    if engine == "smetana":
        return "!pragma layout smetana"
    elif engine == "elk":
        return "!pragma layout elk"
    # graphviz is the default, no pragma needed
    return ""


def get_purdue_level_ordering() -> str:
    """Get hidden links for enforcing Purdue level ordering.

    Returns:
        PlantUML hidden links that enforce vertical ordering
    """
    return """
' Enforce Purdue level ordering (hidden links)
level_4 -[hidden]-> level_3
level_3 -[hidden]-> level_2
level_2 -[hidden]-> level_1
level_1 -[hidden]-> level_0
""".strip()


def get_legend_block(show_protocols: bool = True) -> str:
    """Get legend block showing protocol colors.

    Args:
        show_protocols: Whether to include protocol color legend

    Returns:
        PlantUML legend block
    """
    if not show_protocols:
        return ""

    return """
legend right
  |= Protocol |= Color |
  | EtherNet/IP | <color:#0066CC>━━━</color> |
  | PROFINET | <color:#009933>━━━</color> |
  | Modbus TCP | <color:#FF6600>━━━</color> |
  | OPC-UA | <color:#6600CC>━━━</color> |
  | HART | <color:#996633>- - -</color> |
endlegend
""".strip()
