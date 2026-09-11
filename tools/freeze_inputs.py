"""Explicitly register a reviewed corpus. Normal reproduction only verifies it."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from provenance import MANIFEST, aggregate, input_fingerprints, verify_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='deliberately accept the current input snapshot')
    args = parser.parse_args()
    if args.write:
        files = input_fingerprints()
        MANIFEST.write_text(json.dumps({'format': 1, 'text_hash_policy': 'CRLF normalized to LF; evidence hashed byte-for-byte',
            'reviewed_baseline_revision': '77248bcc97617eb07593723dc8144d9121acb038',
            'corpus_sha256': aggregate(files), 'files': files}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('Verified corpus:', verify_inputs())


if __name__ == '__main__':
    main()
