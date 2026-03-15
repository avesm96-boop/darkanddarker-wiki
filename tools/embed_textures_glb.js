/**
 * Embed textures into a GLB model file.
 *
 * Usage: node tools/embed_textures_glb.js
 *
 * Reads the existing ancient-stingray.glb, resizes raw textures to web-friendly
 * sizes, and embeds them as proper PBR materials into the GLB.
 */
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const ROOT = path.resolve(__dirname, '..');
const TEX_DIR = path.join('C:', 'Users', 'Administrator', 'Desktop', 'New folder (2)', 'Output', 'Exports', 'DungeonCrawler', 'Content', 'DungeonCrawler', 'Characters', 'Monster', 'AncientStingray', 'Textures');
const GLB_IN = path.join(ROOT, 'website/public/monster-models/animations/ancient-stingray-raw.glb');
const GLB_OUT = path.join(ROOT, 'website/public/monster-models/ancient-stingray.glb');

const TEX_SIZE = 1024; // resize 4096 -> 1024 for web

async function run() {
  // 1. Read the existing GLB
  const glbBuf = fs.readFileSync(GLB_IN);
  const jsonLen = glbBuf.readUInt32LE(12);
  const glbJson = JSON.parse(glbBuf.slice(20, 20 + jsonLen).toString('utf8'));

  // Extract existing binary chunk (mesh data)
  const binChunkStart = 20 + jsonLen;
  // Pad jsonLen to 4-byte boundary
  const paddedJsonLen = (jsonLen + 3) & ~3;
  const binHeaderStart = 20 + paddedJsonLen;
  const binLen = glbBuf.readUInt32LE(binHeaderStart);
  const existingBin = glbBuf.slice(binHeaderStart + 8, binHeaderStart + 8 + binLen);

  console.log(`Existing GLB: ${(glbJson.materials || []).length} materials, ${(glbJson.textures || []).length} textures, ${(glbJson.images || []).length} images`);
  console.log(`Existing binary chunk: ${existingBin.length} bytes`);

  // Strip any previously embedded textures — keep only mesh buffer views
  const meshBvIndices = new Set();
  (glbJson.accessors || []).forEach(function(a) { if (a.bufferView !== undefined) meshBvIndices.add(a.bufferView); });
  // Find end of mesh data in the binary chunk
  let meshDataEnd = 0;
  meshBvIndices.forEach(function(idx) {
    const bv = glbJson.bufferViews[idx];
    const end = (bv.byteOffset || 0) + bv.byteLength;
    if (end > meshDataEnd) meshDataEnd = end;
  });
  // Keep only mesh buffer views and trim binary to mesh data only
  const meshOnlyBin = existingBin.slice(0, meshDataEnd);
  glbJson.bufferViews = glbJson.bufferViews.filter(function(_, i) { return meshBvIndices.has(i); });
  glbJson.images = [];
  glbJson.textures = [];
  glbJson.samplers = [];
  console.log(`Stripped to mesh-only: ${meshOnlyBin.length} bytes, ${glbJson.bufferViews.length} buffer views`);

  // 2. Prepare textures - resize to web-friendly size
  console.log(`Resizing textures to ${TEX_SIZE}x${TEX_SIZE}...`);

  // Diffuse/Albedo (baseColor) — resize only, MeshBasicMaterial renders it directly
  const diffusePng = await sharp(path.join(TEX_DIR, 'T_AncientStingray_D.png'))
    .resize(TEX_SIZE, TEX_SIZE)
    .png({ quality: 85 })
    .toBuffer();
  console.log(`  Diffuse: ${(diffusePng.length / 1024).toFixed(0)}KB`);

  // MNR texture: Metallic(R), Normal(GB), Roughness(A)
  // We need to split this into separate textures for glTF:
  //   - Normal map (from G and B channels, with R=128 filler)
  //   - MetallicRoughness (glTF: B=metallic, G=roughness)
  const mnrRaw = await sharp(path.join(TEX_DIR, 'T_AncientStingray_MNR.png'))
    .resize(TEX_SIZE, TEX_SIZE)
    .raw()
    .toBuffer();

  // Build normal map: R=G_channel, G=A_channel (UE uses different normal format), B=255
  // Actually UE4 normal maps: R channel = X (but packed MNR uses G=normalX, B=normalY)
  // For glTF normal map: R=normalX, G=normalY, B=1.0
  const normalPixels = Buffer.alloc(TEX_SIZE * TEX_SIZE * 3);
  const mrPixels = Buffer.alloc(TEX_SIZE * TEX_SIZE * 3);

  for (let i = 0; i < TEX_SIZE * TEX_SIZE; i++) {
    const r = mnrRaw[i * 4 + 0]; // Metallic
    const g = mnrRaw[i * 4 + 1]; // Normal X
    const b = mnrRaw[i * 4 + 2]; // Normal Y
    const a = mnrRaw[i * 4 + 3]; // Roughness

    // Normal map for glTF (RGB)
    normalPixels[i * 3 + 0] = g;       // Normal X
    normalPixels[i * 3 + 1] = b;       // Normal Y
    normalPixels[i * 3 + 2] = 255;     // Normal Z (pointing up)

    // MetallicRoughness for glTF: R=0, G=roughness, B=metallic
    mrPixels[i * 3 + 0] = 0;
    mrPixels[i * 3 + 1] = a;           // Roughness in G
    mrPixels[i * 3 + 2] = r;           // Metallic in B
  }

  const normalPng = await sharp(normalPixels, { raw: { width: TEX_SIZE, height: TEX_SIZE, channels: 3 } })
    .png()
    .toBuffer();
  console.log(`  Normal: ${(normalPng.length / 1024).toFixed(0)}KB`);

  const mrPng = await sharp(mrPixels, { raw: { width: TEX_SIZE, height: TEX_SIZE, channels: 3 } })
    .png()
    .toBuffer();
  console.log(`  MetallicRoughness: ${(mrPng.length / 1024).toFixed(0)}KB`);

  // Emissive mask
  const emissivePng = await sharp(path.join(TEX_DIR, 'T_AncientStingray_EmissiveMask.png'))
    .resize(TEX_SIZE, TEX_SIZE)
    .png()
    .toBuffer();
  console.log(`  Emissive: ${(emissivePng.length / 1024).toFixed(0)}KB`);

  // 3. Build new binary chunk: existing mesh data + texture buffers
  // Each image needs to be padded to 4-byte alignment
  function pad4(buf) {
    const rem = buf.length % 4;
    if (rem === 0) return buf;
    return Buffer.concat([buf, Buffer.alloc(4 - rem, 0)]);
  }

  const existingBinPadded = pad4(meshOnlyBin);
  const diffusePadded = pad4(diffusePng);
  const normalPadded = pad4(normalPng);
  const mrPadded = pad4(mrPng);
  const emissivePadded = pad4(emissivePng);

  let offset = existingBin.length; // Use original (unpadded) as the base offset for alignment

  // Calculate buffer view offsets (relative to start of binary chunk)
  const existingBufferViewCount = glbJson.bufferViews?.length || 0;
  const existingAccessorCount = glbJson.accessors?.length || 0;

  // Texture buffer view offsets start after padded existing data
  const diffuseOffset = existingBinPadded.length;
  const normalOffset = diffuseOffset + diffusePadded.length;
  const mrOffset = normalOffset + normalPadded.length;
  const emissiveOffset = mrOffset + mrPadded.length;

  const newBin = Buffer.concat([existingBinPadded, diffusePadded, normalPadded, mrPadded, emissivePadded]);

  // 4. Update glTF JSON with texture references
  if (!glbJson.bufferViews) glbJson.bufferViews = [];
  if (!glbJson.images) glbJson.images = [];
  if (!glbJson.textures) glbJson.textures = [];
  if (!glbJson.samplers) glbJson.samplers = [];

  // Add sampler
  const samplerIdx = glbJson.samplers.length;
  glbJson.samplers.push({
    magFilter: 9729, // LINEAR
    minFilter: 9987, // LINEAR_MIPMAP_LINEAR
    wrapS: 10497,    // REPEAT
    wrapT: 10497     // REPEAT
  });

  // Add buffer views for each texture
  const bvDiffuse = glbJson.bufferViews.length;
  glbJson.bufferViews.push({ buffer: 0, byteOffset: diffuseOffset, byteLength: diffusePng.length });

  const bvNormal = glbJson.bufferViews.length;
  glbJson.bufferViews.push({ buffer: 0, byteOffset: normalOffset, byteLength: normalPng.length });

  const bvMR = glbJson.bufferViews.length;
  glbJson.bufferViews.push({ buffer: 0, byteOffset: mrOffset, byteLength: mrPng.length });

  const bvEmissive = glbJson.bufferViews.length;
  glbJson.bufferViews.push({ buffer: 0, byteOffset: emissiveOffset, byteLength: emissivePng.length });

  // Add images
  const imgDiffuse = glbJson.images.length;
  glbJson.images.push({ bufferView: bvDiffuse, mimeType: 'image/png' });

  const imgNormal = glbJson.images.length;
  glbJson.images.push({ bufferView: bvNormal, mimeType: 'image/png' });

  const imgMR = glbJson.images.length;
  glbJson.images.push({ bufferView: bvMR, mimeType: 'image/png' });

  const imgEmissive = glbJson.images.length;
  glbJson.images.push({ bufferView: bvEmissive, mimeType: 'image/png' });

  // Add textures
  const texDiffuse = glbJson.textures.length;
  glbJson.textures.push({ sampler: samplerIdx, source: imgDiffuse });

  const texNormal = glbJson.textures.length;
  glbJson.textures.push({ sampler: samplerIdx, source: imgNormal });

  const texMR = glbJson.textures.length;
  glbJson.textures.push({ sampler: samplerIdx, source: imgMR });

  const texEmissive = glbJson.textures.length;
  glbJson.textures.push({ sampler: samplerIdx, source: imgEmissive });

  // Collect every material index actually used by mesh primitives
  const usedMaterialIndices = new Set();
  (glbJson.meshes || []).forEach(function(mesh) {
    (mesh.primitives || []).forEach(function(prim) {
      if (prim.material !== undefined) usedMaterialIndices.add(prim.material);
    });
  });
  // If no primitives reference a material, fall back to index 0
  if (usedMaterialIndices.size === 0) usedMaterialIndices.add(0);
  console.log(`Used material indices: [${[...usedMaterialIndices].join(', ')}]`);

  // Ensure materials array exists and is large enough
  if (!glbJson.materials) glbJson.materials = [];

  // Apply textures to all used material slots
  usedMaterialIndices.forEach(function(mi) {
    while (glbJson.materials.length <= mi) glbJson.materials.push({});
    glbJson.materials[mi] = {
      name: 'MI_AncientStingray',
      pbrMetallicRoughness: {
        baseColorTexture: { index: texDiffuse },
        metallicFactor: 0.0,
        roughnessFactor: 0.85
      }
    };
  });

  // Update buffer total length
  glbJson.buffers[0].byteLength = newBin.length;

  // 5. Write new GLB
  const jsonStr = JSON.stringify(glbJson);
  const jsonBuf = Buffer.from(jsonStr, 'utf8');
  // Pad JSON to 4-byte boundary with spaces
  const jsonPadLen = (4 - (jsonBuf.length % 4)) % 4;
  const jsonPadded = Buffer.concat([jsonBuf, Buffer.alloc(jsonPadLen, 0x20)]);

  const totalLen = 12 + 8 + jsonPadded.length + 8 + newBin.length;
  const out = Buffer.alloc(totalLen);

  // GLB header
  out.writeUInt32LE(0x46546C67, 0); // magic "glTF"
  out.writeUInt32LE(2, 4);           // version
  out.writeUInt32LE(totalLen, 8);    // total length

  // JSON chunk
  out.writeUInt32LE(jsonPadded.length, 12);
  out.writeUInt32LE(0x4E4F534A, 16); // "JSON"
  jsonPadded.copy(out, 20);

  // Binary chunk
  const binStart = 20 + jsonPadded.length;
  out.writeUInt32LE(newBin.length, binStart);
  out.writeUInt32LE(0x004E4942, binStart + 4); // "BIN\0"
  newBin.copy(out, binStart + 8);

  fs.writeFileSync(GLB_OUT, out);
  console.log(`\nWrote ${GLB_OUT}`);
  console.log(`  Size: ${(out.length / 1024 / 1024).toFixed(1)}MB`);
  console.log(`  Materials: ${glbJson.materials.length}`);
  console.log(`  Textures: ${glbJson.textures.length}`);
  console.log(`  Images: ${glbJson.images.length}`);
}

run().catch(err => { console.error(err); process.exit(1); });
