#!/usr/bin/env python

import subprocess
import tempfile
import base64
import argparse
import shutil
import os
import re

ap = argparse.ArgumentParser(description='Easily mock up your C/C++ programs into platform-independent, self-contained executable files. No more GLIBC version pains.')
ap.add_argument('filename', help='path to executable ELF file', nargs='+')
ap.add_argument('-o', '--output', help='output directory to copy ELF files', default='')
ap.add_argument('-f', '--force', help='force clean directory if exists', action='store_true')
ap.add_argument('-D', '--dry', help='dry run mode, print dependencies only', action='store_true')
ap.add_argument('-P', '--patch', help='patch ELF files RPATH (requires patchelf)', action='store_true')
ap.add_argument('-S', '--single', help='output a single file instead of directory', action='store_true')
ap.add_argument('-x', '--suffix', help='start up script file suffix (default .sh)', default='.sh')
args = ap.parse_args()

if args.single:
    temp_dir_object = tempfile.TemporaryDirectory()
    output_dir = temp_dir_object.name
else:
    if args.output:
        output_dir = args.output
    else:
        output_dir = 'bin'

if not args.dry:
    try:
        os.makedirs(output_dir)
    except FileExistsError:
        if args.force:
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)

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

        if '=>' in line:
            m = re.findall(r'^\t(\S+) => (\S+)(?:\s\([0-9a-fx]+\))?$', line)
            if not m:
                continue
            name, path = m[0]
            name = os.path.basename(name)
        else:
            m = re.findall(r'^\t(/\S+ld-linux[^\s]*)\s*\(0x[0-9a-f]+\)$', line)
            if not m:
                continue
            path = m[0]
            name = os.path.basename(path)
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
    dest = os.path.join(output_dir, ld_linux)
    print('Copying:', path, '=>', dest)
    if not args.dry:
        shutil.copyfile(path, dest)
        subprocess.check_call(['chmod', '+x', dest])

for name, path in depends.items():
    dest = os.path.join(output_dir, name)
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
        script = os.path.join(output_dir, name + args.suffix)
        print('Creating startup script:', script)
        if not args.dry:
            with open(script, 'w') as f:
                f.write('#!/bin/bash\nset -e\n')
                f.write(f'test -x "$(dirname "$0")/{ld_linux}" || chmod +x "$(dirname "$0")/{ld_linux}"\n')
                f.write(f'test -x "$(dirname "$0")/{name}" || chmod +x "$(dirname "$0")/{name}"\n')
                if not args.patch:
                    f.write(f'LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$(dirname "$0")" exec -a "$0" "$(dirname "$0")/{ld_linux}" "$(dirname "$0")/{name}" "$@"\n')
                else:
                    f.write(f'exec -a "$0" "$(dirname "$0")/{ld_linux}" "$(dirname "$0")/{name}" "$@"\n')
            subprocess.check_call(['chmod', '+x', script])

if args.single:
    output_file = args.output or args.filename[0]
    for path in args.filename:
        name = os.path.basename(path)
        if len(args.filename) > 1:
            script = f'{args.output}.{name}' if args.output else path
        else:
            script = args.output or path
        output_file = script
        print('Creating executable script:', script)
        with open(script, 'w') as f:
            f.write('#!/bin/bash\nset -e\n')
            f.write(f'_tmpzip=$(mktemp)\n')
            f.write(f'_extractdir=$(mktemp -d)\n')
            f.write(f'test -f $_tmpzip\n')
            f.write(f'test -d $_extractdir\n')
            f.write(f'cat > $_tmpzip << __MOCKUP_PAYLOAD_EOF__\n')
            with tempfile.NamedTemporaryFile(suffix='.tar.gz') as zip_file:
                old_dir = os.getcwd()
                os.chdir(output_dir)
                print('Compressing:', output_dir)
                subprocess.check_call(['tar', '-zcvf', zip_file.name, '.'])
                os.chdir(old_dir)
                print('Base64 encoding:', zip_file.name)
                f.write(subprocess.check_output(['base64', zip_file.name]).decode('latin1'))
            f.write(f'\n__MOCKUP_PAYLOAD_EOF__\n')
            f.write(f'_olddir=$PWD\n')
            f.write(f'cd $_extractdir\n')
            f.write(f'base64 -d < $_tmpzip | tar -zx\n')
            f.write(f'rm -f $_tmpzip\n')
            f.write(f'cd $_olddir\n')
            f.write(f'test -x "$_extractdir/{ld_linux}" || chmod +x "$_extractdir/{ld_linux}"\n')
            f.write(f'test -x "$_extractdir/{name}" || chmod +x "$_extractdir/{name}"\n')
            if not args.patch:
                f.write(f'LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$_extractdir" exec -a "$0" "$_extractdir/{ld_linux}" "$_extractdir"$0")/{name}" "$@"\n')
            else:
                f.write(f'exec -a "$0" "$_extractdir/{ld_linux}" "$_extractdir/{name}" "$@"\n')
        subprocess.check_call(['chmod', '+x', script])

    print()
    print(f'Done! Now run `{output_file}` to enjoy platform-independent executable!')
    print(f'You can copy the single-file `{output_file}` to anywhere, any Linux distribution.')
    print(f'Just run `{output_file}` in it and everything works as it was on your computer!')
else:
    print()
    print(f'Done! Now run `{output_dir}/{os.path.basename(files[0])}{args.suffix}` to enjoy platform-independent executable!')
    print(f'You can copy the directory `{output_dir}` to anywhere, any Linux distribution.')
    print(f'Just run `{os.path.basename(files[0])}{args.suffix}` in it and everything works as it was on your computer!')
