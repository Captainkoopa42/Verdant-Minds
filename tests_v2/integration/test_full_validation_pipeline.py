from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_validation_pipeline_smoke(tmp_path: Path) -> None:
    out_root = tmp_path / 'outputs'
    subprocess.run(
        [
            sys.executable,
            '-m',
            'cultivation.cli',
            'run',
            '--cycles',
            '20',
            '--seeds',
            '0-1',
            '--provider',
            'local',
            '--basin-routing',
            '--enable-all-dynamics',
            '--boundary-use-ecwf',
            '--density-regulation',
            '--bud-pressure-threshold',
            '0.001',
            '--checkpoint-interval',
            '10',
            '--outdir',
            str(out_root),
        ],
        check=True,
    )

    run_dir = sorted(out_root.glob('run_*'))[-1]
    validation_dir = tmp_path / 'validation'
    subprocess.run(
        [
            sys.executable,
            'analysis/run_full_validation.py',
            '--run-dir',
            str(run_dir),
            '--seeds',
            '2',
            '--outdir',
            str(validation_dir),
            '--n-nulls',
            '25',
            '--skip-slow',
        ],
        check=True,
    )

    report_path = validation_dir / 'validation_report.json'
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding='utf-8'))
    for key in [
        'task1_baseline',
        'task2_phase_diagram',
        'task3_daughter',
        'task4_semantic',
        'task5_compression',
        'task6_stability',
        'task7_robustness',
        'task8_h1_coherence',
    ]:
        assert 'status' in report[key]

    assert report['overall']['earlier_share'] == 1.0
    assert report['overall']['critical_failures'] == 0
