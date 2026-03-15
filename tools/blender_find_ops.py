import bpy
import addon_utils
addon_utils.enable("io_scene_psk_psa", default_set=True)
print(f"Addon loaded: {addon_utils.check('io_scene_psk_psa')}")

print("\n=== PSK/PSA operators ===")
for mod_name in dir(bpy.ops):
    if any(x in mod_name.lower() for x in ['psk', 'psa', 'unreal', 'actorx']):
        mod = getattr(bpy.ops, mod_name)
        ops = [o for o in dir(mod) if not o.startswith('_')]
        print(f"  bpy.ops.{mod_name}: {ops}")

print("\n=== All import operators ===")
for op in dir(bpy.ops.import_scene):
    if not op.startswith('_'):
        print(f"  bpy.ops.import_scene.{op}")
