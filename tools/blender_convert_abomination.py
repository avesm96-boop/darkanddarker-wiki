"""
Blender headless converter for Abomination: PSK + PSA + textures → GLB files.

Exports:
  - Per-variant textured model GLBs (common, elite, nightmare)
  - Per-animation GLBs with manifest.json
  - A base display GLB (abomination.glb) using Common textures

Run:
  "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe" ^
      --background --python tools/blender_convert_abomination.py

Requires the io_scene_psk_psa addon installed in Blender.
"""

import bpy
import os
import sys
import json
import re
import addon_utils

# ── Blender addon ────────────────────────────────────────────────────────────

addon_utils.enable("io_scene_psk_psa", default_set=True)
print(f"PSK/PSA addon loaded: {addon_utils.check('io_scene_psk_psa')}")

# ── Config ───────────────────────────────────────────────────────────────────

# PSK and PSA source (FModel export)
MONSTER_DIR = r"C:\Users\pawel\Desktop\Projects\Output\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster\Abomination"

# Textures source (project Exports — has all variant textures)
TEXTURE_DIR = r"C:\Users\pawel\Desktop\Projects\DnDMainProject\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster\Abomination\Textures"

PSK_FILE = os.path.join(MONSTER_DIR, "Mesh", "SK_Abomination_LOD0.psk")
ANIM_DIR = os.path.join(MONSTER_DIR, "Animations")

OUT_ROOT = r"C:\Users\pawel\Desktop\Projects\DnDMainProject\darkanddarker-wiki\website\public\monster-models"

SLUG = "abomination"

# Texture mapping per variant
# Each variant only overrides the diffuse (_D) — MNR and E are shared across all grades
TEXTURE_MAP = {
    "common": {
        "body": {
            "D": os.path.join(TEXTURE_DIR, "T_Abomination_D.png"),
            "MNR": os.path.join(TEXTURE_DIR, "T_Abomination_MNR.png"),
            "E": os.path.join(TEXTURE_DIR, "T_Abomination_E.png"),
        },
        "hammer": {
            "D": os.path.join(TEXTURE_DIR, "T_Abomination_hammer_D.png"),
            "MNR": os.path.join(TEXTURE_DIR, "T_Abomination_hammer_MNR.png"),
        },
    },
    "elite": {
        "body": {
            "D": os.path.join(TEXTURE_DIR, "T_Abomination_Elite_D.png"),
            "MNR": os.path.join(TEXTURE_DIR, "T_Abomination_MNR.png"),
            "E": os.path.join(TEXTURE_DIR, "T_Abomination_E.png"),
        },
        "hammer": {
            "D": os.path.join(TEXTURE_DIR, "T_Abomination_hammer_Elite_D.png"),
            "MNR": os.path.join(TEXTURE_DIR, "T_Abomination_hammer_MNR.png"),
        },
    },
    "nightmare": {
        "body": {
            "D": os.path.join(TEXTURE_DIR, "T_Abomination_Nightmare_D.png"),
            "MNR": os.path.join(TEXTURE_DIR, "T_Abomination_MNR.png"),
            "E": os.path.join(TEXTURE_DIR, "T_Abomination_E.png"),
        },
        "hammer": {
            "D": os.path.join(TEXTURE_DIR, "T_Abomination_hammer_Nightmare_D.png"),
            "MNR": os.path.join(TEXTURE_DIR, "T_Abomination_hammer_MNR.png"),
        },
    },
}

# Animation name patterns that should loop
LOOP_PATTERNS = [
    r"idle",
    r"loop",
    r"run(?!.*(?:start|stop|end))",
    r"walk(?!.*(?:start|stop|end))",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def should_loop(anim_name):
    name_lower = anim_name.lower()
    for pattern in LOOP_PATTERNS:
        if re.search(pattern, name_lower):
            return True
    return False


def id_from_filename(filename):
    name = os.path.splitext(filename)[0]
    if name.startswith(("AM_", "AS_", "SM_")):
        name = name[3:]
    slug = re.sub(r'_+', '-', name).lower()
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug or os.path.splitext(filename)[0].lower()


def label_from_filename(filename):
    name = os.path.splitext(filename)[0]
    if name.startswith(("AM_", "AS_", "SM_")):
        name = name[3:]
    label = name.replace("_", " ")
    label = re.sub(r'([a-z])([A-Z])', r'\1 \2', label)
    label = re.sub(r'\s+', ' ', label).strip()
    label = " ".join(w.capitalize() if w.islower() else w for w in label.split())
    return label or name


# ── Blender operations ───────────────────────────────────────────────────────

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=True)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)
    for block in list(bpy.data.armatures):
        bpy.data.armatures.remove(block)
    for block in list(bpy.data.actions):
        bpy.data.actions.remove(block)
    for block in list(bpy.data.materials):
        bpy.data.materials.remove(block)
    for block in list(bpy.data.images):
        bpy.data.images.remove(block)


def find_armature():
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def find_meshes():
    return [obj for obj in bpy.data.objects if obj.type == "MESH"]


def apply_textures_to_mesh(mesh_obj, variant="common"):
    """Apply PBR textures to mesh materials based on variant."""
    tex_config = TEXTURE_MAP.get(variant, TEXTURE_MAP["common"])

    for mat_slot in mesh_obj.material_slots:
        if mat_slot.material is None:
            continue

        mat = mat_slot.material
        mat_name_lower = mat.name.lower()

        # Determine which texture set to use based on material slot name
        tex_set = None
        if "hammer" in mat_name_lower or "weapon" in mat_name_lower:
            tex_set = tex_config.get("hammer")
        else:
            # Default to body textures
            tex_set = tex_config.get("body")

        if not tex_set:
            continue

        # Enable nodes
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear existing nodes
        nodes.clear()

        # Create Principled BSDF
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

        # Create output
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (400, 0)
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        # Diffuse / Base Color
        diffuse_path = tex_set.get("D")
        if diffuse_path and os.path.exists(diffuse_path):
            tex_node = nodes.new("ShaderNodeTexImage")
            tex_node.location = (-600, 300)
            tex_node.image = bpy.data.images.load(diffuse_path)
            tex_node.image.colorspace_settings.name = "sRGB"
            links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
            print(f"      Applied diffuse: {os.path.basename(diffuse_path)} → {mat.name}")

        # MNR texture (Metallic in R, Normal-derived in G, Roughness in B)
        mnr_path = tex_set.get("MNR")
        if mnr_path and os.path.exists(mnr_path):
            mnr_node = nodes.new("ShaderNodeTexImage")
            mnr_node.location = (-600, 0)
            mnr_node.image = bpy.data.images.load(mnr_path)
            mnr_node.image.colorspace_settings.name = "Non-Color"

            # Separate RGB to get M, N, R channels
            sep = nodes.new("ShaderNodeSeparateColor")
            sep.location = (-300, 0)
            links.new(mnr_node.outputs["Color"], sep.inputs["Color"])

            # R = Metallic
            links.new(sep.outputs[0], bsdf.inputs["Metallic"])
            # B = Roughness
            links.new(sep.outputs[2], bsdf.inputs["Roughness"])

            print(f"      Applied MNR: {os.path.basename(mnr_path)} → {mat.name}")

        # Emissive
        emissive_path = tex_set.get("E")
        if emissive_path and os.path.exists(emissive_path):
            emissive_node = nodes.new("ShaderNodeTexImage")
            emissive_node.location = (-600, -300)
            emissive_node.image = bpy.data.images.load(emissive_path)
            emissive_node.image.colorspace_settings.name = "sRGB"
            links.new(emissive_node.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 1.0
            print(f"      Applied emissive: {os.path.basename(emissive_path)} → {mat.name}")


def remove_all_actions(armature_obj):
    if armature_obj.animation_data:
        armature_obj.animation_data.action = None
        if hasattr(armature_obj.animation_data, 'nla_tracks'):
            for track in list(armature_obj.animation_data.nla_tracks):
                armature_obj.animation_data.nla_tracks.remove(track)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action, do_unlink=True)


def strip_root_motion(action):
    removed = 0
    for fc in list(action.fcurves):
        if fc.data_path == 'pose.bones["root"].location':
            action.fcurves.remove(fc)
            removed += 1
    if removed:
        print(f"      Stripped {removed} root-motion fcurves")


def export_glb(out_path, include_animations=False):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB",
        use_selection=True,
        export_animations=include_animations,
        export_skins=True,
        export_morph=False,
        export_lights=False,
        export_cameras=False,
        export_apply=False,
        export_image_format="AUTO",
        export_materials="EXPORT",
    )


def export_anim_glb(armature_obj, out_path):
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_nla_strips=False,
        export_current_frame=False,
        export_skins=False,
        export_morph=False,
        export_lights=False,
        export_cameras=False,
        export_apply=False,
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  Abomination PSK/PSA → GLB Converter")
    print("=" * 60)

    anim_out_dir = os.path.join(OUT_ROOT, "animations", SLUG)
    os.makedirs(anim_out_dir, exist_ok=True)

    # ── Step 1: Import PSK ────────────────────────────────────────────────
    clear_scene()
    print("\n[1/4] Importing skeleton mesh...")
    print(f"  PSK: {PSK_FILE}")

    bpy.ops.psk.import_file(filepath=PSK_FILE)

    armature_obj = find_armature()
    if armature_obj is None:
        print("ERROR: No armature found after PSK import!")
        return

    meshes = find_meshes()
    print(f"  Armature: '{armature_obj.name}' ({len(armature_obj.data.bones)} bones)")
    print(f"  Meshes: {len(meshes)}")
    for m in meshes:
        mat_names = [s.material.name if s.material else "None" for s in m.material_slots]
        print(f"    {m.name}: materials = {mat_names}")

    # Apply transforms
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # ── Step 2: Export textured model GLBs per variant ────────────────────
    print("\n[2/4] Exporting textured model GLBs...")

    for variant in ["common", "elite", "nightmare"]:
        print(f"\n  Variant: {variant}")

        # Apply textures
        for mesh_obj in meshes:
            apply_textures_to_mesh(mesh_obj, variant)

        # Remove any animations before model export
        remove_all_actions(armature_obj)

        # Export variant model
        variant_path = os.path.join(OUT_ROOT, "animations", SLUG, f"{SLUG}-{variant}.glb")
        export_glb(variant_path, include_animations=False)
        size_mb = os.path.getsize(variant_path) / 1024 / 1024
        print(f"  Exported: {variant_path} ({size_mb:.1f}MB)")

    # Also export the base display model (Common textures) as the main .glb
    print("\n  Exporting base display model...")
    for mesh_obj in meshes:
        apply_textures_to_mesh(mesh_obj, "common")
    remove_all_actions(armature_obj)
    base_model_path = os.path.join(OUT_ROOT, f"{SLUG}.glb")
    export_glb(base_model_path, include_animations=False)
    size_mb = os.path.getsize(base_model_path) / 1024 / 1024
    print(f"  Base model: {base_model_path} ({size_mb:.1f}MB)")

    # Also export raw model for animation directory
    raw_path = os.path.join(anim_out_dir, f"{SLUG}-raw.glb")
    export_glb(raw_path, include_animations=False)

    # ── Step 3: Convert each PSA to animation GLB ─────────────────────────
    print("\n[3/4] Converting animations...")

    psa_files = sorted([
        f for f in os.listdir(ANIM_DIR)
        if f.endswith(".psa")
    ])
    print(f"  Found {len(psa_files)} PSA files")

    manifest = {"monster": SLUG, "animations": []}
    converted = 0

    for psa_file in psa_files:
        psa_path = os.path.join(ANIM_DIR, psa_file)
        anim_id = id_from_filename(psa_file)
        label = label_from_filename(psa_file)
        loop = should_loop(psa_file)

        print(f"    {psa_file} → {anim_id}.glb", end="")

        # Clear previous actions
        remove_all_actions(armature_obj)

        # Import PSA
        bpy.ops.object.select_all(action="DESELECT")
        armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = armature_obj

        actions_before = set(bpy.data.actions.keys())
        try:
            bpy.ops.psa.import_file('EXEC_DEFAULT', filepath=psa_path)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        new_actions = set(bpy.data.actions.keys()) - actions_before
        if not new_actions:
            print("  SKIP (no action)")
            continue

        action = bpy.data.actions[next(iter(new_actions))]
        if not armature_obj.animation_data:
            armature_obj.animation_data_create()
        armature_obj.animation_data.action = action

        strip_root_motion(action)

        # Export animation GLB
        out_path = os.path.join(anim_out_dir, f"{anim_id}.glb")
        try:
            export_anim_glb(armature_obj, out_path)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        size_kb = os.path.getsize(out_path) // 1024
        print(f"  ({size_kb}KB) {'[loop]' if loop else ''}")

        manifest["animations"].append({
            "id": anim_id,
            "label": label,
            "file": f"{anim_id}.glb",
            "loop": loop,
        })
        converted += 1

    # ── Step 4: Write manifest ────────────────────────────────────────────
    print("\n[4/4] Writing manifest...")

    manifest_path = os.path.join(anim_out_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"  Manifest: {manifest_path}")
    print(f"\n{'=' * 60}")
    print(f"  DONE: {converted}/{len(psa_files)} animations converted")
    print(f"  Model GLBs: common, elite, nightmare + base display")
    print(f"{'=' * 60}")


main()
