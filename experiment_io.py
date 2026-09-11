"""Consistent, deterministic tables and presentation for both experiments."""
import csv
import json


def write_csv(path, rows, fields=None):
    if not rows and fields is None:
        raise ValueError(f'No schema for empty output: {path}')
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def plot_style():
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.grid': True, 'axes.axisbelow': True,
                         'grid.alpha': .15, 'figure.facecolor': 'white',
                         'savefig.facecolor': 'white'})
