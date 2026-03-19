"""CLI entry point for cultivation runs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig, parse_seeds
from cultivation.spec_parser import CultivationSpec, SpecValidationError
from cultivation.spec_runner import SpecRunner
from verdant_v2.ethomorphic_config import EthomorphicParams


def _build_ethomorphic_params(args: argparse.Namespace) -> EthomorphicParams | None:
    """Build optional ethomorphic parameter overrides from CLI args."""

    updates = {
        "num_cognitive_dims": args.ecwf_cognitive_dims,
        "num_ethical_dims": args.ecwf_ethical_dims,
        "adaptive_rate": args.ecwf_adaptive_rate,
        "feedback_factor": args.ecwf_feedback_factor,
        "emergence_entropy_min": args.emergence_entropy_min,
        "emergence_entropy_max": args.emergence_entropy_max,
        "emergence_magnitude_threshold": args.emergence_magnitude_threshold,
    }
    filtered = {key: value for key, value in updates.items() if value is not None}
    return EthomorphicParams(**filtered) if filtered else None


def _load_spec(path: str) -> CultivationSpec:
    try:
        return CultivationSpec.from_file(path)
    except SpecValidationError as exc:
        raise SystemExit(f"Spec validation failed: {exc}") from exc


def _print_spec_summary(spec: CultivationSpec) -> None:
    print(f"Spec: {spec.name}")
    print(f"Description: {spec.description}")
    print(f"Total cycles: {spec.total_cycles}")
    print(f"Phases: {len(spec.phases)}")
    for phase in spec.phases:
        print(
            f"- {phase.name}: cycles={phase.cycles}, topics={len(phase.topics)}, "
            f"self_reflect_interval={phase.self_reflect_interval}"
        )


def main() -> None:
    """Run cultivation CLI."""
    parser = argparse.ArgumentParser(prog="python -m cultivation.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run multi-seed cultivation")
    run_p.add_argument("--cycles", type=int, default=120)
    run_p.add_argument("--provider", default="local", choices=["local", "anthropic", "groq", "mistral", "tutor"])
    run_p.add_argument("--tutor-backend", default="groq", choices=["local", "groq", "anthropic", "mistral"])
    run_p.add_argument("--tutor-model", default=None)
    run_p.add_argument("--tutor-temperature", type=float, default=0.8)
    run_p.add_argument("--seeds", default="0-19", help="Seed range/list, e.g. 0-19 or 0,2,4")
    run_p.add_argument("--outdir", default="outputs")
    run_p.add_argument("--pressure-every", type=int, default=5)
    run_p.add_argument("--basin-routing", action="store_true")
    run_p.add_argument("--enable-pruning", action="store_true")
    run_p.add_argument("--enable-budding", action="store_true")
    run_p.add_argument("--enable-boundary-emergence", action="store_true")
    run_p.add_argument("--enable-all-dynamics", action="store_true")
    run_p.add_argument("--boundary-use-ecwf", action=argparse.BooleanOptionalAction, default=True)
    run_p.add_argument("--bud-pressure-threshold", type=float, default=0.01)
    run_p.add_argument("--density-regulation", action=argparse.BooleanOptionalAction, default=True)
    run_p.add_argument("--checkpoint-interval", type=int, default=0)
    run_p.add_argument("--checkpoint-format", choices=["json", "msgpack"], default="json")
    run_p.add_argument("--fast-bridge", action=argparse.BooleanOptionalAction, default=False)
    run_p.add_argument("--self-reflect-interval", type=int, default=0)
    run_p.add_argument("--basin-use-registry", action=argparse.BooleanOptionalAction, default=True)
    run_p.add_argument("--ecwf-cognitive-dims", type=int, default=None)
    run_p.add_argument("--ecwf-ethical-dims", type=int, default=None)
    run_p.add_argument("--ecwf-adaptive-rate", type=float, default=None)
    run_p.add_argument("--ecwf-feedback-factor", type=float, default=None)
    run_p.add_argument("--emergence-entropy-min", type=float, default=None)
    run_p.add_argument("--emergence-entropy-max", type=float, default=None)
    run_p.add_argument("--emergence-magnitude-threshold", type=float, default=None)
    run_p.add_argument("--intervention-mode", default="none", choices=["none", "ablate_oldest_nodes", "scramble_ee_edges"])
    run_p.add_argument("--intervention-cycle", type=int, default=None)
    run_p.add_argument("--ablation-fraction", type=float, default=0.1)
    run_p.add_argument("--intervention-target", default="global", choices=["global", "largest_basin"])
    run_p.add_argument("--intervention-seed", type=int, default=None)

    resume_p = sub.add_parser("resume", help="Resume cultivation from a checkpoint")
    resume_p.add_argument("--checkpoint", required=True)
    resume_p.add_argument("--additional-cycles", type=int, required=True)
    resume_p.add_argument("--provider", default="local", choices=["local", "anthropic", "groq", "mistral", "tutor"])
    resume_p.add_argument("--tutor-backend", default="groq", choices=["local", "groq", "anthropic", "mistral"])
    resume_p.add_argument("--tutor-model", default=None)
    resume_p.add_argument("--tutor-temperature", type=float, default=0.8)
    resume_p.add_argument("--outdir", default="outputs")
    resume_p.add_argument("--pressure-every", type=int, default=5)
    resume_p.add_argument("--checkpoint-interval", type=int, default=0)
    resume_p.add_argument("--checkpoint-format", choices=["json", "msgpack"], default="json")
    resume_p.add_argument("--fast-bridge", action=argparse.BooleanOptionalAction, default=False)
    resume_p.add_argument("--self-reflect-interval", type=int, default=0)

    cultivate_p = sub.add_parser("cultivate", help="Run VCult spec cultivation")
    cultivate_p.add_argument("--spec", required=True)
    cultivate_p.add_argument("--provider", default="local", choices=["local", "tutor"])
    cultivate_p.add_argument("--seeds", default="0-0", help="Seed range/list, e.g. 0-4 or 0,2,4")
    cultivate_p.add_argument("--outdir", default="outputs")

    validate_p = sub.add_parser("validate-spec", help="Validate a VCult spec without running it")
    validate_p.add_argument("--spec", required=True)

    preview_p = sub.add_parser("preview-spec", help="Preview the first N generated inputs from a VCult spec")
    preview_p.add_argument("--spec", required=True)
    preview_p.add_argument("--cycles", type=int, default=20)

    args = parser.parse_args()

    if args.command == "run":
        enable_pruning = bool(args.enable_pruning or args.enable_all_dynamics)
        enable_budding = bool(args.enable_budding or args.enable_all_dynamics)
        enable_boundary_emergence = bool(args.enable_boundary_emergence or args.enable_all_dynamics)
        ethomorphic_params = _build_ethomorphic_params(args)
        config = RunnerConfig(
            cycles=args.cycles,
            provider=args.provider,
            tutor_backend=args.tutor_backend,
            tutor_model=args.tutor_model,
            tutor_temperature=args.tutor_temperature,
            outdir=args.outdir,
            pressure_every=args.pressure_every,
            basin_routing=args.basin_routing,
            intervention_mode=args.intervention_mode,
            intervention_cycle=args.intervention_cycle,
            ablation_fraction=args.ablation_fraction,
            intervention_target=args.intervention_target,
            intervention_seed=args.intervention_seed,
            enable_pruning=enable_pruning,
            enable_budding=enable_budding,
            enable_boundary_emergence=enable_boundary_emergence,
            basin_pressure_threshold=args.bud_pressure_threshold,
            boundary_use_ecwf=args.boundary_use_ecwf,
            density_regulation_enabled=args.density_regulation,
            checkpoint_interval=args.checkpoint_interval,
            checkpoint_format=args.checkpoint_format,
            fast_bridge=args.fast_bridge,
            self_reflect_interval=args.self_reflect_interval,
            basin_use_registry=args.basin_use_registry,
            ethomorphic_params=ethomorphic_params,
        )
        runner = CultivationRunner(config)
        run_dir = runner.run(parse_seeds(args.seeds))
        print(f"Cultivation complete. Run directory: {run_dir.resolve()}")
    if args.command == "resume":
        config = RunnerConfig(
            cycles=args.additional_cycles,
            provider=args.provider,
            tutor_backend=args.tutor_backend,
            tutor_model=args.tutor_model,
            tutor_temperature=args.tutor_temperature,
            outdir=args.outdir,
            pressure_every=args.pressure_every,
            checkpoint_interval=args.checkpoint_interval,
            checkpoint_format=args.checkpoint_format,
            fast_bridge=args.fast_bridge,
            self_reflect_interval=args.self_reflect_interval,
        )
        runner = CultivationRunner(config)
        run_dir = runner.resume(args.checkpoint, args.additional_cycles)
        print(f"Resumed cultivation complete. Run directory: {run_dir.resolve()}")
    if args.command == "cultivate":
        spec = _load_spec(args.spec)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path(args.outdir) / f"run_{stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        for seed in parse_seeds(args.seeds):
            seed_dir = run_dir / f"seed_{seed}"
            SpecRunner(spec, seed=seed, provider=args.provider, outdir=str(seed_dir)).run()
        print(f"Spec cultivation complete. Run directory: {run_dir.resolve()}")
    if args.command == "validate-spec":
        spec = _load_spec(args.spec)
        _print_spec_summary(spec)
    if args.command == "preview-spec":
        spec = _load_spec(args.spec)
        for item in spec.generate_input_sequence()[: max(0, args.cycles)]:
            print(f"cycle={item['cycle']:>3} phase={item['phase']} self_reflection={item['is_self_reflection']} input={item['input_text']}")


if __name__ == "__main__":
    main()
