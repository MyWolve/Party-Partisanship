"""Rebuild, audit, test, and compare all results without network access.

python reproduce.py          regenerate outputs after every check passes
python reproduce.py --check compare generated tables/text with saved outputs
python reproduce.py --repeat also compare two complete runs in this environment
"""
import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'party-partisanship-mpl'))
os.environ.setdefault('MPLBACKEND', 'Agg')

from provenance import aggregate, code_fingerprints, digest, verify_inputs


def run(script, *args):
    command = [sys.executable, *script.split(), *map(str, args)]
    result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                            encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout, end='', flush=True)
    if result.returncode:
        raise RuntimeError(f'Failed ({result.returncode}): {script}')
    return result.stdout


def outputs(directory, numeric_only=False):
    return {p.relative_to(directory).as_posix(): digest(p, binary=p.suffix=='.png')
            for p in sorted(directory.rglob('*')) if p.is_file()
            and (not numeric_only or p.suffix in ('.csv', '.json', '.md', '.gz'))}


def experiments(destination):
    run('experiments/experiment_e1.py', '--output-dir', destination/'experiments/results_e1')
    run('experiments/experiment_e7.py', '--output-dir', destination/'experiments/results_e7')
    run('tools/export_dataset.py', '--output-dir', destination/'data/processed')
    run('tools/verify_dataset.py', '--dataset', destination/'data/processed',
        '--classification', destination/'experiments/results_e1/classification_audit.csv')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--repeat', action='store_true')
    args = parser.parse_args()
    corpus = verify_inputs()
    with tempfile.TemporaryDirectory(prefix='party-reproduce-') as name:
        staging = Path(name)
        logs = {}
        logs['derivation'] = run('tools/build_audit_data.py', '--check')
        logs['tests'] = run('-m unittest discover', '-s', 'tests', '-v')
        logs['integrity'] = run('check_data.py', '--output', staging/'integrity.json')
        logs['benchmark_rebuild'] = run('experiments/build_benchmarks_e7.py', '--check')
        logs['reconciliation'] = run('tools/reconcile_members.py', '--check')
        logs['source_coverage'] = run('tools/review_source_coverage.py', '--check')
        first = staging/'first'
        experiments(first)
        tables = outputs(first, numeric_only=True)
        repeats = None
        if args.repeat:
            second = staging/'second'
            experiments(second)
            if tables != outputs(second, numeric_only=True):
                raise ValueError('Repeated runs produced different tables or findings')
            repeats = {'tables_identical': True, 'images_identical': outputs(first) == outputs(second)}
        if verify_inputs() != corpus:
            raise ValueError('Inputs changed during reproduction')
        if args.check:
            differences = [p for p, sha in tables.items() if not (ROOT/p).exists()
                           or digest(ROOT/p) != sha]
            if differences:
                raise ValueError(f'Saved results differ: {differences}')
            print('PASS: all regenerated tables and findings match the saved outputs')
        else:
            for p in first.rglob('*'):
                if p.is_file():
                    dest = ROOT/p.relative_to(first)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(p, dest)
            shutil.copyfile(staging/'integrity.json', ROOT/'audit/integrity.json')
        code = code_fingerprints()
        revision = subprocess.run(['git','-c',f'safe.directory={ROOT.as_posix()}','rev-parse','HEAD'],
                                   cwd=ROOT, capture_output=True, text=True)
        manifest = {'corpus_sha256': corpus, 'code_sha256': aggregate(code), 'code_files': code,
            'git_base_revision': revision.stdout.strip() if revision.returncode==0 else None,
            'python': platform.python_version(), 'platform': platform.platform(),
            'dependencies': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
            'commands': ['tools/build_audit_data.py --check', '-m unittest discover -s tests -v',
                         'check_data.py', 'experiments/build_benchmarks_e7.py --check', 'tools/reconcile_members.py --check',
                         'tools/review_source_coverage.py --check',
                         'experiments/experiment_e1.py', 'experiments/experiment_e7.py',
                         'tools/export_dataset.py', 'tools/verify_dataset.py'],
            'table_sha256': aggregate(tables), 'outputs': outputs(first), 'repeat_check': repeats,
            'saved_results_match': args.check, 'status': 'pass'}
        # Environment/log metadata is separate from deterministic analytical outputs.
        (ROOT/'audit/run_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        (ROOT/'audit/validation_log.txt').write_text('\n'.join(f'{name}\n{log}' for name,log in logs.items()),encoding='utf-8')
        print('PASS: reproducibility audit complete; tables SHA256', aggregate(tables))


if __name__ == '__main__':
    main()
