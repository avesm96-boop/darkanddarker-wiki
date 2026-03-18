"""
Find ALL DCAttributeModMagnitudeCalculation functions by scanning the
neighborhood of the known ActionSpeed function (VA 0x14565ea80).

C++ methods from the same class hierarchy are compiled near each other.
We scan +/- 100KB around ActionSpeed and disassemble every function,
looking for the same structural pattern.
"""

import struct
import re
import json
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

EXE_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Dark and Darker\DungeonCrawler\Binaries\Win64\DungeonCrawler.exe"

# Known function
ACTION_SPEED_VA = 0x14565ea80
ACTION_SPEED_SIZE = 283


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


def va_to_file(sections, image_base, va):
    return rva_to_file(sections, va - image_base)


def find_functions_by_int3(data, start_file, end_file):
    """Find function boundaries by scanning for INT3 (0xCC) padding."""
    functions = []
    i = start_file
    while i < end_file:
        # Skip INT3 padding
        while i < end_file and data[i] == 0xCC:
            i += 1
        if i >= end_file:
            break
        # Start of a function
        func_start = i
        # Find end (next INT3 or end of region)
        while i < end_file and data[i] != 0xCC:
            i += 1
        func_end = i
        func_size = func_end - func_start
        if func_size >= 16:  # Skip tiny fragments
            functions.append((func_start, func_size))
    return functions


def analyze_function(data, sections, image_base, md, file_offset, size):
    """Disassemble and analyze a function."""
    va = image_base
    for s in sections:
        if s['ro'] <= file_offset < s['ro'] + s['rs']:
            va = image_base + s['va'] + (file_offset - s['ro'])
            break

    code = data[file_offset:file_offset + size]
    instructions = list(md.disasm(code, va))

    float_constants = []
    call_targets = []
    has_mulss = False
    has_addss = False
    has_divss = False
    has_subss = False
    member_offsets = set()
    attr_read_pattern_count = 0

    for insn in instructions:
        if insn.mnemonic in ('mulss', 'mulsd'):
            has_mulss = True
        if insn.mnemonic in ('addss', 'addsd'):
            has_addss = True
        if insn.mnemonic in ('divss', 'divsd'):
            has_divss = True
        if insn.mnemonic in ('subss', 'subsd'):
            has_subss = True
        if insn.mnemonic == 'call':
            # Extract call target
            if insn.op_str.startswith('0x'):
                try:
                    call_targets.append(int(insn.op_str, 16))
                except ValueError:
                    pass
        if insn.mnemonic == 'ret':
            break

        # Extract RIP-relative float constants
        if 'rip' in insn.op_str and insn.mnemonic in (
            'movss', 'mulss', 'divss', 'addss', 'subss', 'comiss', 'ucomiss',
            'movsd', 'mulsd', 'divsd', 'addsd', 'subsd',
        ):
            match = re.search(r'\[rip ([+-] 0x[0-9a-f]+)\]', insn.op_str)
            if match:
                disp = int(match.group(1).replace(' ', ''), 16)
                target_rva = (insn.address - image_base) + insn.size + disp
                target_file = rva_to_file(sections, target_rva)
                if target_file and target_file + 4 <= len(data):
                    fval = struct.unpack('<f', data[target_file:target_file+4])[0]
                    if abs(fval) < 100000 and fval == fval:
                        float_constants.append((insn.address, insn.mnemonic, round(fval, 6)))

    return {
        'va': va,
        'file_offset': file_offset,
        'size': size,
        'instructions': instructions,
        'float_constants': float_constants,
        'call_targets': call_targets,
        'has_mulss': has_mulss,
        'has_addss': has_addss,
        'has_divss': has_divss,
        'has_subss': has_subss,
        'unique_floats': sorted(set(f[2] for f in float_constants)),
        'num_calls': len(call_targets),
    }


def format_function(func, data, sections, image_base):
    """Format function disassembly with annotations."""
    lines = []
    for insn in func['instructions']:
        line = f"    {insn.address:#018x}: {insn.mnemonic:10s} {insn.op_str}"

        if 'rip' in insn.op_str:
            match = re.search(r'\[rip ([+-] 0x[0-9a-f]+)\]', insn.op_str)
            if match:
                disp = int(match.group(1).replace(' ', ''), 16)
                target_rva = (insn.address - image_base) + insn.size + disp
                target_file = rva_to_file(sections, target_rva)
                if target_file and target_file + 4 <= len(data):
                    fval = struct.unpack('<f', data[target_file:target_file+4])[0]
                    if abs(fval) < 100000 and fval == fval and fval != 0:
                        line += f"  ; float={fval}"

        if insn.mnemonic == 'ret':
            lines.append(line)
            break
        lines.append(line)

    return '\n'.join(lines)


def main():
    print("Loading exe...")
    with open(EXE_PATH, 'rb') as f:
        data = f.read()
    image_base, sections = parse_pe(data)

    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True

    # Find the ActionSpeed function's file offset
    as_file = va_to_file(sections, image_base, ACTION_SPEED_VA)
    print(f"ActionSpeed function: VA {ACTION_SPEED_VA:#x}, file {as_file:#x}")

    # Extract call targets from ActionSpeed to use as fingerprint
    as_func = analyze_function(data, sections, image_base, md, as_file, ACTION_SPEED_SIZE)
    as_calls = as_func['call_targets']
    print(f"  ActionSpeed calls: {[hex(c) for c in as_calls]}")
    print(f"  ActionSpeed floats: {as_func['unique_floats']}")

    # Scan neighborhood: +/- 100KB
    scan_start = as_file - 100_000
    scan_end = as_file + 100_000
    scan_start = max(scan_start, 0)
    scan_end = min(scan_end, len(data))

    print(f"\nScanning neighborhood: file {scan_start:#x} to {scan_end:#x} ({(scan_end-scan_start)//1024}KB)")

    funcs_raw = find_functions_by_int3(data, scan_start, scan_end)
    print(f"  Found {len(funcs_raw)} functions by INT3 boundaries")

    # Analyze all functions
    all_funcs = []
    for fo, size in funcs_raw:
        func = analyze_function(data, sections, image_base, md, fo, min(size, 4096))
        all_funcs.append(func)

    # Find functions with same call signature as ActionSpeed
    # ActionSpeed calls: helper1(capture attr spec), helper2(capture attr spec),
    # init helper, get_magnitude helper x2, cleanup
    # Key pattern: calls to the same helper functions
    as_call_set = set(as_calls)

    # Find functions that share call targets with ActionSpeed
    similar_funcs = []
    for func in all_funcs:
        if func['va'] == ACTION_SPEED_VA:
            func['label'] = 'ActionSpeed (KNOWN: 0.25*AGI + 0.75*DEX)'
            similar_funcs.append(func)
            continue

        shared_calls = set(func['call_targets']) & as_call_set
        # Functions sharing 2+ call targets are likely siblings
        if len(shared_calls) >= 2:
            func['shared_calls'] = len(shared_calls)
            similar_funcs.append(func)

    print(f"  Functions sharing 2+ call targets with ActionSpeed: {len(similar_funcs)}")

    # Sort by VA
    similar_funcs.sort(key=lambda f: f['va'])

    # Print all similar functions
    print(f"\n{'='*100}")
    print("ALL SIBLING FUNCTIONS (same call signature as ActionSpeed)")
    print(f"{'='*100}")

    for i, func in enumerate(similar_funcs):
        label = func.get('label', '')
        shared = func.get('shared_calls', 0)
        floats = func['unique_floats']

        # Classify
        if func.get('label'):
            classification = label
        elif func['has_mulss'] and func['has_addss']:
            # Weight pair?
            pairs = []
            for a in floats:
                for b in floats:
                    if a != b and abs(a + b - 1.0) < 0.02:
                        pairs.append((min(a,b), max(a,b)))
            if pairs:
                classification = f"WEIGHTED COMBINATION: {pairs[0][0]} + {pairs[0][1]}"
            else:
                classification = f"MATH FUNCTION (mul+add, floats: {floats})"
        elif func['has_mulss']:
            classification = f"MULTIPLIER (floats: {floats})"
        elif not floats or floats == [0.0]:
            if func['size'] < 150:
                classification = "SIMPLE/PASS-THROUGH (no float math, small)"
            else:
                classification = f"COMPLEX (no float consts, {func['num_calls']} calls)"
        else:
            classification = f"OTHER (floats: {floats})"

        print(f"\n{'='*100}")
        print(f"Function #{i+1}: VA {func['va']:#x} | Size: {func['size']} bytes | Calls: {func['num_calls']} | Shared: {shared}")
        print(f"  Classification: {classification}")
        if floats:
            print(f"  Float constants: {floats}")
        print(f"  SSE ops: {'mulss ' if func['has_mulss'] else ''}{'addss ' if func['has_addss'] else ''}{'divss ' if func['has_divss'] else ''}{'subss' if func['has_subss'] else ''}")
        print()
        print(format_function(func, data, sections, image_base))

    # Summary table
    print(f"\n\n{'='*100}")
    print("SUMMARY TABLE")
    print(f"{'='*100}")
    print(f"{'#':>3} {'VA':>18} {'Size':>6} {'Calls':>6} {'Floats':>40} {'Classification'}")
    print('-' * 120)
    for i, func in enumerate(similar_funcs):
        label = func.get('label', '')
        floats = func['unique_floats']
        floats_str = ', '.join(f'{f:.4f}' for f in floats) if floats else '-'

        if func.get('label'):
            cls = label
        elif func['has_mulss'] and func['has_addss']:
            pairs = [(a,b) for a in floats for b in floats if a<b and abs(a+b-1)<0.02]
            cls = f"WEIGHTED: {pairs[0][0]}+{pairs[0][1]}" if pairs else f"MATH({floats_str})"
        elif func['has_mulss']:
            cls = f"MUL({floats_str})"
        elif not floats or all(f == 0.0 for f in floats):
            cls = "SIMPLE" if func['size'] < 150 else "COMPLEX"
        else:
            cls = f"OTHER({floats_str})"

        print(f"{i+1:3d} {func['va']:#018x} {func['size']:6d} {func['num_calls']:6d} {floats_str:>40s} {cls}")


if __name__ == '__main__':
    main()
