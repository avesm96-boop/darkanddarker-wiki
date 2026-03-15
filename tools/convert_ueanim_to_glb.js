/**
 * Convert .ueanim (CUE4Parse/FModel UEFORMAT) animation files to GLB format
 * for Three.js playback in the monster model viewer.
 *
 * Usage: node tools/convert_ueanim_to_glb.js
 *
 * Reads .ueanim binary files, parses bone keyframes, converts from UE4 coordinate
 * space (left-hand Z-up) to glTF (right-hand Y-up), and writes per-animation GLB
 * files with proper glTF animation data.
 */
const fs = require('fs');
const path = require('path');

// ── Config ──────────────────────────────────────────────────────────────────

const ANIM_DIR = path.join('C:', 'Users', 'Administrator', 'Desktop', 'New folder (2)',
  'Output', 'Exports', 'DungeonCrawler', 'Content', 'DungeonCrawler',
  'Characters', 'Monster', 'AncientStingray', 'Animations');

const OUT_DIR = path.join(__dirname, '..', 'website', 'public', 'monster-models',
  'animations', 'ancient-stingray');

// [ueanimFilename, outputId, label, loop]
// Using AS_ prefix files (raw animation sequences, not AM_ montages)
const ANIMATIONS = [
  ['AS_AncientStingray_TailAttack_L.ueanim', 'tail-attack-l', 'Tail Attack L', false],
  ['AS_AncientStingray_TailAttack_R.ueanim', 'tail-attack-r', 'Tail Attack R', false],
  ['AS_AncientStingray_TailSlash_Down.ueanim', 'tail-slash-down', 'Tail Slash Down', false],
  ['AS_AncientStingray_TailSlash_High.ueanim', 'tail-slash-high', 'Tail Slash High', false],
  ['AS_AncientStingray_WaterArrow_1.ueanim', 'water-arrow-1', 'Water Arrow 1', false],
  ['AS_AncientStingray_WaterArrow_2.ueanim', 'water-arrow-2', 'Water Arrow 2', false],
  ['AS_AncientStingray_Death.ueanim', 'death', 'Death', false],
  ['AS_AncientStingray_Hit.ueanim', 'hit', 'Hit', false],
  ['AS_AncientStingray_DivineJudgment.ueanim', 'divine-judgment', 'Divine Judgment', false],
  ['AS_AncientStingray_LightningBubble.ueanim', 'lightning-bubble', 'Lightning Bubble', false],
  ['AS_AncientStingray_LightningNova_Start.ueanim', 'lightning-nova', 'Lightning Nova', false],
  ['AS_AncientStingray_Rush_Start.ueanim', 'rush', 'Rush', false],
  ['AS_AncientStingray_ShortDash.ueanim', 'short-dash', 'Short Dash', false],
  ['AS_AncientStingray_idle_Combat.ueanim', 'idle-combat', 'Combat Idle', true],
];

// ── UEFORMAT Parser ─────────────────────────────────────────────────────────

function readFString(buf, offset) {
  const len = buf.readInt32LE(offset);
  offset += 4;
  const str = buf.toString('utf8', offset, offset + len);
  offset += len;
  return { value: str, offset };
}

function parseUEAnim(filePath) {
  const buf = fs.readFileSync(filePath);
  let off = 0;

  // Magic "UEFORMAT" (8 bytes)
  const magic = buf.toString('ascii', off, off + 8);
  off += 8;
  if (magic !== 'UEFORMAT') throw new Error(`Invalid magic: ${magic}`);

  // Identifier (fstring)
  const ident = readFString(buf, off);
  off = ident.offset;
  if (ident.value !== 'UEANIM') throw new Error(`Expected UEANIM, got ${ident.value}`);

  // Version (single byte)
  const version = buf.readUInt8(off);
  off += 1;

  // Object name (fstring)
  const objName = readFString(buf, off);
  off = objName.offset;

  // Is compressed (bool)
  const isCompressed = buf.readUInt8(off) !== 0;
  off += 1;

  if (isCompressed) {
    throw new Error('Compressed .ueanim not yet supported');
  }

  let numFrames = 0;
  let fps = 30;
  const tracks = [];

  // For version < 7, numFrames and fps are inline before sections
  if (version < 7) {
    numFrames = buf.readInt32LE(off); off += 4;
    fps = buf.readFloatLE(off); off += 4;
  }

  // Read sections until EOF
  while (off < buf.length) {
    const sectionName = readFString(buf, off);
    off = sectionName.offset;
    const arraySize = buf.readInt32LE(off); off += 4;
    const byteSize = buf.readInt32LE(off); off += 4;
    const sectionEnd = off + byteSize;

    if (sectionName.value === 'METADATA') {
      numFrames = buf.readInt32LE(off); off += 4;
      fps = buf.readFloatLE(off); off += 4;
      // Skip remaining metadata fields
      off = sectionEnd;
    } else if (sectionName.value === 'TRACKS') {
      for (let t = 0; t < arraySize; t++) {
        const boneName = readFString(buf, off);
        off = boneName.offset;

        // Position keys
        const numPosKeys = buf.readInt32LE(off); off += 4;
        const posKeys = [];
        for (let k = 0; k < numPosKeys; k++) {
          const frame = buf.readInt32LE(off); off += 4;
          const x = buf.readFloatLE(off); off += 4;
          const y = buf.readFloatLE(off); off += 4;
          const z = buf.readFloatLE(off); off += 4;
          posKeys.push({ frame, x, y, z });
        }

        // Rotation keys
        const numRotKeys = buf.readInt32LE(off); off += 4;
        const rotKeys = [];
        for (let k = 0; k < numRotKeys; k++) {
          const frame = buf.readInt32LE(off); off += 4;
          const x = buf.readFloatLE(off); off += 4;
          const y = buf.readFloatLE(off); off += 4;
          const z = buf.readFloatLE(off); off += 4;
          const w = buf.readFloatLE(off); off += 4;
          rotKeys.push({ frame, x, y, z, w });
        }

        // Scale keys
        const numScaleKeys = buf.readInt32LE(off); off += 4;
        const scaleKeys = [];
        for (let k = 0; k < numScaleKeys; k++) {
          const frame = buf.readInt32LE(off); off += 4;
          const x = buf.readFloatLE(off); off += 4;
          const y = buf.readFloatLE(off); off += 4;
          const z = buf.readFloatLE(off); off += 4;
          scaleKeys.push({ frame, x, y, z });
        }

        tracks.push({
          boneName: boneName.value,
          posKeys,
          rotKeys,
          scaleKeys,
        });
      }
    } else {
      // Skip unknown sections
      off = sectionEnd;
    }
  }

  return { version, objectName: objName.value, numFrames, fps, tracks };
}

// ── Coordinate Conversion ───────────────────────────────────────────────────
// UE4 (left-hand Z-up) → glTF (right-hand Y-up)
// For local bone transforms: swap Y↔Z components, scale positions by 1/100
//
// For version >= 8 (PreserveOriginalTransforms), data is raw UE4 coordinates.
// The Blender plugin's sign flips are applied on import, NOT baked into the file.

function ue4PosToGltf(x, y, z) {
  return [x / 100, z / 100, y / 100];
}

function ue4QuatToGltf(qx, qy, qz, qw) {
  return [qx, qz, qy, qw]; // swap Y↔Z
}

function ue4ScaleToGltf(sx, sy, sz) {
  return [sx, sz, sy]; // swap Y↔Z
}

// ── GLB Builder ─────────────────────────────────────────────────────────────

function buildAnimationGLB(animData) {
  const { tracks, numFrames, fps } = animData;

  // Collect all unique bone names and create nodes
  const boneNames = tracks.map(t => t.boneName);

  // Build accessors, bufferViews, and binary data
  const accessors = [];
  const bufferViews = [];
  const channels = [];
  const samplers = [];
  const binaryChunks = [];
  let currentByteOffset = 0;

  for (let ti = 0; ti < tracks.length; ti++) {
    const track = tracks[ti];
    const nodeIndex = ti;

    // ── Position keys ──
    if (track.posKeys.length > 0) {
      const inputData = new Float32Array(track.posKeys.length);
      const outputData = new Float32Array(track.posKeys.length * 3);

      for (let k = 0; k < track.posKeys.length; k++) {
        const key = track.posKeys[k];
        inputData[k] = key.frame / fps;
        const [gx, gy, gz] = ue4PosToGltf(key.x, key.y, key.z);
        outputData[k * 3 + 0] = gx;
        outputData[k * 3 + 1] = gy;
        outputData[k * 3 + 2] = gz;
      }

      const inputBuf = Buffer.from(inputData.buffer);
      const outputBuf = Buffer.from(outputData.buffer);

      const inputBVIdx = bufferViews.length;
      bufferViews.push({
        buffer: 0,
        byteOffset: currentByteOffset,
        byteLength: inputBuf.length,
      });
      binaryChunks.push(inputBuf);
      currentByteOffset += inputBuf.length;

      const outputBVIdx = bufferViews.length;
      bufferViews.push({
        buffer: 0,
        byteOffset: currentByteOffset,
        byteLength: outputBuf.length,
      });
      binaryChunks.push(outputBuf);
      currentByteOffset += outputBuf.length;

      // Input accessor (time)
      const inputAccIdx = accessors.length;
      accessors.push({
        bufferView: inputBVIdx,
        componentType: 5126, // FLOAT
        count: track.posKeys.length,
        type: 'SCALAR',
        min: [inputData[0]],
        max: [inputData[inputData.length - 1]],
      });

      // Output accessor (vec3 translation)
      const outputAccIdx = accessors.length;
      accessors.push({
        bufferView: outputBVIdx,
        componentType: 5126,
        count: track.posKeys.length,
        type: 'VEC3',
      });

      const samplerIdx = samplers.length;
      samplers.push({
        input: inputAccIdx,
        output: outputAccIdx,
        interpolation: 'LINEAR',
      });

      channels.push({
        sampler: samplerIdx,
        target: { node: nodeIndex, path: 'translation' },
      });
    }

    // ── Rotation keys ──
    if (track.rotKeys.length > 0) {
      const inputData = new Float32Array(track.rotKeys.length);
      const outputData = new Float32Array(track.rotKeys.length * 4);

      for (let k = 0; k < track.rotKeys.length; k++) {
        const key = track.rotKeys[k];
        inputData[k] = key.frame / fps;
        const [gx, gy, gz, gw] = ue4QuatToGltf(key.x, key.y, key.z, key.w);
        outputData[k * 4 + 0] = gx;
        outputData[k * 4 + 1] = gy;
        outputData[k * 4 + 2] = gz;
        outputData[k * 4 + 3] = gw;
      }

      const inputBuf = Buffer.from(inputData.buffer);
      const outputBuf = Buffer.from(outputData.buffer);

      const inputBVIdx = bufferViews.length;
      bufferViews.push({
        buffer: 0,
        byteOffset: currentByteOffset,
        byteLength: inputBuf.length,
      });
      binaryChunks.push(inputBuf);
      currentByteOffset += inputBuf.length;

      const outputBVIdx = bufferViews.length;
      bufferViews.push({
        buffer: 0,
        byteOffset: currentByteOffset,
        byteLength: outputBuf.length,
      });
      binaryChunks.push(outputBuf);
      currentByteOffset += outputBuf.length;

      const inputAccIdx = accessors.length;
      accessors.push({
        bufferView: inputBVIdx,
        componentType: 5126,
        count: track.rotKeys.length,
        type: 'SCALAR',
        min: [inputData[0]],
        max: [inputData[inputData.length - 1]],
      });

      const outputAccIdx = accessors.length;
      accessors.push({
        bufferView: outputBVIdx,
        componentType: 5126,
        count: track.rotKeys.length,
        type: 'VEC4',
      });

      const samplerIdx = samplers.length;
      samplers.push({
        input: inputAccIdx,
        output: outputAccIdx,
        interpolation: 'LINEAR',
      });

      channels.push({
        sampler: samplerIdx,
        target: { node: nodeIndex, path: 'rotation' },
      });
    }

    // ── Scale keys ──
    if (track.scaleKeys.length > 0) {
      // Skip scale if it's just [1,1,1] (identity)
      const isIdentity = track.scaleKeys.length === 1 &&
        Math.abs(track.scaleKeys[0].x - 1) < 0.0001 &&
        Math.abs(track.scaleKeys[0].y - 1) < 0.0001 &&
        Math.abs(track.scaleKeys[0].z - 1) < 0.0001;

      if (!isIdentity) {
        const inputData = new Float32Array(track.scaleKeys.length);
        const outputData = new Float32Array(track.scaleKeys.length * 3);

        for (let k = 0; k < track.scaleKeys.length; k++) {
          const key = track.scaleKeys[k];
          inputData[k] = key.frame / fps;
          const [gx, gy, gz] = ue4ScaleToGltf(key.x, key.y, key.z);
          outputData[k * 3 + 0] = gx;
          outputData[k * 3 + 1] = gy;
          outputData[k * 3 + 2] = gz;
        }

        const inputBuf = Buffer.from(inputData.buffer);
        const outputBuf = Buffer.from(outputData.buffer);

        const inputBVIdx = bufferViews.length;
        bufferViews.push({
          buffer: 0,
          byteOffset: currentByteOffset,
          byteLength: inputBuf.length,
        });
        binaryChunks.push(inputBuf);
        currentByteOffset += inputBuf.length;

        const outputBVIdx = bufferViews.length;
        bufferViews.push({
          buffer: 0,
          byteOffset: currentByteOffset,
          byteLength: outputBuf.length,
        });
        binaryChunks.push(outputBuf);
        currentByteOffset += outputBuf.length;

        const inputAccIdx = accessors.length;
        accessors.push({
          bufferView: inputBVIdx,
          componentType: 5126,
          count: track.scaleKeys.length,
          type: 'SCALAR',
          min: [inputData[0]],
          max: [inputData[inputData.length - 1]],
        });

        const outputAccIdx = accessors.length;
        accessors.push({
          bufferView: outputBVIdx,
          componentType: 5126,
          count: track.scaleKeys.length,
          type: 'VEC3',
        });

        const samplerIdx = samplers.length;
        samplers.push({
          input: inputAccIdx,
          output: outputAccIdx,
          interpolation: 'LINEAR',
        });

        channels.push({
          sampler: samplerIdx,
          target: { node: nodeIndex, path: 'scale' },
        });
      }
    }
  }

  // Build the glTF JSON
  const gltf = {
    asset: { version: '2.0', generator: 'ueanim-to-glb converter' },
    scene: 0,
    scenes: [{ nodes: [0] }],
    nodes: boneNames.map(name => ({ name })),
    animations: [{
      name: animData.objectName,
      channels,
      samplers,
    }],
    accessors,
    bufferViews,
    buffers: [{ byteLength: currentByteOffset }],
  };

  // Pack into GLB
  const jsonStr = JSON.stringify(gltf);
  const jsonBuf = Buffer.from(jsonStr, 'utf8');
  // Pad JSON to 4-byte alignment
  const jsonPadding = (4 - (jsonBuf.length % 4)) % 4;
  const jsonChunk = Buffer.concat([
    jsonBuf,
    Buffer.alloc(jsonPadding, 0x20), // space padding per glTF spec
  ]);

  const binBuf = Buffer.concat(binaryChunks);
  // Pad binary to 4-byte alignment
  const binPadding = (4 - (binBuf.length % 4)) % 4;
  const binChunk = Buffer.concat([
    binBuf,
    Buffer.alloc(binPadding, 0x00),
  ]);

  // GLB header: magic(4) + version(4) + length(4)
  // JSON chunk: length(4) + type(4) + data
  // BIN chunk: length(4) + type(4) + data
  const totalLength = 12 + 8 + jsonChunk.length + 8 + binChunk.length;

  const glb = Buffer.alloc(totalLength);
  let pos = 0;

  // Header
  glb.writeUInt32LE(0x46546C67, pos); pos += 4; // "glTF" magic
  glb.writeUInt32LE(2, pos); pos += 4;           // version
  glb.writeUInt32LE(totalLength, pos); pos += 4;

  // JSON chunk
  glb.writeUInt32LE(jsonChunk.length, pos); pos += 4;
  glb.writeUInt32LE(0x4E4F534A, pos); pos += 4; // "JSON"
  jsonChunk.copy(glb, pos); pos += jsonChunk.length;

  // BIN chunk
  glb.writeUInt32LE(binChunk.length, pos); pos += 4;
  glb.writeUInt32LE(0x004E4942, pos); pos += 4; // "BIN\0"
  binChunk.copy(glb, pos);

  return glb;
}

// ── Main ────────────────────────────────────────────────────────────────────

function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const manifest = {
    monster: 'ancient-stingray',
    animations: [],
  };

  let successCount = 0;

  for (const [filename, id, label, loop] of ANIMATIONS) {
    const inputPath = path.join(ANIM_DIR, filename);

    if (!fs.existsSync(inputPath)) {
      console.error(`  SKIP ${filename} — file not found`);
      continue;
    }

    try {
      console.log(`Converting ${filename} → ${id}.glb ...`);

      const animData = parseUEAnim(inputPath);
      console.log(`  ${animData.tracks.length} tracks, ${animData.numFrames} frames, ${animData.fps.toFixed(1)} fps`);

      const glb = buildAnimationGLB(animData);
      const outPath = path.join(OUT_DIR, `${id}.glb`);
      fs.writeFileSync(outPath, glb);
      console.log(`  ✓ ${outPath} (${(glb.length / 1024).toFixed(1)} KB)`);

      manifest.animations.push({ id, label, file: `${id}.glb`, loop });
      successCount++;
    } catch (err) {
      console.error(`  ERROR ${filename}: ${err.message}`);
    }
  }

  // Write manifest
  const manifestPath = path.join(OUT_DIR, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`\nWrote manifest.json (${manifest.animations.length} animations)`);
  console.log(`Done: ${successCount}/${ANIMATIONS.length} converted successfully`);
}

main();
