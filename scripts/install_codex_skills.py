#!/usr/bin/env python3
"""Install ig-reel and ig-human for Codex, preserving local modifications."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('ig-reel', 'ig-human')
MARKER = '.instagram-agent-install.json'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def install(destination):
    plans = []
    for name in NAMES:
        source, target = ROOT/'skills'/name, destination/name
        if target.is_symlink():
            raise RuntimeError(f'Refusing to overwrite symlink: {target}')
        files = [p for p in source.iterdir() if p.is_file() and p.suffix in ('.md', '.py', '.json')]
        marker = target/MARKER
        if marker.is_symlink():
            raise RuntimeError(f'Refusing symlinked installation manifest: {marker}')
        previous = json.loads(marker.read_text()) if marker.exists() else {}
        for path in files:
            existing = target/path.name
            if existing.is_symlink():
                raise RuntimeError(f'Refusing to overwrite symlink: {existing}')
            if existing.exists() and digest(existing) not in (previous.get(path.name), digest(path)):
                raise RuntimeError(f'Local changes or unrelated skill at {existing}; preserve it before installing')
        plans.append((files, target))
    for files, target in plans:
        target.mkdir(parents=True, exist_ok=True)
        for path in files:
            shutil.copy2(path, target/path.name)
        (target/MARKER).write_text(json.dumps({p.name: digest(p) for p in files}, indent=2)+'\n')
        print(f'Installed {target.name}: {target}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skills-dir', type=Path, default=Path.home()/'.agents/skills')
    args = parser.parse_args()
    install(args.skills_dir.expanduser())
