from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from verdant_kernel import VerdantKernel, save_checkpoint
from verdant_perception import VerdantPerceptionPipeline

from .gateway import ImportOptions, RunImportError, VerdantMediaGateway


def _choose_files() -> list[Path]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        selected = filedialog.askopenfilenames(title="Choose files for Verdant")
        root.destroy()
        return [Path(item) for item in selected]
    except Exception as exc:
        raise SystemExit(
            "No --input was supplied and the graphical file chooser is unavailable: "
            f"{type(exc).__name__}: {exc}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verdant-media",
        description=(
            "Preserve and ingest user-selected images, audio, video, or supported Verdant run packages. "
            "Unsupported files are archived without fabricated interpretation."
        ),
    )
    parser.add_argument("--input", action="append", default=[], help="File or folder. Repeat as needed.")
    parser.add_argument("--checkpoint", help="Existing .vdk checkpoint to continue before importing media.")
    parser.add_argument("--run-source", help=".vdk, .vrun.zip, or ZIP containing a .vdk checkpoint.")
    parser.add_argument(
        "--run-mode",
        choices=("inspect", "continue", "branch"),
        default="continue",
        help="How to use --run-source.",
    )
    parser.add_argument("--checkpoint-member", help="Specific .vdk member when a ZIP contains several.")
    parser.add_argument("--branch-label", help="Required name override for a branched run.")
    parser.add_argument("--output-dir", default="verdant_user_run", help="Output directory.")
    parser.add_argument("--seed", type=int, default=7741)
    parser.add_argument("--state-dim", type=int, default=128)
    parser.add_argument("--run-label", default="user-media-run")
    parser.add_argument("--start", type=float, default=0.0, help="Start time in seconds.")
    parser.add_argument("--end", type=float, help="End time in seconds.")
    parser.add_argument("--video-fps", type=float, default=5.0)
    parser.add_argument("--audio-window", type=float, default=0.20, help="Audio packet duration in seconds.")
    parser.add_argument("--max-frames", type=int, default=300)
    parser.add_argument("--max-source-mb", type=float, default=512.0)
    parser.add_argument("--archive-only", action="store_true")
    parser.add_argument("--no-video-audio", action="store_true")
    parser.add_argument("--no-perception", action="store_true")
    parser.add_argument("--inspect-only", action="store_true", help="Inspect run/media types without committing media.")
    return parser


def run(argv: Sequence[str] | None = None) -> dict:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    gateway = VerdantMediaGateway()

    if args.run_source:
        loaded = gateway.load_run(
            Path(args.run_source),
            mode=args.run_mode,
            branch_label=args.branch_label,
            checkpoint_member=args.checkpoint_member,
        )
        if args.run_mode == "inspect":
            summary = {
                "mode": "run_inspection",
                "source": str(loaded.inspection.source_path),
                "package_kind": loaded.inspection.package_kind,
                "checkpoint_sha256": loaded.inspection.checkpoint_sha256,
                "kernel_id": loaded.inspection.state.identity.kernel_id,
                "run_label": loaded.inspection.state.identity.run_label,
                "generation": loaded.inspection.state.lineage.generation,
                "metrics": loaded.inspection.metrics,
            }
            (output_dir / "run_inspection.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
            return summary
        assert loaded.kernel is not None
        kernel = loaded.kernel
    elif args.checkpoint:
        loaded = gateway.load_run(Path(args.checkpoint), mode="continue")
        assert loaded.kernel is not None
        kernel = loaded.kernel
    else:
        kernel = VerdantKernel(seed=args.seed, state_dim=args.state_dim, run_label=args.run_label)

    inputs = [Path(item) for item in args.input] or _choose_files()
    if args.inspect_only:
        summary = {
            "mode": "media_type_inspection",
            "inputs": [
                {
                    "path": str(path),
                    "classification": gateway.classify(path)[0],
                    "mime_type": gateway.classify(path)[1],
                    "nbytes": path.stat().st_size if path.exists() and path.is_file() else None,
                }
                for path in inputs
            ],
        }
        (output_dir / "media_type_inspection.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
        return summary

    options = ImportOptions(
        start_seconds=args.start,
        end_seconds=args.end,
        video_fps=args.video_fps,
        audio_window_seconds=args.audio_window,
        maximum_frames=args.max_frames,
        maximum_source_bytes=int(args.max_source_mb * 1024 * 1024),
        include_video_audio=not args.no_video_audio,
        archive_only=args.archive_only,
    )
    results = gateway.import_many(kernel, inputs, output_dir=output_dir, options=options)
    perception = VerdantPerceptionPipeline()
    perceptual_reports = []
    archive_paths = {
        result.sensory_result.archive.archive_id: result.sensory_result.archive_path
        for result in results
        if result.sensory_result is not None
    }
    if not args.no_perception:
        for result in results:
            if result.sensory_result is None:
                continue
            has_vision = any(sample.modality.value == "vision" for sample in result.sensory_result.samples)
            if not has_vision:
                continue
            bound = perception.process(
                kernel,
                result.temporal_event_ids,
                archive_paths,
            )
            perceptual_reports.append(bound.report)

    checkpoint_path = output_dir / "current_run.vdk"
    checkpoint_sha256 = save_checkpoint(checkpoint_path, kernel.snapshot())
    report_path = output_dir / "media_import_summary.json"
    summary = {
        "mode": "media_ingestion",
        "kernel_id": kernel.state.identity.kernel_id,
        "run_label": kernel.state.identity.run_label,
        "generation": kernel.state.lineage.generation,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha256,
        "imports": [
            {
                "source_path": str(result.source_path),
                "media_kind": result.media_kind,
                "mime_type": result.mime_type,
                "media_import_id": result.media_archive.import_id,
                "media_archive_path": str(result.media_archive.archive_path),
                "source_sha256": result.media_archive.source_sha256,
                "translated": result.translated,
                "translation_status": result.translation_status,
                "sensory_archive_path": str(result.sensory_archive_path) if result.sensory_archive_path else None,
                "sensory_sample_count": len(result.sensory_result.samples) if result.sensory_result else 0,
                "temporal_event_ids": list(result.temporal_event_ids),
                "notes": list(result.notes),
                "metadata": result.metadata,
            }
            for result in results
        ],
        "perceptual_reports": [item.model_dump(mode="json") for item in perceptual_reports],
        "metrics": kernel.metrics(),
        "semantic_counts": {
            "concepts": len(kernel.state.concepts),
            "relations": len(kernel.state.relations),
            "claims": len(kernel.state.claims),
            "contradictions": len(kernel.state.contradictions),
        },
    }
    report_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    companions = [
        result.media_archive.archive_path for result in results
    ] + [
        result.sensory_archive_path for result in results if result.sensory_archive_path is not None
    ] + [report_path]
    run_package_path = output_dir / "current_run.vrun.zip"
    package = gateway.write_run_package(
        kernel,
        run_package_path,
        companion_paths=companions,
        metadata={"user_media_import_count": len(results)},
    )
    summary["run_package_path"] = str(run_package_path)
    summary["run_package_id"] = package.package_id
    report_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    try:
        summary = run()
    except (ValueError, RunImportError) as exc:
        print(f"Verdant import failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
