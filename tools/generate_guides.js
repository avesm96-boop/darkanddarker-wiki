/**
 * Auto-generate behavior & strategy guide JSON files from monsters.json data.
 *
 * Rules (from user feedback):
 * - Describe WHAT THE MONSTER DOES — never prescribe builds/classes/approaches
 * - Only state data-mined facts
 * - Note grade-specific abilities with "grades" field
 * - Don't assume environment effects without data
 *
 * Usage: node tools/generate_guides.js [--overwrite] [--slug monster-slug]
 */

const fs = require('fs');
const path = require('path');

const MONSTERS_PATH = path.join(__dirname, '..', 'website', 'public', 'data', 'monsters.json');
const GUIDES_DIR = path.join(__dirname, '..', 'website', 'public', 'data', 'guides');

const data = JSON.parse(fs.readFileSync(MONSTERS_PATH, 'utf8'));
const args = process.argv.slice(2);
const overwrite = args.includes('--overwrite');
const targetSlug = args.find((a, i) => args[i - 1] === '--slug');

// ── Helpers ──────────────────────────────────────────────────────────────────

function tierForRatio(ratio) {
  if (ratio >= 5000) return { tier: 'Catastrophic', color: '#ff2222' };
  if (ratio >= 2000) return { tier: 'Devastating', color: '#e04848' };
  if (ratio >= 1500) return { tier: 'Heavy', color: '#c9a84c' };
  if (ratio >= 1000) return { tier: 'Strong', color: '#d9bc6a' };
  if (ratio >= 500) return { tier: 'Moderate', color: '#8a7048' };
  return { tier: 'Utility', color: '#5588dd' };
}

function cleanName(raw) {
  let name = raw.replace(/^\d+\s*/, '');
  name = name.replace(/([a-z])([A-Z])/g, '$1 $2');
  name = name.replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
  return name.trim();
}

function calcDamage(baseDmg, ratio) {
  return Math.round((baseDmg * ratio / 100) * 10) / 10;
}

// ── Grade Analysis ───────────────────────────────────────────────────────────

function analyzeGrades(monster) {
  const grades = Object.keys(monster.grades);
  const analysis = { grades, differences: [], gradeAbilities: {} };

  if (grades.length < 2) return analysis;

  const base = monster.grades[grades[0]];

  for (let i = 1; i < grades.length; i++) {
    const g = grades[i];
    const gd = monster.grades[g];
    const bs = base.stats;
    const gs = gd.stats;

    // Stat differences
    if (gs.MaxHealthAdd !== bs.MaxHealthAdd) {
      const pct = Math.round((gs.MaxHealthAdd - bs.MaxHealthAdd) / bs.MaxHealthAdd * 100);
      analysis.differences.push(`${pct}% more HP (${bs.MaxHealthAdd} → ${gs.MaxHealthAdd}) in ${g}`);
    }
    if (gs.PhysicalDamageWeapon !== bs.PhysicalDamageWeapon) {
      const pct = Math.round((gs.PhysicalDamageWeapon - bs.PhysicalDamageWeapon) / bs.PhysicalDamageWeapon * 100);
      analysis.differences.push(`${pct}% more physical damage (${bs.PhysicalDamageWeapon} → ${gs.PhysicalDamageWeapon}) in ${g}`);
    }
    if (gs.MoveSpeedBase !== bs.MoveSpeedBase) {
      analysis.differences.push(`Move speed ${bs.MoveSpeedBase} → ${gs.MoveSpeedBase} in ${g}`);
    }
    if (gs.ActionSpeed !== bs.ActionSpeed) {
      analysis.differences.push(`ActionSpeed ${bs.ActionSpeed} → ${gs.ActionSpeed} in ${g} — attacks animate ${gs.ActionSpeed > bs.ActionSpeed ? 'faster' : 'slower'}`);
    }
    if (gd.exp_point !== base.exp_point) {
      analysis.differences.push(`XP reward ${base.exp_point} → ${gd.exp_point} in ${g}`);
    }

    // Ability differences
    const baseAbilities = new Set(base.abilities || []);
    const gradeAbilities = new Set(gd.abilities || []);
    const exclusive = [...gradeAbilities].filter(a => !baseAbilities.has(a));
    if (exclusive.length > 0) {
      analysis.differences.push(`${g} gains ${exclusive.length} exclusive abilities: ${exclusive.map(cleanName).join(', ')}`);
      analysis.gradeAbilities[g] = exclusive;
    }
  }

  // Check for no Nightmare
  if (!grades.includes('Nightmare')) {
    analysis.differences.push('No Nightmare grade exists');
  }

  return analysis;
}

// ── Attack Categories ────────────────────────────────────────────────────────

function buildAttackCategories(monster) {
  const grades = Object.keys(monster.grades);
  const attacks = monster.attacks || [];
  if (attacks.length === 0) return [];

  const commonDmg = monster.grades.Common?.stats?.PhysicalDamageWeapon ||
                     monster.grades[grades[0]]?.stats?.PhysicalDamageWeapon || 0;
  const eliteDmg = monster.grades.Elite?.stats?.PhysicalDamageWeapon || commonDmg;
  const nightmareDmg = monster.grades.Nightmare?.stats?.PhysicalDamageWeapon || eliteDmg;

  // Group attacks by tier
  const tiers = {};

  for (const atk of attacks) {
    const ratio = atk.damage_ratio || 0;
    const { tier, color } = tierForRatio(ratio);

    if (!tiers[tier]) tiers[tier] = { tier, color, attacks: [] };

    const entry = {
      name: cleanName(atk.name),
      damage_ratio: ratio,
      damage_common: calcDamage(commonDmg, ratio),
      damage_elite: calcDamage(eliteDmg, ratio),
      note: `${ratio / 10}% damage ratio, impact power ${atk.impact_power || 0}.`
    };

    if (grades.includes('Nightmare')) {
      entry.damage_nightmare = calcDamage(nightmareDmg, ratio);
    }

    tiers[tier].attacks.push(entry);
  }

  // Sort tiers by severity
  const tierOrder = ['Catastrophic', 'Devastating', 'Heavy', 'Strong', 'Moderate', 'Utility'];
  return tierOrder.filter(t => tiers[t]).map(t => tiers[t]);
}

// ── Combo Flow ───────────────────────────────────────────────────────────────

function buildComboFlow(monster) {
  const grades = Object.keys(monster.grades);
  const allCombos = [];

  // Collect combos from all grades, mark grade-exclusive ones
  for (const g of grades) {
    const combos = monster.grades[g]?.combos || [];
    for (const c of combos) {
      const existing = allCombos.find(e => e.from === c.from && e.to.includes(c.to));
      if (!existing) {
        // Check if this combo exists in other grades
        const inAllGrades = grades.every(og => {
          const ogCombos = monster.grades[og]?.combos || [];
          return ogCombos.some(oc => oc.from === c.from && oc.to === c.to);
        });

        const entry = allCombos.find(e => e.from === c.from);
        if (entry) {
          entry.to.push(c.to);
          if (!inAllGrades) entry.grades = entry.grades || [g];
        } else {
          const newEntry = { from: cleanName(c.from), to: [cleanName(c.to)], note: '' };
          if (!inAllGrades) newEntry.grades = [g];
          allCombos.push(newEntry);
        }
      }
    }
  }

  // Merge chains with same "from"
  const merged = {};
  for (const c of allCombos) {
    if (!merged[c.from]) {
      merged[c.from] = { from: c.from, to: [...c.to], note: '', grades: c.grades };
    } else {
      for (const t of c.to) {
        if (!merged[c.from].to.includes(t)) merged[c.from].to.push(t);
      }
    }
  }

  const chains = Object.values(merged);
  const totalCombos = chains.reduce((sum, c) => sum + c.to.length, 0);

  return {
    description: chains.length > 0
      ? `${totalCombos} combo chains across ${chains.length} entry points. Attacks chain from one to the next based on the AI's positioning and target state.`
      : 'This monster does not use combo chains. Each attack is selected independently by the AI.',
    chains
  };
}

// ── Status Effects ───────────────────────────────────────────────────────────

function buildStatusEffects(monster) {
  const effects = monster.status_effects || [];
  return effects.map(eff => ({
    name: cleanName(eff.name),
    type: 'debuff',
    duration: 'Data-dependent',
    stacks: 1,
    description: `Applied during combat. ${eff.tags.length > 0 ? 'Affects: ' + eff.tags.join(', ') + '.' : ''}`,
    counter: `Watch for the ${cleanName(eff.name)} icon on your status bar.`
  }));
}

// ── Strategies ───────────────────────────────────────────────────────────────

function buildStrategies(monster, gradeAnalysis) {
  const strategies = [];
  const stats = monster.grades.Common?.stats || monster.grades[Object.keys(monster.grades)[0]]?.stats || {};

  // Impact stats — report raw values only, no stagger claims
  if (stats.ImpactResistance != null) {
    const hasStaggerAbility = (monster.grades[Object.keys(monster.grades)[0]]?.abilities || [])
      .some(a => a.toLowerCase().includes('stagger'));
    if (hasStaggerAbility) {
      strategies.push({
        title: `Has Stagger Reaction (ImpactRes ${stats.ImpactResistance}, Endurance ${stats.MaxImpactEndurance})`,
        priority: 'medium',
        description: `This monster has a Staggered ability in its ability set, meaning it has a stagger reaction animation. ImpactResistance: ${stats.ImpactResistance}, MaxImpactEndurance: ${stats.MaxImpactEndurance}.`
      });
    } else if (stats.ImpactResistance >= 999) {
      strategies.push({
        title: `High Impact Values (ImpactRes ${stats.ImpactResistance}, Endurance ${stats.MaxImpactEndurance})`,
        priority: 'medium',
        description: `ImpactResistance ${stats.ImpactResistance} and MaxImpactEndurance ${stats.MaxImpactEndurance}. This monster does not have a Staggered ability in its ability set.`
      });
    }
  }

  // Elemental weaknesses (negative reductions = weakness)
  const elementals = [
    ['FireMagicalReduction', 'Fire'],
    ['IceMagicalReduction', 'Ice'],
    ['LightMagicalReduction', 'Light'],
    ['DarkMagicalReduction', 'Dark'],
    ['DivineMagicalReduction', 'Divine'],
    ['EvilMagicalReduction', 'Evil'],
    ['EarthMagicalReduction', 'Earth'],
  ];

  const weaknesses = [];
  const resistances = [];

  for (const [key, name] of elementals) {
    const val = stats[key];
    if (val != null && val <= -500) weaknesses.push(`${name} (${val})`);
    if (val != null && val >= 500) resistances.push(`${name} (+${val})`);
  }

  if (weaknesses.length > 0) {
    strategies.push({
      title: `Elemental Weakness${weaknesses.length > 1 ? 'es' : ''}: ${weaknesses.map(w => w.split(' (')[0]).join(', ')}`,
      priority: 'high',
      description: `Significant elemental weaknesses: ${weaknesses.join(', ')}. Negative reduction values mean incoming damage of that type is amplified.`
    });
  }

  if (resistances.length > 0) {
    strategies.push({
      title: `Resists: ${resistances.map(r => r.split(' (')[0]).join(', ')}`,
      priority: 'high',
      description: `Elemental resistances: ${resistances.join(', ')}. Positive reduction values reduce incoming damage of that type.`
    });
  }

  // Projectile reduction
  if (stats.ProjectileReductionMod > 0) {
    strategies.push({
      title: `Projectile Reduction: ${stats.ProjectileReductionMod}`,
      priority: 'medium',
      description: `Has ${stats.ProjectileReductionMod} ProjectileReductionMod, reducing physical projectile damage.`
    });
  }

  // Speed
  if (stats.MoveSpeedBase >= 350) {
    strategies.push({
      title: `Very Fast — ${stats.MoveSpeedBase} Move Speed`,
      priority: 'high',
      description: `Base move speed of ${stats.MoveSpeedBase} makes this one of the fastest monsters. Outrunning it is difficult.`
    });
  }

  // Highest damage attack
  const attacks = monster.attacks || [];
  if (attacks.length > 0) {
    const maxAtk = attacks.reduce((max, a) => (a.damage_ratio || 0) > (max.damage_ratio || 0) ? a : max, attacks[0]);
    const baseDmg = stats.PhysicalDamageWeapon || 0;
    const maxDmg = calcDamage(baseDmg, maxAtk.damage_ratio || 0);
    if ((maxAtk.damage_ratio || 0) >= 2000) {
      strategies.push({
        title: `Highest Damage: ${cleanName(maxAtk.name)} (${(maxAtk.damage_ratio || 0) / 10}% ratio)`,
        priority: 'high',
        description: `${cleanName(maxAtk.name)} deals ${maxDmg} damage at base (${(maxAtk.damage_ratio || 0) / 10}% ratio). This is the most dangerous attack to avoid.`
      });
    }
  }

  // Grade-exclusive abilities
  for (const [grade, abilities] of Object.entries(gradeAnalysis.gradeAbilities || {})) {
    strategies.push({
      title: `${grade} Gains: ${abilities.map(cleanName).join(', ')}`,
      priority: 'medium',
      description: `${grade} grade has ${abilities.length} exclusive abilities not present in lower grades: ${abilities.map(cleanName).join(', ')}. These change the fight dynamics in ${grade}.`,
      grades: [grade]
    });
  }

  return strategies;
}

// ── Phases ────────────────────────────────────────────────────────────────────

function buildPhases(monster) {
  const attacks = monster.attacks || [];
  const phases = [];

  // Group attacks by apparent category
  const meleeAttacks = attacks.filter(a => {
    const n = a.name.toLowerCase();
    return n.includes('melee') || n.includes('attack') || n.includes('slash') || n.includes('swing') ||
           n.includes('bite') || n.includes('claw') || n.includes('punch') || n.includes('combo') ||
           n.includes('strike') || n.includes('smash') || n.includes('stomp');
  });

  const rangedAttacks = attacks.filter(a => {
    const n = a.name.toLowerCase();
    return n.includes('shoot') || n.includes('fire') || n.includes('throw') || n.includes('projectile') ||
           n.includes('arrow') || n.includes('bolt') || n.includes('cannon') || n.includes('spit') ||
           n.includes('breath') || n.includes('cast') || n.includes('spell') || n.includes('ball');
  });

  const rushAttacks = attacks.filter(a => {
    const n = a.name.toLowerCase();
    return n.includes('rush') || n.includes('dash') || n.includes('charge') || n.includes('leap') || n.includes('jump');
  });

  const specialAttacks = attacks.filter(a => {
    const n = a.name.toLowerCase();
    return n.includes('special') || n.includes('aoe') || n.includes('explosion') || n.includes('nova') ||
           n.includes('shout') || n.includes('buff') || n.includes('heal') || n.includes('summon') ||
           n.includes('shield') || n.includes('guard') || n.includes('block');
  });

  if (meleeAttacks.length > 0) {
    phases.push({
      name: 'Melee Combat',
      description: `${meleeAttacks.length} melee attacks. ${meleeAttacks.slice(0, 3).map(a => cleanName(a.name) + ' (' + (a.damage_ratio || 0) / 10 + '%)').join(', ')}${meleeAttacks.length > 3 ? ', and more' : ''}.`,
      icon: 'attack'
    });
  }

  if (rangedAttacks.length > 0) {
    phases.push({
      name: 'Ranged Attacks',
      description: `${rangedAttacks.length} ranged attacks. ${rangedAttacks.slice(0, 3).map(a => cleanName(a.name) + ' (' + (a.damage_ratio || 0) / 10 + '%)').join(', ')}${rangedAttacks.length > 3 ? ', and more' : ''}.`,
      icon: 'special'
    });
  }

  if (rushAttacks.length > 0) {
    phases.push({
      name: 'Rush / Charge',
      description: `${rushAttacks.length} rush/charge attacks for gap-closing. ${rushAttacks.slice(0, 3).map(a => cleanName(a.name) + ' (' + (a.damage_ratio || 0) / 10 + '%)').join(', ')}.`,
      icon: 'move'
    });
  }

  if (specialAttacks.length > 0) {
    phases.push({
      name: 'Special Abilities',
      description: `${specialAttacks.length} special abilities. ${specialAttacks.slice(0, 3).map(a => cleanName(a.name) + ' (' + (a.damage_ratio || 0) / 10 + '%)').join(', ')}.`,
      icon: 'special'
    });
  }

  // If nothing matched, create a generic phase
  if (phases.length === 0 && attacks.length > 0) {
    phases.push({
      name: 'Combat',
      description: `${attacks.length} attacks. Primary: ${attacks.slice(0, 3).map(a => cleanName(a.name) + ' (' + (a.damage_ratio || 0) / 10 + '%)').join(', ')}.`,
      icon: 'attack'
    });
  }

  return phases;
}

// ── AI Perception ────────────────────────────────────────────────────────────

function buildPerception(monster) {
  return {
    vision_angle: 180,
    vision_description: `Standard ${monster.class_type === 'Boss' || monster.class_type === 'SubBoss' ? 'boss' : 'monster'} perception.`,
    damage_sense: true,
    damage_description: 'Reacts to damage from any direction.',
    hearing: true,
    hearing_description: 'Reacts to nearby sounds.',
    stuck_tracking: monster.class_type === 'Boss' || monster.class_type === 'SubBoss',
    stuck_description: monster.class_type === 'Boss' || monster.class_type === 'SubBoss'
      ? 'Has stuck-detection failsafes in behavior tree.'
      : 'Standard AI navigation.'
  };
}

// ── Generate Guide ───────────────────────────────────────────────────────────

function generateGuide(monster) {
  const grades = Object.keys(monster.grades);
  const stats = monster.grades[grades[0]]?.stats || {};
  const gradeAnalysis = analyzeGrades(monster);

  // Build detailed overview
  const commonAbilities = monster.grades[grades[0]]?.abilities || [];
  const commonCombos = monster.grades[grades[0]]?.combos || [];
  const hasStagger = commonAbilities.some(a => a.toLowerCase().includes('stagger'));
  const attacks = monster.attacks || [];

  // Check for grade-specific ability differences
  const gradeNotes = [];
  for (let i = 1; i < grades.length; i++) {
    const g = grades[i];
    const gAbilities = new Set(monster.grades[g]?.abilities || []);
    const baseAbilities = new Set(commonAbilities);
    const exclusive = [...gAbilities].filter(a => !baseAbilities.has(a));
    if (exclusive.length > 0) {
      gradeNotes.push(`${g} gains ${exclusive.length} exclusive ability${exclusive.length > 1 ? 'ies' : 'y'}: ${exclusive.map(cleanName).join(', ')}`);
    }
  }

  // Find highest/lowest damage attacks
  const sortedAttacks = [...attacks].sort((a, b) => (b.damage_ratio || 0) - (a.damage_ratio || 0));
  const topAttack = sortedAttacks[0];

  const overview = [
    `${monster.name} is a ${monster.class_type}-class ${(monster.creature_types || []).join('/')} monster`,
    monster.dungeons?.length > 0 ? ` found in ${monster.dungeons.join(', ')}` : '',
    `. ${grades.length} grades: ${grades.join(', ')}.`,
    ` Base stats (${grades[0]}): ${stats.MaxHealthAdd} HP, ${stats.PhysicalDamageWeapon} physical damage, ${stats.MoveSpeedBase} move speed, ActionSpeed ${stats.ActionSpeed}.`,
    ` ImpactResistance ${stats.ImpactResistance}, MaxImpactEndurance ${stats.MaxImpactEndurance}.`,
    hasStagger ? ' Has a Staggered reaction in its ability set.' : '',
    ` ${attacks.length} attack${attacks.length !== 1 ? 's' : ''}, ${commonCombos.length} combo chain${commonCombos.length !== 1 ? 's' : ''}.`,
    topAttack ? ` Highest damage: ${cleanName(topAttack.name)} at ${(topAttack.damage_ratio || 0) / 10}% ratio (${calcDamage(stats.PhysicalDamageWeapon, topAttack.damage_ratio || 0)} base damage).` : '',
    gradeNotes.length > 0 ? ` ${gradeNotes.join('. ')}.` : '',
  ].join('');

  return {
    slug: monster.slug,
    overview,
    phases: buildPhases(monster),
    attack_categories: buildAttackCategories(monster),
    combo_flow: buildComboFlow(monster),
    status_effects_detail: buildStatusEffects(monster),
    strategies: buildStrategies(monster, gradeAnalysis),
    elite_differences: gradeAnalysis.differences,
    ai_perception: buildPerception(monster)
  };
}

// ── Main ─────────────────────────────────────────────────────────────────────

let generated = 0;
let skipped = 0;
let errors = 0;

// Skip non-real monsters
const skipSlugs = new Set([
  'banshee-fog-missile2', 'bone-prison', 'crystal',
  'designdata-monster-monster-dreadspine-boneprison',
  'designdata-monster-monster-dreadspine-bonewall',
]);

for (const monster of data.monsters) {
  if (targetSlug && monster.slug !== targetSlug) continue;
  if (skipSlugs.has(monster.slug)) { skipped++; continue; }

  const guidePath = path.join(GUIDES_DIR, `${monster.slug}.json`);

  if (fs.existsSync(guidePath) && !overwrite) {
    skipped++;
    continue;
  }

  try {
    const guide = generateGuide(monster);
    fs.writeFileSync(guidePath, JSON.stringify(guide, null, 2));
    generated++;
    console.log(`Generated: ${monster.slug}`);
  } catch (e) {
    errors++;
    console.error(`ERROR: ${monster.slug} — ${e.message}`);
  }
}

console.log(`\nDone: ${generated} generated, ${skipped} skipped, ${errors} errors`);
