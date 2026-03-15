"""
Blender headless converter for standard monsters: PSK + PSA + textures → GLB files.

A "standard" monster has:
  - A single main PSK mesh (SK_*_LOD0.psk)
  - All PSA animations in one Animations/ directory
  - Textures with _D (diffuse), _MNR/_ORM (PBR), optionally _E (emissive)
  - Variant diffuses: _Elite_D, _Nightmare_D

Run:
  "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe" ^
      --background --python tools/blender_convert_standard.py -- --name CaveTroll --slug cave-troll

Arguments (after --):
  --name DIR_NAME     Directory name in the Monster exports (e.g. CaveTroll)
  --slug SLUG         Output slug (e.g. cave-troll)
  --psk FILENAME      Override PSK filename (default: auto-detect SK_*_LOD0.psk)
"""

import bpy
import os
import sys
import json
import re
import addon_utils

# ── Blender addon ────────────────────────────────────────────────────────────

addon_utils.enable("io_scene_psk_psa", default_set=True)

# ── Config ───────────────────────────────────────────────────────────────────

FMODEL_ROOT = r"C:\Users\Administrator\Desktop\New folder (2)\Output\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster"
PROJECT_ROOT = r"C:\Users\Administrator\Desktop\DnDMainProject\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster"
OUT_ROOT = r"C:\Users\Administrator\Desktop\DnDMainProject\darkanddarker-wiki\website\public\monster-models"

LOOP_PATTERNS = [
    r"idle", r"loop",
    r"swim(?!.*(?:start|end|spawn))",
    r"run(?!.*(?:start|stop|end))",
    r"walk(?!.*(?:start|stop|end))",
    r"fly(?!.*(?:start|stop|end|land))",
    r"hover", r"patrol", r"breath(?:e|ing)",
]

# ── CLI Args ─────────────────────────────────────────────────────────────────

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {"name": None, "slug": None, "psk": None}
    i = 0
    while i < len(argv):
        if argv[i] == "--name" and i + 1 < len(argv):
            args["name"] = argv[i + 1]; i += 2
        elif argv[i] == "--slug" and i + 1 < len(argv):
            args["slug"] = argv[i + 1]; i += 2
        elif argv[i] == "--psk" and i + 1 < len(argv):
            args["psk"] = argv[i + 1]; i += 2
        else:
            i += 1
    return args

# ── Helpers ──────────────────────────────────────────────────────────────────

def should_loop(name):
    name_lower = name.lower()
    return any(re.search(p, name_lower) for p in LOOP_PATTERNS)

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

def find_psk(monster_dir, override=None):
    """Find the best PSK file for a standard monster."""
    if override:
        # Try exact path first, then search
        exact = os.path.join(monster_dir, override)
        if os.path.exists(exact):
            return exact
        for root, dirs, files in os.walk(monster_dir):
            if override in files:
                return os.path.join(root, override)

    # Auto-detect: find *_LOD0.psk (SK_ preferred but not required)
    candidates = []
    for root, dirs, files in os.walk(monster_dir):
        for f in files:
            if not f.endswith(".psk"):
                continue
            if "LOD1" in f or "LOD2" in f:
                continue  # Skip lower LODs
            if "Invisible" in f:
                continue
            full = os.path.join(root, f)
            is_variant = "Elite" in f or "Nightmare" in f
            is_sk = f.startswith("SK_")
            is_lod0 = "LOD0" in f

            if not is_variant and is_sk and is_lod0:
                candidates.insert(0, full)  # Best: SK_ + LOD0 + base
            elif not is_variant and is_lod0:
                candidates.insert(1 if candidates else 0, full)  # LOD0 + base but not SK_
            elif not is_variant:
                candidates.append(full)
    return candidates[0] if candidates else None

def find_psa_files(monster_dir):
    """Find all PSA files recursively."""
    psa_files = []
    for root, dirs, files in os.walk(monster_dir):
        for f in sorted(files):
            if f.endswith(".psa"):
                psa_files.append(os.path.join(root, f))
    return psa_files

def find_texture_dirs(monster_name):
    """Find all directories containing textures for this monster.
    Handles both 'Textures/' and 'Texture/' (singular) naming.
    Searches in both project Exports and FModel exports."""
    tex_dirs = []
    for base in [PROJECT_ROOT, FMODEL_ROOT]:
        monster_path = os.path.join(base, monster_name)
        if not os.path.isdir(monster_path):
            continue
        # Search for Textures/ or Texture/ directories
        for root, dirs, files in os.walk(monster_path):
            dir_name = os.path.basename(root).lower()
            if dir_name in ("textures", "texture"):
                tex_dirs.append(root)
            # Don't recurse into Animations
            if "Animations" in dirs:
                dirs.remove("Animations")
    return tex_dirs

def find_textures(monster_name):
    """Find and map textures for all variants.
    Handles multiple naming conventions:
      - _D.png / _diffuse.png / _BaseColor.png (diffuse)
      - _MNR.png / _ORM.png / _MetalAndRough*.png (PBR packed)
      - _roughness.png (standalone roughness)
      - _N.png / _Normal.png / _normal.png (normal map)
      - _E.png / _Emissive*.png / _E.png (emissive)
      - _Elite_D.png / _D_Elite.png / _Elite_diffuse.png (variant diffuse)
      - _Nightmare_D.png / _D_Nightmare.png (variant diffuse)
    """
    tex_dirs = find_texture_dirs(monster_name)
    if not tex_dirs:
        return {}

    # Collect all PNGs from all texture dirs recursively (project Exports preferred = later override)
    all_tex = {}
    for d in tex_dirs:
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.endswith(".png"):
                    all_tex[f] = os.path.join(root, f)

    if not all_tex:
        return {}

    # Classify textures
    diffuses = {}  # variant -> [(filename, path)]
    pbr_files = []  # MNR/ORM/MetalAndRough
    emissive_files = []
    normal_files = []
    roughness_files = []

    for fname, fpath in sorted(all_tex.items()):
        fl = fname.lower()

        # Skip alpha/mask/AO-only files for material assignment
        if fl.endswith("_alpha.png") or fl.endswith("_mask.png") or fl.endswith("_ao.png"):
            continue

        # Detect variant
        is_elite = "_elite" in fl
        is_nightmare = "_nightmare" in fl
        is_variant = is_elite or is_nightmare

        # Detect type by suffix patterns (order matters)
        is_diffuse = False
        is_pbr = False
        is_emissive = False
        is_normal = False
        is_roughness = False

        # Diffuse patterns
        if (fl.endswith("_d.png") or "_diffuse" in fl or "_basecolor" in fl or
            "_albedo" in fl or
            (is_elite and "_d.png" in fl) or (is_nightmare and "_d.png" in fl) or
            fl.endswith("_d_elite.png") or fl.endswith("_d_nightmare.png")):
            is_diffuse = True
        # PBR packed patterns
        elif ("_mnr" in fl or "_orm" in fl or "occlusionroughnessmetallic" in fl or
              "_metalandrough" in fl or "metallness" in fl):
            is_pbr = True
        # Emissive patterns
        elif ("_e.png" in fl or "emissive" in fl) and not fl.endswith("_basecolor.png") and not fl.endswith("_albedo.png"):
            is_emissive = True
        # Normal patterns
        elif "_n.png" in fl or "_normal" in fl:
            is_normal = True
        # Roughness patterns
        elif "_roughness" in fl:
            is_roughness = True
        # RGB texture that's likely a diffuse (e.g. T_Dragon9_skin1_Body_RGB.png)
        elif fl.endswith("_rgb.png"):
            is_diffuse = True
        else:
            continue  # Unknown type, skip

        if is_diffuse:
            if is_elite:
                diffuses.setdefault("elite", []).append((fname, fpath))
            elif is_nightmare:
                diffuses.setdefault("nightmare", []).append((fname, fpath))
            else:
                diffuses.setdefault("common", []).append((fname, fpath))
        elif is_pbr:
            pbr_files.append((fname, fpath))
        elif is_emissive:
            emissive_files.append((fname, fpath))
        elif is_normal:
            normal_files.append((fname, fpath))
        elif is_roughness:
            roughness_files.append((fname, fpath))

    # If no diffuses found with standard patterns, look more broadly
    if not diffuses:
        for fname, fpath in sorted(all_tex.items()):
            fl = fname.lower()
            # Any _D.png or _diffuse.png we might have missed
            if fl.endswith("_d.png") or "_diffuse" in fl:
                diffuses.setdefault("common", []).append((fname, fpath))

    if not diffuses:
        return {}

    # Build variant texture maps
    shared_pbr = pbr_files[0][1] if pbr_files else None
    shared_emissive = emissive_files[0][1] if emissive_files else None

    variants = {}
    for variant in ["common", "elite", "nightmare"]:
        diffs = diffuses.get(variant, diffuses.get("common", []))
        if not diffs:
            continue
        tex = {"diffuses": [d[1] for d in diffs]}
        if shared_pbr:
            tex["MNR"] = shared_pbr
        if shared_emissive:
            tex["E"] = shared_emissive
        variants[variant] = tex

    return variants

# ── Blender operations ───────────────────────────────────────────────────────

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=True)
    for block in list(bpy.data.meshes): bpy.data.meshes.remove(block)
    for block in list(bpy.data.armatures): bpy.data.armatures.remove(block)
    for block in list(bpy.data.actions): bpy.data.actions.remove(block)
    for block in list(bpy.data.materials): bpy.data.materials.remove(block)
    for block in list(bpy.data.images): bpy.data.images.remove(block)

def find_armature():
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None

def find_meshes():
    return [obj for obj in bpy.data.objects if obj.type == "MESH"]

def apply_textures(mesh_obj, variant_tex):
    """Apply PBR textures to all material slots of a mesh."""
    diffuses = variant_tex.get("diffuses", [])
    mnr_path = variant_tex.get("MNR")
    emissive_path = variant_tex.get("E")

    for slot_idx, mat_slot in enumerate(mesh_obj.material_slots):
        if mat_slot.material is None:
            continue

        mat = mat_slot.material
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (400, 0)
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        # Pick diffuse - try to match by material slot index, fall back to first
        diff_path = diffuses[slot_idx] if slot_idx < len(diffuses) else (diffuses[0] if diffuses else None)

        # Better matching: try to match diffuse filename to material name
        mat_name_lower = mat.name.lower()
        for d in diffuses:
            d_base = os.path.basename(d).lower().replace("_d.png", "").replace("_elite_d.png", "").replace("_nightmare_d.png", "")
            if d_base.replace("t_", "").replace("mi_", "") in mat_name_lower.replace("mi_", ""):
                diff_path = d
                break

        if diff_path and os.path.exists(diff_path):
            tex_node = nodes.new("ShaderNodeTexImage")
            tex_node.location = (-600, 300)
            tex_node.image = bpy.data.images.load(diff_path)
            tex_node.image.colorspace_settings.name = "sRGB"
            links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

        if mnr_path and os.path.exists(mnr_path):
            mnr_node = nodes.new("ShaderNodeTexImage")
            mnr_node.location = (-600, 0)
            mnr_node.image = bpy.data.images.load(mnr_path)
            mnr_node.image.colorspace_settings.name = "Non-Color"
            sep = nodes.new("ShaderNodeSeparateColor")
            sep.location = (-300, 0)
            links.new(mnr_node.outputs["Color"], sep.inputs["Color"])
            links.new(sep.outputs[0], bsdf.inputs["Metallic"])
            links.new(sep.outputs[2], bsdf.inputs["Roughness"])

        if emissive_path and os.path.exists(emissive_path):
            em_node = nodes.new("ShaderNodeTexImage")
            em_node.location = (-600, -300)
            em_node.image = bpy.data.images.load(emissive_path)
            em_node.image.colorspace_settings.name = "sRGB"
            links.new(em_node.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 1.0

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
        filepath=out_path, export_format="GLB", use_selection=True,
        export_animations=include_animations, export_skins=True,
        export_morph=False, export_lights=False, export_cameras=False,
        export_apply=False, export_image_format="AUTO", export_materials="EXPORT",
    )

def export_anim_glb(armature_obj, out_path):
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.export_scene.gltf(
        filepath=out_path, export_format="GLB", use_selection=True,
        export_animations=True, export_nla_strips=False,
        export_current_frame=False, export_skins=False,
        export_morph=False, export_lights=False, export_cameras=False,
        export_apply=False,
    )

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    if not args["name"] or not args["slug"]:
        print("ERROR: --name and --slug are required")
        print("Usage: blender --background --python blender_convert_standard.py -- --name CaveTroll --slug cave-troll")
        return

    name = args["name"]
    slug = args["slug"]
    monster_dir = os.path.join(FMODEL_ROOT, name)
    anim_out_dir = os.path.join(OUT_ROOT, "animations", slug)

    print(f"\n{'='*60}")
    print(f"  Standard Monster Converter: {name} ({slug})")
    print(f"{'='*60}")

    if not os.path.isdir(monster_dir):
        print(f"ERROR: Monster directory not found: {monster_dir}")
        return

    os.makedirs(anim_out_dir, exist_ok=True)

    # ── Find PSK ──────────────────────────────────────────────────────────
    psk_file = find_psk(monster_dir, args["psk"])
    if not psk_file:
        print(f"ERROR: No PSK file found in {monster_dir}")
        return
    print(f"\n  PSK: {psk_file}")

    # ── Find textures ─────────────────────────────────────────────────────
    variants = find_textures(name)
    print(f"  Texture variants: {list(variants.keys()) if variants else 'NONE'}")
    for v, tex in variants.items():
        print(f"    {v}: {len(tex.get('diffuses',[]))} diffuse, MNR={'yes' if tex.get('MNR') else 'no'}, E={'yes' if tex.get('E') else 'no'}")

    # ── Find PSAs ─────────────────────────────────────────────────────────
    psa_files = find_psa_files(monster_dir)
    # Filter to only Animations subdirectory
    anim_psa = [p for p in psa_files if "Animation" in p]
    if not anim_psa:
        anim_psa = psa_files  # Fallback to all
    print(f"  PSA files: {len(anim_psa)}")

    # ── Step 1: Import PSK ────────────────────────────────────────────────
    clear_scene()
    print(f"\n[1/4] Importing skeleton...")
    try:
        bpy.ops.psk.import_file(filepath=psk_file)
    except Exception as e:
        print(f"  ERROR importing PSK: {e}")
        return

    armature_obj = find_armature()
    if not armature_obj:
        print("  ERROR: No armature found!")
        return

    meshes = find_meshes()
    print(f"  Armature: '{armature_obj.name}' ({len(armature_obj.data.bones)} bones)")
    print(f"  Meshes: {len(meshes)}")
    for m in meshes:
        mat_names = [s.material.name if s.material else "None" for s in m.material_slots]
        print(f"    {m.name}: materials = {mat_names}")

    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # ── Step 2: Export textured models ────────────────────────────────────
    print(f"\n[2/4] Exporting textured model GLBs...")

    if variants:
        for variant, tex in variants.items():
            print(f"\n  Variant: {variant}")
            for mesh_obj in meshes:
                apply_textures(mesh_obj, tex)
            remove_all_actions(armature_obj)
            variant_path = os.path.join(anim_out_dir, f"{slug}-{variant}.glb")
            export_glb(variant_path)
            size_mb = os.path.getsize(variant_path) / 1024 / 1024
            print(f"  Exported: {variant_path} ({size_mb:.1f}MB)")

        # Base display model (Common textures)
        print(f"\n  Base display model...")
        common_tex = variants.get("common", list(variants.values())[0])
        for mesh_obj in meshes:
            apply_textures(mesh_obj, common_tex)
        remove_all_actions(armature_obj)
    else:
        print("  No textures found — exporting untextured model")
        remove_all_actions(armature_obj)

    base_path = os.path.join(OUT_ROOT, f"{slug}.glb")
    export_glb(base_path)
    size_mb = os.path.getsize(base_path) / 1024 / 1024
    print(f"  Base model: {base_path} ({size_mb:.1f}MB)")

    # Raw model
    raw_path = os.path.join(anim_out_dir, f"{slug}-raw.glb")
    export_glb(raw_path)

    # ── Step 3: Convert animations ────────────────────────────────────────
    print(f"\n[3/4] Converting {len(anim_psa)} animations...")

    manifest = {"monster": slug, "animations": []}
    converted = 0

    for psa_path in anim_psa:
        fname = os.path.basename(psa_path)
        anim_id = id_from_filename(fname)
        label = label_from_filename(fname)
        loop = should_loop(fname)

        print(f"    {fname} → {anim_id}.glb", end="")

        remove_all_actions(armature_obj)
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

        out_path = os.path.join(anim_out_dir, f"{anim_id}.glb")
        try:
            export_anim_glb(armature_obj, out_path)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        size_kb = os.path.getsize(out_path) // 1024
        print(f"  ({size_kb}KB) {'[loop]' if loop else ''}")

        manifest["animations"].append({
            "id": anim_id, "label": label,
            "file": f"{anim_id}.glb", "loop": loop,
        })
        converted += 1

    # ── Step 4: Write manifest ────────────────────────────────────────────
    print(f"\n[4/4] Writing manifest...")
    manifest_path = os.path.join(anim_out_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  DONE: {slug} — {converted}/{len(anim_psa)} animations, {len(variants)} variants")
    print(f"{'='*60}")


main()
