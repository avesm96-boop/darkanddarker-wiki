# FModel Export Automation — Research

## Goal
Investigate whether game data extraction can be automated for fully automated patch-day rebuilds.

## Option 1: FModel CLI Mode
FModel is a GUI application (WPF/.NET). No official CLI mode as of 2026. Some community forks exist but are unreliable.
**Verdict:** Not viable.

## Option 2: CUE4Parse Library
CUE4Parse (github.com/FabianFG/CUE4Parse) is the C#/.NET library FModel uses internally.
- Programmatic .pak reading, asset deserialization, JSON export
- Actively maintained (same author as FModel)
- Would require a small C# console app
**Verdict:** Most promising. ~1-2 days implementation.

## Option 3: UE4SS / UnrealPak
- UE4SS: Runtime mod framework, not for offline extraction
- UnrealPak: Extracts raw assets but not JSON
**Verdict:** Not suitable for JSON pipeline.

## Option 4: Python Libraries
- unrealpak, UE4Parse — limited compared to CUE4Parse
**Verdict:** May work for simple cases but incomplete.

## Recommendation
Use CUE4Parse via .NET console app. Next steps:
1. Set up .NET 8 SDK
2. Create tools/export_game_data/ C# project
3. Implement asset export for required content paths
4. Integrate into scripts/build.sh as optional Phase -1
