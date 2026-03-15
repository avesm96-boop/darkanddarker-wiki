const fs = require('fs');

function readGlb(path) {
  const buf = fs.readFileSync(path);
  const jsonLen = buf.readUInt32LE(12);
  return {
    json: JSON.parse(buf.slice(20, 20 + jsonLen).toString('utf8')),
    buf: buf,
    binStart: 20 + ((jsonLen + 3) & ~3) + 8
  };
}

// Compare model and animation bone rest poses
var model = readGlb('website/public/monster-models/ancient-stingray.glb');
var anim = readGlb('website/public/monster-models/animations/ancient-stingray/idle-combat.glb');

console.log('=== MODEL bone rest poses (first 10 nodes) ===');
(model.json.nodes || []).slice(0, 10).forEach(function(n, i) {
  console.log('  ' + i + ' "' + n.name + '" t=' + JSON.stringify(n.translation) + ' r=' + JSON.stringify(n.rotation) + ' s=' + JSON.stringify(n.scale));
});

console.log('\n=== ANIM bone rest poses (last 10 nodes, where root bone is) ===');
var animNodes = anim.json.nodes || [];
animNodes.slice(Math.max(0, animNodes.length - 10)).forEach(function(n, i) {
  var idx = Math.max(0, animNodes.length - 10) + i;
  console.log('  ' + idx + ' "' + n.name + '" t=' + JSON.stringify(n.translation) + ' r=' + JSON.stringify(n.rotation) + ' s=' + JSON.stringify(n.scale));
});

// Find matching bones and compare
console.log('\n=== COMPARING key bones between model and animation ===');
var keyBones = ['root', 'ASR', 'Upper', 'Lower', 'head'];
keyBones.forEach(function(boneName) {
  var modelNode = null, animNode = null;
  var modelIdx = -1, animIdx = -1;
  model.json.nodes.forEach(function(n, i) { if (n.name === boneName) { modelNode = n; modelIdx = i; } });
  anim.json.nodes.forEach(function(n, i) { if (n.name === boneName) { animNode = n; animIdx = i; } });

  if (modelNode && animNode) {
    console.log('"' + boneName + '":');
    console.log('  MODEL (node ' + modelIdx + '): t=' + JSON.stringify(modelNode.translation) + ' r=' + JSON.stringify(modelNode.rotation));
    console.log('  ANIM  (node ' + animIdx + '): t=' + JSON.stringify(animNode.translation) + ' r=' + JSON.stringify(animNode.rotation));
  }
});

// Check ASR bone translation range in animation
console.log('\n=== ASR bone animation range in idle-combat ===');
var animData = anim.json;
var animObj = (animData.animations || [])[0];
if (animObj) {
  var asrIdx = animData.nodes.findIndex(function(n) { return n.name === 'ASR'; });
  console.log('ASR node index:', asrIdx);

  animObj.channels.forEach(function(ch) {
    if (ch.target.node !== asrIdx) return;
    if (ch.target.path !== 'translation') return;

    var sampler = animObj.samplers[ch.sampler];
    var outputAcc = animData.accessors[sampler.output];
    var bv = animData.bufferViews[outputAcc.bufferView];
    var offset = anim.binStart + (bv.byteOffset || 0) + (outputAcc.byteOffset || 0);
    var count = outputAcc.count;

    var minY = Infinity, maxY = -Infinity;
    var minX = Infinity, maxX = -Infinity;
    var minZ = Infinity, maxZ = -Infinity;
    for (var i = 0; i < count; i++) {
      var x = anim.buf.readFloatLE(offset + i * 12 + 0);
      var y = anim.buf.readFloatLE(offset + i * 12 + 4);
      var z = anim.buf.readFloatLE(offset + i * 12 + 8);
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (y < minY) minY = y; if (y > maxY) maxY = y;
      if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
    }
    console.log('ASR.translation X: min=' + minX.toFixed(2) + ' max=' + maxX.toFixed(2));
    console.log('ASR.translation Y: min=' + minY.toFixed(2) + ' max=' + maxY.toFixed(2));
    console.log('ASR.translation Z: min=' + minZ.toFixed(2) + ' max=' + maxZ.toFixed(2));
    console.log('frames:', count);
  });
}

// Check the scene root transforms
console.log('\n=== Scene root transforms ===');
var modelHasParent = {};
model.json.nodes.forEach(function(n) { (n.children || []).forEach(function(c) { modelHasParent[c] = true; }); });
console.log('MODEL scene roots:');
model.json.nodes.forEach(function(n, i) {
  if (!modelHasParent[i]) console.log('  ' + i + ' "' + n.name + '" t=' + JSON.stringify(n.translation) + ' r=' + JSON.stringify(n.rotation) + ' s=' + JSON.stringify(n.scale));
});

var animHasParent = {};
anim.json.nodes.forEach(function(n) { (n.children || []).forEach(function(c) { animHasParent[c] = true; }); });
console.log('ANIM scene roots:');
anim.json.nodes.forEach(function(n, i) {
  if (!animHasParent[i]) console.log('  ' + i + ' "' + n.name + '" t=' + JSON.stringify(n.translation) + ' r=' + JSON.stringify(n.rotation) + ' s=' + JSON.stringify(n.scale));
});
