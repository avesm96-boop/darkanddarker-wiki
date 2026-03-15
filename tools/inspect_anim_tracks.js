const fs = require('fs');
['idle-combat', 'rush', 'tail-attack-r'].forEach(function(name) {
  const p = 'website/public/monster-models/animations/ancient-stingray/' + name + '.glb';
  if (!fs.existsSync(p)) { console.log(name + ': NOT FOUND'); return; }
  const buf = fs.readFileSync(p);
  const jsonLen = buf.readUInt32LE(12);
  const j = JSON.parse(buf.slice(20, 20 + jsonLen).toString('utf8'));
  console.log('\n=== ' + name + ' ===');
  const anim = (j.animations || [])[0];
  if (!anim) { console.log('No animation'); return; }

  // Find scene root nodes (no parent)
  var hasParent = {};
  j.nodes.forEach(function(n) { (n.children || []).forEach(function(c) { hasParent[c] = true; }); });
  console.log('Scene roots:');
  j.nodes.forEach(function(n, i) {
    if (!hasParent[i]) console.log('  node ' + i + ' "' + n.name + '" t=' + JSON.stringify(n.translation) + ' r=' + JSON.stringify(n.rotation) + ' s=' + JSON.stringify(n.scale) + ' children=' + (n.children||[]).length);
  });

  // Check which nodes are animated
  var nodeChannels = {};
  anim.channels.forEach(function(ch) {
    var node = j.nodes[ch.target.node];
    var nm = node ? node.name : '?';
    if (!nodeChannels[nm]) nodeChannels[nm] = { idx: ch.target.node, paths: [] };
    nodeChannels[nm].paths.push(ch.target.path);
  });

  // Show all animated nodes that have translation tracks
  console.log('Animated nodes with translation:');
  Object.keys(nodeChannels).forEach(function(nm) {
    var info = nodeChannels[nm];
    if (info.paths.indexOf('translation') >= 0) {
      var isSceneRoot = !hasParent[info.idx];
      console.log('  ' + (isSceneRoot ? '>>> SCENE ROOT <<< ' : '') + nm + ' (node ' + info.idx + '): ' + info.paths.join(', '));
    }
  });

  // Count total
  console.log('Total animated nodes: ' + Object.keys(nodeChannels).length);
});
