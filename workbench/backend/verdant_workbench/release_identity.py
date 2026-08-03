from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

RELEASE_ID = "verdant-minds-v5-workbench-1.0.1"


def _tree_hash(root: Path, paths: Iterable[Path]) -> str:
    h = hashlib.sha256()
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(p for p in path.rglob('*') if p.is_file())
    for path in sorted(set(files), key=lambda p: str(p.relative_to(root)).replace('\\', '/')):
        rel = str(path.relative_to(root)).replace('\\', '/')
        if any(part in {'__pycache__', '.pytest_cache', 'node_modules', '.git'} for part in path.parts):
            continue
        if path.suffix in {'.pyc', '.pyo'}:
            continue
        h.update(rel.encode('utf-8'))
        h.update(b'\0')
        h.update(path.read_bytes())
        h.update(b'\0')
    return h.hexdigest()


def source_build_identity() -> dict[str, str]:
    root = Path(__file__).resolve().parents[3]
    engine_paths = [p for p in root.iterdir() if p.is_dir() and p.name.startswith('verdant_')]
    engine_paths += [root / 'run_ethomorphism_benchmark.py', root / 'run_verdant_media.py']
    workbench_paths = [
        root / 'workbench' / 'backend' / 'verdant_workbench',
        root / 'workbench' / 'frontend' / 'src',
        root / 'workbench' / 'frontend' / 'dist',
        root / 'workbench' / 'frontend' / 'package.json',
        root / 'workbench' / 'frontend' / 'tsconfig.json',
        root / 'workbench' / 'frontend' / 'vite.config.ts',
        root / 'workbench' / 'frontend' / 'index.html',
        root / 'workbench' / 'schemas',
        root / 'workbench' / 'plugins',
        root / 'run_verdant_workbench.py',
    ]
    dependency_lock = root / 'requirements-lock.txt'
    return {
        'release_id': RELEASE_ID,
        'engine_source_sha256': _tree_hash(root, engine_paths),
        'workbench_source_sha256': _tree_hash(root, workbench_paths),
        'dependency_lock_sha256': hashlib.sha256(dependency_lock.read_bytes()).hexdigest() if dependency_lock.exists() else '',
    }
