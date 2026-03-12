#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const RAW_DIR = path.join(__dirname, "..", "raw");
const EXTRACTED_DIR = path.join(__dirname, "..", "extracted");

function detectUeType(data) {
  // Handle arrays (FModel exports as arrays)
  if (Array.isArray(data) && data.length > 0) {
    return detectUeType(data[0]);
  }

  if (typeof data !== "object" || data === null) return "Unknown";

  // Check Type field
  if (data.Type) {
    const type = String(data.Type).trim();

    // Map common FModel types
    const typeMap = {
      DataTable: "DataTable",
      PrimaryAssetLabel: "PrimaryAssetLabel",
      UserDefinedEnum: "UserDefinedEnum",
      CurveTable: "CurveTable",
      Blueprint: "BlueprintGeneratedClass",
      BlueprintGeneratedClass: "BlueprintGeneratedClass",
      ArtData: "ArtDataAsset",
      ArtDataItem: "ArtDataAsset",
      ArtDataAccessory: "ArtDataAsset",
      ArtDataArmor: "ArtDataAsset",
      ArtDataWeapon: "ArtDataAsset",
      ArtDataMonster: "ArtDataAsset",
      ArtDataCharacter: "ArtDataAsset",
      Material: "Material",
      Texture2D: "Texture",
      StaticMesh: "StaticMesh",
      SkeletalMesh: "SkeletalMesh",
      AnimSequence: "AnimSequence",
    };

    if (typeMap[type]) return typeMap[type];
    return type;
  }

  // Fallback: check ClassName
  if (data.ClassName) {
    const className = String(data.ClassName).split("::").pop();
    if (className.includes("DataTable")) return "DataTable";
    if (className.includes("Blueprint")) return "BlueprintGeneratedClass";
  }

  return "Unknown";
}

function scanDir(dir) {
  const manifest = [];

  function walkDir(currentDir) {
    const files = fs.readdirSync(currentDir, { withFileTypes: true });

    for (const file of files) {
      const fullPath = path.join(currentDir, file.name);

      if (file.isDirectory()) {
        walkDir(fullPath);
      } else if (file.name.endsWith(".json")) {
        try {
          const relPath = path.relative(RAW_DIR, fullPath);
          const sizeKb = (fs.statSync(fullPath).size / 1024).toFixed(2);

          const content = fs.readFileSync(fullPath, "utf-8");
          const data = JSON.parse(content);

          const type = detectUeType(data);

          manifest.push({
            path: relPath.replace(/\\/g, "/"),
            type,
            size_kb: parseFloat(sizeKb),
          });
        } catch (e) {
          manifest.push({
            path: path.relative(RAW_DIR, fullPath).replace(/\\/g, "/"),
            type: "Error",
            size_kb: 0,
            error: e.message,
          });
        }
      }
    }
  }

  walkDir(dir);
  return manifest;
}

function main() {
  console.log(`Scanning ${RAW_DIR}...`);

  const manifest = scanDir(RAW_DIR);

  const summary = {};
  for (const entry of manifest) {
    summary[entry.type] = (summary[entry.type] || 0) + 1;
  }

  const output = {
    total_files: manifest.length,
    summary,
    files: manifest,
  };

  const outFile = path.join(EXTRACTED_DIR, "manifest.json");
  fs.mkdirSync(EXTRACTED_DIR, { recursive: true });
  fs.writeFileSync(outFile, JSON.stringify(output, null, 2));

  console.log(`\nManifest written to ${outFile}\n`);
  console.log("Summary:");
  Object.entries(summary)
    .sort((a, b) => b[1] - a[1])
    .forEach(([type, count]) => {
      console.log(`  ${type.padEnd(30)} ${String(count).padStart(4)} files`);
    });
}

main();
