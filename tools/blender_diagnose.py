"""
Diagnostic script — run this first to check bone names.

"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe" --background --python tools\blender_diagnose.py
"""

import bpy
import os

PSK_FILE = r"C:\Users\Administrator\Desktop\New folder (2)\Output\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster\AncientStingray\Meshes\SK_AncientStingray_LOD0.psk"

PSA_FILE = r"C:\Users\Administrator\Desktop\New folder (2)\Output\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster\AncientStingray\Animations\AS_AncientStingray_idle_Combat.psa"

GLB_FILE = r"C:\Users\Administrator\Desktop\DnDMainProject\darkanddarker-wiki\website\public\monster-models\ancient-stingray.glb"

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=True)

def print_scene_objects():
    print("\n--- Scene objects ---")
    for obj in bpy.data.objects:
        print(f"  {obj.name}  type={obj.type}")
        if obj.type == "ARMATURE":
            bones = list(obj.data.bones)
            print(f"    Bone count: {len(bones)}")
            print(f"    First 10 bones: {[b.name for b in bones[:10]]}")

# ── Test 1: PSK import ───────────────────────────────────────────────────────
print("\n========== TEST 1: PSK import ==========")
clear_scene()
try:
    bpy.ops.psk.import(filepath=PSK_FILE)
    print("PSK import: OK")
except Exception as e:
    print(f"PSK import FAILED: {e}")
print_scene_objects()

# ── Test 2: GLB import ───────────────────────────────────────────────────────
print("\n========== TEST 2: GLB import ==========")
clear_scene()
try:
    bpy.ops.import_scene.gltf(filepath=GLB_FILE)
    print("GLB import: OK")
except Exception as e:
    print(f"GLB import FAILED: {e}")
print_scene_objects()

# ── Test 3: PSA bone names ───────────────────────────────────────────────────
print("\n========== TEST 3: PSA bone names ==========")
import struct

def read_psa_bones(filepath):
    with open(filepath, "rb") as f:
        buf = f.read()
    off = 0
    while off + 32 <= len(buf):
        chunk_id = buf[off:off+20].decode("ascii", errors="replace").rstrip("\x00").strip()
        data_size = struct.unpack_from("<I", buf, off+24)[0]
        data_count = struct.unpack_from("<I", buf, off+28)[0]
        data_start = off + 32
        if chunk_id == "BONENAMES":
            bones = []
            for i in range(data_count):
                o = data_start + i * data_size
                name = buf[o:o+64].decode("ascii", errors="replace").rstrip("\x00").strip()
                bones.append(name)
            return bones
        off = data_start + data_size * data_count
    return []

psa_bones = read_psa_bones(PSA_FILE)
print(f"PSA bone count: {len(psa_bones)}")
print(f"PSA first 10 bones: {psa_bones[:10]}")
