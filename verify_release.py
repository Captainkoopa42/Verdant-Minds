from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "workbench" / "backend"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(BACKEND), ENV.get("PYTHONPATH", "")]).rstrip(os.pathsep)
ENV.update({"OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1"})

ENGINE_GROUPS = [
    ["tests/test_verdant_kernel.py","tests/test_chunk_v2.py","tests/test_language_phase.py","tests/test_claims_phase.py","tests/test_ecwf_phase.py","tests/test_governance_phase.py","tests/test_shards_phase.py","tests/test_objects_phase.py","tests/test_workspace_phase.py","tests/test_media_gateway_phase.py","tests/test_sensory_phase.py","tests/test_perception_phase.py"],
    ["tests/test_development_phase.py","tests/test_plasticity_phase.py","tests/test_structures_phase.py","tests/test_compilation_phase.py"],
    ["tests/test_structure_interaction_phase.py","tests/test_hierarchy_phase.py"],
    ["tests/test_refolding_phase.py"],
    ["tests/test_benchmark_phase.py"],
]
WORKBENCH_FILES = [
    "tests/test_adapter_equivalence.py",
    "tests/test_worker_and_api.py",
    "tests/test_wb02_persistence.py",
    "tests/test_wb03_live_console.py",
    "tests/test_wb04_curriculum_grammar.py",
    "tests/test_wb05_forensic_structures.py",
    "tests/test_wb06_living_explorer.py",
    "tests/test_wb07_experiments.py",
    "tests/test_wb08_providers.py",
    "tests/test_wb09_plugins_hardening.py",
    "tests/test_wb10_release_polish.py",
]



def run(cmd:list[str], label:str, *, cwd:Path=ROOT)->bool:
    print(f"\n=== {label} ===", flush=True)
    proc=subprocess.run(cmd,cwd=cwd,env=ENV)
    return proc.returncode==0


def main()->int:
    ap=argparse.ArgumentParser(description="Verify Verdant Minds V5 / Workbench 1.0.1 in safe test partitions.")
    ap.add_argument("--with-proofs",action="store_true",help="Also execute final WB-08/WB-09 machine proofs.")
    args=ap.parse_args()
    ok=True
    for i,group in enumerate(ENGINE_GROUPS,1):
        if group == ["tests/test_benchmark_phase.py"]:
            collected=subprocess.run([sys.executable,"-m","pytest","--collect-only","-q",group[0]],cwd=ROOT,env=ENV,capture_output=True,text=True)
            nodes=[line.strip() for line in collected.stdout.splitlines() if "::" in line]
            if collected.returncode!=0 or not nodes:
                print(collected.stdout); print(collected.stderr,file=sys.stderr); ok=False
            for node in nodes:
                ok=run([sys.executable,"-m","pytest","-q",node],f"Engine benchmark {node}") and ok
        else:
            ok=run([sys.executable,"-m","pytest","-q",*group],f"Engine partition {i}/{len(ENGINE_GROUPS)}") and ok
    # Workbench tests are intentionally executed one node per fresh pytest process.
    # This avoids the known long-process numerical/runtime slowdown while preserving
    # exactly the same assertions.
    for file in WORKBENCH_FILES:
        collected=subprocess.run([sys.executable,"-m","pytest","--collect-only","-q",file],cwd=BACKEND,env=ENV,capture_output=True,text=True)
        if collected.returncode!=0:
            print(collected.stdout); print(collected.stderr,file=sys.stderr); ok=False; continue
        nodes=[line.strip() for line in collected.stdout.splitlines() if "::" in line]
        for node in nodes:
            ok=run([sys.executable,"-m","pytest","-q",node],f"Workbench {node}",cwd=BACKEND) and ok
    with tempfile.TemporaryDirectory(prefix="verdant-release-check-") as td:
        ok=run([sys.executable,"run_verdant_workbench.py","--home",td,"--check"],"Startup + artifact diagnostic") and ok
    if args.with_proofs:
        for proof in ["workbench/backend/wb08_proof.py","workbench/backend/wb09_proof.py"]:
            ok=run([sys.executable,proof],f"Machine proof {Path(proof).stem}") and ok
    print("\nVERDANT MINDS V5 / WORKBENCH 1.0.1 RELEASE:","PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__=="__main__":
    raise SystemExit(main())
