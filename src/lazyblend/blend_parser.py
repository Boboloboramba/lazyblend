"""Parse Blender .blend file headers for metadata."""

import datetime
import struct
from dataclasses import dataclass, field
from pathlib import Path

from lazyblend.blend_inspector import BlendMetadata

BLEND_MAGIC = b"BLENDER"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


@dataclass
class BlendInfo:
    path: str
    size: int
    modified: float
    version: str = ""
    pointer_size: str = ""
    endianness: str = ""
    version_number: str = ""
    valid: bool = False
    compressed: bool = False
    metadata: BlendMetadata | None = None
    thumbnail: str = ""

    @property
    def size_str(self) -> str:
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.1f} GB"

    @property
    def modified_str(self) -> str:
        dt = datetime.datetime.fromtimestamp(self.modified)
        return dt.strftime("%Y-%m-%d %H:%M")


def parse_blend_header(filepath: str) -> BlendInfo:
    """Parse the header of a .blend file to extract metadata.

    Supports both regular and zstd-compressed blend files.
    Regular header format: BLENDER[fmt][endian][ptrsize][version]
    """
    path = Path(filepath)
    try:
        stat = path.stat()
    except OSError:
        return BlendInfo(path=str(filepath), size=0, modified=0)

    info = BlendInfo(
        path=str(path),
        size=stat.st_size,
        modified=stat.st_mtime,
    )

    try:
        with open(filepath, "rb") as f:
            header = f.read(20)
            if len(header) < 12:
                return info

            # Check for zstd-compressed blend file
            if header[:4] == ZSTD_MAGIC:
                info.compressed = True
                info.valid = True
                info.version = "Compressed (.blend.zst)"
                return info

            # Check for regular blend magic (7 bytes: "BLENDER")
            if header[:7] != BLEND_MAGIC:
                return info

            info.valid = True

            # Find pointer size marker ('-' or '_') after the magic
            ptr_idx = -1
            endian_idx = -1
            for i in range(7, min(15, len(header))):
                c = chr(header[i])
                if c in "-_" and ptr_idx == -1:
                    ptr_idx = i
                if c in "vV" and endian_idx == -1:
                    endian_idx = i

            if ptr_idx >= 0:
                info.pointer_size = "64-bit" if chr(header[ptr_idx]) == "_" else "32-bit"

            if endian_idx >= 0:
                info.endianness = "Little" if chr(header[endian_idx]) == "v" else "Big"

            # Try to extract version number (3 ASCII digits after endianness)
            if endian_idx >= 0 and endian_idx + 4 <= len(header):
                ver_bytes = header[endian_idx + 1 : endian_idx + 4]
                if all(48 <= b <= 57 for b in ver_bytes):  # ASCII digits
                    ver_str = ver_bytes.decode("ascii")
                    if ver_str != "000":
                        info.version_number = f"{ver_str[0]}.{ver_str[1]}.{ver_str[2]}"
                        info.version = f"Blender {info.version_number}"

    except (OSError, IOError):
        pass

    return info


def extract_thumbnail(filepath: str) -> bytes | None:
    """Try to extract an embedded PNG thumbnail from a .blend file.

    Blender embeds thumbnails as PNG data in the file header area.
    This is a best-effort extraction - not all blend files have thumbnails.
    """
    try:
        with open(filepath, "rb") as f:
            data = f.read(4096)  # Read first 4KB for thumbnail
            # Look for PNG header within the blend header
            png_start = data.find(b"\x89PNG\r\n\x1a\n")
            if png_start == -1:
                return None
            # Read until PNG end marker
            f.seek(png_start)
            chunk = f.read(32 * 1024)  # Read up to 32KB for thumbnail
            png_end = chunk.find(b"IEND\xaeB`\x82")
            if png_end == -1:
                return None
            return chunk[: png_end + 8]  # Include IEND chunk + CRC
    except (OSError, IOError):
        return None
