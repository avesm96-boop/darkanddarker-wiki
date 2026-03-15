const fs = require('fs');

// Check idle-combat and one attack animation
['idle-combat', 'rush', 'tail-attack-r'].forEach(function(name) {
  const path = 'website/public/monster-models/animations/ancient-stingray/' + name + '.glb';
  const buf = fs.readFileSync(path);
  const jsonLen = buf.readUInt32LE(12);
  const j = JSON.parse(buf.slice(20, 20 + jsonLen));
  const binStart = 20 + ((jsonLen + 3) & ~3) + 8;

  console.log('\n=== ' + name + ' ===');
  const anim = (j.animations || [])[0];
  if (!anim) return;

  // Find "root" node index
  const rootNodeIdx = (j.nodes || []).findIndex(function(n) { return n.name === 'root'; });
  console.log('root node index:', rootNodeIdx);

  // Find translation channel for root
  anim.channels.forEach(function(ch) {
    if (ch.target.node !== rootNodeIdx) return;
    if (ch.target.path !== 'translation') return;

    const sampler = anim.samplers[ch.sampler];
    const outputAcc = j.accessors[sampler.output];
    const bv = j.bufferViews[outputAcc.bufferView];
    const offset = binStart + (bv.byteOffset || 0) + (outputAcc.byteOffset || 0);
    const count = outputAcc.count;

    // Read first, last, and min/max Y values
    let minY = Infinity, maxY = -Infinity;
    for (let i = 0; i < count; i++) {
      const y = buf.readFloatLE(offset + i * 12 + 4); // Y is second component of vec3
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    const y0 = buf.readFloatLE(offset + 4);
    const yLast = buf.readFloatLE(offset + (count - 1) * 12 + 4);
    console.log('root.translation Y: first=' + y0.toFixed(2) + ' last=' + yLast.toFixed(2) + ' min=' + minY.toFixed(2) + ' max=' + maxY.toFixed(2) + ' frames=' + count);

    // Also X and Z range
    let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
    for (let i = 0; i < count; i++) {
      const x = buf.readFloatLE(offset + i * 12 + 0);
      const z = buf.readFloatLE(offset + i * 12 + 8);
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
    }
    console.log('root.translation X: min=' + minX.toFixed(2) + ' max=' + maxX.toFixed(2));
    console.log('root.translation Z: min=' + minZ.toFixed(2) + ' max=' + maxZ.toFixed(2));
  });
});
