/**
 * Bulk embed textures into raw GLB model files.
 *
 * Usage:
 *   node tools/embed_textures_bulk.js                    # all monsters
 *   node tools/embed_textures_bulk.js cyclops cave-troll  # specific monsters
 *
 * For each monster, reads the {slug}-raw.glb from the animations directory,
 * finds the diffuse texture in the FModel exports, resizes to 1024x1024,
 * and embeds it into the GLB as a PBR material.
 */
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const ROOT = path.resolve(__dirname, '..');
const MODELS_DIR = path.join(ROOT, 'website/public/monster-models');
const ANIMS_DIR = path.join(MODELS_DIR, 'animations');
const EXPORTS_ROOT = 'C:\\Users\\Administrator\\Desktop\\New folder (2)\\Output\\Exports\\DungeonCrawler\\Content\\DungeonCrawler\\Characters\\Monster';
const TEX_SIZE = 1024;

// Map slug -> FModel directory name (CamelCase)
function findMonsterDir(slug) {
  const entries = fs.readdirSync(EXPORTS_ROOT);
  // Try exact kebab-to-camel match
  const slugLower = slug.replace(/-/g, '').toLowerCase();
  for (const entry of entries) {
    if (entry.toLowerCase().replace(/[^a-z0-9]/g, '') === slugLower) {
      return path.join(EXPORTS_ROOT, entry);
    }
  }
  // Try partial match
  for (const entry of entries) {
    if (entry.toLowerCase().includes(slug.replace(/-/g, ''))) {
      return path.join(EXPORTS_ROOT, entry);
    }
  }
  return null;
}

// Recursively find a texture file matching a pattern
function findTexture(dir, patterns) {
  if (!fs.existsSync(dir)) return null;

  const allFiles = [];
  function walk(d) {
    for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, entry.name);
      if (entry.isDirectory()) walk(full);
      else allFiles.push(full);
    }
  }
  walk(dir);

  for (const pattern of patterns) {
    const found = allFiles.find(f => {
      const name = path.basename(f).toLowerCase();
      return name.includes(pattern.toLowerCase()) && name.endsWith('.png');
    });
    if (found) return found;
  }
  return null;
}

function pad4(buf) {
  const rem = buf.length % 4;
  if (rem === 0) return buf;
  return Buffer.concat([buf, Buffer.alloc(4 - rem, 0)]);
}

async function processMonster(slug) {
  const rawGlb = path.join(ANIMS_DIR, `${slug}-raw.glb`);
  const outGlb = path.join(MODELS_DIR, `${slug}.glb`);

  if (!fs.existsSync(rawGlb)) {
    console.log(`  SKIP ${slug}: no raw GLB at ${rawGlb}`);
    return false;
  }

  if (fs.existsSync(outGlb)) {
    console.log(`  SKIP ${slug}: textured GLB already exists`);
    return false;
  }

  // Find the FModel directory
  const monsterDir = findMonsterDir(slug);
  if (!monsterDir) {
    console.log(`  SKIP ${slug}: no FModel directory found`);
    return false;
  }

  // Find diffuse texture — try common naming patterns
  const baseName = path.basename(monsterDir);
  const diffusePath = findTexture(monsterDir, [
    `T_${baseName}_D`,
    `T_${baseName}_Body_D`,
    `T_${baseName}_Diffuse`,
    `${baseName}_D`,
    `_D.`,
    `_Diffuse.`,
    `_BaseColor.`,
    `_Color.`,
  ]);

  if (!diffusePath) {
    console.log(`  SKIP ${slug}: no diffuse texture found in ${monsterDir}`);
    return false;
  }

  console.log(`  Processing ${slug}...`);
  console.log(`    Raw GLB: ${path.basename(rawGlb)}`);
  console.log(`    Texture: ${path.basename(diffusePath)}`);

  // 1. Read the raw GLB
  const glbBuf = fs.readFileSync(rawGlb);
  const jsonLen = glbBuf.readUInt32LE(12);
  const glbJson = JSON.parse(glbBuf.slice(20, 20 + jsonLen).toString('utf8'));

  const paddedJsonLen = (jsonLen + 3) & ~3;
  const binHeaderStart = 20 + paddedJsonLen;
  const binLen = glbBuf.readUInt32LE(binHeaderStart);
  const existingBin = glbBuf.slice(binHeaderStart + 8, binHeaderStart + 8 + binLen);

  // Strip any previous textures — keep only mesh buffer views
  const meshBvIndices = new Set();
  (glbJson.accessors || []).forEach(a => { if (a.bufferView !== undefined) meshBvIndices.add(a.bufferView); });
  let meshDataEnd = 0;
  meshBvIndices.forEach(idx => {
    const bv = glbJson.bufferViews[idx];
    const end = (bv.byteOffset || 0) + bv.byteLength;
    if (end > meshDataEnd) meshDataEnd = end;
  });
  const meshOnlyBin = existingBin.slice(0, meshDataEnd);
  glbJson.bufferViews = glbJson.bufferViews.filter((_, i) => meshBvIndices.has(i));
  glbJson.images = [];
  glbJson.textures = [];
  glbJson.samplers = [];

  // 2. Resize diffuse texture
  const diffusePng = await sharp(diffusePath)
    .resize(TEX_SIZE, TEX_SIZE)
    .png({ quality: 85 })
    .toBuffer();
  console.log(`    Diffuse resized: ${(diffusePng.length / 1024).toFixed(0)}KB`);

  // 3. Build new binary chunk
  const existingBinPadded = pad4(meshOnlyBin);
  const diffusePadded = pad4(diffusePng);
  const diffuseOffset = existingBinPadded.length;
  const newBin = Buffer.concat([existingBinPadded, diffusePadded]);

  // 4. Update glTF JSON
  if (!glbJson.bufferViews) glbJson.bufferViews = [];
  if (!glbJson.images) glbJson.images = [];
  if (!glbJson.textures) glbJson.textures = [];
  if (!glbJson.samplers) glbJson.samplers = [];

  const samplerIdx = glbJson.samplers.length;
  glbJson.samplers.push({
    magFilter: 9729,
    minFilter: 9987,
    wrapS: 10497,
    wrapT: 10497
  });

  const bvDiffuse = glbJson.bufferViews.length;
  glbJson.bufferViews.push({ buffer: 0, byteOffset: diffuseOffset, byteLength: diffusePng.length });

  const imgDiffuse = glbJson.images.length;
  glbJson.images.push({ bufferView: bvDiffuse, mimeType: 'image/png' });

  const texDiffuse = glbJson.textures.length;
  glbJson.textures.push({ sampler: samplerIdx, source: imgDiffuse });

  // Apply to all used material slots
  const usedMaterialIndices = new Set();
  (glbJson.meshes || []).forEach(mesh => {
    (mesh.primitives || []).forEach(prim => {
      if (prim.material !== undefined) usedMaterialIndices.add(prim.material);
    });
  });
  if (usedMaterialIndices.size === 0) usedMaterialIndices.add(0);

  if (!glbJson.materials) glbJson.materials = [];
  usedMaterialIndices.forEach(mi => {
    while (glbJson.materials.length <= mi) glbJson.materials.push({});
    glbJson.materials[mi] = {
      name: `MI_${baseName}`,
      pbrMetallicRoughness: {
        baseColorTexture: { index: texDiffuse },
        metallicFactor: 0.0,
        roughnessFactor: 0.85
      }
    };
  });

  glbJson.buffers[0].byteLength = newBin.length;

  // 5. Write new GLB
  const jsonStr = JSON.stringify(glbJson);
  const jsonBuf = Buffer.from(jsonStr, 'utf8');
  const jsonPadLen = (4 - (jsonBuf.length % 4)) % 4;
  const jsonPadded2 = Buffer.concat([jsonBuf, Buffer.alloc(jsonPadLen, 0x20)]);

  const totalLen = 12 + 8 + jsonPadded2.length + 8 + newBin.length;
  const out = Buffer.alloc(totalLen);

  out.writeUInt32LE(0x46546C67, 0);
  out.writeUInt32LE(2, 4);
  out.writeUInt32LE(totalLen, 8);
  out.writeUInt32LE(jsonPadded2.length, 12);
  out.writeUInt32LE(0x4E4F534A, 16);
  jsonPadded2.copy(out, 20);

  const binStart = 20 + jsonPadded2.length;
  out.writeUInt32LE(newBin.length, binStart);
  out.writeUInt32LE(0x004E4942, binStart + 4);
  newBin.copy(out, binStart + 8);

  fs.writeFileSync(outGlb, out);
  const sizeMB = (out.length / 1024 / 1024).toFixed(1);
  console.log(`    Output: ${slug}.glb (${sizeMB}MB, ${glbJson.materials.length} materials)`);
  return true;
}

async function main() {
  const args = process.argv.slice(2);

  let slugs;
  if (args.length > 0) {
    slugs = args;
  } else {
    // Find all monsters with raw GLBs
    slugs = fs.readdirSync(ANIMS_DIR)
      .filter(f => f.endsWith('-raw.glb'))
      .map(f => f.replace('-raw.glb', ''));
  }

  console.log(`\nEmbed Textures — Processing ${slugs.length} monsters\n`);

  let success = 0, skip = 0, fail = 0;
  for (const slug of slugs) {
    try {
      const ok = await processMonster(slug);
      if (ok) success++; else skip++;
    } catch (err) {
      console.log(`  ERROR ${slug}: ${err.message}`);
      fail++;
    }
  }

  console.log(`\nDone: ${success} created, ${skip} skipped, ${fail} failed`);
}

main().catch(err => { console.error(err); process.exit(1); });
