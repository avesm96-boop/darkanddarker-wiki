const fs = require('fs');
function readGlb(path) {
  const buf = fs.readFileSync(path);
  const jsonLen = buf.readUInt32LE(12);
  return JSON.parse(buf.slice(20, 20 + jsonLen).toString('utf8'));
}
var raw = readGlb('website/public/monster-models/animations/ancient-stingray-raw.glb');
var anim = readGlb('website/public/monster-models/animations/ancient-stingray/idle-combat.glb');
var old = readGlb('website/public/monster-models/ancient-stingray.glb');

var bones = ['root', 'ASR', 'Upper', 'Lower', 'head'];
bones.forEach(function(name) {
  var r = null, a = null, o = null;
  raw.nodes.forEach(function(n) { if (n.name === name) r = n; });
  anim.nodes.forEach(function(n) { if (n.name === name) a = n; });
  old.nodes.forEach(function(n) { if (n.name === name) o = n; });
  console.log('"' + name + '":');
  console.log('  RAW MODEL: t=' + JSON.stringify(r && r.translation) + ' r=' + JSON.stringify(r && r.rotation));
  console.log('  ANIM:      t=' + JSON.stringify(a && a.translation) + ' r=' + JSON.stringify(a && a.rotation));
  console.log('  OLD MODEL: t=' + JSON.stringify(o && o.translation) + ' r=' + JSON.stringify(o && o.rotation));
});
