from __future__ import annotations

import argparse
from pathlib import Path

from run_verdant_cultivation import CultivationSession
from verdant_development.v5x import V5XDevelopmentPipeline
from verdant_kernel import VerdantKernel, load_checkpoint
from verdant_thermodynamics import AppendOnlyTelemetryWriter, record_from_development


class V5XCultivationSession(CultivationSession):
    """Opt-in V5-X cultivation session; canonical V5 runner remains untouched."""

    def __init__(
        self,
        kernel: VerdantKernel,
        checkpoint_path: Path,
        *,
        telemetry_writer: AppendOnlyTelemetryWriter | None = None,
        run_id: str | None = None,
        branch_commit: str | None = None,
    ) -> None:
        super().__init__(kernel, checkpoint_path)
        self.development = V5XDevelopmentPipeline(self.development)
        self.telemetry_writer = telemetry_writer
        self.run_id = run_id or kernel.state.identity.kernel_id
        self.branch_commit = branch_commit

    def teach(self, *args, **kwargs):
        result = super().teach(*args, **kwargs)
        if self.telemetry_writer is not None:
            self.telemetry_writer.append(
                record_from_development(
                    kernel=self.kernel,
                    result=result,
                    run_id=self.run_id,
                    branch_commit=self.branch_commit,
                )
            )
        return result

    def _print_cycle(self, result) -> None:
        super()._print_cycle(result)
        if result.thermodynamics is not None:
            thermo = result.thermodynamics
            print(
                "THERMO:",
                f"Tg={thermo.t_g:.4f}",
                f"Tcog={thermo.t_cog:.4f}",
                f"Hsys={thermo.h_sys:.4f}",
                f"Henv={thermo.h_env:.4f}",
                f"phase={thermo.phase.value}",
                "(measurement-only)",
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verdant V5-X cultivation + telemetry wrapper")
    parser.add_argument("--checkpoint", default="verdant_v5x_cultivation.vdk")
    parser.add_argument("--script", type=Path, help="optional JSONL cultivation script")
    parser.add_argument("--seed", type=int, default=7741)
    parser.add_argument("--state-dim", type=int, default=128)
    parser.add_argument("--telemetry-jsonl", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--branch-commit", default="V5-X")
    args = parser.parse_args()

    checkpoint = Path(args.checkpoint)
    if checkpoint.exists():
        kernel = VerdantKernel.from_state(load_checkpoint(checkpoint))
    else:
        kernel = VerdantKernel(seed=args.seed, state_dim=args.state_dim, run_label="v5x-cultivation")
    session = V5XCultivationSession(
        kernel,
        checkpoint,
        telemetry_writer=AppendOnlyTelemetryWriter(args.telemetry_jsonl),
        run_id=args.run_id,
        branch_commit=args.branch_commit,
    )
    if args.script:
        session.run_jsonl(args.script)
    else:
        session.status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
