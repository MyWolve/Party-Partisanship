"""Portable input fingerprints, separate from environment-specific run metadata."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'audit/input_manifest.json'


def digest(path, binary=False):
    data = path.read_bytes()
    if not binary:
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def aggregate(mapping):
    return hashlib.sha256(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def input_fingerprints(root=ROOT):
    root = Path(root)
    paths = [p for pattern in ('Parliament_*/*.csv', 'House of Commons/*.xml',
             'experiments/experiment_7_data/*', 'evidence/*', 'audit/derived/*')
             for p in root.glob(pattern) if p.is_file()]
    paths += [root / p for p in ('audit/baseline_discrepancies.json', 'audit/data_decisions.json',
                                'audit/whip_designations.json', 'experiments/benchmarks_e7.csv')]
    return {p.relative_to(root).as_posix(): digest(p, binary=p.parent.name == 'evidence')
            for p in sorted(paths)}


def verify_inputs(root=ROOT):
    root = Path(root)
    expected = json.loads((root / 'audit/input_manifest.json').read_text(encoding='utf-8'))
    actual = input_fingerprints(root)
    changed = sorted(k for k in set(actual) | set(expected['files']) if actual.get(k) != expected['files'].get(k))
    if changed or aggregate(actual) != expected['corpus_sha256']:
        raise ValueError(f'Frozen input corpus changed: {changed[:20]}')
    return expected['corpus_sha256']


def code_fingerprints(root=ROOT):
    paths = [p for pattern in ('*.py', 'experiments/*.py', 'tools/*.py', 'tests/*.py', 'requirements*.txt')
             for p in root.glob(pattern)]
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(paths)}
