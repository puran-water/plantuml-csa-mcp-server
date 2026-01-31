"""PlantUML text encoding for shareable URLs.

Implements the PlantUML text encoding algorithm to generate URLs that can
be used with PlantUML servers (e.g., plantuml.com/plantuml).

The encoding uses a modified base64 alphabet and deflate compression.
"""
from __future__ import annotations

import zlib

# PlantUML uses a custom base64 alphabet
PLANTUML_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
STANDARD_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _encode_6bit(b: int) -> str:
    """Encode a 6-bit value to PlantUML alphabet character."""
    if b < 10:
        return chr(48 + b)  # '0' to '9'
    b -= 10
    if b < 26:
        return chr(65 + b)  # 'A' to 'Z'
    b -= 26
    if b < 26:
        return chr(97 + b)  # 'a' to 'z'
    b -= 26
    if b == 0:
        return "-"
    if b == 1:
        return "_"
    return "?"


def _encode_3bytes(b1: int, b2: int, b3: int) -> str:
    """Encode 3 bytes (24 bits) to 4 PlantUML alphabet characters."""
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F

    return (
        _encode_6bit(c1) + _encode_6bit(c2) + _encode_6bit(c3) + _encode_6bit(c4)
    )


def encode_plantuml(source: str) -> str:
    """Encode PlantUML source for URL usage.

    Args:
        source: PlantUML source text

    Returns:
        Encoded string suitable for PlantUML server URLs
    """
    # Compress using deflate
    compressed = zlib.compress(source.encode("utf-8"), 9)

    # Remove zlib header (2 bytes) and checksum (4 bytes) to get raw deflate
    # Actually, PlantUML uses raw deflate, but zlib adds wrapper
    # Use zlib.compressobj with wbits=-15 for raw deflate
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed = compressor.compress(source.encode("utf-8"))
    compressed += compressor.flush()

    # Encode to PlantUML alphabet
    result = []
    data = list(compressed)

    # Pad to multiple of 3
    while len(data) % 3 != 0:
        data.append(0)

    # Encode each 3-byte chunk
    for i in range(0, len(data), 3):
        result.append(_encode_3bytes(data[i], data[i + 1], data[i + 2]))

    return "".join(result)


def _decode_6bit(c: str) -> int:
    """Decode a PlantUML alphabet character to 6-bit value."""
    if c == "_":
        return 63
    if c == "-":
        return 62
    char_code = ord(c)
    if char_code >= ord("a"):
        return char_code - 61  # 'a' is 36
    if char_code >= ord("A"):
        return char_code - 55  # 'A' is 10
    return char_code - 48  # '0' is 0


def _decode_4chars(c1: str, c2: str, c3: str, c4: str) -> tuple[int, int, int]:
    """Decode 4 PlantUML alphabet characters to 3 bytes."""
    b1 = _decode_6bit(c1)
    b2 = _decode_6bit(c2)
    b3 = _decode_6bit(c3)
    b4 = _decode_6bit(c4)

    return (
        (b1 << 2) | (b2 >> 4),
        ((b2 & 0xF) << 4) | (b3 >> 2),
        ((b3 & 0x3) << 6) | b4,
    )


def decode_plantuml(encoded: str) -> str:
    """Decode PlantUML encoded string back to source.

    Args:
        encoded: Encoded PlantUML string

    Returns:
        Decoded PlantUML source text
    """
    # Decode from PlantUML alphabet
    data = []
    for i in range(0, len(encoded), 4):
        chunk = encoded[i : i + 4]
        if len(chunk) < 4:
            chunk = chunk.ljust(4, "A")  # Pad with 'A' (value 10)
        b1, b2, b3 = _decode_4chars(chunk[0], chunk[1], chunk[2], chunk[3])
        data.extend([b1, b2, b3])

    # Decompress using raw deflate
    try:
        decompressor = zlib.decompressobj(-15)
        decompressed = decompressor.decompress(bytes(data))
        return decompressed.decode("utf-8")
    except zlib.error:
        # Try with trailing data tolerance
        decompressor = zlib.decompressobj(-15)
        decompressed = decompressor.decompress(bytes(data), max_length=1024 * 1024)
        return decompressed.decode("utf-8")


def get_plantuml_urls(
    encoded: str,
    server_url: str = "https://www.plantuml.com/plantuml",
) -> dict[str, str]:
    """Generate PlantUML server URLs for different formats.

    Args:
        encoded: Encoded PlantUML string (from encode_plantuml)
        server_url: PlantUML server base URL

    Returns:
        Dict with svg_url, png_url, and edit_url
    """
    server_url = server_url.rstrip("/")

    return {
        "svg_url": f"{server_url}/svg/{encoded}",
        "png_url": f"{server_url}/png/{encoded}",
        "edit_url": f"{server_url}/uml/{encoded}",
        "encoded": encoded,
    }
