"""
Decompile DCAttributeModMagnitudeCalculation* functions from DungeonCrawler.exe
to find the exact Action Speed formula (and all other stat contribution formulas).

Strategy:
1. Parse PE sections to map file offsets <-> virtual addresses
2. Find all class name strings (UTF-16) in .rdata
3. Find cross-references to those strings from .text (via LEA or MOV with RIP-relative)
4. From xrefs, find the StaticClass() functions
5. From StaticClass(), find the CDO and vtable
6. Disassemble CalculateBaseMagnitude_Implementation
"""

import struct
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

EXE_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Dark and Darker\DungeonCrawler\Binaries\Win64\DungeonCrawler.exe"

# ── PE Section Parsing ──────────────────────────────────────────────────

def parse_pe(data):
    """Parse PE headers and return section info."""
    pe_offset = struct.unpack_from('<I', data, 0x3C)[0]
    num_sections = struct.unpack_from('<H', data, pe_offset + 6)[0]
    opt_header_size = struct.unpack_from('<H', data, pe_offset + 20)[0]
    image_base = struct.unpack_from('<Q', data, pe_offset + 24 + 24)[0]

    section_offset = pe_offset + 24 + opt_header_size
    sections = []
    for i in range(num_sections):
        off = section_offset + i * 40
        name = data[off:off+8].rstrip(b'\x00').decode('ascii', errors='ignore')
        virt_size = struct.unpack_from('<I', data, off + 8)[0]
        virt_addr = struct.unpack_from('<I', data, off + 12)[0]
        raw_size = struct.unpack_from('<I', data, off + 16)[0]
        raw_offset = struct.unpack_from('<I', data, off + 20)[0]
        chars = struct.unpack_from('<I', data, off + 36)[0]
        sections.append({
            'name': name, 'va': virt_addr, 'vs': virt_size,
            'ro': raw_offset, 'rs': raw_size, 'chars': chars,
            'executable': bool(chars & 0x20000000),
        })
    return image_base, sections


def file_to_va(sections, image_base, file_offset):
    """Convert file offset to virtual address."""
    for s in sections:
        if s['ro'] <= file_offset < s['ro'] + s['rs']:
            return image_base + s['va'] + (file_offset - s['ro'])
    return None


def va_to_file(sections, image_base, va):
    """Convert virtual address to file offset."""
    rva = va - image_base
    for s in sections:
        if s['va'] <= rva < s['va'] + s['vs']:
            return s['ro'] + (rva - s['va'])
    return None


# ── String and XREF Finding ────────────────────────────────────────────

def find_utf16_strings(data, prefix):
    """Find all UTF-16LE strings starting with prefix."""
    needle = prefix.encode('utf-16-le')
    results = []
    pos = 0
    while True:
        pos = data.find(needle, pos)
        if pos < 0:
            break
        # Read until null terminator
        end = pos
        while end < len(data) - 1:
            if data[end:end+2] == b'\x00\x00':
                break
            end += 2
        name = data[pos:end].decode('utf-16-le', errors='ignore')
        results.append((pos, name))
        pos = end + 2
    return results


def find_xrefs_to_va(data, sections, image_base, target_va):
    """Find all RIP-relative LEA/MOV instructions that reference target_va."""
    xrefs = []
    for s in sections:
        if not s['executable']:
            continue
        start = s['ro']
        end = start + s['rs']

        for i in range(start, min(end, len(data) - 7)):
            # LEA with REX.W: 48 8D [modrm] [disp32] or 4C 8D [modrm] [disp32]
            if data[i] in (0x48, 0x4C) and data[i+1] == 0x8D:
                modrm = data[i+2]
                # RIP-relative: mod=00, r/m=101 -> modrm & 0xC7 == 0x05
                if (modrm & 0xC7) == 0x05:
                    disp = struct.unpack('<i', data[i+3:i+7])[0]
                    instr_va = file_to_va(sections, image_base, i)
                    if instr_va is None:
                        continue
                    ref_va = instr_va + 7 + disp
                    if ref_va == target_va:
                        xrefs.append(('LEA', i, instr_va))

            # MOV reg, [rip+disp32]: 48 8B [modrm] [disp32]
            if data[i] in (0x48, 0x4C) and data[i+1] == 0x8B:
                modrm = data[i+2]
                if (modrm & 0xC7) == 0x05:
                    disp = struct.unpack('<i', data[i+3:i+7])[0]
                    instr_va = file_to_va(sections, image_base, i)
                    if instr_va is None:
                        continue
                    ref_va = instr_va + 7 + disp
                    if ref_va == target_va:
                        xrefs.append(('MOV', i, instr_va))

            # Also check for CALL [rip+disp32]: FF 15 [disp32]
            if data[i] == 0xFF and data[i+1] == 0x15:
                disp = struct.unpack('<i', data[i+2:i+6])[0]
                instr_va = file_to_va(sections, image_base, i)
                if instr_va is None:
                    continue
                ref_va = instr_va + 6 + disp
                if ref_va == target_va:
                    xrefs.append(('CALL_IND', i, instr_va))

    return xrefs


def find_xrefs_to_va_range(data, sections, image_base, target_va_start, target_va_end):
    """Find RIP-relative instructions referencing any VA in the given range."""
    xrefs = []
    for s in sections:
        if not s['executable']:
            continue
        start = s['ro']
        end = start + s['rs']

        for i in range(start, min(end, len(data) - 7)):
            if data[i] in (0x48, 0x4C) and data[i+1] in (0x8D, 0x8B):
                modrm = data[i+2]
                if (modrm & 0xC7) == 0x05:
                    disp = struct.unpack('<i', data[i+3:i+7])[0]
                    instr_va = file_to_va(sections, image_base, i)
                    if instr_va is None:
                        continue
                    ref_va = instr_va + 7 + disp
                    if target_va_start <= ref_va < target_va_end:
                        xrefs.append((i, instr_va, ref_va))

    return xrefs


# ── Disassembly ─────────────────────────────────────────────────────────

def disassemble_function(data, sections, image_base, start_file_offset, max_bytes=2048):
    """Disassemble from a given file offset, return instruction list."""
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True

    start_va = file_to_va(sections, image_base, start_file_offset)
    code = data[start_file_offset:start_file_offset + max_bytes]

    instructions = []
    for insn in md.disasm(code, start_va):
        instructions.append(insn)
        # Stop at RET
        if insn.mnemonic == 'ret':
            break
        # Stop at INT3 (padding between functions)
        if insn.mnemonic == 'int3':
            break

    return instructions


def format_disasm(instructions, data, sections, image_base, max_lines=100):
    """Format disassembly with annotations for floats and strings."""
    lines = []
    for i, insn in enumerate(instructions[:max_lines]):
        line = f"  {insn.address:016x}: {insn.mnemonic:8s} {insn.op_str}"

        # Annotate RIP-relative references
        if 'rip' in insn.op_str:
            # Extract displacement
            # The actual target depends on the instruction encoding
            match = re.search(r'\[rip ([+-] 0x[0-9a-f]+)\]', insn.op_str)
            if match:
                disp_str = match.group(1).replace(' ', '')
                disp = int(disp_str, 16)
                target_va = insn.address + insn.size + disp
                target_file = va_to_file(sections, image_base, target_va)
                if target_file is not None and target_file + 4 <= len(data):
                    # Try as float
                    fval = struct.unpack('<f', data[target_file:target_file+4])[0]
                    if abs(fval) < 10000 and fval == fval and fval != 0:
                        line += f"  ; float = {fval:.6f}"
                    # Try as pointer
                    if target_file + 8 <= len(data):
                        ptr = struct.unpack('<Q', data[target_file:target_file+8])[0]
                        ptr_file = va_to_file(sections, image_base, ptr)
                        if ptr_file is not None:
                            line += f"  ; -> VA {ptr:#018x}"
                    # Try as int32
                    ival = struct.unpack('<I', data[target_file:target_file+4])[0]
                    if 0 < ival < 1000:
                        line += f"  ; int32 = {ival}"

        lines.append(line)
    return '\n'.join(lines)


# ── Main ────────────────────────────────────────────────────────────────

def main():
    print("Loading DungeonCrawler.exe...")
    with open(EXE_PATH, 'rb') as f:
        data = f.read()
    print(f"  Size: {len(data):,} bytes")

    image_base, sections = parse_pe(data)
    print(f"  Image base: {image_base:#x}")
    print(f"  Sections: {len(sections)}")
    for s in sections:
        flag = 'X' if s['executable'] else ' '
        print(f"    [{flag}] {s['name']:10s} VA={s['va']:#010x} Size={s['vs']:#010x} FileOff={s['ro']:#010x}")

    # Find all DCAttributeModMagnitudeCalculation class name strings
    print("\nFinding class name strings (UTF-16)...")
    class_strings = find_utf16_strings(data, 'DCAttributeModMagnitudeCalculation')
    # Deduplicate by name
    seen = set()
    unique_classes = []
    for offset, name in class_strings:
        if name not in seen:
            seen.add(name)
            unique_classes.append((offset, name))

    print(f"  Found {len(unique_classes)} unique class names:")
    for offset, name in unique_classes:
        va = file_to_va(sections, image_base, offset)
        print(f"    {name} @ file {offset:#x} (VA {va:#x})")

    # For each class, find cross-references
    print("\nSearching for cross-references (this may take a while)...")
    for offset, name in unique_classes:
        va = file_to_va(sections, image_base, offset)
        if va is None:
            continue

        # Search a small range around the string for xrefs
        # (checking all executable sections)
        xrefs = find_xrefs_to_va(data, sections, image_base, va)

        if xrefs:
            print(f"\n{'='*80}")
            print(f"CLASS: {name}")
            print(f"String VA: {va:#x}")
            print(f"Cross-references: {len(xrefs)}")
            for xref_type, file_off, xref_va in xrefs:
                print(f"  {xref_type} @ VA {xref_va:#x} (file {file_off:#x})")

                # Disassemble from 64 bytes before the xref to capture function start
                func_start = file_off - 64
                # Look for function prologue (push rbp; sub rsp, XX or similar)
                # Scan backwards for INT3 padding or push rbp
                for j in range(file_off - 1, max(file_off - 256, 0), -1):
                    if data[j] == 0xCC:  # INT3
                        func_start = j + 1
                        break
                    if data[j] == 0x55 and j > 0 and data[j-1] == 0xCC:  # push rbp after int3
                        func_start = j
                        break

                print(f"\n  Disassembly from {func_start:#x}:")
                instrs = disassemble_function(data, sections, image_base, func_start, max_bytes=4096)
                print(format_disasm(instrs, data, sections, image_base, max_lines=200))
        else:
            print(f"  {name}: no xrefs found")


if __name__ == '__main__':
    main()
