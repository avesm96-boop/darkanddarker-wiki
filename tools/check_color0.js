const fs = require('fs');
const buf = fs.readFileSync('website/public/monster-models/ancient-stingray.glb');
const jsonLen = buf.readUInt32LE(12);
const j = JSON.parse(buf.slice(20, 20 + jsonLen).toString('utf8'));
(j.meshes || []).forEach(function(m, mi) {
  (m.primitives || []).forEach(function(p, pi) {
    var attrs = Object.keys(p.attributes);
    var hasColor = attrs.some(function(a) { return a.startsWith('COLOR'); });
    console.log('mesh ' + mi + ' prim ' + pi + ': ' + attrs.join(', ') + (hasColor ? ' ** HAS COLOR **' : ''));
  });
});
