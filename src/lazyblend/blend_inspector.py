"""Deep inspection of .blend files using Blender's Python API.

Runs Blender in background mode to extract scene, object, material,
and render metadata without opening the GUI.
"""

import hashlib
import json
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path

EXTRACT_TIMEOUT = 10  # seconds

EXTRACTION_SCRIPT = r"""
import bpy, json, sys, os

# Suppress Blender's verbose output
import logging
logging.getLogger().setLevel("ERROR")

scenes = []
for scene in bpy.data.scenes:
    objects = {}
    for obj in scene.objects:
        t = obj.type
        objects[t] = objects.get(t, 0) + 1

    scenes.append({
        "name": scene.name,
        "object_count": len(scene.objects),
        "objects_by_type": objects,
        "render_engine": scene.render.engine,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
        "fps": scene.render.fps,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "frame_current": scene.frame_current,
    })

objects_by_type = {}
object_names = []
for obj in bpy.data.objects:
    t = obj.type
    objects_by_type[t] = objects_by_type.get(t, 0) + 1
    if obj.name:
        object_names.append(obj.name)

materials = []
for m in bpy.data.materials:
    materials.append(m.name)

collections = []
for c in bpy.data.collections:
    collections.append(c.name)

# Get enabled addons
addons = []
try:
    for k, v in bpy.context.preferences.addons.items():
        addons.append(k)
except Exception:
    pass

result = {
    "scenes": scenes,
    "total_objects": len(bpy.data.objects),
    "objects_by_type": objects_by_type,
    "object_names": object_names,
    "total_polygons": sum(len(m.polygons) for m in bpy.data.meshes),
    "total_vertices": sum(len(m.vertices) for m in bpy.data.meshes),
    "materials": materials,
    "collections": collections,
    "render_engine": scenes[0]["render_engine"] if scenes else "",
    "resolution_x": scenes[0]["resolution_x"] if scenes else 0,
    "resolution_y": scenes[0]["resolution_y"] if scenes else 0,
    "fps": scenes[0]["fps"] if scenes else 0,
    "frame_start": scenes[0]["frame_start"] if scenes else 0,
    "frame_end": scenes[0]["frame_end"] if scenes else 0,
    "camera_count": len(bpy.data.cameras),
    "light_count": len(bpy.data.lights),
    "addons": addons,
    "blender_version": bpy.app.version_string,
}

# Write thumbnail if requested
thumb_path = os.environ.get("LAZYBLEND_THUMBNAIL", "")
if thumb_path:
    try:
        # First try extracting packed images
        for img in bpy.data.images:
            if img.packed_file:
                packed = img.packed_file
                with open(thumb_path, "wb") as tf:
                    tf.write(packed.data)
                break
        else:
            # Render a quick 128x128 preview
            scene = bpy.context.scene
            if scene:
                scene.render.resolution_x = 128
                scene.render.resolution_y = 128
                scene.render.resolution_percentage = 100
                scene.render.filepath = thumb_path
                scene.render.image_settings.file_format = "PNG"
                bpy.ops.render.render(write_still=True)
    except Exception:
        pass

# Write to output file instead of stdout to avoid Blender's own output
output_path = os.environ.get("LAZYBLEND_OUTPUT", "/tmp/lazyblend_extract.json")
with open(output_path, "w") as f:
    json.dump(result, f)
"""

RENAME_SCRIPT = r"""
import bpy, sys, os

# Get item type, old name, and new name from environment variables
item_type = os.environ.get("LAZYBLEND_RENAME_TYPE", "")
old_name = os.environ.get("LAZYBLEND_RENAME_OLD", "")
new_name = os.environ.get("LAZYBLEND_RENAME_NEW", "")

if not item_type or not old_name or not new_name:
    sys.exit(1)

renamed = False

if item_type == "scene":
    item = bpy.data.scenes.get(old_name)
    if item:
        item.name = new_name
        renamed = True

elif item_type == "object":
    item = bpy.data.objects.get(old_name)
    if item:
        item.name = new_name
        renamed = True

elif item_type == "collection":
    item = bpy.data.collections.get(old_name)
    if item:
        item.name = new_name
        renamed = True

elif item_type == "material":
    item = bpy.data.materials.get(old_name)
    if item:
        item.name = new_name
        renamed = True

elif item_type == "mesh":
    item = bpy.data.meshes.get(old_name)
    if item:
        item.name = new_name
        renamed = True

elif item_type == "light":
    item = bpy.data.lights.get(old_name)
    if item:
        item.name = new_name
        renamed = True

elif item_type == "camera":
    item = bpy.data.cameras.get(old_name)
    if item:
        item.name = new_name
        renamed = True

if renamed:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
"""


@dataclass
class SceneInfo:
    name: str
    object_count: int
    objects_by_type: dict[str, int]
    render_engine: str
    resolution_x: int
    resolution_y: int
    resolution_percentage: int
    fps: float
    frame_start: int
    frame_end: int
    frame_current: int


@dataclass
class BlendMetadata:
    scenes: list[SceneInfo] = field(default_factory=list)
    total_objects: int = 0
    objects_by_type: dict[str, int] = field(default_factory=dict)
    object_names: list[str] = field(default_factory=list)
    total_polygons: int = 0
    total_vertices: int = 0
    materials: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    render_engine: str = ""
    resolution_x: int = 0
    resolution_y: int = 0
    fps: float = 0
    frame_start: int = 0
    frame_end: int = 0
    camera_count: int = 0
    light_count: int = 0
    addons: list[str] = field(default_factory=list)
    blender_version: str = ""
    thumbnail_path: str = ""
    extracted_at: float = 0.0
    error: str = ""

    @property
    def polygon_str(self) -> str:
        if self.total_polygons < 1000:
            return str(self.total_polygons)
        return f"{self.total_polygons / 1000:.1f}K"

    @property
    def vertex_str(self) -> str:
        if self.total_vertices < 1000:
            return str(self.total_vertices)
        return f"{self.total_vertices / 1000:.1f}K"

    @property
    def resolution_str(self) -> str:
        if self.resolution_x and self.resolution_y:
            pct = self.resolution_x * self.resolution_y // 100
            return f"{self.resolution_x}x{self.resolution_y}"
        return ""

    @property
    def object_summary(self) -> str:
        if not self.objects_by_type:
            return str(self.total_objects)
        parts = []
        for t, count in sorted(self.objects_by_type.items(), key=lambda x: -x[1]):
            label = t.lower().replace("_", " ")
            if count == 1:
                label = label.rstrip("s") if label.endswith("s") else label
            parts.append(f"{count} {label}")
        return f"{self.total_objects} ({', '.join(parts)})"


def _cache_key(filepath: str) -> str:
    """Generate a cache key from the file path and modification time."""
    mtime = os.path.getmtime(filepath)
    raw = f"{filepath}:{mtime}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def get_cached_metadata(cache_dir: Path, filepath: str) -> BlendMetadata | None:
    """Load cached metadata if it exists and is still valid."""
    try:
        mtime = os.path.getmtime(filepath)
        key = _cache_key(filepath)
        cache_file = _cache_path(cache_dir, key)
        if not cache_file.exists():
            return None
        data = json.loads(cache_file.read_text())
        # Check if cache was created after the file was modified
        if data.get("extracted_at", 0) < mtime:
            return None
        return _dict_to_metadata(data)
    except (json.JSONDecodeError, OSError):
        return None


def save_metadata_cache(cache_dir: Path, filepath: str, metadata: BlendMetadata) -> None:
    """Save metadata to the cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(filepath)
    cache_file = _cache_path(cache_dir, key)
    cache_file.write_text(json.dumps(asdict(metadata), indent=2))


def extract_metadata(
    filepath: str,
    blender_path: str = "blender",
    thumb_dir: Path | None = None,
) -> BlendMetadata:
    """Run Blender in background mode to extract metadata from a blend file.

    Returns a BlendMetadata object with the extracted data, or an error
    if extraction failed.
    """
    import time
    import uuid

    metadata = BlendMetadata(extracted_at=time.time())

    if not os.path.exists(filepath):
        metadata.error = "File not found"
        return metadata

    # Use fixed temp paths to avoid NamedTemporaryFile handle conflicts
    uid = uuid.uuid4().hex[:8]
    output_path = f"/tmp/lazyblend_{uid}.json"
    script_path = f"/tmp/lazyblend_{uid}.py"

    # Set up thumbnail path if requested
    thumb_path = ""
    if thumb_dir:
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_key = hashlib.md5(filepath.encode()).hexdigest()
        thumb_path = str(thumb_dir / f"{thumb_key}.png")

    try:
        # Write extraction script
        with open(script_path, "w") as f:
            f.write(EXTRACTION_SCRIPT)

        env = {**os.environ, "LAZYBLEND_OUTPUT": output_path}
        if thumb_path:
            env["LAZYBLEND_THUMBNAIL"] = thumb_path

        result = subprocess.run(
            shlex.split(blender_path) + [
                "-b",  # background mode
                filepath,
                "--python", script_path,
            ],
            capture_output=True,
            text=True,
            timeout=EXTRACT_TIMEOUT,
            env=env,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            for line in reversed(stderr.split("\n")):
                if line.strip() and not line.startswith("  "):
                    metadata.error = line.strip()[:200]
                    break
            if not metadata.error:
                metadata.error = f"Blender exited with code {result.returncode}"
            return metadata

        # Read JSON from the output file
        if not os.path.exists(output_path):
            metadata.error = "No output file created"
            return metadata

        output = Path(output_path).read_text().strip()
        if not output:
            metadata.error = "Empty output file"
            return metadata

        data = json.loads(output)
        metadata = _dict_to_metadata(data, metadata)
        if thumb_path and os.path.exists(thumb_path):
            metadata.thumbnail_path = thumb_path
        return metadata

    except subprocess.TimeoutExpired:
        metadata.error = f"Extraction timed out ({EXTRACT_TIMEOUT}s)"
        return metadata
    except json.JSONDecodeError as e:
        metadata.error = f"Invalid JSON output: {e}"
        return metadata
    except FileNotFoundError:
        metadata.error = f"Blender not found at '{blender_path}'"
        return metadata
    except Exception as e:
        metadata.error = f"Extraction failed: {e}"
        return metadata
    finally:
        for path in [script_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass


def _dict_to_metadata(
    data: dict, base: BlendMetadata | None = None
) -> BlendMetadata:
    """Convert a dictionary to a BlendMetadata object."""
    import time

    scenes = []
    for s in data.get("scenes", []):
        scenes.append(
            SceneInfo(
                name=s.get("name", ""),
                object_count=s.get("object_count", 0),
                objects_by_type=s.get("objects_by_type", {}),
                render_engine=s.get("render_engine", ""),
                resolution_x=s.get("resolution_x", 0),
                resolution_y=s.get("resolution_y", 0),
                resolution_percentage=s.get("resolution_percentage", 100),
                fps=s.get("fps", 0),
                frame_start=s.get("frame_start", 0),
                frame_end=s.get("frame_end", 0),
                frame_current=s.get("frame_current", 0),
            )
        )

    return BlendMetadata(
        scenes=scenes,
        total_objects=data.get("total_objects", 0),
        objects_by_type=data.get("objects_by_type", {}),
        object_names=data.get("object_names", []),
        total_polygons=data.get("total_polygons", 0),
        total_vertices=data.get("total_vertices", 0),
        materials=data.get("materials", []),
        collections=data.get("collections", []),
        render_engine=data.get("render_engine", ""),
        resolution_x=data.get("resolution_x", 0),
        resolution_y=data.get("resolution_y", 0),
        fps=data.get("fps", 0),
        frame_start=data.get("frame_start", 0),
        frame_end=data.get("frame_end", 0),
        camera_count=data.get("camera_count", 0),
        light_count=data.get("light_count", 0),
        addons=data.get("addons", []),
        blender_version=data.get("blender_version", ""),
        extracted_at=base.extracted_at if base else time.time(),
    )


def rename_item(
    filepath: str,
    item_type: str,
    old_name: str,
    new_name: str,
    blender_path: str = "blender",
) -> bool:
    """Rename an item in a blend file using Blender.

    Returns True if successful, False otherwise.
    """
    if not os.path.exists(filepath):
        return False

    import uuid

    uid = uuid.uuid4().hex[:8]
    script_path = f"/tmp/lazyblend_rename_{uid}.py"

    try:
        with open(script_path, "w") as f:
            f.write(RENAME_SCRIPT)

        env = {
            **os.environ,
            "LAZYBLEND_RENAME_TYPE": item_type,
            "LAZYBLEND_RENAME_OLD": old_name,
            "LAZYBLEND_RENAME_NEW": new_name,
        }

        result = subprocess.run(
            shlex.split(blender_path) + ["-b", filepath, "--python", script_path],
            capture_output=True,
            text=True,
            timeout=EXTRACT_TIMEOUT,
            env=env,
        )

        return result.returncode == 0

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False
    finally:
        if os.path.exists(script_path):
            try:
                os.unlink(script_path)
            except OSError:
                pass
