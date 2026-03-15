"""
Blender headless batch converter: PSK + PSA files → per-animation GLB files.

Run from command line:
  "C:\Program Files\Blender Foundation\Blender 4.x\blender.exe" ^
      --background --python tools/blender_convert_anims.py

Requires the io_scene_psk_psa addon installed in Blender.
"""

import bpy
import os
import json
import addon_utils

# Ensure the PSK/PSA extension is loaded in headless mode
addon_utils.enable("io_scene_psk_psa", default_set=True)
print(f"PSK/PSA addon loaded: {addon_utils.check('io_scene_psk_psa')}")

# ── Config ──────────────────────────────────────────────────────────────────

PSK_FILE = r"C:\Users\Administrator\Desktop\New folder (2)\Output\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster\AncientStingray\Meshes\SK_AncientStingray_LOD0.psk"

ANIM_DIR = r"C:\Users\Administrator\Desktop\New folder (2)\Output\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster\AncientStingray\Animations"

OUT_DIR = r"C:\Users\Administrator\Desktop\DnDMainProject\darkanddarker-wiki\website\public\monster-models\animations\ancient-stingray"

# [psa_filename, output_id, display_label, loops]
# Looping animations: idles, swims, rush loops, surge loops
ANIMATIONS = [
    # ── Idle / Stance ────────────────────────────────────────────────────────
    ("AS_AncientStingray_idle_Combat.psa",              "idle-combat",              "Combat Idle",              True),
    ("AS_AncientStingray_idle_peace.psa",               "idle-peace",               "Peace Idle",               True),
    ("AS_AncientStingray_idle_ADD.psa",                 "idle-add",                 "Idle (Additive)",          True),
    ("AS_AncientStingray_Pose.psa",                     "pose",                     "Pose",                     False),
    ("AS_AncientStingray_Tpose.psa",                    "tpose",                    "T-Pose",                   False),
    ("AS_AncientStingray_StanceChange_Combat.psa",      "stance-change-combat",     "Stance Change (Combat)",   False),
    ("AS_AncientStingray_EyeBlink.psa",                 "eye-blink",                "Eye Blink",                False),

    # ── Tail Attacks ─────────────────────────────────────────────────────────
    ("AS_AncientStingray_TailAttack_L.psa",             "tail-attack-l",            "Tail Attack L",            False),
    ("AS_AncientStingray_TailAttack_R.psa",             "tail-attack-r",            "Tail Attack R",            False),
    ("AS_AncientStingray_TailSlash_Down.psa",           "tail-slash-down",          "Tail Slash Down",          False),
    ("AS_AncientStingray_TailSlash_High.psa",           "tail-slash-high",          "Tail Slash High",          False),

    # ── Ranged / Projectiles ─────────────────────────────────────────────────
    ("AS_AncientStingray_WaterArrow_1.psa",             "water-arrow-1",            "Water Arrow 1",            False),
    ("AS_AncientStingray_WaterArrow_2.psa",             "water-arrow-2",            "Water Arrow 2",            False),
    ("AS_AncientStingray_Turning_WaterArrow1_L.psa",    "turning-water-arrow-1-l",  "Turning Water Arrow 1 L",  False),
    ("AS_AncientStingray_Turning_WaterArrow1_R.psa",    "turning-water-arrow-1-r",  "Turning Water Arrow 1 R",  False),
    ("AS_AncientStingray_Turning_WaterArrow2_L.psa",    "turning-water-arrow-2-l",  "Turning Water Arrow 2 L",  False),
    ("AS_AncientStingray_Turning_WaterArrow2_R.psa",    "turning-water-arrow-2-r",  "Turning Water Arrow 2 R",  False),

    # ── Rush ─────────────────────────────────────────────────────────────────
    ("AS_AncientStingray_Rush_Start.psa",               "rush-start",               "Rush Start",               False),
    ("AS_AncientStingray_Rush_Loop.psa",                "rush-loop",                "Rush Loop",                True),

    # ── Short Dash ───────────────────────────────────────────────────────────
    ("AS_AncientStingray_ShortDash.psa",                "short-dash",               "Short Dash",               False),

    # ── Special Abilities ────────────────────────────────────────────────────
    ("AS_AncientStingray_LightningBubble.psa",          "lightning-bubble",          "Lightning Bubble",         False),
    ("AS_AncientStingray_LightningBubble_Elite.psa",    "lightning-bubble-elite",    "Lightning Bubble (Elite)", False),
    ("AS_AncientStingray_LightningNova_Start.psa",      "lightning-nova-start",      "Lightning Nova Start",     False),
    ("AS_AncientStingray_LightningNova_Loop.psa",       "lightning-nova-loop",       "Lightning Nova Loop",      True),
    ("AS_AncientStingray_LightningNova_End.psa",        "lightning-nova-end",        "Lightning Nova End",       False),
    ("AS_AncientStingray_DivineJudgment.psa",           "divine-judgment",           "Divine Judgment",          False),

    # ── Turning ──────────────────────────────────────────────────────────────
    ("AS_AncientStingray_Turning_L.psa",                "turning-l",                "Turning L",                False),
    ("AS_AncientStingray_Turning_R.psa",                "turning-r",                "Turning R",                False),

    # ── Swimming ─────────────────────────────────────────────────────────────
    ("AS_AncientStingray_Swim_Start.psa",               "swim-start",               "Swim Start",               False),
    ("AS_AncientStingray_Swim_Front.psa",               "swim-front",               "Swim Front",               True),
    ("AS_AncientStingray_Swim_Glide.psa",               "swim-glide",               "Swim Glide",               True),
    ("AS_AncientStingray_Swim_Slow.psa",                "swim-slow",                "Swim Slow",                True),
    ("AS_AncientStingray_Swim_Idle.psa",                "swim-idle",                "Swim Idle",                True),
    ("AS_AncientStingray_Swim_End.psa",                 "swim-end",                 "Swim End",                 False),
    ("AS_AncientStingray_Swim_10m_L.psa",               "swim-10m-l",               "Swim 10m L",               False),
    ("AS_AncientStingray_Swim_10m_R.psa",               "swim-10m-r",               "Swim 10m R",               False),
    ("AS_AncientStingray_Swim_15m_L.psa",               "swim-15m-l",               "Swim 15m L",               False),
    ("AS_AncientStingray_Swim_15m_R.psa",               "swim-15m-r",               "Swim 15m R",               False),
    ("AS_AncientStingray_Swim_SpawnLocation_End.psa",   "swim-spawn-end",           "Swim Spawn End",           False),

    # ── Ambush Surge ─────────────────────────────────────────────────────────
    ("AS_AncientStingray_Ambush_Surge_start.psa",       "ambush-surge-start",       "Ambush Surge Start",       False),
    ("AS_AncientStingray_Ambush_Surge_Loop.psa",        "ambush-surge-loop",        "Ambush Surge Loop",        True),
    ("AS_AncientStingray_Ambush_Surge_End.psa",         "ambush-surge-end",         "Ambush Surge End",         False),

    # ── Hit / Death ──────────────────────────────────────────────────────────
    ("AS_AncientStingray_Hit.psa",                      "hit",                      "Hit",                      False),
    ("AS_AncientStingray_WillHit.psa",                  "will-hit",                 "Will Hit",                 False),
    ("AS_AncientStingray_Death.psa",                    "death",                    "Death",                    False),

    # ── Inplace (backstep) ───────────────────────────────────────────────────
    ("Inplace/AS_AncientStingray_BackSteb_Inplace.psa", "backstep-inplace",         "Backstep (Inplace)",       False),
]

# ── Helpers ──────────────────────────────────────────────────────────────────

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
    """Import the PSK — creates a proper armature with all bones."""
    bpy.ops.psk.import_file(filepath=filepath)

def import_psa(armature_obj, filepath):
    """Import a PSA animation onto the active armature. Returns the new action or None."""
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj

    actions_before = set(bpy.data.actions.keys())
    bpy.ops.psa.import_file('EXEC_DEFAULT', filepath=filepath)
    new_actions = set(bpy.data.actions.keys()) - actions_before

    if not new_actions:
        return None

    action = bpy.data.actions[next(iter(new_actions))]
    print(f"    New action: '{action.name}'  frames: {int(action.frame_range[0])}–{int(action.frame_range[1])}")

    # Assign to armature so the GLB exporter sees it
    if not armature_obj.animation_data:
        armature_obj.animation_data_create()
    armature_obj.animation_data.action = action
    return action

def remove_all_actions(armature_obj):
    """Strip all actions so the next import starts clean."""
    if armature_obj.animation_data:
        armature_obj.animation_data.action = None
        if hasattr(armature_obj.animation_data, 'nla_tracks'):
            for track in list(armature_obj.animation_data.nla_tracks):
                armature_obj.animation_data.nla_tracks.remove(track)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action, do_unlink=True)

def strip_root_motion(action):
    """Remove root bone location fcurves so animations play in-place.

    PSA animations carry world-space locomotion on the 'root' bone (e.g. 978 cm
    forward for Rush). Stripping the location channels keeps the body animation
    while preventing the model from flying off-screen in the web viewer.
    """
    removed = 0
    for fc in list(action.fcurves):
        # Bone fcurves have data_path like 'pose.bones["root"].location'
        if fc.data_path == 'pose.bones["root"].location':
            action.fcurves.remove(fc)
            removed += 1
    if removed:
        print(f"    Stripped {removed} root-motion fcurves (location XYZ)")

def export_model_glb(out_path):
    """Export the full model (mesh + armature, no animations) as a GLB."""
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

def export_glb(armature_obj, out_path):
    """Export the armature (+ current action) as a GLB animation file."""
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj

    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_nla_strips=False,          # only the active action
        export_current_frame=False,
        export_skins=False,               # no mesh/skin needed, just bones
        export_morph=False,
        export_lights=False,
        export_cameras=False,
        export_apply=False,
    )

# ── Main ────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("\n=== Blender PSA → GLB converter ===")
    print(f"PSK:  {PSK_FILE}")
    print(f"ANIM: {ANIM_DIR}")
    print(f"OUT:  {OUT_DIR}\n")

    # 1. Start clean
    clear_scene()

    # 2. Import the PSK skeleton
    if not os.path.exists(PSK_FILE):
        print(f"ERROR: PSK file not found: {PSK_FILE}")
        return

    print("Importing PSK skeleton...")
    import_skeleton(PSK_FILE)

    # Print everything in scene to help debug
    print("Scene objects after PSK import:")
    for obj in bpy.data.objects:
        extra = f"({len(obj.data.bones)} bones)" if obj.type == "ARMATURE" else ""
        print(f"  {obj.type:10}  {obj.name}  {extra}")

    armature_obj = find_armature()
    if armature_obj is None:
        print("ERROR: No armature found after PSK import.")
        return
    print(f"  Armature: '{armature_obj.name}' ({len(armature_obj.data.bones)} bones)")

    # Apply the armature's object-level rotation so bone rest poses
    # match the model GLB's coordinate system (Y-up, meters).
    # Without this, the animation GLBs keep a -90° X rotation on the root
    # bone that flips the model when played in the web viewer.
    print(f"  Armature rotation BEFORE apply: {list(armature_obj.rotation_euler)}")
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    print(f"  Armature rotation AFTER apply:  {list(armature_obj.rotation_euler)}")

    # 2b. Export model GLB (mesh + armature, same coordinate system as animations)
    model_out = os.path.join(os.path.dirname(OUT_DIR), "ancient-stingray-raw.glb")
    remove_all_actions(armature_obj)
    export_model_glb(model_out)
    size_mb = os.path.getsize(model_out) / 1024 / 1024
    print(f"  Model GLB: {model_out}  ({size_mb:.1f}MB)")

    manifest = {"monster": "ancient-stingray", "animations": []}
    converted = 0

    # 3. Convert each PSA
    for psa_file, anim_id, label, loop in ANIMATIONS:
        psa_path = os.path.join(ANIM_DIR, psa_file)

        if not os.path.exists(psa_path):
            print(f"  SKIP  {psa_file}  (not found)")
            continue

        print(f"  Converting  {psa_file}  →  {anim_id}.glb")

        # Clean previous action
        remove_all_actions(armature_obj)

        # Import animation
        action = import_psa(armature_obj, psa_path)

        if action is None:
            print(f"    WARNING: no action created for {psa_file}, skipping")
            continue

        # Export GLB
        out_path = os.path.join(OUT_DIR, f"{anim_id}.glb")
        export_glb(armature_obj, out_path)

        size_kb = os.path.getsize(out_path) // 1024
        print(f"    Wrote {out_path}  ({size_kb}KB)")

        manifest["animations"].append({
            "id": anim_id,
            "label": label,
            "file": f"{anim_id}.glb",
            "loop": loop,
        })
        converted += 1

    # 4. Write manifest
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone. {converted}/{len(ANIMATIONS)} animations converted.")
    print(f"Manifest: {manifest_path}")


main()
