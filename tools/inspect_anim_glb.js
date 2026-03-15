const fs = require('fs');
const glbBuf = fs.readFileSync('website/public/monster-models/animations/ancient-stingray/idle-combat.glb');
const jsonLen = glbBuf.readUInt32LE(12);
const j = JSON.parse(glbBuf.slice(20, 20 + jsonLen));

console.log('=== NODES (first 12) ===');
(j.nodes || []).slice(0, 12).forEach(function(n, i) {
  console.log(i, JSON.stringify({ name: n.name, translation: n.translation, children: (n.children || []).length }));
});

console.log('\n=== ROOT NODES (no parent) ===');
var hasParent = {};
(j.nodes || []).forEach(function(n) {
  (n.children || []).forEach(function(c) { hasParent[c] = true; });
});
(j.nodes || []).forEach(function(n, i) {
  if (!hasParent[i]) console.log('root node', i, n.name, 'translation=' + JSON.stringify(n.translation));
});

console.log('\n=== ANIMATION CHANNELS (first 20) ===');
(j.animations || []).forEach(function(a, ai) {
  console.log('anim[' + ai + '] name=' + a.name + ' channels=' + a.channels.length);
  var summary = {};
  a.channels.forEach(function(ch) {
    var node = j.nodes[ch.target.node];
    var prop = ch.target.path;
    if (!summary[prop]) summary[prop] = [];
    summary[prop].push(node ? node.name : '?');
  });
  Object.keys(summary).forEach(function(prop) {
    var nodes = summary[prop];
    console.log('  ' + prop + ' (' + nodes.length + ' bones): ' + nodes.slice(0, 4).join(', ') + (nodes.length > 4 ? ' ...' : ''));
  });
});

console.log('\n=== SCENES ===');
(j.scenes || []).forEach(function(s, i) {
  console.log('scene', i, 'nodes:', s.nodes);
});
