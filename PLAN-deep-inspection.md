# Plan: Blender API Deep File Inspection

## Overview

Add deep metadata extraction from blend files using Blender's Python API in background mode. This will show object counts, scene info, materials, collections, and more — all without opening Blender interactively.

## Architecture

### New Module: `src/lazyblend/blend_inspector.py`

Runs `blender -b <file> --python-expr "<script>"` in a background subprocess to extract metadata. The Python script runs inside Blender's interpreter and has full access to `bpy`.

### Data Model: `BlendMetadata`

```python
@dataclass
class BlendMetadata:
    scenes: list[SceneInfo]
    total_objects: int
    objects_by_type: dict[str, int]  # {"MESH": 5, "LIGHT": 3, ...}
    total_polygons: int
    total_vertices: int
    materials: list[str]
    collections: list[str]
    render_engine: str
    resolution: tuple[int, int]  # (x, y)
    fps: float
    frame_start: int
    frame_end: int
    addons: list[str]
    camera_count: int
    light_count: int
    extracted_at: float  # timestamp
```

### Caching: `~/.config/lazyblend/cache/`

- Cache key: SHA256 of file path + modification time
- Cache format: JSON files in `~/.config/lazyblend/cache/<hash>.json`
- TTL: Re-extract if file modified time > cached extracted_at
- Cache invalidation: On rescan, check mtimes

### Extraction Script

A Python script string sent to Blender's `--python-expr`:

```python
import bpy, json, sys

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
        "resolution": (scene.render.resolution_x, scene.render.resolution_y),
        "fps": scene.render.fps,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
    })

result = {
    "scenes": scenes,
    "total_objects": len(bpy.data.objects),
    "objects_by_type": {},
    "total_polygons": sum(len(m.polygons) for m in bpy.data.meshes),
    "total_vertices": sum(len(m.vertices) for m in bpy.data.meshes),
    "materials": [m.name for m in bpy.data.materials],
    "collections": [c.name for c in bpy.data.collections],
    "addons": [k for k, v in bpy.context.preferences.addons.items() if v.enabled],
    "camera_count": len(bpy.data.cameras),
    "light_count": len(bpy.data.lights),
}

# Aggregate object types across all scenes
for scene_info in scenes:
    for t, count in scene_info["objects_by_type"].items():
        result["objects_by_type"][t] = result["objects_by_type"].get(t, 0) + count

json.dump(result, sys.stdout)
```

## UI Changes

### Info Panel (existing `#info-panel`)

When deep metadata is available, display additional sections:

```
BoxTest1.blend
Path: /home/user/BlenderFiles/BoxTest1.blend
Size: 96.3 KB | Modified: 2026-08-26 05:18
Version: Compressed (.blend.zst)

Scenes: 1 (Scene)
Objects: 24 (12 mesh, 6 light, 3 camera, 3 empty)
Polygons: 48.2K | Vertices: 24.1K
Materials: 5 | Collections: 3
Render: Cycles | 1920x1080 @ 24fps
Frames: 1-250
```

### Loading State

Show "Analyzing..." while Blender subprocess runs. Use `@work(thread=True)` to avoid blocking.

## File Changes

| File | Change |
|------|--------|
| `src/lazyblend/blend_inspector.py` | **New** — extraction script, subprocess runner, cache manager |
| `src/lazyblend/blend_parser.py` | Add `metadata: BlendMetadata | None` field to `BlendInfo` |
| `src/lazyblend/app.py` | Update `_update_info_panel()` to show deep metadata, trigger async extraction on row highlight |
| `src/lazyblend/config.py` | Add `cache_dir` path constant |

## Performance Strategy

1. **Lazy extraction** — Only extract when user highlights a file (not during scan)
2. **Async subprocess** — Run Blender in a Textual worker thread
3. **Disk cache** — Avoid re-extracting unchanged files
4. **Timeout** — 10 second timeout per file, skip on failure
5. **Graceful degradation** — If Blender not found or extraction fails, show header-only info

## Implementation Steps

1. Create `blend_inspector.py` with extraction script and subprocess runner
2. Add `BlendMetadata` dataclass and cache logic
3. Add `metadata` field to `BlendInfo`
4. Update `app.py` to trigger async extraction on highlight
5. Update `_update_info_panel()` to render deep metadata
6. Add loading/error states
7. Test with real blend files
