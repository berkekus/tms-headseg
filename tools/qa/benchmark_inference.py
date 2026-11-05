"""Repeat the real desktop inference check and retain a comparable timing ledger."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('desktop-python', 'python', 'model', 'mri', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--repeats', type=int, default=3)
    a = p.parse_args()
    if a.repeats < 3:
        p.error('Use at least three repeats.')
    out = a.output.resolve()
    if any((x / '.git').exists() for x in (out, *out.parents)):
        p.error('Keep benchmark outputs outside every Git checkout.')
    out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]
    source = root / 'tools/mri_prototype/check_inference.py'
    protocol = {'experiment': 'E2', 'device': 'cpu', 'tta': False, 'math_threads': 4,
                'repeats': a.repeats, 'process_policy': 'Fresh model/process each repeat; OS file cache uncontrolled.',
                'boundaries': {'model_load_seconds': 'Predictor/model initialization plus E2 input geometry preparation.',
                               'prediction_seconds': 'Prediction, file export and source-grid restoration.',
                               'desktop_seconds': 'Desktop start request through report and automatic 3D opening; includes event processing/screenshots.'},
                'platform': platform.platform(), 'cpu': platform.processor(),
                'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root)),
                'helper_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'model': str(a.model.resolve()), 'mri': str(a.mri.resolve()),
                'inference_python': str(a.python.resolve()), 'desktop_python': str(a.desktop_python.resolve())}
    if platform.system() == 'Windows':
        hardware = subprocess.check_output(['powershell', '-NoProfile', '-Command',
            'Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory | ConvertTo-Json; Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json'], text=True)
        protocol['hardware_inventory'] = hardware
    (out / 'protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    rows = []
    hashes = None
    for index in range(1, a.repeats + 1):
        case = out / f'repeat-{index}'
        case.mkdir()
        command = [str(a.desktop_python), str(source), '--python', str(a.python), '--model', str(a.model),
                   '--mri', str(a.mri), '--output', str(case), '--experiment', 'E2']
        print(f'Repeat {index}/{a.repeats} starting', flush=True)
        start = time.monotonic()
        with (case / 'console.log').open('w', encoding='utf-8') as log:
            try:
                code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=1900).returncode
            except subprocess.TimeoutExpired:
                code = -1
        row = {'repeat': index, 'status': 'FAIL', 'model_load_seconds': '', 'prediction_seconds': '',
               'desktop_seconds': '', 'helper_process_seconds': time.monotonic() - start}
        records = list(case.glob('*-verification.json'))
        if code == 0 and len(records) == 1:
            record = json.loads(records[0].read_text(encoding='utf-8'))
            assert record['state'] == 'passed' and record['source_hashes_unchanged']
            if hashes is not None and record['source_hashes'] != hashes:
                raise RuntimeError('Input/model hashes changed between repeats.')
            hashes = record['source_hashes']
            row.update(status='PASS', model_load_seconds=record['timing']['model_load_seconds'],
                       prediction_seconds=record['timing']['prediction_seconds'], desktop_seconds=record['elapsed_seconds'])
        rows.append(row)
        with (out / 'timings.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(row))
            writer.writeheader(); writer.writerows(rows)
        print(f'Repeat {index}: {row}', flush=True)
    passed = [r for r in rows if r['status'] == 'PASS']
    result = {'status': 'PASS' if len(passed) == a.repeats else 'FAIL', 'attempted': len(rows),
              'passed': len(passed), 'failed': len(rows) - len(passed),
              'median_seconds_successful_only': {k: statistics.median(r[k] for r in passed)
                  for k in ('model_load_seconds', 'prediction_seconds', 'desktop_seconds')} if passed else {}}
    (out / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    lines = ['# E2 CPU inference timing benchmark', '',
             '| Repeat | Status | Model/preparation (s) | Prediction/restore (s) | Desktop total (s) |',
             '| --- | --- | ---: | ---: | ---: |']
    for r in rows:
        values = [f'{r[k]:.3f}' if isinstance(r[k], (int, float)) else '—'
                  for k in ('model_load_seconds', 'prediction_seconds', 'desktop_seconds')]
        lines.append(f"| {r['repeat']} | {r['status']} | " + ' | '.join(values) + ' |')
    if passed:
        values = [f'{statistics.median(r[k] for r in passed):.3f}'
                  for k in ('model_load_seconds', 'prediction_seconds', 'desktop_seconds')]
        lines.append('| Median of successful runs | | ' + ' | '.join(values) + ' |')
    lines += ['', f"Status: {result['status']}. Passed: {len(passed)}/{len(rows)}.", '',
              'Fresh processes; OS cache uncontrolled. One public subject, not anatomical validation or a GPU comparison.',
              'Model/preparation and prediction are included in desktop total, not additional to it.',
              'See protocol.json for boundaries and timings.csv for every attempt.']
    (out / 'README.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(result), flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
