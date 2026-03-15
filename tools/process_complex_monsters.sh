#!/bin/bash
# Process all complex monsters by mapping each sub-monster to the correct PSK + PSA + slug
BLENDER="/c/Program Files/Blender Foundation/Blender 4.5/blender.exe"
SCRIPT="C:/Users/Administrator/Desktop/DnDMainProject/darkanddarker-wiki/tools/blender_convert_standard.py"
LOGDIR="/tmp/blender_complex"
mkdir -p "$LOGDIR"

run() {
  local name="$1" slug="$2" psk="$3"
  echo "Processing: $name → $slug"
  if [ -n "$psk" ]; then
    "$BLENDER" --background --python "$SCRIPT" -- --name "$name" --slug "$slug" --psk "$psk" > "$LOGDIR/${slug}.log" 2>&1 &
  else
    "$BLENDER" --background --python "$SCRIPT" -- --name "$name" --slug "$slug" > "$LOGDIR/${slug}.log" 2>&1 &
  fi
}

# === SKELETON FAMILY (17 sub-monsters) ===
# Each has its own subdir under Skeleton/ with PSK + PSA
run "Skeleton/SkeletonArcher" "skeleton-archer" "SK_Skeleton_Archer_LOD0.psk"
run "Skeleton/SkeletonAxeman" "skeleton-axeman" "SK_SkeletonAxeman_LOD0.psk"
run "Skeleton/SkeletonChampion" "skeleton-champion" "SK_Skeleton_Champion_LOD0.psk"
run "Skeleton/SkeletonCrossbowman" "skeleton-crossbowman" "SK_Skeleton_Crossbowman_LOD0.psk"
run "Skeleton/SkeletonFootman" "skeleton-footman" "SK_SkeletonFootman_LOD0.psk"
run "Skeleton/SkeletonGuardman" "skeleton-guardman" "SK_SkeletonGuardman_LOD0.psk"
run "Skeleton/SkeletonMage" "skeleton-mage" "SK_SkeletonMage_LOD0.psk"
run "Skeleton/SkeletonRoyalGuard" "skeleton-royal-guard" "SK_SkeletonRoyalGuard_LOD0.psk"
run "Skeleton/SkeletonSpearman" "skeleton-spearman" "SK_Skeletonspearman_LOD0.psk"
run "Skeleton/SkeletonSwordman" "skeleton-swordman" "SK_Skeletonswordman_LOD0.psk"
run "Skeleton/SkeletonWarlord" "skeleton-warlord" "SK_Skeleton_Warlord_LOD0.psk"
run "Skeleton/FrostSkeletonArcher" "frost-skeleton-archer" "SK_FrostSkeleton_Archer_LOD0.psk"
run "Skeleton/FrostSkeletonAxeman" "frost-skeleton-axeman" "SK_FrostSkeletonAxeman_LOD0.psk"
run "Skeleton/FrostSkeletonCrossbowman" "frost-skeleton-crossbowman" "SK_FrostSkeletonCrossbowman_LOD0.psk"
run "Skeleton/FrostSkeletonFootman" "frost-skeleton-footman" "SK_FrostSkeletonFootman_LOD0.psk"
run "Skeleton/FrostSkeletonGuardman" "frost-skeleton-guardman" "SK_FrostSkeletonGuardman_LOD0.psk"
run "Skeleton/FrostSkeletonHalberdier" "frost-skeleton-halberdier" "SK_FrostSkeletonHalberdier_LOD0.psk"
run "Skeleton/FrostSkeletonMaceman" "frost-skeleton-maceman" "SK_FrostSkeletonMaceman_LOD0.psk"

wait
echo "=== Skeleton family done ==="

# === GOBLIN FAMILY (6 sub-monsters) ===
run "Goblin/GoblinArcher" "goblin-archer" "SK_GoblinArcher_LOD0.psk"
run "Goblin/GoblinAxeman" "goblin-axeman" "SK_GoblinAxeman_LOD0.psk"
run "Goblin/GoblinBolaslinger" "goblin-bolaslinger" "SK_GoblinBolaslinger_LOD0.psk"
run "Goblin/GoblinMage" "goblin-mage" "SK_Base_Mesh_LOD0.psk"
run "Goblin/GoblinWarrior" "goblin-warrior" "SK_Goblin_rig_LOD0.psk"
run "Goblin/LootGoblin" "loot-goblin" "SK_LootGoblin_LOD0.psk"

wait
echo "=== Goblin family done ==="

# === DWARF FAMILY (4 sub-monsters) ===
run "Dwarf/DwarfAxeman" "dwarf-axeman" "SK_DwarfAxeman_LOD0.psk"
run "Dwarf/DwarfHandcannoneer" "dwarf-handcannoneer" "SK_DwarfHandcannoneer_LOD0.psk"
run "Dwarf/DwarfKnight" "dwarf-knight" "SK_DwarfKnight_LOD0.psk"
run "Dwarf/DwarfMauler" "dwarf-mauler" "SK_DwarfMauler_LOD0.psk"

# === PIRATE FAMILY (5 sub-monsters) ===
run "Pirate/PirateAxeThrower" "pirate-axe-thrower"
run "Pirate/PirateBowman" "pirate-bowman"
run "Pirate/PirateCrossbowman" "pirate-crossbowman"
run "Pirate/PirateSwiftBlade" "pirate-swiftblade"
run "Pirate/PirateSwordman" "pirate-swordman"

wait
echo "=== Dwarf + Pirate families done ==="

# === TIDEWALKER FAMILY (5 sub-monsters + Reefling) ===
run "Tidewalker/TidewalkerClubFighter" "tidewalker-clubfighter" "SK_TidewalkerClubFighter_LOD0.psk"
run "Tidewalker/TidewalkerShaman" "tidewalker-shaman" "SK_TidewalkerShaman_LOD0.psk"
run "Tidewalker/TidewalkerSlinger" "tidewalker-slinger" "SK_TidewalkerSlinger_LOD0.psk"
run "Tidewalker/TidewalkerSpearer" "tidewalker-spearer" "SK_TidewalkerSpearer_LOD0.psk"
run "Tidewalker/Reefling" "reefling" "SK_Reefling_LOD0.psk"

# === DEMON FAMILY (3 sub-monsters) ===
run "Demon/DemonBerserker" "demon-berserker" "SK_Demon2_LOD0.psk"
run "Demon/DemonImp" "demon-imp" "SK_Imp_LOD0.psk"
run "Demon/FrostDemon" "frost-demon" "SK_FrostDemon_01_LOD0.psk"

wait
echo "=== Tidewalker + Demon families done ==="

# === WOLF FAMILY (2 sub-monsters — share Common/ animations) ===
run "Wolf/DireWolf" "dire-wolf" "Wolf_Realistic_SK_LOD0.psk"
run "Wolf/FrostWolf" "frost-wolf" "SK_FrostWolf_LOD0.psk"

# === ZOMBIE FAMILY (3 sub-monsters) ===
run "Zombie/Zombie" "zombie" "SK_Zombie_1_LOD0.psk"
run "Zombie/FrostWalker" "frost-walker" "SK_FrostWalker_LOD0.psk"
run "Zombie/SeaWalker" "sea-walker" "SK_Seawalker_LOD0.psk"

# === FROST GIANT (2 sub-monsters — use Common/ mesh for Shielder) ===
run "FrostGiant/FrostGiantBerserker" "frost-giant-berserker"
run "FrostGiant/FrostGiantShielder" "frost-giant-shielder"

wait
echo "=== Wolf + Zombie + FrostGiant families done ==="

# === SINGLE MONSTERS (use main body PSK, skip accessory parts) ===
run "Banshee" "banshee-boss" "SK_Banshee_LOD0.psk"
run "Wraith" "wraith" "SK_Wraith_LOD0.psk"
run "Dreadspine" "dreadspine" "SK_Dreadspine_LOD0.psk"
run "Cyclops" "cyclops" "SK_Cyclops_LOD0.psk"
run "DeathBeetle" "death-beetle" "SK_FlyingBug12_LOD0.psk"

# === MIMIC (use one representative mesh — MidLevel Large as default) ===
run "Mimic" "mimic-large-mid-level" "SK_MimicMidLevelLarge_LOD0.psk"
run "Mimic" "mimic-large-simple" "SK_MimicSimpleLarge_LOD0.psk"
run "Mimic" "mimic-large-ornate" "SK_MimicOrnateLarge_LOD0.psk"
run "Mimic" "mimic-medium-mid-level" "SK_MimicMidLevelMedium_LOD0.psk"
run "Mimic" "mimic-medium-simple" "SK_MimicSimpleMedium_LOD0.psk"
run "Mimic" "mimic-medium-ornate" "SK_MimicOrnateMedium_LOD0.psk"
run "Mimic" "mimic-small-mid-level" "SK_MimicMidLevelSmall_LOD0.psk"

wait
echo "=== Single monsters + Mimics done ==="

# === FROST IMP (inside Demon/FrostDemon but separate monster) ===
# FrostImp doesn't have its own PSK — it likely shares with DemonImp
# Skip for now

echo ""
echo "ALL COMPLEX MONSTERS PROCESSED"
