#!/usr/bin/env python

import subprocess
import argparse
import shutil
import os
import re

ap = argparse.ArgumentParser(description='Easily mock up your C/C++ programs into platform-independent, self-contained executable files. No more GLIBC version pains.')
ap.add_argument('filename', help='path to executable ELF file', nargs='+')
ap.add_argument('-o', '--output', help='output directory to copy ELF files', required=True)
ap.add_argument('-f', '--force', help='force clean directory if exists', action='store_true')
ap.add_argument('-D', '--dry', help='dry run mode, print dependencies only', action='store_true')
ap.add_argument('-P', '--patch', help='patch ELF files RPATH (requires patchelf)', action='store_true')
ap.add_argument('-s', '--suffix', help='start up script file suffix (default .sh)', default='.sh')
args = ap.parse_args()

if not args.dry:
    try:
        os.makedirs(args.output)
    except FileExistsError:
        if args.force:
            shutil.rmtree(args.output)
            os.makedirs(args.output)

files = [os.path.abspath(p) for p in args.filename]
depends = {os.path.basename(p): p for p in files}
updates = list(files)

print('Mocking:', files)

while updates:
    lines = subprocess.check_output([
        'ldd',
        *updates,
    ], env={
        'LC_ALL': 'C',
        'LANG': 'C',
        'LANGUAGE': 'C',
    }).decode().splitlines()

    updates = []
    for line in lines:
        # print(line)
        if not line.startswith('\t'):
            continue

        m = re.findall(r'^\t(\S+) => (\S+)(?:\s\([0-9a-fx]+\))?$', line)
        if not m:
            continue
        name, path = m[0]
        name = os.path.basename(name)
        if name in depends:
            if depends[name] != path:
                print(f'WARNING: multiple path found for {name}: {depends[name]}, {path}')
            continue
        if path == 'not found':
            print(f'WARNING: dependency not found for {name}')
            continue
        depends[name] = path
        print('Found:', name, '=>', path)
        updates.append(path)

    print('Depends:', updates)

print('Dependencies:', depends)

ld_linux = [n for n in depends if n.startswith('ld-linux-')]
if ld_linux:
    ld_linux = ld_linux[0]
    path = depends.pop(ld_linux)
    dest = os.path.join(args.output, ld_linux)
    print('Copying:', path, '=>', dest)
    if not args.dry:
        shutil.copyfile(path, dest)
        subprocess.check_call(['chmod', '+x', dest])

for name, path in depends.items():
    dest = os.path.join(args.output, name)
    print('Copying:', path, '=>', dest)
    if not args.dry:
        shutil.copyfile(path, dest)

    if args.patch:
        print('Patching:', dest)
        if not args.dry:
            subprocess.check_call(['chmod', '+x', dest])
            subprocess.check_call(['patchelf', '--set-rpath', '$ORIGIN', dest])

        if path in files:
            print('Set Interpreter:', dest)
            if not args.dry:
                subprocess.check_call(['patchelf', '--set-interpreter', f'./{ld_linux}', dest])

if args.suffix:
    for path in args.filename:
        name = os.path.basename(path)
        script = os.path.join(args.output, name + args.suffix)
        print('Creating startup script:', script)
        if not args.dry:
            with open(script, 'w') as f:
                f.write('#!/bin/bash\nset -e\n')
                if not args.patch:
                    f.write('LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$(dirname "$0")"')
                f.write(f'test -x "$(dirname "$0")/{ld_linux}" || chmod +x "$(dirname "$0")/{ld_linux}"\n')
                f.write(f'test -x "$(dirname "$0")/{name}" || chmod +x "$(dirname "$0")/{name}"\n')
                f.write(f'exec -a "$0" "$(dirname "$0")/{ld_linux}" "$(dirname "$0")/{name}" "$@"\n')
            subprocess.check_call(['chmod', '+x', script])

    print()
    print(f'Done! Now run `{args.output}/{os.path.basename(files[0])}{args.suffix}` to enjoy platform-independent executable!')
    print(f'You can copy the directory `{args.output}` to anywhere, any Linux distribution.')
    print(f'Just run `{os.path.basename(files[0])}{args.suffix}` in it and everything works as it was on your computer!')
