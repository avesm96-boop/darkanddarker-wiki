const fs = require('fs');
const buf = fs.readFileSync('website/public/monster-models/ancient-stingray.glb');
const jsonLen = buf.readUInt32LE(12);
const j = JSON.parse(buf.slice(20, 20 + jsonLen));

const hasParent = {};
(j.nodes || []).forEach(function(n) {
  (n.children || []).forEach(function(c) { hasParent[c] = true; });
});

console.log('=== ROOT NODES ===');
(j.nodes || []).forEach(function(n, i) {
  if (!hasParent[i]) {
    console.log(' ', i, n.name, 't=' + JSON.stringify(n.translation), 'children=' + (n.children || []).length);
  }
});

const rootIdx = (j.nodes || []).findIndex(function(n, i) { return !hasParent[i]; });
if (rootIdx >= 0) {
  const rootNode = j.nodes[rootIdx];
  console.log('\n=== CHILDREN OF ROOT ===');
  (rootNode.children || []).slice(0, 8).forEach(function(ci) {
    const c = j.nodes[ci];
    console.log(' ', ci, c.name, 't=' + JSON.stringify(c.translation), 'children=' + (c.children || []).length);
  });
}

if (j.skins && j.skins[0]) {
  const joints = j.skins[0].joints;
  console.log('\n=== SKIN JOINTS (first 6) ===');
  joints.slice(0, 6).forEach(function(ji) { console.log(' ', ji, j.nodes[ji].name); });
  console.log('Total joints:', joints.length);
}
