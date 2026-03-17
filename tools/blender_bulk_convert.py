"""
Blender headless BULK converter: all monsters' PSK + PSA files → per-animation GLB files.

Scans the FModel exports Monster directory, finds PSK meshes and PSA animations
for each monster, converts them to web-ready GLB files with manifests.

Run from command line:
  "C:\\Program Files\\Blender Foundation\\Blender 4.3\\blender.exe" ^
      --background --python tools/blender_bulk_convert.py -- [options]

Options (after --):
  --monster SLUG     Only process a specific monster (e.g. --monster Skeleton)
  --skip-existing    Skip monsters that already have a manifest.json
  --dry-run          List what would be converted without doing it
  --list             Just list all discovered monsters and exit

Requires the io_scene_psk_psa addon installed in Blender.
"""

import bpy
import os
import sys
import json
import re
import glob
import addon_utils

# ── Blender addon ────────────────────────────────────────────────────────────

addon_utils.enable("io_scene_psk_psa", default_set=True)
print(f"PSK/PSA addon loaded: {addon_utils.check('io_scene_psk_psa')}")

# ── Config ───────────────────────────────────────────────────────────────────

EXPORTS_ROOT = r"C:\Users\pawel\Desktop\Projects\Output\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster"

OUT_ROOT = r"C:\Users\pawel\Desktop\Projects\DnDMainProject\darkanddarker-wiki\website\public\monster-models"

# Animation name patterns that should loop
LOOP_PATTERNS = [
    r"idle",
    r"loop",
    r"swim(?!.*(?:start|end|spawn))",
    r"run(?!.*(?:start|stop|end))",
    r"walk(?!.*(?:start|stop|end))",
    r"fly(?!.*(?:start|stop|end|land))",
    r"hover",
    r"patrol",
    r"breath(?:e|ing)",
]

# Directories to skip (not actual monsters)
SKIP_DIRS = {"Common", "BP_DCMonsterAIController.json", "BP_DCMonsterBase.json", "EcosystemFish"}

# ── CLI Args ─────────────────────────────────────────────────────────────────

def parse_args():
    # Everything after "--" is our args
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {
        "monster": None,
        "skip_existing": False,
        "dry_run": False,
        "list_only": False,
    }
    i = 0
    while i < len(argv):
        if argv[i] == "--monster" and i + 1 < len(argv):
            args["monster"] = argv[i + 1]
            i += 2
        elif argv[i] == "--skip-existing":
            args["skip_existing"] = True
            i += 1
        elif argv[i] == "--dry-run":
            args["dry_run"] = True
            i += 1
        elif argv[i] == "--list":
            args["list_only"] = True
            i += 1
        else:
            i += 1
    return args

# ── Helpers ──────────────────────────────────────────────────────────────────

def slug_from_name(name):
    """Convert CamelCase monster dir name to kebab-case slug."""
    # Insert hyphens before capitals (but not for sequences like "AI")
    s = re.sub(r'(?<=[a-z])(?=[A-Z])', '-', name)
    s = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', '-', s)
    return s.lower().strip("-")


def should_loop(anim_name):
    """Guess whether an animation should loop based on its filename."""
    name_lower = anim_name.lower()
    for pattern in LOOP_PATTERNS:
        if re.search(pattern, name_lower):
            return True
    return False


def label_from_filename(filename):
    """Generate a human-readable label from a PSA filename.

    Simpler approach: strip prefix, convert underscores to spaces.
    e.g. "AM_Skeleton_Attack_Combo1.psa" → "Skeleton Attack Combo1"
         "AS_AncientStingray_idle_Combat.psa" → "AncientStingray Idle Combat"
    """
    name = os.path.splitext(filename)[0]
    # Strip AM_ or AS_ or SM_ prefix
    if name.startswith(("AM_", "AS_", "SM_")):
        name = name[3:]
    # Replace underscores with spaces
    label = name.replace("_", " ")
    # Insert spaces before capitals in CamelCase segments
    label = re.sub(r'([a-z])([A-Z])', r'\1 \2', label)
    # Clean up
    label = re.sub(r'\s+', ' ', label).strip()
    # Capitalize first letter of each word if all lowercase
    label = " ".join(w.capitalize() if w.islower() else w for w in label.split())
    return label or name


def id_from_filename(filename):
    """Generate a kebab-case id from a PSA filename.

    Uses a simpler approach: strip the AM_/AS_ prefix, convert the rest
    to kebab-case. This preserves the full name to avoid collisions
    (e.g. FrostSkeletonArcher_MeleeAttack1 stays distinct from
    FrostSkeletonFootman_MeleeAttack1).
    """
    name = os.path.splitext(filename)[0]
    # Strip AM_ or AS_ prefix
    if name.startswith(("AM_", "AS_", "SM_")):
        name = name[3:]
    # Replace underscores with hyphens, lowercase
    slug = re.sub(r'_+', '-', name).lower()
    # Clean up
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug or os.path.splitext(filename)[0].lower()


# ── Discovery ────────────────────────────────────────────────────────────────

def discover_monsters():
    """Scan the exports root and find all monsters with PSK + PSA files."""
    monsters = []

    for entry in sorted(os.listdir(EXPORTS_ROOT)):
        full = os.path.join(EXPORTS_ROOT, entry)
        if not os.path.isdir(full):
            continue
        if entry in SKIP_DIRS:
            continue
        if entry.endswith(".json"):
            continue

        # Recursively find PSK files (LOD0 preferred)
        psk_files = []
        for root, dirs, files in os.walk(full):
            for f in files:
                if f.endswith("_LOD0.psk") or f.endswith("_LOD0_LOD0.psk"):
                    psk_files.append(os.path.join(root, f))

        # Pick best PSK: prefer SK_ prefix (skeletal mesh), avoid SM_ (static mesh)
        # and avoid _Elite_, _Nightmare_ variants — use base mesh
        best_psk = None
        for psk in psk_files:
            name = os.path.basename(psk)
            if name.startswith("SM_"):
                continue  # static mesh, skip
            if "Invisible" in name:
                continue
            if best_psk is None:
                best_psk = psk
            elif "Elite" not in name and "Nightmare" not in name:
                # Prefer non-variant
                if "Elite" in os.path.basename(best_psk) or "Nightmare" in os.path.basename(best_psk):
                    best_psk = psk
                elif name.startswith("SK_") and not os.path.basename(best_psk).startswith("SK_"):
                    best_psk = psk

        if not best_psk:
            continue

        # Find all PSA files recursively
        psa_files = []
        for root, dirs, files in os.walk(full):
            for f in sorted(files):
                if f.endswith(".psa"):
                    psa_files.append(os.path.join(root, f))

        if not psa_files:
            continue

        slug = slug_from_name(entry)

        monsters.append({
            "name": entry,
            "slug": slug,
            "psk": best_psk,
            "psa_files": psa_files,
            "psa_count": len(psa_files),
        })

    return monsters


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


def find_armature():
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def import_skeleton(filepath):
    bpy.ops.psk.import_file(filepath=filepath)


def import_psa(armature_obj, filepath):
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    actions_before = set(bpy.data.actions.keys())
    try:
        bpy.ops.psa.import_file('EXEC_DEFAULT', filepath=filepath)
    except Exception as e:
        print(f"    ERROR importing PSA: {e}")
        return None
    new_actions = set(bpy.data.actions.keys()) - actions_before
    if not new_actions:
        return None
    action = bpy.data.actions[next(iter(new_actions))]
    if not armature_obj.animation_data:
        armature_obj.animation_data_create()
    armature_obj.animation_data.action = action
    return action


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


def export_model_glb(out_path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_skins=True,
        export_morph=False,
        export_lights=False,
        export_cameras=False,
        export_apply=False,
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


# ── Process one monster ──────────────────────────────────────────────────────

def process_monster(monster, dry_run=False):
    slug = monster["slug"]
    anim_out_dir = os.path.join(OUT_ROOT, "animations", slug)

    print(f"\n{'='*60}")
    print(f"  {monster['name']}  ({slug})")
    print(f"  PSK: {os.path.basename(monster['psk'])}")
    print(f"  PSA: {monster['psa_count']} animation files")
    print(f"  OUT: {anim_out_dir}")
    print(f"{'='*60}")

    if dry_run:
        for psa in monster["psa_files"]:
            fname = os.path.basename(psa)
            anim_id = id_from_filename(fname)
            label = label_from_filename(fname)
            loop = should_loop(fname)
            print(f"    {fname:50s} → {anim_id}.glb  [{label}]  {'LOOP' if loop else ''}")
        return 0

    os.makedirs(anim_out_dir, exist_ok=True)

    # 1. Clear and import skeleton
    clear_scene()
    print("  Importing skeleton...")

    try:
        import_skeleton(monster["psk"])
    except Exception as e:
        print(f"  ERROR importing PSK: {e}")
        return 0

    armature_obj = find_armature()
    if armature_obj is None:
        print("  ERROR: No armature found after PSK import, skipping.")
        return 0

    print(f"  Armature: '{armature_obj.name}' ({len(armature_obj.data.bones)} bones)")

    # Apply transforms
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 2. Export raw model GLB
    model_out = os.path.join(OUT_ROOT, "animations", f"{slug}-raw.glb")
    remove_all_actions(armature_obj)
    export_model_glb(model_out)
    size_mb = os.path.getsize(model_out) / 1024 / 1024
    print(f"  Model GLB: {size_mb:.1f}MB")

    # 3. Convert each PSA
    manifest = {"monster": slug, "animations": []}
    converted = 0

    for psa_path in monster["psa_files"]:
        fname = os.path.basename(psa_path)
        anim_id = id_from_filename(fname)
        label = label_from_filename(fname)
        loop = should_loop(fname)

        print(f"    {fname} → {anim_id}.glb", end="")

        remove_all_actions(armature_obj)
        action = import_psa(armature_obj, psa_path)

        if action is None:
            print("  SKIP (no action)")
            continue

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
            "id": anim_id,
            "label": label,
            "file": f"{anim_id}.glb",
            "loop": loop,
        })
        converted += 1

    # 4. Write manifest
    manifest_path = os.path.join(anim_out_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"  Done: {converted}/{monster['psa_count']} animations converted")
    return converted


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  Blender Bulk PSA → GLB Converter                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\nExports root: {EXPORTS_ROOT}")
    print(f"Output root:  {OUT_ROOT}\n")

    # Discover
    monsters = discover_monsters()
    print(f"Found {len(monsters)} monsters with PSK + PSA files")
    print(f"Total PSA files: {sum(m['psa_count'] for m in monsters)}")

    if args["list_only"]:
        print(f"\n{'Name':<30} {'Slug':<30} {'PSA':>5}")
        print("-" * 67)
        for m in monsters:
            print(f"{m['name']:<30} {m['slug']:<30} {m['psa_count']:>5}")
        return

    # Filter
    if args["monster"]:
        target = args["monster"].lower()
        monsters = [m for m in monsters if m["slug"] == target or m["name"].lower() == target]
        if not monsters:
            print(f"\nERROR: Monster '{args['monster']}' not found.")
            return

    if args["skip_existing"]:
        before = len(monsters)
        monsters = [m for m in monsters if not os.path.exists(
            os.path.join(OUT_ROOT, "animations", m["slug"], "manifest.json")
        )]
        print(f"Skipping {before - len(monsters)} monsters with existing manifests")

    print(f"\nProcessing {len(monsters)} monsters...")

    total_converted = 0
    total_failed = 0

    for i, monster in enumerate(monsters, 1):
        print(f"\n[{i}/{len(monsters)}]", end="")
        try:
            count = process_monster(monster, dry_run=args["dry_run"])
            total_converted += count
        except Exception as e:
            print(f"  FATAL ERROR processing {monster['name']}: {e}")
            total_failed += 1

    print(f"\n{'='*60}")
    print(f"COMPLETE: {total_converted} animations converted, {total_failed} monsters failed")
    print(f"{'='*60}")


main()
