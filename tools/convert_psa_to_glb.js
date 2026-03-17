/**
 * Convert PSA (ActorX) animation files to GLB format for Three.js playback.
 *
 * Usage: node tools/convert_psa_to_glb.js
 *
 * Reads PSA files from the FModel export directory, parses bone keyframes,
 * and writes per-animation GLB files with glTF animation data that can be
 * loaded by Three.js GLTFLoader and applied to the main model's skeleton.
 */
const fs = require('fs');
const path = require('path');

// ── Config ──────────────────────────────────────────────────────────────────

const ANIM_DIR = path.join('C:', 'Users', 'pawel', 'Desktop', 'Projects',
  'Output', 'Exports', 'DungeonCrawler', 'Content', 'DungeonCrawler',
  'Characters', 'Monster', 'AncientStingray', 'Animations');

const OUT_DIR = path.join(__dirname, '..', 'website', 'public', 'monster-models',
  'animations', 'ancient-stingray');

const MODEL_GLB = path.join(__dirname, '..', 'website', 'public', 'monster-models', 'ancient-stingray.glb');

// No external skeleton JSON needed — corrections computed from PSA rest vs model GLB rest.

// Animation files to convert: [psaFilename, outputId, label, loop]
const ANIMATIONS = [
  ['AS_AncientStingray_TailAttack_L.psa', 'tail-attack-l', 'Tail Attack L', false],
  ['AS_AncientStingray_TailAttack_R.psa', 'tail-attack-r', 'Tail Attack R', false],
  ['AS_AncientStingray_TailSlash_Down.psa', 'tail-slash-down', 'Tail Slash Down', false],
  ['AS_AncientStingray_TailSlash_High.psa', 'tail-slash-high', 'Tail Slash High', false],
  ['AS_AncientStingray_WaterArrow_1.psa', 'water-arrow-1', 'Water Arrow 1', false],
  ['AS_AncientStingray_WaterArrow_2.psa', 'water-arrow-2', 'Water Arrow 2', false],
  ['AS_AncientStingray_Death.psa', 'death', 'Death', false],
  ['AS_AncientStingray_Hit.psa', 'hit', 'Hit', false],
  ['AS_AncientStingray_DivineJudgment.psa', 'divine-judgment', 'Divine Judgment', false],
  ['AS_AncientStingray_LightningBubble.psa', 'lightning-bubble', 'Lightning Bubble', false],
  ['AS_AncientStingray_LightningNova_Start.psa', 'lightning-nova', 'Lightning Nova', false],
  ['AS_AncientStingray_Rush_Start.psa', 'rush', 'Rush', false],
  ['AS_AncientStingray_ShortDash.psa', 'short-dash', 'Short Dash', false],
  ['AS_AncientStingray_idle_Combat.psa', 'idle-combat', 'Combat Idle', true],
];

// ── PSA Parser ──────────────────────────────────────────────────────────────

function readChunkHeader(buf, offset) {
  return {
    id: buf.slice(offset, offset + 20).toString('ascii').replace(/\0/g, ''),
    flags: buf.readUInt32LE(offset + 20),
    dataSize: buf.readUInt32LE(offset + 24),
    dataCount: buf.readUInt32LE(offset + 28),
  };
}

function parsePsa(filePath) {
  const buf = fs.readFileSync(filePath);
  const chunks = {};
  let off = 0;

  while (off + 32 <= buf.length) {
    const h = readChunkHeader(buf, off);
    const dataStart = off + 32;
    const dataEnd = dataStart + h.dataSize * h.dataCount;
    chunks[h.id] = { ...h, dataStart };
    off = dataEnd;
  }

  // Parse bones (FNamedBoneBinary: 120 bytes each)
  // Layout: name[64], flags[4], numChildren[4], parentIdx[4], quat[16], pos[12], length[4], size[12]
  const bc = chunks['BONENAMES'];
  const bones = [];
  for (let i = 0; i < bc.dataCount; i++) {
    const o = bc.dataStart + i * bc.dataSize;
    const name = buf.slice(o, o + 64).toString('ascii').replace(/\0/g, '').trim();
    const parentIdx = buf.readInt32LE(o + 72);
    // Reference skeleton rest pose (orientation + position)
    const restQx = buf.readFloatLE(o + 76);
    const restQy = buf.readFloatLE(o + 80);
    const restQz = buf.readFloatLE(o + 84);
    const restQw = buf.readFloatLE(o + 88);
    const restPx = buf.readFloatLE(o + 92);
    const restPy = buf.readFloatLE(o + 96);
    const restPz = buf.readFloatLE(o + 100);
    bones.push({
      name, parentIdx,
      restQuat: [restQx, restQy, restQz, restQw],
      restPos: [restPx, restPy, restPz],
    });
  }

  // Parse animation keys (position vec3 + rotation quat + time float = 32 bytes)
  const kc = chunks['ANIMKEYS'];
  const numBones = bones.length;
  const numKeys = kc.dataCount;
  const numFrames = Math.floor(numKeys / numBones);
  const keys = [];
  for (let i = 0; i < numKeys; i++) {
    const o = kc.dataStart + i * 32;
    keys.push({
      px: buf.readFloatLE(o),
      py: buf.readFloatLE(o + 4),
      pz: buf.readFloatLE(o + 8),
      qx: buf.readFloatLE(o + 12),
      qy: buf.readFloatLE(o + 16),
      qz: buf.readFloatLE(o + 20),
      qw: buf.readFloatLE(o + 24),
      time: buf.readFloatLE(o + 28),
    });
  }

  // Parse scale keys if present (scale vec3 + time float = 16 bytes)
  let scaleKeys = null;
  if (chunks['SCALEKEYS']) {
    const sc = chunks['SCALEKEYS'];
    scaleKeys = [];
    for (let i = 0; i < sc.dataCount; i++) {
      const o = sc.dataStart + i * 16;
      scaleKeys.push({
        sx: buf.readFloatLE(o),
        sy: buf.readFloatLE(o + 4),
        sz: buf.readFloatLE(o + 8),
        time: buf.readFloatLE(o + 12),
      });
    }
  }

  return { bones, numFrames, numBones, keys, scaleKeys };
}

// ── Coordinate conversion: UE4 (left-hand Z-up) → glTF (right-hand Y-up) ──

function ueToGltfPos(px, py, pz) {
  // UE4 uses centimeters, glTF uses meters
  // Axis remap: gltf_x = ue_x, gltf_y = ue_z, gltf_z = ue_y
  // Verified against FModel's glTF output (no negation needed for local bone transforms)
  return [px / 100, pz / 100, py / 100];
}

function ueToGltfQuat(qx, qy, qz, qw) {
  // Axis remap: swap Y↔Z (no negation for local bone transforms)
  // Verified against FModel's glTF output for rest pose
  return [qx, qz, qy, qw];
}

function ueToGltfScale(sx, sy, sz) {
  return [sx, sz, sy];
}

// ── Rest-pose loading ────────────────────────────────────────────────────────

function loadModelRestPose() {
  const buf = fs.readFileSync(MODEL_GLB);
  const jsonLen = buf.readUInt32LE(12);
  const json = JSON.parse(buf.slice(20, 20 + jsonLen).toString('utf8'));
  const restPose = {};
  for (const jointIdx of json.skins[0].joints) {
    const node = json.nodes[jointIdx];
    restPose[node.name] = {
      t: node.translation || [0, 0, 0],
      r: node.rotation || [0, 0, 0, 1],
    };
  }
  return restPose;
}


// Quaternion math helpers
function quatInverse(q) {
  // For unit quaternions, inverse = conjugate
  return [-q[0], -q[1], -q[2], q[3]];
}

function quatMultiply(a, b) {
  return [
    a[3]*b[0] + a[0]*b[3] + a[1]*b[2] - a[2]*b[1],
    a[3]*b[1] + a[1]*b[3] + a[2]*b[0] - a[0]*b[2],
    a[3]*b[2] + a[2]*b[3] + a[0]*b[1] - a[1]*b[0],
    a[3]*b[3] - a[0]*b[0] - a[1]*b[1] - a[2]*b[2],
  ];
}

function quatNormalize(q) {
  const len = Math.sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]);
  if (len < 1e-10) return [0, 0, 0, 1];
  return [q[0]/len, q[1]/len, q[2]/len, q[3]/len];
}

/**
 * Compute per-bone retargeting corrections by comparing PSA frame 0 with model rest pose.
 * For each bone: correction maps PSA's reference frame to the model's frame.
 *   Rotation: q_corrected = q_correction * q_psa_anim
 *     where q_correction = q_model_rest * inverse(q_psa_rest)
 *   Position: p_corrected = p_model_rest + (p_psa_anim - p_psa_rest)
 */
/**
 * Compute per-bone retargeting corrections.
 * Compares PSA reference skeleton (BONENAMES, in UE4 space) directly against the
 * model GLB rest pose (glTF space).  No external SKEL JSON required.
 */
function computeRetargetCorrections(psa, modelRestPose) {
  const corrections = {};
  let correctedCount = 0;

  for (let b = 0; b < psa.numBones; b++) {
    const bone = psa.bones[b];
    const modelRest = modelRestPose[bone.name];
    if (!modelRest) continue;

    // Convert PSA rest pose to glTF space
    const psaPosGltf = ueToGltfPos(bone.restPos[0], bone.restPos[1], bone.restPos[2]);
    // PSA BONENAMES quats are already in "rest" orientation (not conjugated)
    const psaRotGltf = ueToGltfQuat(bone.restQuat[0], bone.restQuat[1], bone.restQuat[2], bone.restQuat[3]);

    const posDist = Math.sqrt(
      (psaPosGltf[0]-modelRest.t[0])**2 +
      (psaPosGltf[1]-modelRest.t[1])**2 +
      (psaPosGltf[2]-modelRest.t[2])**2
    );
    const rotDot = Math.abs(
      psaRotGltf[0]*modelRest.r[0] + psaRotGltf[1]*modelRest.r[1] +
      psaRotGltf[2]*modelRest.r[2] + psaRotGltf[3]*modelRest.r[3]
    );

    if (posDist > 0.001 || rotDot < 0.9999) {
      const rotCorrection = quatNormalize(quatMultiply(modelRest.r, quatInverse(psaRotGltf)));
      corrections[bone.name] = {
        rotCorrection,
        psaRestPos: psaPosGltf,
        modelRestPos: modelRest.t,
      };
      correctedCount++;
    }
  }

  console.log(`  Retarget corrections for ${correctedCount} bones`);
  return corrections;
}

// ── GLB Writer ──────────────────────────────────────────────────────────────

function buildAnimationGlb(psa, animName, retargetCorrections) {
  const { bones, numFrames, numBones, keys, scaleKeys } = psa;

  // Determine FPS from key timestamps
  // Keys are interleaved: frame0_bone0, frame0_bone1, ..., frame1_bone0, ...
  // Time values increment per frame (all bones in same frame have same time)
  const fps = 30; // Standard UE4 animation fps
  const duration = (numFrames - 1) / fps;

  // Build node hierarchy
  const nodes = [];
  const childrenMap = {};
  for (let i = 0; i < bones.length; i++) {
    childrenMap[i] = [];
  }
  let rootIdx = -1;
  for (let i = 0; i < bones.length; i++) {
    if (bones[i].parentIdx >= 0) {
      childrenMap[bones[i].parentIdx].push(i);
    } else {
      rootIdx = i;
    }
  }

  for (let i = 0; i < bones.length; i++) {
    const node = { name: bones[i].name };
    if (childrenMap[i].length > 0) {
      node.children = childrenMap[i];
    }
    nodes.push(node);
  }

  // Build animation data: per-bone time + translation + rotation + scale tracks
  const timeStamps = [];
  for (let f = 0; f < numFrames; f++) {
    timeStamps.push(f / fps);
  }
  const timeBuffer = new Float32Array(timeStamps);

  // Per-bone translation and rotation data
  const translationBuffers = [];
  const rotationBuffers = [];
  const scaleBuffers = [];

  for (let b = 0; b < numBones; b++) {
    const trans = new Float32Array(numFrames * 3);
    const rot = new Float32Array(numFrames * 4);
    const scale = new Float32Array(numFrames * 3);

    for (let f = 0; f < numFrames; f++) {
      const keyIdx = f * numBones + b;
      const key = keys[keyIdx];
      let pos = ueToGltfPos(key.px, key.py, key.pz);
      // UE5 PSA ANIMKEYS are NOT conjugated (unlike UE4 ActorX convention)
      let quat = ueToGltfQuat(key.qx, key.qy, key.qz, key.qw);

      // Apply bone retargeting: map PSA's reference frame to model's frame
      const rc = retargetCorrections[bones[b].name];
      if (rc) {
        // Position: model_rest + (psa_anim - psa_rest)
        pos = [
          rc.modelRestPos[0] + (pos[0] - rc.psaRestPos[0]),
          rc.modelRestPos[1] + (pos[1] - rc.psaRestPos[1]),
          rc.modelRestPos[2] + (pos[2] - rc.psaRestPos[2]),
        ];
        // Rotation: q_correction * q_psa_anim
        quat = quatNormalize(quatMultiply(rc.rotCorrection, quat));
      }

      let [rx, ry, rz, rw] = quat;

      // Quaternion sign normalization: ensure consecutive keyframes are on the
      // same hemisphere so SLERP takes the shortest path.
      if (f > 0) {
        const pi = (f - 1) * 4;
        const dot = rot[pi] * rx + rot[pi + 1] * ry + rot[pi + 2] * rz + rot[pi + 3] * rw;
        if (dot < 0) {
          rx = -rx; ry = -ry; rz = -rz; rw = -rw;
        }
      }

      trans[f * 3 + 0] = pos[0];
      trans[f * 3 + 1] = pos[1];
      trans[f * 3 + 2] = pos[2];
      rot[f * 4 + 0] = rx;
      rot[f * 4 + 1] = ry;
      rot[f * 4 + 2] = rz;
      rot[f * 4 + 3] = rw;

      if (scaleKeys) {
        const sk = scaleKeys[keyIdx];
        const [sx, sy, sz] = ueToGltfScale(sk.sx, sk.sy, sk.sz);
        scale[f * 3 + 0] = sx;
        scale[f * 3 + 1] = sy;
        scale[f * 3 + 2] = sz;
      } else {
        scale[f * 3 + 0] = 1;
        scale[f * 3 + 1] = 1;
        scale[f * 3 + 2] = 1;
      }
    }

    translationBuffers.push(trans);
    rotationBuffers.push(rot);
    scaleBuffers.push(scale);
  }

  // Assemble binary buffer: time array (shared) + per-bone translation + rotation + scale
  const bufferParts = [];
  let totalSize = 0;

  // Time buffer (shared across all channels)
  const timeBuf = Buffer.from(timeBuffer.buffer);
  bufferParts.push(timeBuf);
  const timeOffset = totalSize;
  const timeByteLen = timeBuf.length;
  totalSize += timeBuf.length;

  // Per-bone data
  const boneAccessors = [];
  for (let b = 0; b < numBones; b++) {
    const tBuf = Buffer.from(translationBuffers[b].buffer);
    const rBuf = Buffer.from(rotationBuffers[b].buffer);
    const sBuf = Buffer.from(scaleBuffers[b].buffer);

    const tOff = totalSize;
    bufferParts.push(tBuf);
    totalSize += tBuf.length;

    const rOff = totalSize;
    bufferParts.push(rBuf);
    totalSize += rBuf.length;

    const sOff = totalSize;
    bufferParts.push(sBuf);
    totalSize += sBuf.length;

    boneAccessors.push({
      translationOffset: tOff,
      translationByteLen: tBuf.length,
      rotationOffset: rOff,
      rotationByteLen: rBuf.length,
      scaleOffset: sOff,
      scaleByteLen: sBuf.length,
    });
  }

  const binChunk = Buffer.concat(bufferParts);

  // Build glTF JSON
  const bufferViews = [];
  const accessors = [];
  const channels = [];
  const samplers = [];

  // BufferView 0: timestamps
  bufferViews.push({
    buffer: 0,
    byteOffset: timeOffset,
    byteLength: timeByteLen,
  });
  // Accessor 0: timestamps
  const timeAccessorIdx = 0;
  accessors.push({
    bufferView: 0,
    componentType: 5126, // FLOAT
    count: numFrames,
    type: 'SCALAR',
    min: [0],
    max: [duration],
  });

  let bvIdx = 1;
  let accIdx = 1;

  for (let b = 0; b < numBones; b++) {
    const ba = boneAccessors[b];

    // Translation bufferView + accessor
    bufferViews.push({ buffer: 0, byteOffset: ba.translationOffset, byteLength: ba.translationByteLen });
    accessors.push({
      bufferView: bvIdx,
      componentType: 5126,
      count: numFrames,
      type: 'VEC3',
    });
    const transAccIdx = accIdx;
    bvIdx++;
    accIdx++;

    // Rotation bufferView + accessor
    bufferViews.push({ buffer: 0, byteOffset: ba.rotationOffset, byteLength: ba.rotationByteLen });
    accessors.push({
      bufferView: bvIdx,
      componentType: 5126,
      count: numFrames,
      type: 'VEC4',
    });
    const rotAccIdx = accIdx;
    bvIdx++;
    accIdx++;

    // Scale bufferView + accessor
    bufferViews.push({ buffer: 0, byteOffset: ba.scaleOffset, byteLength: ba.scaleByteLen });
    accessors.push({
      bufferView: bvIdx,
      componentType: 5126,
      count: numFrames,
      type: 'VEC3',
    });
    const scaleAccIdx = accIdx;
    bvIdx++;
    accIdx++;

    // Translation channel + sampler
    const transSamplerIdx = samplers.length;
    samplers.push({ input: timeAccessorIdx, output: transAccIdx, interpolation: 'LINEAR' });
    channels.push({ sampler: transSamplerIdx, target: { node: b, path: 'translation' } });

    // Rotation channel + sampler
    const rotSamplerIdx = samplers.length;
    samplers.push({ input: timeAccessorIdx, output: rotAccIdx, interpolation: 'LINEAR' });
    channels.push({ sampler: rotSamplerIdx, target: { node: b, path: 'rotation' } });

    // Scale channel + sampler
    const scaleSamplerIdx = samplers.length;
    samplers.push({ input: timeAccessorIdx, output: scaleAccIdx, interpolation: 'LINEAR' });
    channels.push({ sampler: scaleSamplerIdx, target: { node: b, path: 'scale' } });
  }

  const gltfJson = {
    asset: { version: '2.0', generator: 'DnD-Wiki PSA Converter' },
    scene: 0,
    scenes: [{ nodes: [rootIdx] }],
    nodes,
    animations: [{
      name: animName,
      channels,
      samplers,
    }],
    bufferViews,
    accessors,
    buffers: [{ byteLength: binChunk.length }],
  };

  // Write GLB
  const jsonStr = JSON.stringify(gltfJson);
  const jsonBuf = Buffer.from(jsonStr, 'utf8');
  const jsonPadLen = (4 - (jsonBuf.length % 4)) % 4;
  const jsonPadded = Buffer.concat([jsonBuf, Buffer.alloc(jsonPadLen, 0x20)]);

  // Pad binary to 4-byte boundary
  const binPadLen = (4 - (binChunk.length % 4)) % 4;
  const binPadded = Buffer.concat([binChunk, Buffer.alloc(binPadLen, 0)]);

  const totalLen = 12 + 8 + jsonPadded.length + 8 + binPadded.length;
  const out = Buffer.alloc(totalLen);

  // GLB header
  out.writeUInt32LE(0x46546C67, 0); // "glTF"
  out.writeUInt32LE(2, 4);           // version
  out.writeUInt32LE(totalLen, 8);    // total length

  // JSON chunk
  out.writeUInt32LE(jsonPadded.length, 12);
  out.writeUInt32LE(0x4E4F534A, 16); // "JSON"
  jsonPadded.copy(out, 20);

  // Binary chunk
  const binStart = 20 + jsonPadded.length;
  out.writeUInt32LE(binPadded.length, binStart);
  out.writeUInt32LE(0x004E4942, binStart + 4); // "BIN\0"
  binPadded.copy(out, binStart + 8);

  return out;
}

// ── Main ────────────────────────────────────────────────────────────────────

function main() {
  // Ensure output directory exists
  fs.mkdirSync(OUT_DIR, { recursive: true });

  console.log('Loading model rest pose...');
  const modelRestPose = loadModelRestPose();
  console.log(`  ${Object.keys(modelRestPose).length} bones in model`);

  const manifest = {
    monster: 'ancient-stingray',
    animations: [],
  };

  // Compute retarget corrections from first available PSA vs model rest pose
  console.log('\nComputing retarget corrections (PSA rest vs model GLB)...');
  let retargetCorrections = {};
  const firstPsa = ANIMATIONS.find(([f]) => fs.existsSync(path.join(ANIM_DIR, f)));
  if (firstPsa) {
    const psa = parsePsa(path.join(ANIM_DIR, firstPsa[0]));
    retargetCorrections = computeRetargetCorrections(psa, modelRestPose);
  }

  for (const [psaFile, id, label, loop] of ANIMATIONS) {
    const psaPath = path.join(ANIM_DIR, psaFile);
    if (!fs.existsSync(psaPath)) {
      console.log(`  SKIP ${psaFile} (not found)`);
      continue;
    }

    console.log(`Converting ${psaFile}...`);
    const psa = parsePsa(psaPath);
    console.log(`  Bones: ${psa.numBones}, Frames: ${psa.numFrames}, Keys: ${psa.keys.length}`);

    const glb = buildAnimationGlb(psa, id, retargetCorrections);
    const outPath = path.join(OUT_DIR, `${id}.glb`);
    fs.writeFileSync(outPath, glb);
    console.log(`  Wrote ${outPath} (${(glb.length / 1024).toFixed(0)}KB)`);

    manifest.animations.push({ id, label, file: `${id}.glb`, loop });
  }

  // Write manifest
  const manifestPath = path.join(OUT_DIR, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`\nWrote manifest: ${manifestPath}`);
  console.log(`Total animations: ${manifest.animations.length}`);
}

main();
