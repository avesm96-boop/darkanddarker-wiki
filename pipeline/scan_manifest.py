"""Scan all exported JSON files and categorize by UE type."""

import json
import os
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "raw"
EXTRACTED_DIR = Path(__file__).resolve().parent.parent / "extracted"

UE_TYPES = {
    "DataTable": "DataTable",
    "BlueprintGeneratedClass": "BlueprintGeneratedClass",
    "Blueprint": "BlueprintGeneratedClass",
    "UserDefinedEnum": "UserDefinedEnum",
    "Enum": "UserDefinedEnum",
    "CurveTable": "CurveTable",
    "SoundCue": "SoundCue",
    "StaticMesh": "StaticMesh",
    "SkeletalMesh": "SkeletalMesh",
    "ParticleSystem": "ParticleSystem",
    "AnimBlueprint": "AnimBlueprint",
    "AnimSequence": "AnimSequence",
    "Material": "Material",
    "MaterialFunction": "MaterialFunction",
    "Texture2D": "Texture2D",
    "ShaderArchive": "ShaderArchive",
}

CATEGORY_KEYWORDS = {
    "DataTable": ["rows", "table_type", "asset"],
    "Blueprint": ["properties", "generated_class"],
    "Enum": ["enums", "enum_values"],
    "Material": ["material", "shader"],
    "Mesh": ["vertices", "skeletal"],
}


def detect_ue_type(data: dict) -> str:
    """Detect UE type from JSON structure."""
    if not isinstance(data, dict):
        return "Unknown"

    # Check for Type field
    if "Type" in data:
        ue_type = data.get("Type", "").split("::")[-1]
        if ue_type in UE_TYPES:
            return UE_TYPES[ue_type]

    # Check for ClassName field
    if "ClassName" in data:
        class_name = data.get("ClassName", "").split("::")[-1]
        if class_name in UE_TYPES:
            return UE_TYPES[class_name]

    # Heuristic: check structure
    keys = set(data.keys())
    if "Rows" in keys or "rows" in keys:
        return "DataTable"
    if "EnumValues" in keys or "enum_values" in keys:
        return "UserDefinedEnum"
    if "Curves" in keys or "curves" in keys:
        return "CurveTable"
    if "Properties" in keys or "properties" in keys:
        return "BlueprintGeneratedClass"

    return "Unknown"


def main():
    manifest = []

    for json_file in sorted(RAW_DIR.rglob("*.json")):
        try:
            size_kb = json_file.stat().st_size / 1024
            rel_path = json_file.relative_to(RAW_DIR)

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            ue_type = detect_ue_type(data)

            manifest.append(
                {
                    "path": str(rel_path).replace("\\", "/"),
                    "type": ue_type,
                    "size_kb": round(size_kb, 2),
                }
            )
        except Exception as e:
            manifest.append(
                {
                    "path": str(json_file.relative_to(RAW_DIR)).replace("\\", "/"),
                    "type": "Error",
                    "size_kb": 0,
                    "error": str(e),
                }
            )

    # Write manifest
    out_file = EXTRACTED_DIR / "manifest.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    summary = {}
    for entry in manifest:
        t = entry["type"]
        summary[t] = summary.get(t, 0) + 1

    output = {
        "total_files": len(manifest),
        "summary": summary,
        "files": manifest,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Manifest written to {out_file}")
    print(f"\nSummary:")
    for cat, count in sorted(summary.items(), key=lambda x: -x[1]):
        print(f"  {cat:30} {count:4} files")


if __name__ == "__main__":
    main()
