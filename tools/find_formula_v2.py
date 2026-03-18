"""
Find ActionSpeed formula by searching all executable code for SSE float
instructions that reference weight constants (0.25, 0.75, etc.) via
RIP-relative addressing, then disassemble the surrounding function.
"""

import struct
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

EXE_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Dark and Darker\DungeonCrawler\Binaries\Win64\DungeonCrawler.exe"


def parse_pe(data):
    pe_offset = struct.unpack_from('<I', data, 0x3C)[0]
    num_sections = struct.unpack_from('<H', data, pe_offset + 6)[0]
    opt_header_size = struct.unpack_from('<H', data, pe_offset + 20)[0]
    image_base = struct.unpack_from('<Q', data, pe_offset + 24 + 24)[0]
    section_offset = pe_offset + 24 + opt_header_size
    sections = []
    for i in range(num_sections):
        off = section_offset + i * 40
        name = data[off:off+8].rstrip(b'\x00').decode('ascii', errors='ignore')
        sections.append({
            'name': name,
            'va': struct.unpack_from('<I', data, off + 12)[0],
            'vs': struct.unpack_from('<I', data, off + 8)[0],
            'ro': struct.unpack_from('<I', data, off + 20)[0],
            'rs': struct.unpack_from('<I', data, off + 16)[0],
            'executable': bool(struct.unpack_from('<I', data, off + 36)[0] & 0x20000000),
        })
    return image_base, sections


def rva_to_file(sections, rva):
    for s in sections:
        if s['va'] <= rva < s['va'] + s['vs']:
            return s['ro'] + (rva - s['va'])
    return None


def main():
    print("Loading exe...")
    with open(EXE_PATH, 'rb') as f:
        data = f.read()
    image_base, sections = parse_pe(data)
    print(f"  Size: {len(data):,}, Image base: {image_base:#x}")

    # Step 1: Find all aligned float constants in .rdata
    rdata = next(s for s in sections if s['name'] == '.rdata')
    print(f"\n.rdata: file {rdata['ro']:#x}, VA {rdata['va']:#x}, size {rdata['rs']:#x}")

    # Build a map: file_offset -> float_value for weight candidates
    weight_map = {}  # file_offset -> float_value
    weight_rvas = {}  # rva -> float_value
    for fval in [0.125, 0.15, 0.2, 0.25, 0.3, 1/3, 0.35, 0.4, 0.45,
                 0.5, 0.55, 0.6, 0.65, 2/3, 0.7, 0.75, 0.8, 0.85, 0.875]:
        fbytes = struct.pack('<f', fval)
        pos = rdata['ro']
        end = rdata['ro'] + rdata['rs']
        while pos < end:
            pos = data.find(fbytes, pos, end)
            if pos < 0:
                break
            if pos % 4 == 0:
                rva = rdata['va'] + (pos - rdata['ro'])
                weight_map[pos] = round(fval, 6)
                weight_rvas[rva] = round(fval, 6)
            pos += 1

    print(f"  {len(weight_map)} weight-candidate float locations")

    # Step 2: Scan all executable sections for mulss/movss with RIP-relative
    # that resolves to one of our weight constants
    print("\nScanning executable sections for float weight references...")

    # SSE scalar float instructions with RIP-relative memory operand:
    # movss xmm, [rip+disp32]: F3 0F 10 [modrm] [disp32]  (modrm & 0xC7 == 0x05)
    # mulss xmm, [rip+disp32]: F3 0F 59 [modrm] [disp32]
    # divss xmm, [rip+disp32]: F3 0F 5E [modrm] [disp32]

    hits = []  # (file_offset, instruction_va, float_value, opcode_type)

    for s in sections:
        if not s['executable']:
            continue
        start = s['ro']
        end = start + s['rs']
        sdata = data[start:end]

        print(f"  Scanning {s['name']} ({s['rs']:,} bytes)...")

        for i in range(len(sdata) - 8):
            # Check for F3 0F [10/59/5E] [modrm with RIP-relative]
            if sdata[i] == 0xF3 and sdata[i+1] == 0x0F and sdata[i+2] in (0x10, 0x59, 0x5E):
                modrm = sdata[i+3]
                if (modrm & 0xC7) == 0x05:
                    # RIP-relative: disp32 at i+4
                    disp = struct.unpack('<i', sdata[i+4:i+8])[0]
                    instr_file = start + i
                    instr_rva = s['va'] + i
                    instr_va = image_base + instr_rva
                    # Target = next instruction VA + displacement
                    # Instruction length = 8 bytes (F3 0F XX modrm disp32)
                    target_rva = instr_rva + 8 + disp
                    target_file = rva_to_file(sections, target_rva)

                    if target_file and target_file in weight_map:
                        fval = weight_map[target_file]
                        op = {0x10: 'movss', 0x59: 'mulss', 0x5E: 'divss'}[sdata[i+2]]
                        hits.append((instr_file, instr_va, fval, op))

    print(f"\n  Total float weight references found: {len(hits)}")

    # Step 3: Group hits by proximity (same function = within ~2KB)
    hits.sort(key=lambda h: h[0])
    groups = []
    current_group = []
    for hit in hits:
        if current_group and hit[0] - current_group[-1][0] > 2048:
            groups.append(current_group)
            current_group = [hit]
        else:
            current_group.append(hit)
    if current_group:
        groups.append(current_group)

    print(f"  {len(groups)} function groups")

    # Step 4: Find groups that have a weight pair (two floats summing to ~1.0)
    # or have interesting weight patterns
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True

    interesting_groups = []
    for group in groups:
        floats = set(round(h[2], 4) for h in group)
        has_pair = False
        for a in floats:
            for b in floats:
                if a != b and abs(a + b - 1.0) < 0.02:
                    has_pair = True
        if has_pair:
            interesting_groups.append(('WEIGHT_PAIR', group, floats))
        elif len(floats) >= 2:
            interesting_groups.append(('MULTI_FLOAT', group, floats))

    # Sort: weight pairs first
    interesting_groups.sort(key=lambda g: (0 if g[0] == 'WEIGHT_PAIR' else 1, -len(g[1])))

    print(f"\n{'='*80}")
    print(f"WEIGHT-PAIR FUNCTIONS (two floats summing to 1.0)")
    print(f"{'='*80}")

    for tag, group, floats in interesting_groups:
        if tag != 'WEIGHT_PAIR':
            continue

        # Find function boundaries (scan for INT3/RET)
        first_file = group[0][0]
        last_file = group[-1][0]

        # Scan backwards for function start
        func_start = first_file
        for j in range(first_file - 1, max(first_file - 512, 0), -1):
            if data[j] == 0xCC:  # INT3 padding
                func_start = j + 1
                break

        # Scan forwards for function end
        func_end = last_file + 64
        for j in range(last_file + 8, min(last_file + 2048, len(data))):
            if data[j] == 0xCC:
                func_end = j
                break
            if data[j] == 0xC3:  # RET
                func_end = j + 1
                break

        func_size = func_end - func_start
        func_rva = None
        for s in sections:
            if s['ro'] <= func_start < s['ro'] + s['rs']:
                func_rva = s['va'] + (func_start - s['ro'])
                break
        func_va = image_base + func_rva if func_rva else 0

        floats_str = ', '.join(f'{f:.4f}' for f in sorted(floats))
        print(f"\n{'-'*80}")
        print(f"Function @ VA {func_va:#x}, size ~{func_size} bytes")
        print(f"  Weight floats: {floats_str}")
        print(f"  Float refs in group:")
        for fo, va, fv, op in group:
            print(f"    {va:#x}: {op} loading {fv}")

        # Disassemble the whole function
        func_code = data[func_start:func_end]
        print(f"\n  Assembly ({func_size} bytes):")
        for insn in md.disasm(func_code, func_va):
            line = f"    {insn.address:#018x}: {insn.mnemonic:10s} {insn.op_str}"

            # Annotate RIP-relative memory accesses
            if 'rip' in insn.op_str:
                match = re.search(r'\[rip ([+-] 0x[0-9a-f]+)\]', insn.op_str)
                if match:
                    disp = int(match.group(1).replace(' ', ''), 16)
                    target_rva = (insn.address - image_base) + insn.size + disp
                    target_file = rva_to_file(sections, target_rva)
                    if target_file and target_file + 8 <= len(data):
                        fval = struct.unpack('<f', data[target_file:target_file+4])[0]
                        dval = struct.unpack('<d', data[target_file:target_file+8])[0]
                        if abs(fval) < 100000 and fval == fval:
                            line += f"  ; float={fval}"
                        # Also show if it's a pointer
                        ptr = struct.unpack('<Q', data[target_file:target_file+8])[0]
                        if image_base <= ptr < image_base + 0x10000000:
                            line += f"  ; ptr->VA {ptr:#x}"
            print(line)
        print()

    # Also print multi-float groups
    print(f"\n{'='*80}")
    print(f"MULTI-FLOAT FUNCTIONS (2+ different weight constants, no pair summing to 1.0)")
    print(f"{'='*80}")
    count = 0
    for tag, group, floats in interesting_groups:
        if tag != 'MULTI_FLOAT':
            continue
        count += 1
        if count > 10:
            print(f"  ... and {sum(1 for t,_,_ in interesting_groups if t=='MULTI_FLOAT') - 10} more")
            break
        floats_str = ', '.join(f'{f:.4f}' for f in sorted(floats))
        first_va = group[0][1]
        print(f"  VA {first_va:#x}: floats = {floats_str}")


if __name__ == '__main__':
    main()
