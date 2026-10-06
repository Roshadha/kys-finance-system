"""Narrow regression check for the DLL named in the user's screenshot.

This is not a general Windows 7 compatibility verifier.
"""
import sys
from pathlib import Path
import pefile

root = Path(sys.argv[1])
count = 0
problems = []
for path in root.rglob('*'):
    if path.suffix.lower() not in ('.exe', '.dll', '.pyd'):
        continue
    with pefile.PE(str(path), fast_load=True) as pe:
        count += 1
        if pe.FILE_HEADER.Machine != 0x14c:
            problems.append('{}: not x86'.format(path.name))
        pe.parse_data_directories(directories=[1, 13])
        for attribute in ('DIRECTORY_ENTRY_IMPORT', 'DIRECTORY_ENTRY_DELAY_IMPORT'):
            for entry in getattr(pe, attribute, []):
                name = entry.dll.decode('ascii').lower()
                if name.startswith('api-ms-win-core-path-'):
                    problems.append('{} imports {}'.format(path.name, name))
if problems:
    raise SystemExit('\n'.join(problems))
print('PASS: {} x86 binaries; no direct/delay imports of api-ms-win-core-path-*.dll'.format(count))
print('Actual Windows 7 testing is still required.')
