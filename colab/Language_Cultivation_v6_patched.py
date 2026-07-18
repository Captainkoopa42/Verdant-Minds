# ==========================================
# VERDANT MINDS â€” Language Cultivation v6
# Branch: V4 | github.com/Captainkoopa42/Verdant-Minds
#
# KEY CHANGES FROM v5:
# - All data moved OFF Drive â†’ /content/verdant_data/ (local ~100GB)
# - Upload zip at start, download zip at end
# - See-and-Say schema fixed: see_and_say_variants in sentences
# - Teaching list uses correct see_and_say_session schema
# - Custom graph evaluator kept as fallback
# ==========================================

import gc

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 1 â€” Install, clone, hardware monitor
# (No Drive mount needed)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from pathlib import Path
import os, sys, json, time, shutil, threading, subprocess, zipfile

REPO_DIR   = Path('/content/Verdant-Minds')
TARGET_REF = "V4"

if not REPO_DIR.exists():
    subprocess.run(['git','clone','--branch',TARGET_REF,
        'https://github.com/Captainkoopa42/Verdant-Minds.git',str(REPO_DIR)],check=False)
else:
    subprocess.run(['git','-C',str(REPO_DIR),'fetch','origin'],check=False)
    subprocess.run(['git','-C',str(REPO_DIR),'checkout',TARGET_REF],check=False)
    subprocess.run(['git','-C',str(REPO_DIR),'pull','--ff-only','origin',TARGET_REF],check=False)

os.chdir(REPO_DIR)
subprocess.run([sys.executable,'-m','pip','uninstall','-y','numpy'],check=False)
subprocess.run([sys.executable,'-m','pip','install','-q','numpy'],check=False)
req = REPO_DIR / 'requirements.txt'
if req.exists():
    subprocess.run([sys.executable,'-m','pip','install','-q','-r',str(req)],check=False)
subprocess.run([sys.executable,'-m','pip','install','-q','-e',str(REPO_DIR)],check=False)
os.environ['PYTHONPATH'] = str(REPO_DIR)
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

print('REPO_DIR =', REPO_DIR)
print('Branch   :', subprocess.run(
    ['git','-C',str(REPO_DIR),'rev-parse','--abbrev-ref','HEAD'],
    capture_output=True,text=True).stdout.strip())
print('Commit   :', subprocess.run(
    ['git','-C',str(REPO_DIR),'log','--oneline','-1'],
    capture_output=True,text=True).stdout.strip())

import psutil

class VerdantHardwareMonitor:
    def __init__(self):
        self.process    = psutil.Process(os.getpid())
        self.peak_ram_mb = 0
        self.running    = True
        self.thread     = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
        print("[Hardware] Monitor initialized.")
    def _monitor(self):
        while self.running:
            self.peak_ram_mb = max(self.peak_ram_mb,
                self.process.memory_info().rss/(1024*1024))
            time.sleep(0.1)
    def snapshot(self, label=""):
        cur = self.process.memory_info().rss/(1024*1024)
        print(f"  [RAM - {label}] Current: {cur:.0f} MB | Peak: {self.peak_ram_mb:.0f} MB")
    def stop(self):
        self.running = False
        print(f"[Hardware] Final Peak RAM: {self.peak_ram_mb:.0f} MB")

verdant_monitor = VerdantHardwareMonitor()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 1.5 â€” Upload existing data OR start fresh
# Data lives at /content/verdant_data/ (local, ~100GB available)
# Upload verdant_data.zip from your machine to restore previous state
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from google.colab import files as colab_files

# â”€â”€ Set a label if running this notebook side-by-side with another
#    Colab tab (e.g. comparing original vs patched runner). Only
#    affects the final downloaded zip filename â€” safe to leave blank.
RUN_LABEL = ""   # e.g. "patched" or "original" â€” no spaces

LOCAL_DATA = Path('/content/verdant_data')
LOCAL_DATA.mkdir(parents=True, exist_ok=True)

# â”€â”€ Set to False if starting completely fresh â”€â”€
UPLOAD_EXISTING = True

if UPLOAD_EXISTING:
    print("Upload verdant_data.zip (your saved checkpoint + shards)")
    print("Press Cancel / skip if starting fresh.\n")
    try:
        uploaded = colab_files.upload()
        if uploaded:
            zip_name = list(uploaded.keys())[0]
            print(f"Extracting {zip_name} ...")
            with zipfile.ZipFile(zip_name, 'r') as zf:
                zf.extractall('/content/')
            os.remove(zip_name)
            print("Extracted to /content/verdant_data/")
            # Show what was restored
            chk = LOCAL_DATA / 'checkpoints' / 'verdant_latest.json'
            shards_dir = LOCAL_DATA / 'checkpoints' / 'verdant_latest_shards' / 'shards'
            n_shards = len(list(shards_dir.glob('*.json'))) if shards_dir.exists() else 0
            print(f"Checkpoint exists: {chk.exists()}")
            print(f"Shard files found: {n_shards}")
        else:
            print("No file uploaded â€” starting fresh.")
    except Exception as exc:
        print(f"Upload skipped ({exc}) â€” starting fresh.")
else:
    print("Starting fresh (UPLOAD_EXISTING=False)")

CHECKPOINT_DIR  = LOCAL_DATA / 'checkpoints'
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_PATH = CHECKPOINT_DIR / 'verdant_latest.json'
print(f"\nData root : {LOCAL_DATA}")
print(f"Checkpoint: {CHECKPOINT_PATH}")

_DISK_MIN_GB = 10  # abort ingest if free space drops below this
_disk_free_gb = shutil.disk_usage('/content').free // (1024**3)
print(f"Disk free : {_disk_free_gb} GB")
if _disk_free_gb < _DISK_MIN_GB:
    raise RuntimeError(
        f"Only {_disk_free_gb} GB free on /content â€” below the "
        f"{_DISK_MIN_GB} GB safety floor. Aborting before ingest to avoid "
        f"a mid-save crash. Free up space (delete old verdant_data.zip "
        f"uploads, restart runtime) before re-running this cell.")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2 â€” Load + PRE-SPLIT until active canvas < 500 nodes
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


# ══════════════════════════════════════════════════════════════
# MONKEY PATCHES — belt-and-suspenders for Colab against GitHub V4
# Permanent copies of these fixes live in the local repo extract
# (Verdant-Minds-4 (2)). Patches remain so a stock V4 clone still
# gets the same behaviour until upstream merges.
#
# Patches applied:
#   [MP-1] load_state sets _checkpoint_path (/tmp thaw fix)
#   [MP-2] thaw() honours lru_cache_size from manifest
#   [MP-2b] thaw() self-heals missing shard files
#   [MP-3] mitosis caps 450/16000 (configure_mitosis below)
#   [MP-4] graph/connections dual-write on prune paths
#   [MP-5] Council influence_weights persist (checkpoint + sidecar)
#   [MP-6] peer downweight under conflict (salience ceiling fix)
# ══════════════════════════════════════════════════════════════

def _apply_monkey_patches():
    """Apply runtime fixes. Safe to re-run; idempotent enough for Colab."""
    import tempfile as _tempfile

    # ── MP-1: load_state sets _checkpoint_path ──────────────
    try:
        from verdant import system as _vsys_module
        _orig_load_state = _vsys_module.VerdantSystem.load_state

        def _patched_load_state(self, path: str) -> None:
            self._checkpoint_path = path
            _orig_load_state(self, path)

        _vsys_module.VerdantSystem.load_state = _patched_load_state
        print("[MP-1] ✓ load_state() patched — _checkpoint_path set from path arg")
    except Exception as e:
        print(f"[MP-1] ✗ load_state patch failed: {e}")

    # ── MP-2 / MP-2b: thaw LRU + missing-shard self-heal ────
    try:
        from verdant.memory import graph as _graph_module

        def _patched_thaw(self, shard_id: str, memory_root) -> None:
            from pathlib import Path as _Path
            shard_id = str(shard_id)
            root = _Path(memory_root)
            if shard_id == self.active_shard_id:
                return
            if self._dirty:
                self.flush_shards(root)
            if shard_id in self._warm_cache:
                canvas = self._warm_cache.pop(shard_id)
            else:
                meta = (self.manifest.get("shards", {}) or {}).get(shard_id, {})
                path_value = (meta.get("path", f"shards/{shard_id}.json")
                              if isinstance(meta, dict)
                              else f"shards/{shard_id}.json")
                target_path = root / str(path_value)
                if not target_path.exists() and not str(path_value).startswith("shards/"):
                    target_path = root / "shards" / str(path_value)
                if not target_path.exists():
                    print(f"[thaw self-heal] shard file missing on disk: "
                          f"{shard_id[:70]} — marking split, staying on "
                          f"active shard '{self.active_shard_id[:60] if self.active_shard_id else 'none'}'")
                    if isinstance(meta, dict):
                        meta["state"] = "split"
                    ci = self.manifest.get("concept_index", {})
                    for label in list(ci.keys()):
                        homes = ci[label] if isinstance(ci[label], list) else [ci[label]]
                        homes = [h for h in homes if h != shard_id]
                        if homes:
                            ci[label] = homes
                        else:
                            del ci[label]
                    return
                from verdant.memory.persistence import load_state as _ls
                document = _ls(target_path)
                from verdant.memory.graph import MemoryWeb as _MW
                canvas = _MW.from_state_dict(
                    document.get("memory_web", document))
            self._strip_ghosts(canvas)
            self.active_canvas = canvas
            self.active_shard_id = shard_id
            self._warm_cache[shard_id] = self.active_canvas
            lru_size = int((self.manifest.get("defaults", {}) or {})
                           .get("lru_cache_size", 2) or 2)
            lru_size = max(1, lru_size)
            while len(self._warm_cache) > lru_size:
                self._warm_cache.pop(next(iter(self._warm_cache)))
            self._refresh_active_manifest(dirty=False)
            self._load_mandatory_bridge_ghosts(root)

        _graph_module.ShardedMemoryWeb.thaw = _patched_thaw
        print("[MP-2] ✓ thaw() patched — lru_cache_size + missing-shard self-heal")
    except Exception as e:
        print(f"[MP-2] ✗ thaw patch failed: {e}")

    # ── MP-4: memory_store/graph edge desync fix ────────────
    try:
        from verdant.memory import graph as _graph_module

        def _remove_connection(self, a, b):
            a, b = str(a), str(b)
            removed = False
            if self.graph.has_edge(a, b):
                self.graph.remove_edge(a, b)
                removed = True
                self.metrics["total_connections"] = max(
                    0, int(self.metrics.get("total_connections", 0)) - 1)
            for node, other in ((a, b), (b, a)):
                if node in self.memory_store:
                    self.memory_store[node]["connections"] = [
                        x for x in self.memory_store[node].get("connections", [])
                        if str(x[0]) != other
                    ]
            return removed

        _graph_module.MemoryWeb.remove_connection = _remove_connection

        def _rebuild_memory_connection_cache(memory_web):
            repaired = 0
            for node in memory_web.graph.nodes:
                if node not in memory_web.memory_store:
                    continue
                connections = []
                for neighbor in memory_web.graph.neighbors(node):
                    weight = float(
                        memory_web.graph[node][neighbor].get("weight", 0.0))
                    connections.append((str(neighbor), weight))
                memory_web.memory_store[node]["connections"] = connections
                repaired += 1
            return repaired

        def _count_memory_divergence(memory_web):
            divergence = []
            for node, data in memory_web.memory_store.items():
                cached = set(str(x[0]) for x in data.get("connections", []))
                graph_neighbors = (
                    set(str(n) for n in memory_web.graph.neighbors(node))
                    if node in memory_web.graph else set())
                if cached != graph_neighbors:
                    divergence.append({
                        "node": node,
                        "missing_from_memory": sorted(graph_neighbors - cached),
                        "phantom_memory_edges": sorted(cached - graph_neighbors),
                    })
            return divergence

        from verdant.memory import basin_dynamics as _bd_module
        _orig_prune = _bd_module.prune_basin_edges
        _orig_regulate = _bd_module.regulate_density

        def _traced_prune_basin_edges(memory_web, *a, **kw):
            before = len(_count_memory_divergence(memory_web))
            result = _orig_prune(memory_web, *a, **kw)
            _rebuild_memory_connection_cache(memory_web)
            after = len(_count_memory_divergence(memory_web))
            if before != after or before > 0:
                print(f"[MP-4] prune_basin_edges: divergence {before}->0 "
                      f"(resynced)")
            return result

        def _traced_regulate_density(memory_web, *a, **kw):
            before = len(_count_memory_divergence(memory_web))
            result = _orig_regulate(memory_web, *a, **kw)
            _rebuild_memory_connection_cache(memory_web)
            after = len(_count_memory_divergence(memory_web))
            if before != after or before > 0:
                print(f"[MP-4] regulate_density: divergence {before}->0 "
                      f"(resynced)")
            return result

        _bd_module.prune_basin_edges = _traced_prune_basin_edges
        _bd_module.regulate_density = _traced_regulate_density

        global rebuild_memory_connection_cache, count_memory_divergence
        rebuild_memory_connection_cache = _rebuild_memory_connection_cache
        count_memory_divergence = _count_memory_divergence

        print("[MP-4] ✓ memory_store/graph sync patched "
              "(remove_connection + prune/regulate resync)")
    except Exception as e:
        print(f"[MP-4] ✗ memory sync patch failed: {e}")

    # ── MP-5: Council persistence (checkpoint + legacy sidecar) ──
    # Prefer kings.council inside the main checkpoint when present
    # (permanent repo fix). Fall back to verdant_latest_council.json
    # for older exports. Never invent weights.
    try:
        from verdant import system as _vsys_module
        _orig_save_state = _vsys_module.VerdantSystem.save_state
        _orig_load_state2 = _vsys_module.VerdantSystem.load_state  # after MP-1

        def _council_payload(council):
            payload = {
                "influence_weights": dict(council.influence_weights),
                "interaction_history": list(council.interaction_history)[-200:],
                "conflict_history": list(getattr(council, "conflict_history", []) or [])[-50:],
                "metrics": dict(getattr(council, "metrics", {}) or {}),
            }
            if hasattr(council, "majority_threshold"):
                payload["majority_threshold"] = float(council.majority_threshold)
            return payload

        def _apply_council_state(council, council_state, source_label):
            if not isinstance(council_state, dict):
                return
            if hasattr(council, "from_state_dict"):
                council.from_state_dict(council_state)
            else:
                weights = council_state.get("influence_weights", {})
                for king, w in (weights or {}).items():
                    if king in council.influence_weights:
                        council.influence_weights[king] = float(w)
                for king in council.influence_weights:
                    council.influence_weights[king] = max(
                        0.5, min(1.5, float(council.influence_weights[king])))
                hist = council_state.get("interaction_history", [])
                if isinstance(hist, list):
                    council.interaction_history = list(hist[-200:])
            print(f"[MP-5] Council weights restored from {source_label}: "
                  f"{council.influence_weights} "
                  f"({len(council.interaction_history)} prior interactions)")

        def _patched_save_state(self, path: str) -> None:
            _orig_save_state(self, path)
            # Always write sidecar for back-compat with older loaders / exports
            try:
                council_state = _council_payload(self.council)
                sidecar = Path(path).with_name(Path(path).stem + "_council.json")
                tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
                tmp.write_text(json.dumps(council_state, indent=2), encoding="utf-8")
                tmp.replace(sidecar)
            except Exception as e:
                print(f"[MP-5] council save failed (non-fatal): {e}")

        def _patched_load_state2(self, path: str) -> None:
            _orig_load_state2(self, path)
            try:
                # 1) Prefer in-checkpoint kings.council (repo permanent fix)
                restored_from_ckpt = False
                try:
                    raw = json.loads(Path(path).read_text(encoding="utf-8"))
                    ck_council = (raw.get("kings") or {}).get("council")
                    if isinstance(ck_council, dict) and ck_council.get("influence_weights"):
                        _apply_council_state(self.council, ck_council, "checkpoint")
                        restored_from_ckpt = True
                except Exception:
                    pass
                # 2) Legacy sidecar if checkpoint had no council block
                if not restored_from_ckpt:
                    sidecar = Path(path).with_name(Path(path).stem + "_council.json")
                    if sidecar.exists():
                        council_state = json.loads(sidecar.read_text(encoding="utf-8"))
                        _apply_council_state(self.council, council_state, "sidecar")
                    else:
                        print(f"[MP-5] no prior council state found "
                              f"({Path(path).stem}_council.json) — "
                              f"starting Council fresh at 1.0/1.0/1.0")
            except Exception as e:
                print(f"[MP-5] council restore failed (non-fatal): {e}")

        _vsys_module.VerdantSystem.save_state = _patched_save_state
        _vsys_module.VerdantSystem.load_state = _patched_load_state2
        print("[MP-5] ✓ Council influence_weights persist "
              "(checkpoint + atomic sidecar, real values only)")
    except Exception as e:
        print(f"[MP-5] ✗ Council persistence patch failed: {e}")

    # ── MP-6: peer downweight under conflict (Defect B) ─────
    # Without this, Ethics=1.5 + peers@1.0 caps ratio at 0.4286
    # → max salience 0.300 < ETHICS_ANCHOR_THRESHOLD 0.35.
    try:
        from verdant.governance import council as _council_module

        def _patched_update_influence(self) -> None:
            if len(self.interaction_history) < 10:
                return
            recent = self.interaction_history[-20:]
            avg_conflicts = sum(r["conflicts"] for r in recent) / len(recent)
            if avg_conflicts > 0.5:
                self.influence_weights["EthicsKing"] = min(
                    1.5, self.influence_weights["EthicsKing"] + 0.01,
                )
                for peer in ("DataKing", "ForefrontKing"):
                    self.influence_weights[peer] = max(
                        0.5, self.influence_weights[peer] - 0.005,
                    )
            for king in self.influence_weights:
                self.influence_weights[king] = max(
                    0.5, min(1.5, self.influence_weights[king]))

        _council_module.ThreeKingsCouncil._update_influence = _patched_update_influence
        print("[MP-6] ✓ Council peer-downweight under conflict "
              "(ethics ratio can clear 0.50 → salience ≥ 0.35)")
    except Exception as e:
        print(f"[MP-6] ✗ influence patch failed: {e}")

    print("[Monkey Patches] All patches applied (MP-1..MP-6).")


def validate_shard_manifest(system, checkpoint_path, label=""):
    """Check every non-split shard in the manifest actually exists on
    disk. Mark any missing ones as split so the router/thaw() never
    tries to load them again, and strip them from concept_index.
    Call this after ANY load_state() call â€” initial load, mid-run
    reload, or eval-isolation restore â€” since all three can leave the
    manifest pointing at shards that were never flushed to disk."""
    shard_root = Path(checkpoint_path).parent / (
        Path(checkpoint_path).stem + "_shards")
    manifest = getattr(system.memory_web, "manifest", {}) or {}
    shards = manifest.get("shards", {}) or {}
    missing = []
    for sid, meta in shards.items():
        if not isinstance(meta, dict):
            continue
        if meta.get("state") == "split":
            continue
        rel = str(meta.get("path", f"shards/{sid}.json"))
        # Handle both "basin_x.json" and "shards/basin_x.json" forms
        candidate = shard_root / rel
        if not candidate.exists() and not rel.startswith("shards/"):
            candidate = shard_root / "shards" / rel
        if not candidate.exists():
            missing.append(sid)

    if missing:
        tag = f" [{label}]" if label else ""
        print(f"[Shard Validate]{tag} {len(missing)} shard(s) in manifest "
              f"missing on disk â€” marking split:")
        for sid in missing:
            print(f"    {sid[:70]}")
            shards[sid]["state"] = "split"
        ci = manifest.get("concept_index", {})
        for concept_label in list(ci.keys()):
            homes = ci[concept_label] if isinstance(ci[concept_label], list) else [ci[concept_label]]
            homes = [h for h in homes if h not in missing]
            if homes:
                ci[concept_label] = homes
            else:
                del ci[concept_label]
        # If the currently active shard itself is gone, fall back to monolith
        if getattr(system.memory_web, "active_shard_id", None) in missing:
            print(f"[Shard Validate]{tag} active shard was missing â€” "
                  f"resetting active_canvas to monolith")
            system.memory_web.active_shard_id = "basin_monolith_000000"
    else:
        tag = f" [{label}]" if label else ""
        print(f"[Shard Validate]{tag} all manifest shards verified on disk.")
    return missing


def write_shard_checksums(checkpoint_path, label=""):
    """Compute and store a SHA-256 checksum for every shard file on
    disk, in a sidecar file next to the manifest. Call this right
    after any save_state() / flush_shards() so we have a known-good
    baseline to compare against later â€” catches silent corruption
    from zip upload/download cycles that json.load() wouldn't notice
    (a truncated-but-still-parseable file, a byte flip inside a
    string value, etc.)."""
    import hashlib
    shard_root = Path(checkpoint_path).parent / (
        Path(checkpoint_path).stem + "_shards")
    shard_dir = shard_root / "shards"
    if not shard_dir.exists():
        return {}
    checksums = {}
    for f in sorted(shard_dir.glob("*.json")):
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        checksums[f.name] = h
    sidecar = shard_root / "shard_checksums.json"
    sidecar.write_text(json.dumps(checksums, indent=2), encoding='utf-8')
    tag = f" [{label}]" if label else ""
    print(f"[Checksum]{tag} wrote {len(checksums)} shard checksums "
          f"-> {sidecar.name}")
    return checksums


def verify_shard_checksums(checkpoint_path, label=""):
    """Compare current shard files against the last-written checksum
    sidecar. Reports mismatches (corruption) and files present in one
    set but not the other (added/removed since last checksum). Does
    NOT abort anything â€” this is diagnostic, not a hard gate, since a
    mismatch here is informational (e.g. legitimately new shards from
    mitosis) rather than always an error."""
    import hashlib
    shard_root = Path(checkpoint_path).parent / (
        Path(checkpoint_path).stem + "_shards")
    shard_dir = shard_root / "shards"
    sidecar = shard_root / "shard_checksums.json"
    tag = f" [{label}]" if label else ""
    if not sidecar.exists():
        print(f"[Checksum]{tag} no prior checksum file to compare against "
              f"â€” run write_shard_checksums() first to establish a baseline.")
        return {"corrupted": [], "new": [], "missing": []}

    prior = json.loads(sidecar.read_text(encoding='utf-8'))
    current = {}
    if shard_dir.exists():
        for f in sorted(shard_dir.glob("*.json")):
            current[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()

    corrupted = [name for name in (set(prior) & set(current))
                 if prior[name] != current[name]]
    new_files = sorted(set(current) - set(prior))
    missing_files = sorted(set(prior) - set(current))

    if corrupted:
        print(f"[Checksum]{tag} CORRUPTION DETECTED in {len(corrupted)} "
              f"shard file(s) â€” checksum mismatch vs last known-good:")
        for name in corrupted:
            print(f"    {name}")
    else:
        print(f"[Checksum]{tag} no corruption detected "
              f"({len(prior & current) if isinstance(prior, set) else len(set(prior)&set(current))} files checked)"
              if False else
              f"[Checksum]{tag} no corruption detected "
              f"({len(set(prior) & set(current))} files checked)")
    if new_files:
        print(f"[Checksum]{tag} {len(new_files)} new shard(s) since last "
              f"checksum (expected after mitosis): {new_files[:5]}")
    if missing_files:
        print(f"[Checksum]{tag} {len(missing_files)} shard(s) from last "
              f"checksum no longer present (expected if split/pruned): "
              f"{missing_files[:5]}")
    return {"corrupted": corrupted, "new": new_files, "missing": missing_files}

_apply_monkey_patches()

from verdant.system import VerdantSystem
from verdant.io.query_interface import QueryInterface

MITOSIS_CAPS = {
    "force": {"max_nodes_per_shard": 128,   "max_edges_per_shard": 4000},
    "watch": {"max_nodes_per_shard": 450,   "max_edges_per_shard": 16000},  # MP-3: tuned from 384/12000
    "safe":  {"max_nodes_per_shard": 10000, "max_edges_per_shard": 250000},
}

def configure_mitosis(system, mode):
    if not hasattr(system.memory_web, "manifest"):
        print("[Shard] No manifest â€” sharded branch not loaded?")
        return
    d = system.memory_web.manifest.setdefault("defaults", {})
    d.update(MITOSIS_CAPS[mode])
    d.setdefault("thaw_penalty", 0.35)
    d.setdefault("thaw_threshold", 0.12)
    d.setdefault("noise_floor", 0.01)
    d["lru_cache_size"] = 8
    print(f"[Shard] mode={mode} caps={MITOSIS_CAPS[mode]} lru=8")

def shard_status(system, label=""):
    mw        = system.memory_web
    manifest  = getattr(mw,"manifest",{}) or {}
    shards    = manifest.get("shards",{}) if isinstance(manifest,dict) else {}
    bridges   = manifest.get("weak_bridge_edges",[]) if isinstance(manifest,dict) else []
    mandatory = [b for b in bridges if b.get("mandatory")]
    active    = getattr(mw,"active_shard_id","raw")
    print(f"\n[Shard Status] {label}")
    print(f"  active: {active[:60]}")
    print(f"  nodes: {mw.graph.number_of_nodes()} | edges: {mw.graph.number_of_edges()}")
    print(f"  shards: {len(shards)} | weak bridges: {len(bridges)} | mandatory: {len(mandatory)}")
    for sid, meta in list(shards.items())[:4]:
        print(f"   - {sid[:50]} state={meta.get('state')} nodes={meta.get('node_count')}")

system = VerdantSystem()
if CHECKPOINT_PATH.exists():
    system.load_state(str(CHECKPOINT_PATH))
    system._checkpoint_path = str(CHECKPOINT_PATH)
    validate_shard_manifest(system, CHECKPOINT_PATH, label="Cell 2 initial load")
    verify_shard_checksums(CHECKPOINT_PATH, label="Cell 2 initial load")
    print("Loaded checkpoint:", CHECKPOINT_PATH)
else:
    print("No checkpoint found â€” starting fresh.")
    system._checkpoint_path = str(CHECKPOINT_PATH)

verdant_monitor.snapshot("After load")
print(f"Graph: {system.memory_web.graph.number_of_nodes()} nodes, "
      f"{system.memory_web.graph.number_of_edges()} edges")

for split_round in range(5):
    n = system.memory_web.graph.number_of_nodes()
    if n <= 500:
        print(f"[Pre-split] Active canvas: {n} nodes â€” safe to proceed.")
        break
    print(f"[Pre-split round {split_round}] {n} nodes > 500 â€” forcing mitosis...")
    configure_mitosis(system, "force")
    system.save_state(str(CHECKPOINT_PATH))
    del system
    gc.collect()
    time.sleep(2)
    system = VerdantSystem()
    system.load_state(str(CHECKPOINT_PATH))
    system._checkpoint_path = str(CHECKPOINT_PATH)
    print(f"  Reloaded: {system.memory_web.graph.number_of_nodes()} nodes")

configure_mitosis(system, "watch")
query_interface = QueryInterface(system)

metrics = system.get_metrics()
BASELINE_STATS = {
    'node_count':  int(system.memory_web.graph.number_of_nodes()),
    'edge_count':  int(system.memory_web.graph.number_of_edges()),
    'basin_count': int(metrics.get('basin_count', 0)),
    't_g':         float(metrics.get('t_g', 0.5)),
}
TG_TRAJECTORY            = [BASELINE_STATS['t_g']]
TRAINING_TOP_ACTIVATIONS = {}
TRAINING_COVERAGE        = {'expected': 0, 'hit': 0}
BASIN_SNAPSHOT_BEFORE    = {
    str(b.get('basin_id')): len(b.get('nodes', []))
    for b in metrics.get('basins', []) if isinstance(b, dict)
}
TOTAL_INGEST_CALLS = 0

print("\nBaseline stats:")
print(json.dumps(BASELINE_STATS, indent=2))
shard_status(system, "Ready for corpus ingest")
verdant_monitor.snapshot("Pre-corpus baseline")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2.5 â€” Write causal corpus WITH see_and_say_variants
# Schema fix: run_session reads see_and_say_variants from sentences
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

CORPUS_SENTENCES_PATH = Path('corpus/sentences/teaching_sentences_physical_world.json')
CORPUS_SENTENCES_PATH.parent.mkdir(parents=True, exist_ok=True)

# Each sentence that maps to a cloze item gets a see_and_say_variants block.
# Format confirmed from see_and_say.py source:
#   {"cloze_id": "...", "masked_sentence": "...", "target_word": "...", "distractor_options": [...]}

CAUSAL_SENTENCES = [
  {"sentence_id":"ts_00001","sentence":"Gravity pulls objects with mass downward.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_001","masked_sentence":"___ pulls objects with mass downward.",
      "target_word":"gravity","distractor_options":["friction","pressure","magnetism"]},
     {"cloze_id":"cs_p_002","masked_sentence":"Gravity pulls objects with ___ downward.",
      "target_word":"mass","distractor_options":["velocity","pressure","charge"]}],
   "relational_map":{"concept_activations_expected":["gravity","mass","downward"],
   "graph_edges_this_sentence_reinforces":[{"from":"gravity","to":"mass","weight_delta":0.8},{"from":"gravity","to":"pulls","weight_delta":0.9},{"from":"pulls","to":"downward","weight_delta":0.7}]}},
  {"sentence_id":"ts_00002","sentence":"High velocity requires greater force to stop.",
   "relational_map":{"concept_activations_expected":["velocity","force","stop"],
   "graph_edges_this_sentence_reinforces":[{"from":"velocity","to":"force","weight_delta":0.8},{"from":"force","to":"stop","weight_delta":0.8},{"from":"velocity","to":"stop","weight_delta":0.6}]}},
  {"sentence_id":"ts_00003","sentence":"Heating a gas increases its pressure inside a sealed container.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_003","masked_sentence":"Heating a gas increases its ___ inside a sealed container.",
      "target_word":"pressure","distractor_options":["volume","temperature","density"]}],
   "relational_map":{"concept_activations_expected":["heat","gas","pressure"],
   "graph_edges_this_sentence_reinforces":[{"from":"heat","to":"pressure","weight_delta":0.9},{"from":"gas","to":"pressure","weight_delta":0.7},{"from":"pressure","to":"volume","weight_delta":0.5}]}},
  {"sentence_id":"ts_00004","sentence":"Dense materials sink below less dense liquids.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_004","masked_sentence":"Dense materials ___ below less dense liquids.",
      "target_word":"sink","distractor_options":["float","rise","expand"]}],
   "relational_map":{"concept_activations_expected":["density","sink","liquid"],
   "graph_edges_this_sentence_reinforces":[{"from":"density","to":"sink","weight_delta":0.9},{"from":"sink","to":"liquid","weight_delta":0.7},{"from":"density","to":"liquid","weight_delta":0.6}]}},
  {"sentence_id":"ts_00005","sentence":"Friction converts kinetic energy into heat.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_005","masked_sentence":"Friction converts kinetic energy into ___.",
      "target_word":"heat","distractor_options":["light","pressure","sound"]}],
   "relational_map":{"concept_activations_expected":["friction","energy","heat"],
   "graph_edges_this_sentence_reinforces":[{"from":"friction","to":"heat","weight_delta":0.9},{"from":"energy","to":"heat","weight_delta":0.8},{"from":"friction","to":"energy","weight_delta":0.7}]}},
  {"sentence_id":"ts_00006","sentence":"Increasing mass increases gravitational attraction.",
   "relational_map":{"concept_activations_expected":["mass","gravity"],
   "graph_edges_this_sentence_reinforces":[{"from":"mass","to":"gravity","weight_delta":0.9},{"from":"mass","to":"attraction","weight_delta":0.7},{"from":"gravity","to":"attraction","weight_delta":0.8}]}},
  {"sentence_id":"ts_00007","sentence":"A compressed spring stores potential energy.",
   "relational_map":{"concept_activations_expected":["compression","energy"],
   "graph_edges_this_sentence_reinforces":[{"from":"compression","to":"energy","weight_delta":0.9},{"from":"spring","to":"energy","weight_delta":0.8},{"from":"compression","to":"spring","weight_delta":0.6}]}},
  {"sentence_id":"ts_00008","sentence":"Electric current flows faster through low resistance wires.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_006","masked_sentence":"Electric current flows faster through low ___ wires.",
      "target_word":"resistance","distractor_options":["density","pressure","mass"]}],
   "relational_map":{"concept_activations_expected":["current","resistance"],
   "graph_edges_this_sentence_reinforces":[{"from":"resistance","to":"current","weight_delta":0.9},{"from":"current","to":"flow","weight_delta":0.8},{"from":"resistance","to":"flow","weight_delta":0.7}]}},
  {"sentence_id":"ts_00009","sentence":"Cold air contracts and becomes denser.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_007","masked_sentence":"Cold air contracts and becomes ___.",
      "target_word":"denser","distractor_options":["lighter","hotter","faster"]}],
   "relational_map":{"concept_activations_expected":["temperature","density"],
   "graph_edges_this_sentence_reinforces":[{"from":"cold","to":"contracts","weight_delta":0.8},{"from":"contracts","to":"density","weight_delta":0.8},{"from":"temperature","to":"density","weight_delta":0.7}]}},
  {"sentence_id":"ts_00010","sentence":"Hot metal expands when its temperature rises.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_008","masked_sentence":"Hot metal ___ when its temperature rises.",
      "target_word":"expands","distractor_options":["contracts","melts","freezes"]}],
   "relational_map":{"concept_activations_expected":["temperature","expansion"],
   "graph_edges_this_sentence_reinforces":[{"from":"temperature","to":"expansion","weight_delta":0.9},{"from":"heat","to":"expansion","weight_delta":0.8},{"from":"metal","to":"expansion","weight_delta":0.6}]}},
  {"sentence_id":"ts_00011","sentence":"Stronger magnetic fields exert greater force on iron.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_009","masked_sentence":"Stronger ___ fields exert greater force on iron.",
      "target_word":"magnetic","distractor_options":["electric","gravitational","thermal"]}],
   "relational_map":{"concept_activations_expected":["magnetic","force","iron"],
   "graph_edges_this_sentence_reinforces":[{"from":"magnetic","to":"force","weight_delta":0.9},{"from":"force","to":"iron","weight_delta":0.8},{"from":"magnetic","to":"iron","weight_delta":0.7}]}},
  {"sentence_id":"ts_00012","sentence":"Acceleration increases when the applied force becomes larger.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_010","masked_sentence":"Acceleration increases when the applied ___ becomes larger.",
      "target_word":"force","distractor_options":["mass","pressure","velocity"]}],
   "relational_map":{"concept_activations_expected":["force","acceleration"],
   "graph_edges_this_sentence_reinforces":[{"from":"force","to":"acceleration","weight_delta":0.9},{"from":"acceleration","to":"velocity","weight_delta":0.7},{"from":"force","to":"velocity","weight_delta":0.6}]}},
  {"sentence_id":"ts_00013","sentence":"Heavy objects require more energy to accelerate.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_011","masked_sentence":"Heavy objects require more energy to ___.",
      "target_word":"accelerate","distractor_options":["float","compress","conduct"]}],
   "relational_map":{"concept_activations_expected":["mass","energy","acceleration"],
   "graph_edges_this_sentence_reinforces":[{"from":"mass","to":"energy","weight_delta":0.8},{"from":"energy","to":"acceleration","weight_delta":0.9},{"from":"mass","to":"acceleration","weight_delta":0.7}]}},
  {"sentence_id":"ts_00014","sentence":"Light travels faster than sound through air.",
   "relational_map":{"concept_activations_expected":["light","speed","sound"],
   "graph_edges_this_sentence_reinforces":[{"from":"light","to":"speed","weight_delta":0.9},{"from":"sound","to":"air","weight_delta":0.7},{"from":"light","to":"sound","weight_delta":0.5}]}},
  {"sentence_id":"ts_00015","sentence":"Pressure rises when the same force acts on a smaller area.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_012","masked_sentence":"Pressure rises when the same force acts on a smaller ___.",
      "target_word":"area","distractor_options":["mass","volume","distance"]}],
   "relational_map":{"concept_activations_expected":["force","pressure","area"],
   "graph_edges_this_sentence_reinforces":[{"from":"force","to":"pressure","weight_delta":0.9},{"from":"area","to":"pressure","weight_delta":0.9},{"from":"pressure","to":"surface","weight_delta":0.6}]}},
  {"sentence_id":"ts_00016","sentence":"Water boils when heat overcomes intermolecular attraction.",
   "relational_map":{"concept_activations_expected":["heat","boiling","water"],
   "graph_edges_this_sentence_reinforces":[{"from":"heat","to":"boiling","weight_delta":0.9},{"from":"boiling","to":"water","weight_delta":0.8},{"from":"heat","to":"water","weight_delta":0.6}]}},
  {"sentence_id":"ts_00017","sentence":"Momentum increases when mass or velocity increases.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_013","masked_sentence":"___ increases when mass or velocity increases.",
      "target_word":"momentum","distractor_options":["pressure","temperature","resistance"]}],
   "relational_map":{"concept_activations_expected":["mass","velocity","momentum"],
   "graph_edges_this_sentence_reinforces":[{"from":"mass","to":"momentum","weight_delta":0.8},{"from":"velocity","to":"momentum","weight_delta":0.8},{"from":"momentum","to":"collision","weight_delta":0.6}]}},
  {"sentence_id":"ts_00018","sentence":"Insulators reduce heat transfer between surfaces.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_014","masked_sentence":"Insulators reduce ___ transfer between surfaces.",
      "target_word":"heat","distractor_options":["current","pressure","momentum"]}],
   "relational_map":{"concept_activations_expected":["insulation","heat","transfer"],
   "graph_edges_this_sentence_reinforces":[{"from":"insulation","to":"heat","weight_delta":0.9},{"from":"heat","to":"transfer","weight_delta":0.8},{"from":"insulation","to":"transfer","weight_delta":0.7}]}},
  {"sentence_id":"ts_00019","sentence":"Conductors allow electricity to move with less resistance.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_015","masked_sentence":"Conductors allow electricity to move with less ___.",
      "target_word":"resistance","distractor_options":["mass","pressure","density"]}],
   "relational_map":{"concept_activations_expected":["conductor","resistance","electricity"],
   "graph_edges_this_sentence_reinforces":[{"from":"conductor","to":"electricity","weight_delta":0.9},{"from":"resistance","to":"electricity","weight_delta":0.8},{"from":"conductor","to":"resistance","weight_delta":0.7}]}},
  {"sentence_id":"ts_00020","sentence":"Higher altitude lowers atmospheric pressure.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_016","masked_sentence":"Higher altitude lowers atmospheric ___.",
      "target_word":"pressure","distractor_options":["temperature","density","resistance"]}],
   "relational_map":{"concept_activations_expected":["altitude","pressure"],
   "graph_edges_this_sentence_reinforces":[{"from":"altitude","to":"pressure","weight_delta":0.9},{"from":"altitude","to":"atmosphere","weight_delta":0.7},{"from":"atmosphere","to":"pressure","weight_delta":0.8}]}},
  {"sentence_id":"ts_00021","sentence":"Radiation transfers heat through empty space.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_017","masked_sentence":"___ transfers heat through empty space.",
      "target_word":"radiation","distractor_options":["conduction","convection","friction"]}],
   "relational_map":{"concept_activations_expected":["radiation","heat","space"],
   "graph_edges_this_sentence_reinforces":[{"from":"radiation","to":"heat","weight_delta":0.9},{"from":"heat","to":"transfer","weight_delta":0.8},{"from":"radiation","to":"space","weight_delta":0.6}]}},
  {"sentence_id":"ts_00022","sentence":"Evaporation cools a surface by removing thermal energy.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_018","masked_sentence":"Evaporation ___ a surface by removing thermal energy.",
      "target_word":"cools","distractor_options":["heats","compresses","charges"]}],
   "relational_map":{"concept_activations_expected":["evaporation","temperature","energy"],
   "graph_edges_this_sentence_reinforces":[{"from":"evaporation","to":"cooling","weight_delta":0.9},{"from":"cooling","to":"temperature","weight_delta":0.8},{"from":"evaporation","to":"energy","weight_delta":0.7}]}},
  {"sentence_id":"ts_00023","sentence":"Greater voltage drives stronger electric current.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_019","masked_sentence":"Greater ___ drives stronger electric current.",
      "target_word":"voltage","distractor_options":["resistance","mass","pressure"]}],
   "relational_map":{"concept_activations_expected":["voltage","current"],
   "graph_edges_this_sentence_reinforces":[{"from":"voltage","to":"current","weight_delta":0.9},{"from":"voltage","to":"resistance","weight_delta":0.7},{"from":"current","to":"resistance","weight_delta":0.8}]}},
  {"sentence_id":"ts_00024","sentence":"Collisions transfer momentum between moving objects.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_020","masked_sentence":"Collisions transfer ___ between moving objects.",
      "target_word":"momentum","distractor_options":["heat","pressure","charge"]}],
   "relational_map":{"concept_activations_expected":["collision","momentum","velocity"],
   "graph_edges_this_sentence_reinforces":[{"from":"collision","to":"momentum","weight_delta":0.9},{"from":"momentum","to":"velocity","weight_delta":0.8},{"from":"collision","to":"velocity","weight_delta":0.7}]}},
  {"sentence_id":"ts_00025","sentence":"Lower temperature slows molecular motion.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_021","masked_sentence":"Lower temperature slows molecular ___.",
      "target_word":"motion","distractor_options":["pressure","density","resistance"]}],
   "relational_map":{"concept_activations_expected":["temperature","motion"],
   "graph_edges_this_sentence_reinforces":[{"from":"temperature","to":"motion","weight_delta":0.9},{"from":"motion","to":"molecule","weight_delta":0.7},{"from":"temperature","to":"molecule","weight_delta":0.6}]}},
  {"sentence_id":"ts_00026","sentence":"Increasing pressure compresses a gas into a smaller volume.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_022","masked_sentence":"Increasing pressure compresses a gas into a smaller ___.",
      "target_word":"volume","distractor_options":["mass","temperature","density"]}],
   "relational_map":{"concept_activations_expected":["pressure","volume","gas"],
   "graph_edges_this_sentence_reinforces":[{"from":"pressure","to":"volume","weight_delta":0.9},{"from":"pressure","to":"gas","weight_delta":0.8},{"from":"gas","to":"volume","weight_delta":0.7}]}},
  {"sentence_id":"ts_00027","sentence":"Buoyant force pushes floating objects upward.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_023","masked_sentence":"___ force pushes floating objects upward.",
      "target_word":"buoyant","distractor_options":["magnetic","gravitational","frictional"]}],
   "relational_map":{"concept_activations_expected":["buoyancy","force","float"],
   "graph_edges_this_sentence_reinforces":[{"from":"buoyancy","to":"force","weight_delta":0.9},{"from":"force","to":"float","weight_delta":0.8},{"from":"buoyancy","to":"float","weight_delta":0.7}]}},
  {"sentence_id":"ts_00028","sentence":"A vacuum prevents sound from traveling.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_024","masked_sentence":"A vacuum prevents ___ from traveling.",
      "target_word":"sound","distractor_options":["heat","light","gravity"]}],
   "relational_map":{"concept_activations_expected":["vacuum","sound"],
   "graph_edges_this_sentence_reinforces":[{"from":"vacuum","to":"sound","weight_delta":0.9},{"from":"sound","to":"medium","weight_delta":0.8},{"from":"vacuum","to":"medium","weight_delta":0.7}]}},
  {"sentence_id":"ts_00029","sentence":"Kinetic energy increases with the square of velocity.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_025","masked_sentence":"Kinetic energy increases with the square of ___.",
      "target_word":"velocity","distractor_options":["mass","pressure","temperature"]}],
   "relational_map":{"concept_activations_expected":["velocity","energy"],
   "graph_edges_this_sentence_reinforces":[{"from":"velocity","to":"energy","weight_delta":0.9},{"from":"energy","to":"motion","weight_delta":0.8},{"from":"velocity","to":"motion","weight_delta":0.7}]}},
  {"sentence_id":"ts_00030","sentence":"Melting ice absorbs heat from its surroundings.",
   "relational_map":{"concept_activations_expected":["heat","melting","temperature"],
   "graph_edges_this_sentence_reinforces":[{"from":"heat","to":"melting","weight_delta":0.9},{"from":"melting","to":"temperature","weight_delta":0.8},{"from":"heat","to":"temperature","weight_delta":0.7}]}},
  {"sentence_id":"ts_00031","sentence":"Electrical resistance converts current into heat.",
   "relational_map":{"concept_activations_expected":["resistance","current","heat"],
   "graph_edges_this_sentence_reinforces":[{"from":"resistance","to":"heat","weight_delta":0.9},{"from":"current","to":"heat","weight_delta":0.7},{"from":"resistance","to":"current","weight_delta":0.8}]}},
  {"sentence_id":"ts_00032","sentence":"Orbiting planets remain bound by gravity.",
   "relational_map":{"concept_activations_expected":["gravity","orbit","planet"],
   "graph_edges_this_sentence_reinforces":[{"from":"gravity","to":"orbit","weight_delta":0.9},{"from":"orbit","to":"planet","weight_delta":0.8},{"from":"gravity","to":"planet","weight_delta":0.7}]}},
  {"sentence_id":"ts_00033","sentence":"More force produces greater acceleration on the same mass.",
   "relational_map":{"concept_activations_expected":["force","acceleration","mass"],
   "graph_edges_this_sentence_reinforces":[{"from":"force","to":"acceleration","weight_delta":0.9},{"from":"mass","to":"acceleration","weight_delta":0.7},{"from":"force","to":"mass","weight_delta":0.5}]}},
  {"sentence_id":"ts_00034","sentence":"Increasing surface area speeds up evaporation.",
   "relational_map":{"concept_activations_expected":["surface","evaporation"],
   "graph_edges_this_sentence_reinforces":[{"from":"surface","to":"evaporation","weight_delta":0.9},{"from":"evaporation","to":"temperature","weight_delta":0.7},{"from":"surface","to":"temperature","weight_delta":0.5}]}},
  {"sentence_id":"ts_00035","sentence":"Wave frequency increases as wavelength decreases.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_026","masked_sentence":"___ increases as wavelength decreases.",
      "target_word":"frequency","distractor_options":["amplitude","pressure","velocity"]}],
   "relational_map":{"concept_activations_expected":["frequency","wavelength","wave"],
   "graph_edges_this_sentence_reinforces":[{"from":"wavelength","to":"frequency","weight_delta":0.9},{"from":"frequency","to":"wave","weight_delta":0.8},{"from":"wavelength","to":"wave","weight_delta":0.7}]}},
  {"sentence_id":"ts_00036","sentence":"Charged particles accelerate inside electric fields.",
   "relational_map":{"concept_activations_expected":["charge","acceleration","field"],
   "graph_edges_this_sentence_reinforces":[{"from":"field","to":"acceleration","weight_delta":0.9},{"from":"charge","to":"field","weight_delta":0.8},{"from":"charge","to":"acceleration","weight_delta":0.7}]}},
  {"sentence_id":"ts_00037","sentence":"Greater density increases the weight of equal volumes.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_027","masked_sentence":"Greater density increases the ___ of equal volumes.",
      "target_word":"weight","distractor_options":["pressure","velocity","temperature"]}],
   "relational_map":{"concept_activations_expected":["density","weight","volume"],
   "graph_edges_this_sentence_reinforces":[{"from":"density","to":"weight","weight_delta":0.9},{"from":"volume","to":"weight","weight_delta":0.7},{"from":"density","to":"volume","weight_delta":0.6}]}},
  {"sentence_id":"ts_00038","sentence":"Turbulence increases drag on fast-moving objects.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_028","masked_sentence":"Turbulence increases ___ on fast-moving objects.",
      "target_word":"drag","distractor_options":["lift","pressure","mass"]}],
   "relational_map":{"concept_activations_expected":["drag","velocity","friction"],
   "graph_edges_this_sentence_reinforces":[{"from":"turbulence","to":"drag","weight_delta":0.9},{"from":"velocity","to":"drag","weight_delta":0.8},{"from":"turbulence","to":"velocity","weight_delta":0.6}]}},
  {"sentence_id":"ts_00039","sentence":"Sound waves lose energy as they travel through matter.",
   "relational_map":{"concept_activations_expected":["sound","energy","matter"],
   "graph_edges_this_sentence_reinforces":[{"from":"sound","to":"energy","weight_delta":0.8},{"from":"energy","to":"matter","weight_delta":0.7},{"from":"sound","to":"matter","weight_delta":0.6}]}},
  {"sentence_id":"ts_00040","sentence":"Increasing temperature raises the pressure of trapped gas.",
   "relational_map":{"concept_activations_expected":["temperature","pressure","gas"],
   "graph_edges_this_sentence_reinforces":[{"from":"temperature","to":"pressure","weight_delta":0.9},{"from":"gas","to":"pressure","weight_delta":0.7},{"from":"temperature","to":"gas","weight_delta":0.6}]}},
  {"sentence_id":"ts_00041","sentence":"Mechanical work transfers energy between systems.",
   "relational_map":{"concept_activations_expected":["work","energy","force"],
   "graph_edges_this_sentence_reinforces":[{"from":"work","to":"energy","weight_delta":0.9},{"from":"force","to":"work","weight_delta":0.8},{"from":"energy","to":"system","weight_delta":0.7}]}},
  {"sentence_id":"ts_00042","sentence":"Stable equilibrium restores objects toward their original position.",
   "relational_map":{"concept_activations_expected":["equilibrium","force","position"],
   "graph_edges_this_sentence_reinforces":[{"from":"equilibrium","to":"force","weight_delta":0.9},{"from":"force","to":"position","weight_delta":0.8},{"from":"equilibrium","to":"position","weight_delta":0.7}]}},
  {"sentence_id":"ts_00043","sentence":"Lower resistance allows higher current at constant voltage.",
   "relational_map":{"concept_activations_expected":["resistance","current","voltage"],
   "graph_edges_this_sentence_reinforces":[{"from":"resistance","to":"current","weight_delta":0.9},{"from":"voltage","to":"current","weight_delta":0.8},{"from":"voltage","to":"resistance","weight_delta":0.7}]}},
  {"sentence_id":"ts_00044","sentence":"Objects in free fall accelerate toward Earth.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_029","masked_sentence":"Objects in free fall ___ toward Earth.",
      "target_word":"accelerate","distractor_options":["float","decelerate","orbit"]}],
   "relational_map":{"concept_activations_expected":["gravity","acceleration","fall"],
   "graph_edges_this_sentence_reinforces":[{"from":"gravity","to":"acceleration","weight_delta":0.9},{"from":"fall","to":"acceleration","weight_delta":0.8},{"from":"gravity","to":"fall","weight_delta":0.7}]}},
  {"sentence_id":"ts_00045","sentence":"Chemical energy converts into electrical energy in a battery.",
   "relational_map":{"concept_activations_expected":["energy","electricity","chemical"],
   "graph_edges_this_sentence_reinforces":[{"from":"chemical","to":"energy","weight_delta":0.8},{"from":"energy","to":"electricity","weight_delta":0.9},{"from":"chemical","to":"electricity","weight_delta":0.7}]}},
  {"sentence_id":"ts_00046","sentence":"Magnetic fields can deflect moving charged particles.",
   "relational_map":{"concept_activations_expected":["magnetic","charge","motion"],
   "graph_edges_this_sentence_reinforces":[{"from":"magnetic","to":"charge","weight_delta":0.9},{"from":"charge","to":"motion","weight_delta":0.8},{"from":"magnetic","to":"motion","weight_delta":0.7}]}},
  {"sentence_id":"ts_00047","sentence":"Thermal conduction moves heat from hot to cold regions.",
   "relational_map":{"concept_activations_expected":["heat","conduction","temperature"],
   "graph_edges_this_sentence_reinforces":[{"from":"heat","to":"conduction","weight_delta":0.9},{"from":"conduction","to":"temperature","weight_delta":0.8},{"from":"temperature","to":"heat","weight_delta":0.7}]}},
  {"sentence_id":"ts_00048","sentence":"Stretching a spring stores elastic potential energy.",
   "relational_map":{"concept_activations_expected":["spring","energy","force"],
   "graph_edges_this_sentence_reinforces":[{"from":"spring","to":"energy","weight_delta":0.9},{"from":"force","to":"spring","weight_delta":0.8},{"from":"energy","to":"force","weight_delta":0.6}]}},
  {"sentence_id":"ts_00049","sentence":"Air resistance slows falling objects as velocity increases.",
   "relational_map":{"concept_activations_expected":["drag","velocity","gravity"],
   "graph_edges_this_sentence_reinforces":[{"from":"drag","to":"velocity","weight_delta":0.9},{"from":"velocity","to":"gravity","weight_delta":0.7},{"from":"drag","to":"gravity","weight_delta":0.6}]}},
  {"sentence_id":"ts_00050","sentence":"Nuclear reactions convert mass directly into energy.",
   "see_and_say_variants":[
     {"cloze_id":"cs_p_030","masked_sentence":"Nuclear reactions convert mass directly into ___.",
      "target_word":"energy","distractor_options":["heat","pressure","motion"]}],
   "relational_map":{"concept_activations_expected":["mass","energy","reaction"],
   "graph_edges_this_sentence_reinforces":[{"from":"mass","to":"energy","weight_delta":0.9},{"from":"reaction","to":"energy","weight_delta":0.8},{"from":"mass","to":"reaction","weight_delta":0.7}]}}
]

CORPUS_SENTENCES_PATH.write_text(json.dumps(CAUSAL_SENTENCES, indent=2), encoding='utf-8')
n_with_variants = sum(1 for s in CAUSAL_SENTENCES if s.get('see_and_say_variants'))
print(f"Wrote {len(CAUSAL_SENTENCES)} sentences ({n_with_variants} with see_and_say_variants)")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2.6 â€” Write teaching list (correct schema for run_session)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

TEACHING_LIST_PATH = Path('corpus/lists/teaching_list_physical_world.json')
TEACHING_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)

# Confirmed schema from see_and_say.py:
# teaching_list.get("see_and_say_session") -> session dict
# session.get("cloze_items") -> list of cloze_id strings
# Cloze item data lives in sentences["see_and_say_variants"]

CLOZE_IDS = [f"cs_p_{i:03d}" for i in range(1, 31)]

TEACHING_LIST = {
  "see_and_say_session": {
    "session_id": "sas_physical_v2",
    "pass_threshold": 0.6,
    "cloze_items": CLOZE_IDS
  },
  "target_concepts": [
    "gravity","mass","pressure","sink","heat","resistance","denser","expands",
    "magnetic","force","accelerate","area","momentum","radiation","cools",
    "voltage","motion","volume","buoyant","sound","velocity","frequency",
    "weight","drag","energy","temperature","friction","density","current","orbit"
  ]
}

TEACHING_LIST_PATH.write_text(json.dumps(TEACHING_LIST, indent=2), encoding='utf-8')
print(f"Wrote teaching list with {len(CLOZE_IDS)} cloze IDs")
print(f"Session: {TEACHING_LIST['see_and_say_session']['session_id']}")
print(f"Schema: see_and_say_session.cloze_items + sentences.see_and_say_variants")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2.7 â€” Write ecology corpus
# 50 causal ecology sentences with see_and_say_variants
# Cross-links to physics concepts already in the graph
# Pacific Northwest / forestry weighted â€” Will's actual domain
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

ECOLOGY_SENTENCES_PATH = Path('corpus/sentences/teaching_sentences_ecology.json')
ECOLOGY_SENTENCES_PATH.parent.mkdir(parents=True, exist_ok=True)

ECOLOGY_SENTENCES = [
  {"sentence_id":"te_00001","sentence":"Photosynthesis converts sunlight into chemical energy stored in plants.",
   "see_and_say_variants":[
     {"cloze_id":"ce_001","masked_sentence":"Photosynthesis converts ___ into chemical energy stored in plants.",
      "target_word":"sunlight","distractor_options":["rainfall","pressure","gravity"]},
     {"cloze_id":"ce_002","masked_sentence":"Photosynthesis converts sunlight into chemical ___ stored in plants.",
      "target_word":"energy","distractor_options":["mass","pressure","density"]}],
   "relational_map":{"concept_activations_expected":["photosynthesis","sunlight","energy","plant"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"photosynthesis","to":"sunlight","weight_delta":0.9},
     {"from":"photosynthesis","to":"energy","weight_delta":0.9},
     {"from":"photosynthesis","to":"plant","weight_delta":0.8},
     {"from":"sunlight","to":"energy","weight_delta":0.7}]}},

  {"sentence_id":"te_00002","sentence":"Decomposers break down dead matter and return nutrients to the soil.",
   "see_and_say_variants":[
     {"cloze_id":"ce_003","masked_sentence":"Decomposers break down dead matter and return ___ to the soil.",
      "target_word":"nutrients","distractor_options":["water","heat","pressure"]}],
   "relational_map":{"concept_activations_expected":["decomposer","nutrient","soil"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"decomposer","to":"nutrient","weight_delta":0.9},
     {"from":"decomposer","to":"soil","weight_delta":0.8},
     {"from":"nutrient","to":"soil","weight_delta":0.8}]}},

  {"sentence_id":"te_00003","sentence":"Predators control prey populations by removing individuals from the herd.",
   "see_and_say_variants":[
     {"cloze_id":"ce_004","masked_sentence":"Predators control ___ populations by removing individuals from the herd.",
      "target_word":"prey","distractor_options":["plant","soil","water"]}],
   "relational_map":{"concept_activations_expected":["predator","prey","population"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"predator","to":"prey","weight_delta":0.9},
     {"from":"predator","to":"population","weight_delta":0.8},
     {"from":"prey","to":"population","weight_delta":0.7}]}},

  {"sentence_id":"te_00004","sentence":"Fire clears accumulated fuel and releases nutrients locked in dead biomass.",
   "see_and_say_variants":[
     {"cloze_id":"ce_005","masked_sentence":"Fire clears accumulated ___ and releases nutrients locked in dead biomass.",
      "target_word":"fuel","distractor_options":["water","soil","canopy"]}],
   "relational_map":{"concept_activations_expected":["fire","fuel","nutrient","biomass"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"fire","to":"fuel","weight_delta":0.9},
     {"from":"fire","to":"nutrient","weight_delta":0.8},
     {"from":"fuel","to":"biomass","weight_delta":0.7},
     {"from":"fire","to":"biomass","weight_delta":0.8}]}},

  {"sentence_id":"te_00005","sentence":"Canopy trees intercept rainfall and reduce erosion on forest slopes.",
   "see_and_say_variants":[
     {"cloze_id":"ce_006","masked_sentence":"Canopy trees intercept rainfall and reduce ___ on forest slopes.",
      "target_word":"erosion","distractor_options":["sunlight","temperature","pressure"]}],
   "relational_map":{"concept_activations_expected":["canopy","rainfall","erosion","slope"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"canopy","to":"rainfall","weight_delta":0.8},
     {"from":"canopy","to":"erosion","weight_delta":0.9},
     {"from":"rainfall","to":"erosion","weight_delta":0.8},
     {"from":"erosion","to":"slope","weight_delta":0.7}]}},

  {"sentence_id":"te_00006","sentence":"Mycorrhizal fungi extend root networks and transfer water and nutrients to trees.",
   "see_and_say_variants":[
     {"cloze_id":"ce_007","masked_sentence":"Mycorrhizal ___ extend root networks and transfer water and nutrients to trees.",
      "target_word":"fungi","distractor_options":["bacteria","insects","roots"]}],
   "relational_map":{"concept_activations_expected":["fungi","root","water","nutrient"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"fungi","to":"root","weight_delta":0.9},
     {"from":"fungi","to":"water","weight_delta":0.8},
     {"from":"fungi","to":"nutrient","weight_delta":0.8},
     {"from":"root","to":"nutrient","weight_delta":0.7}]}},

  {"sentence_id":"te_00007","sentence":"Herbivores convert plant biomass into animal tissue through digestion.",
   "see_and_say_variants":[
     {"cloze_id":"ce_008","masked_sentence":"Herbivores convert plant ___ into animal tissue through digestion.",
      "target_word":"biomass","distractor_options":["water","sunlight","soil"]}],
   "relational_map":{"concept_activations_expected":["herbivore","plant","biomass","energy"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"herbivore","to":"plant","weight_delta":0.9},
     {"from":"herbivore","to":"biomass","weight_delta":0.8},
     {"from":"biomass","to":"energy","weight_delta":0.7},
     {"from":"plant","to":"biomass","weight_delta":0.8}]}},

  {"sentence_id":"te_00008","sentence":"Watersheds collect precipitation and channel runoff toward streams and rivers.",
   "see_and_say_variants":[
     {"cloze_id":"ce_009","masked_sentence":"Watersheds collect ___ and channel runoff toward streams and rivers.",
      "target_word":"precipitation","distractor_options":["sunlight","nutrients","biomass"]}],
   "relational_map":{"concept_activations_expected":["watershed","precipitation","stream","runoff"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"watershed","to":"precipitation","weight_delta":0.9},
     {"from":"watershed","to":"stream","weight_delta":0.8},
     {"from":"precipitation","to":"runoff","weight_delta":0.8},
     {"from":"runoff","to":"stream","weight_delta":0.7}]}},

  {"sentence_id":"te_00009","sentence":"Nitrogen-fixing bacteria convert atmospheric nitrogen into compounds plants can absorb.",
   "see_and_say_variants":[
     {"cloze_id":"ce_010","masked_sentence":"Nitrogen-fixing bacteria convert atmospheric ___ into compounds plants can absorb.",
      "target_word":"nitrogen","distractor_options":["carbon","oxygen","water"]}],
   "relational_map":{"concept_activations_expected":["bacteria","nitrogen","soil","nutrient"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"bacteria","to":"nitrogen","weight_delta":0.9},
     {"from":"nitrogen","to":"soil","weight_delta":0.8},
     {"from":"nitrogen","to":"nutrient","weight_delta":0.9},
     {"from":"bacteria","to":"soil","weight_delta":0.7}]}},

  {"sentence_id":"te_00010","sentence":"Apex predators reduce overgrazing by limiting herbivore populations.",
   "see_and_say_variants":[
     {"cloze_id":"ce_011","masked_sentence":"Apex predators reduce ___ by limiting herbivore populations.",
      "target_word":"overgrazing","distractor_options":["erosion","succession","drought"]}],
   "relational_map":{"concept_activations_expected":["predator","herbivore","population","balance"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"predator","to":"herbivore","weight_delta":0.9},
     {"from":"predator","to":"population","weight_delta":0.8},
     {"from":"herbivore","to":"overgrazing","weight_delta":0.9},
     {"from":"predator","to":"overgrazing","weight_delta":0.8}]}},

  {"sentence_id":"te_00011","sentence":"Competition for sunlight drives trees to grow taller in dense forest stands.",
   "relational_map":{"concept_activations_expected":["competition","sunlight","growth","forest"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"competition","to":"sunlight","weight_delta":0.9},
     {"from":"competition","to":"growth","weight_delta":0.8},
     {"from":"sunlight","to":"growth","weight_delta":0.8}]}},

  {"sentence_id":"te_00012","sentence":"Soil moisture regulates seed germination and determines root development depth.",
   "see_and_say_variants":[
     {"cloze_id":"ce_012","masked_sentence":"Soil ___ regulates seed germination and determines root development depth.",
      "target_word":"moisture","distractor_options":["temperature","density","pressure"]}],
   "relational_map":{"concept_activations_expected":["soil","moisture","germination","root"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"soil","to":"moisture","weight_delta":0.9},
     {"from":"moisture","to":"germination","weight_delta":0.9},
     {"from":"moisture","to":"root","weight_delta":0.8},
     {"from":"germination","to":"root","weight_delta":0.7}]}},

  {"sentence_id":"te_00013","sentence":"Keystone species have outsized effects on ecosystem structure when removed.",
   "see_and_say_variants":[
     {"cloze_id":"ce_013","masked_sentence":"___ species have outsized effects on ecosystem structure when removed.",
      "target_word":"keystone","distractor_options":["pioneer","canopy","prey"]}],
   "relational_map":{"concept_activations_expected":["keystone","ecosystem","species","structure"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"keystone","to":"ecosystem","weight_delta":0.9},
     {"from":"keystone","to":"species","weight_delta":0.8},
     {"from":"species","to":"ecosystem","weight_delta":0.7}]}},

  {"sentence_id":"te_00014","sentence":"Pollinators transfer pollen between flowers enabling plant reproduction.",
   "see_and_say_variants":[
     {"cloze_id":"ce_014","masked_sentence":"Pollinators transfer ___ between flowers enabling plant reproduction.",
      "target_word":"pollen","distractor_options":["nutrients","water","seeds"]}],
   "relational_map":{"concept_activations_expected":["pollinator","pollen","flower","reproduction"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"pollinator","to":"pollen","weight_delta":0.9},
     {"from":"pollinator","to":"flower","weight_delta":0.8},
     {"from":"pollen","to":"reproduction","weight_delta":0.9},
     {"from":"flower","to":"reproduction","weight_delta":0.8}]}},

  {"sentence_id":"te_00015","sentence":"Succession replaces pioneer species with more complex plant communities over time.",
   "see_and_say_variants":[
     {"cloze_id":"ce_015","masked_sentence":"___ replaces pioneer species with more complex plant communities over time.",
      "target_word":"succession","distractor_options":["erosion","competition","migration"]}],
   "relational_map":{"concept_activations_expected":["succession","pioneer","community","plant"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"succession","to":"pioneer","weight_delta":0.9},
     {"from":"succession","to":"community","weight_delta":0.8},
     {"from":"pioneer","to":"community","weight_delta":0.7}]}},

  {"sentence_id":"te_00016","sentence":"Snowpack accumulation determines summer water availability in mountain watersheds.",
   "see_and_say_variants":[
     {"cloze_id":"ce_016","masked_sentence":"___ accumulation determines summer water availability in mountain watersheds.",
      "target_word":"snowpack","distractor_options":["canopy","biomass","soil"]}],
   "relational_map":{"concept_activations_expected":["snowpack","water","watershed","mountain"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"snowpack","to":"water","weight_delta":0.9},
     {"from":"snowpack","to":"watershed","weight_delta":0.8},
     {"from":"water","to":"watershed","weight_delta":0.8},
     {"from":"snowpack","to":"mountain","weight_delta":0.7}]}},

  {"sentence_id":"te_00017","sentence":"Carbon stored in old-growth trees returns to the atmosphere when forests burn.",
   "see_and_say_variants":[
     {"cloze_id":"ce_017","masked_sentence":"___ stored in old-growth trees returns to the atmosphere when forests burn.",
      "target_word":"carbon","distractor_options":["nitrogen","water","pollen"]}],
   "relational_map":{"concept_activations_expected":["carbon","forest","fire","atmosphere"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"carbon","to":"forest","weight_delta":0.9},
     {"from":"fire","to":"carbon","weight_delta":0.9},
     {"from":"carbon","to":"atmosphere","weight_delta":0.8},
     {"from":"forest","to":"fire","weight_delta":0.7}]}},

  {"sentence_id":"te_00018","sentence":"Root systems bind soil particles together and prevent slope failure after heavy rain.",
   "see_and_say_variants":[
     {"cloze_id":"ce_018","masked_sentence":"Root systems bind soil particles together and prevent slope ___ after heavy rain.",
      "target_word":"failure","distractor_options":["erosion","succession","drought"]}],
   "relational_map":{"concept_activations_expected":["root","soil","erosion","slope"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"root","to":"soil","weight_delta":0.9},
     {"from":"root","to":"erosion","weight_delta":0.9},
     {"from":"soil","to":"slope","weight_delta":0.7},
     {"from":"erosion","to":"slope","weight_delta":0.8}]}},

  {"sentence_id":"te_00019","sentence":"Shade-tolerant species survive beneath the canopy by using filtered light efficiently.",
   "relational_map":{"concept_activations_expected":["shade","canopy","light","adaptation"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"shade","to":"canopy","weight_delta":0.9},
     {"from":"canopy","to":"light","weight_delta":0.8},
     {"from":"shade","to":"adaptation","weight_delta":0.7},
     {"from":"light","to":"adaptation","weight_delta":0.6}]}},

  {"sentence_id":"te_00020","sentence":"Nutrient runoff from disturbed soil enters streams and reduces water quality.",
   "see_and_say_variants":[
     {"cloze_id":"ce_019","masked_sentence":"Nutrient ___ from disturbed soil enters streams and reduces water quality.",
      "target_word":"runoff","distractor_options":["succession","migration","decomposition"]}],
   "relational_map":{"concept_activations_expected":["nutrient","runoff","stream","soil"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"nutrient","to":"runoff","weight_delta":0.9},
     {"from":"runoff","to":"stream","weight_delta":0.9},
     {"from":"soil","to":"runoff","weight_delta":0.8}]}},

  {"sentence_id":"te_00021","sentence":"Thermal gradients in water columns determine where fish species can survive.",
   "relational_map":{"concept_activations_expected":["temperature","water","fish","habitat"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"temperature","to":"water","weight_delta":0.8},
     {"from":"temperature","to":"fish","weight_delta":0.9},
     {"from":"fish","to":"habitat","weight_delta":0.8},
     {"from":"temperature","to":"habitat","weight_delta":0.7}]}},

  {"sentence_id":"te_00022","sentence":"Snags provide nesting cavities for birds and shelter for small mammals.",
   "see_and_say_variants":[
     {"cloze_id":"ce_020","masked_sentence":"___ provide nesting cavities for birds and shelter for small mammals.",
      "target_word":"snags","distractor_options":["canopy","roots","fungi"]}],
   "relational_map":{"concept_activations_expected":["snag","habitat","bird","cavity"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"snag","to":"habitat","weight_delta":0.9},
     {"from":"snag","to":"bird","weight_delta":0.9},
     {"from":"snag","to":"cavity","weight_delta":0.9},
     {"from":"bird","to":"habitat","weight_delta":0.7}]}},

  {"sentence_id":"te_00023","sentence":"Ground fire removes ladder fuels and reduces the risk of catastrophic crown fire.",
   "see_and_say_variants":[
     {"cloze_id":"ce_021","masked_sentence":"Ground fire removes ladder ___ and reduces the risk of catastrophic crown fire.",
      "target_word":"fuels","distractor_options":["canopy","biomass","nutrients"]}],
   "relational_map":{"concept_activations_expected":["fire","fuel","risk","canopy"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"fire","to":"fuel","weight_delta":0.9},
     {"from":"fuel","to":"risk","weight_delta":0.8},
     {"from":"fire","to":"canopy","weight_delta":0.8},
     {"from":"fuel","to":"canopy","weight_delta":0.7}]}},

  {"sentence_id":"te_00024","sentence":"Evapotranspiration from forest canopies returns water vapor to the atmosphere.",
   "see_and_say_variants":[
     {"cloze_id":"ce_022","masked_sentence":"Evapotranspiration from forest canopies returns water ___ to the atmosphere.",
      "target_word":"vapor","distractor_options":["nutrients","carbon","pressure"]}],
   "relational_map":{"concept_activations_expected":["evaporation","canopy","water","atmosphere"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"evaporation","to":"canopy","weight_delta":0.8},
     {"from":"evaporation","to":"water","weight_delta":0.9},
     {"from":"water","to":"atmosphere","weight_delta":0.8},
     {"from":"canopy","to":"atmosphere","weight_delta":0.7}]}},

  {"sentence_id":"te_00025","sentence":"Browsing pressure from ungulates determines shrub density in forest meadows.",
   "relational_map":{"concept_activations_expected":["herbivore","browsing","density","vegetation"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"herbivore","to":"browsing","weight_delta":0.9},
     {"from":"browsing","to":"density","weight_delta":0.8},
     {"from":"browsing","to":"vegetation","weight_delta":0.8}]}},

  {"sentence_id":"te_00026","sentence":"Deadfall sequesters carbon and creates microhabitat structure on the forest floor.",
   "see_and_say_variants":[
     {"cloze_id":"ce_023","masked_sentence":"Deadfall sequesters ___ and creates microhabitat structure on the forest floor.",
      "target_word":"carbon","distractor_options":["nitrogen","water","pollen"]}],
   "relational_map":{"concept_activations_expected":["deadfall","carbon","habitat","soil"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"deadfall","to":"carbon","weight_delta":0.9},
     {"from":"deadfall","to":"habitat","weight_delta":0.8},
     {"from":"deadfall","to":"soil","weight_delta":0.7},
     {"from":"carbon","to":"soil","weight_delta":0.6}]}},

  {"sentence_id":"te_00027","sentence":"Seed dispersal by animals expands plant populations across the landscape.",
   "see_and_say_variants":[
     {"cloze_id":"ce_024","masked_sentence":"Seed ___ by animals expands plant populations across the landscape.",
      "target_word":"dispersal","distractor_options":["germination","competition","succession"]}],
   "relational_map":{"concept_activations_expected":["seed","dispersal","animal","population"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"seed","to":"dispersal","weight_delta":0.9},
     {"from":"dispersal","to":"population","weight_delta":0.8},
     {"from":"animal","to":"dispersal","weight_delta":0.9},
     {"from":"seed","to":"population","weight_delta":0.7}]}},

  {"sentence_id":"te_00028","sentence":"Aquifers store groundwater filtered through soil and rock layers over centuries.",
   "see_and_say_variants":[
     {"cloze_id":"ce_025","masked_sentence":"___ store groundwater filtered through soil and rock layers over centuries.",
      "target_word":"aquifers","distractor_options":["watersheds","canopies","glaciers"]}],
   "relational_map":{"concept_activations_expected":["aquifer","groundwater","soil","water"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"aquifer","to":"groundwater","weight_delta":0.9},
     {"from":"aquifer","to":"soil","weight_delta":0.8},
     {"from":"groundwater","to":"water","weight_delta":0.9},
     {"from":"soil","to":"water","weight_delta":0.7}]}},

  {"sentence_id":"te_00029","sentence":"Wildfire intensity increases with fuel moisture loss and rising wind velocity.",
   "relational_map":{"concept_activations_expected":["fire","fuel","moisture","wind"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"fire","to":"fuel","weight_delta":0.9},
     {"from":"fuel","to":"moisture","weight_delta":0.9},
     {"from":"fire","to":"wind","weight_delta":0.8},
     {"from":"moisture","to":"fire","weight_delta":0.8}]}},

  {"sentence_id":"te_00030","sentence":"Riparian zones buffer streams from sediment and regulate water temperature.",
   "see_and_say_variants":[
     {"cloze_id":"ce_026","masked_sentence":"___ zones buffer streams from sediment and regulate water temperature.",
      "target_word":"riparian","distractor_options":["alpine","canopy","wetland"]}],
   "relational_map":{"concept_activations_expected":["riparian","stream","sediment","temperature"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"riparian","to":"stream","weight_delta":0.9},
     {"from":"riparian","to":"sediment","weight_delta":0.8},
     {"from":"riparian","to":"temperature","weight_delta":0.8},
     {"from":"stream","to":"sediment","weight_delta":0.7}]}},

  {"sentence_id":"te_00031","sentence":"Lichens colonize bare rock and begin the slow process of soil formation.",
   "see_and_say_variants":[
     {"cloze_id":"ce_027","masked_sentence":"Lichens colonize bare rock and begin the slow process of ___ formation.",
      "target_word":"soil","distractor_options":["habitat","canopy","biomass"]}],
   "relational_map":{"concept_activations_expected":["lichen","rock","soil","succession"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"lichen","to":"rock","weight_delta":0.9},
     {"from":"lichen","to":"soil","weight_delta":0.9},
     {"from":"lichen","to":"succession","weight_delta":0.8},
     {"from":"rock","to":"soil","weight_delta":0.7}]}},

  {"sentence_id":"te_00032","sentence":"Trophic cascades propagate through food webs when apex predators disappear.",
   "see_and_say_variants":[
     {"cloze_id":"ce_028","masked_sentence":"Trophic ___ propagate through food webs when apex predators disappear.",
      "target_word":"cascades","distractor_options":["succession","competition","dispersal"]}],
   "relational_map":{"concept_activations_expected":["trophic","predator","food_web","cascade"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trophic","to":"predator","weight_delta":0.8},
     {"from":"trophic","to":"food_web","weight_delta":0.9},
     {"from":"predator","to":"cascade","weight_delta":0.8},
     {"from":"food_web","to":"cascade","weight_delta":0.8}]}},

  {"sentence_id":"te_00033","sentence":"Mycorrhizal networks transfer carbon and nutrients between connected trees underground.",
   "relational_map":{"concept_activations_expected":["fungi","carbon","nutrient","root"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"fungi","to":"carbon","weight_delta":0.8},
     {"from":"fungi","to":"nutrient","weight_delta":0.9},
     {"from":"carbon","to":"nutrient","weight_delta":0.6},
     {"from":"fungi","to":"root","weight_delta":0.8}]}},

  {"sentence_id":"te_00034","sentence":"Transpiration pulls water upward through stems and releases vapor through leaf pores.",
   "see_and_say_variants":[
     {"cloze_id":"ce_029","masked_sentence":"Transpiration pulls water upward through stems and releases ___ through leaf pores.",
      "target_word":"vapor","distractor_options":["carbon","nutrients","pollen"]}],
   "relational_map":{"concept_activations_expected":["transpiration","water","root","vapor"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"transpiration","to":"water","weight_delta":0.9},
     {"from":"transpiration","to":"root","weight_delta":0.8},
     {"from":"transpiration","to":"vapor","weight_delta":0.9},
     {"from":"water","to":"vapor","weight_delta":0.7}]}},

  {"sentence_id":"te_00035","sentence":"Seasonal migration follows temperature gradients and tracks shifting food availability.",
   "see_and_say_variants":[
     {"cloze_id":"ce_030","masked_sentence":"Seasonal ___ follows temperature gradients and tracks shifting food availability.",
      "target_word":"migration","distractor_options":["succession","dispersal","competition"]}],
   "relational_map":{"concept_activations_expected":["migration","temperature","food","season"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"migration","to":"temperature","weight_delta":0.9},
     {"from":"migration","to":"food","weight_delta":0.8},
     {"from":"temperature","to":"food","weight_delta":0.6},
     {"from":"migration","to":"season","weight_delta":0.8}]}},

  {"sentence_id":"te_00036","sentence":"Overstory removal increases light reaching the forest floor and shifts understory composition.",
   "relational_map":{"concept_activations_expected":["canopy","light","succession","understory"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"canopy","to":"light","weight_delta":0.9},
     {"from":"light","to":"succession","weight_delta":0.7},
     {"from":"light","to":"understory","weight_delta":0.8},
     {"from":"canopy","to":"understory","weight_delta":0.8}]}},

  {"sentence_id":"te_00037","sentence":"Bioaccumulation concentrates toxins in organisms at higher trophic levels.",
   "relational_map":{"concept_activations_expected":["bioaccumulation","toxin","trophic","predator"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"bioaccumulation","to":"toxin","weight_delta":0.9},
     {"from":"bioaccumulation","to":"trophic","weight_delta":0.8},
     {"from":"toxin","to":"predator","weight_delta":0.7},
     {"from":"trophic","to":"predator","weight_delta":0.8}]}},

  {"sentence_id":"te_00038","sentence":"Tree ring width records annual growth rates determined by rainfall and temperature.",
   "relational_map":{"concept_activations_expected":["growth","climate","temperature","rainfall"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"growth","to":"rainfall","weight_delta":0.8},
     {"from":"growth","to":"temperature","weight_delta":0.8},
     {"from":"rainfall","to":"temperature","weight_delta":0.5},
     {"from":"climate","to":"growth","weight_delta":0.8}]}},

  {"sentence_id":"te_00039","sentence":"Lateral root spread anchors trees against windthrow on steep and saturated terrain.",
   "relational_map":{"concept_activations_expected":["root","wind","slope","anchor"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"root","to":"wind","weight_delta":0.8},
     {"from":"root","to":"slope","weight_delta":0.8},
     {"from":"root","to":"anchor","weight_delta":0.9},
     {"from":"wind","to":"slope","weight_delta":0.6}]}},

  {"sentence_id":"te_00040","sentence":"Fire frequency shapes species composition by favoring fire-adapted plants over time.",
   "relational_map":{"concept_activations_expected":["fire","frequency","adaptation","species"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"fire","to":"frequency","weight_delta":0.8},
     {"from":"fire","to":"adaptation","weight_delta":0.9},
     {"from":"frequency","to":"species","weight_delta":0.7},
     {"from":"adaptation","to":"species","weight_delta":0.8}]}},

  {"sentence_id":"te_00041","sentence":"Soil compaction reduces water infiltration and increases surface runoff during storms.",
   "relational_map":{"concept_activations_expected":["soil","compaction","water","runoff"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"compaction","to":"soil","weight_delta":0.9},
     {"from":"compaction","to":"water","weight_delta":0.8},
     {"from":"compaction","to":"runoff","weight_delta":0.9},
     {"from":"water","to":"runoff","weight_delta":0.7}]}},

  {"sentence_id":"te_00042","sentence":"Bark beetle outbreaks weaken tree defenses and trigger secondary pathogen invasion.",
   "relational_map":{"concept_activations_expected":["insect","defense","pathogen","cascade"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"insect","to":"defense","weight_delta":0.9},
     {"from":"insect","to":"pathogen","weight_delta":0.8},
     {"from":"defense","to":"pathogen","weight_delta":0.7},
     {"from":"pathogen","to":"cascade","weight_delta":0.7}]}},

  {"sentence_id":"te_00043","sentence":"Wolf reintroduction changed elk behavior and allowed riparian vegetation to recover.",
   "relational_map":{"concept_activations_expected":["predator","prey","behavior","vegetation"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"predator","to":"prey","weight_delta":0.9},
     {"from":"predator","to":"behavior","weight_delta":0.9},
     {"from":"behavior","to":"vegetation","weight_delta":0.8},
     {"from":"prey","to":"vegetation","weight_delta":0.7}]}},

  {"sentence_id":"te_00044","sentence":"Fog drip supplements rainfall and sustains moisture in coastal forests during dry seasons.",
   "relational_map":{"concept_activations_expected":["fog","rainfall","moisture","forest"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"fog","to":"rainfall","weight_delta":0.8},
     {"from":"fog","to":"moisture","weight_delta":0.9},
     {"from":"moisture","to":"forest","weight_delta":0.8},
     {"from":"rainfall","to":"moisture","weight_delta":0.8}]}},

  {"sentence_id":"te_00045","sentence":"Forest floor litter retains moisture and moderates soil temperature across seasons.",
   "relational_map":{"concept_activations_expected":["litter","moisture","temperature","soil"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"litter","to":"moisture","weight_delta":0.9},
     {"from":"litter","to":"temperature","weight_delta":0.8},
     {"from":"litter","to":"soil","weight_delta":0.8},
     {"from":"moisture","to":"soil","weight_delta":0.7}]}},

  {"sentence_id":"te_00046","sentence":"Slope aspect determines solar radiation exposure and drives local microclimate variation.",
   "relational_map":{"concept_activations_expected":["aspect","solar","temperature","microclimate"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"aspect","to":"solar","weight_delta":0.9},
     {"from":"aspect","to":"temperature","weight_delta":0.8},
     {"from":"solar","to":"temperature","weight_delta":0.9},
     {"from":"temperature","to":"microclimate","weight_delta":0.8}]}},

  {"sentence_id":"te_00047","sentence":"Ectomycorrhizal associations allow host trees to access phosphorus locked in rocky soils.",
   "relational_map":{"concept_activations_expected":["fungi","root","nutrient","rock"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"fungi","to":"root","weight_delta":0.9},
     {"from":"fungi","to":"nutrient","weight_delta":0.9},
     {"from":"fungi","to":"rock","weight_delta":0.7},
     {"from":"root","to":"nutrient","weight_delta":0.8}]}},

  {"sentence_id":"te_00048","sentence":"Saturated soils create anaerobic conditions that slow decomposition and preserve organic matter.",
   "relational_map":{"concept_activations_expected":["water","oxygen","decomposer","soil"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"water","to":"soil","weight_delta":0.8},
     {"from":"water","to":"decomposer","weight_delta":0.8},
     {"from":"soil","to":"decomposer","weight_delta":0.7},
     {"from":"decomposer","to":"nutrient","weight_delta":0.8}]}},

  {"sentence_id":"te_00049","sentence":"Canopy gaps created by windthrow increase light and biodiversity on the forest floor.",
   "relational_map":{"concept_activations_expected":["disturbance","light","biodiversity","forest"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"wind","to":"canopy","weight_delta":0.9},
     {"from":"canopy","to":"light","weight_delta":0.9},
     {"from":"light","to":"biodiversity","weight_delta":0.8},
     {"from":"disturbance","to":"biodiversity","weight_delta":0.7}]}},

  {"sentence_id":"te_00050","sentence":"Salmon carcasses transport marine nutrients into terrestrial forest ecosystems.",
   "see_and_say_variants":[
     {"cloze_id":"ce_031","masked_sentence":"Salmon carcasses transport marine ___ into terrestrial forest ecosystems.",
      "target_word":"nutrients","distractor_options":["carbon","water","seeds"]}],
   "relational_map":{"concept_activations_expected":["salmon","nutrient","marine","forest"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"salmon","to":"nutrient","weight_delta":0.9},
     {"from":"salmon","to":"forest","weight_delta":0.8},
     {"from":"nutrient","to":"forest","weight_delta":0.7},
     {"from":"salmon","to":"marine","weight_delta":0.9}]}}
]

ECOLOGY_SENTENCES_PATH.write_text(json.dumps(ECOLOGY_SENTENCES, indent=2), encoding='utf-8')
n_with_variants = sum(1 for s in ECOLOGY_SENTENCES if s.get('see_and_say_variants'))
print(f"Wrote {len(ECOLOGY_SENTENCES)} ecology sentences ({n_with_variants} with see_and_say_variants)")
print("Key domains: fire ecology, watershed, mycorrhizal networks, trophic cascades, Pacific Northwest")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2.8 â€” Write ecology teaching list
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

ECOLOGY_TEACHING_LIST_PATH = Path('corpus/lists/teaching_list_ecology.json')
ECOLOGY_TEACHING_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)

ECOLOGY_CLOZE_IDS = [
    "ce_001","ce_002","ce_003","ce_004","ce_005","ce_006","ce_007",
    "ce_008","ce_009","ce_010","ce_011","ce_012","ce_013","ce_014",
    "ce_015","ce_016","ce_017","ce_018","ce_019","ce_020","ce_021",
    "ce_022","ce_023","ce_024","ce_025","ce_026","ce_027","ce_028",
    "ce_029","ce_030","ce_031"
]

ECOLOGY_TEACHING_LIST = {
  "see_and_say_session": {
    "session_id": "sas_ecology_v1",
    "pass_threshold": 0.6,
    "cloze_items": ECOLOGY_CLOZE_IDS,
    "sentences_path": "sentences/teaching_sentences_ecology.json"
  },
  "target_concepts": [
    "sunlight","energy","nutrients","prey","fuel","erosion","fungi",
    "biomass","precipitation","nitrogen","overgrazing","moisture",
    "keystone","pollen","succession","snowpack","carbon","failure",
    "runoff","snags","fuels","vapor","carbon","dispersal","aquifers",
    "riparian","soil","cascades","vapor","migration","nutrients"
  ]
}

ECOLOGY_TEACHING_LIST_PATH.write_text(json.dumps(ECOLOGY_TEACHING_LIST, indent=2), encoding='utf-8')
print(f"Wrote ecology teaching list: {len(ECOLOGY_CLOZE_IDS)} cloze items")
print(f"Session: {ECOLOGY_TEACHING_LIST['see_and_say_session']['session_id']}")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2.9 â€” Write Action-Interaction-Communication corpus
# 50 sentences on agent-action-object structure
# The skeleton of language: who does what to whom
# Cross-links: physics (force/energy), ecology (predator/prey),
#              ethics (harm/warning/boundary), grammar (structure)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

INTERACTION_SENTENCES_PATH = Path('corpus/sentences/teaching_sentences_interaction.json')
INTERACTION_SENTENCES_PATH.parent.mkdir(parents=True, exist_ok=True)

INTERACTION_SENTENCES = [
  {"sentence_id":"ti_00001","sentence":"An agent applies force to an object and changes its position.",
   "see_and_say_variants":[
     {"cloze_id":"ci_001","masked_sentence":"An agent applies ___ to an object and changes its position.",
      "target_word":"force","distractor_options":["heat","pressure","signal"]}],
   "relational_map":{"concept_activations_expected":["agent","force","object","position"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"agent","to":"force","weight_delta":0.9},
     {"from":"agent","to":"object","weight_delta":0.8},
     {"from":"force","to":"position","weight_delta":0.9},
     {"from":"object","to":"position","weight_delta":0.7}]}},

  {"sentence_id":"ti_00002","sentence":"A request signals a need that the speaker cannot fulfill alone.",
   "see_and_say_variants":[
     {"cloze_id":"ci_002","masked_sentence":"A ___ signals a need that the speaker cannot fulfill alone.",
      "target_word":"request","distractor_options":["warning","refusal","signal"]}],
   "relational_map":{"concept_activations_expected":["request","need","speaker","signal"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"request","to":"need","weight_delta":0.9},
     {"from":"request","to":"signal","weight_delta":0.8},
     {"from":"speaker","to":"request","weight_delta":0.8},
     {"from":"need","to":"speaker","weight_delta":0.7}]}},

  {"sentence_id":"ti_00003","sentence":"Giving transfers an object from one agent to another.",
   "see_and_say_variants":[
     {"cloze_id":"ci_003","masked_sentence":"Giving ___ an object from one agent to another.",
      "target_word":"transfers","distractor_options":["destroys","holds","signals"]}],
   "relational_map":{"concept_activations_expected":["giving","transfer","object","agent"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"giving","to":"transfer","weight_delta":0.9},
     {"from":"giving","to":"object","weight_delta":0.8},
     {"from":"transfer","to":"agent","weight_delta":0.8},
     {"from":"object","to":"agent","weight_delta":0.6}]}},

  {"sentence_id":"ti_00004","sentence":"Warning another person prevents harm before it occurs.",
   "see_and_say_variants":[
     {"cloze_id":"ci_004","masked_sentence":"___ another person prevents harm before it occurs.",
      "target_word":"warning","distractor_options":["asking","following","observing"]}],
   "relational_map":{"concept_activations_expected":["warning","harm","prevention","agent"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"warning","to":"harm","weight_delta":0.9},
     {"from":"warning","to":"prevention","weight_delta":0.9},
     {"from":"agent","to":"warning","weight_delta":0.8},
     {"from":"prevention","to":"harm","weight_delta":0.9}]}},

  {"sentence_id":"ti_00005","sentence":"A tool extends the reach of an agent beyond their body.",
   "see_and_say_variants":[
     {"cloze_id":"ci_005","masked_sentence":"A ___ extends the reach of an agent beyond their body.",
      "target_word":"tool","distractor_options":["signal","path","object"]}],
   "relational_map":{"concept_activations_expected":["tool","agent","reach","body"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"tool","to":"agent","weight_delta":0.9},
     {"from":"tool","to":"reach","weight_delta":0.9},
     {"from":"agent","to":"body","weight_delta":0.8},
     {"from":"reach","to":"body","weight_delta":0.7}]}},

  {"sentence_id":"ti_00006","sentence":"Cooperation between agents produces outcomes neither could achieve alone.",
   "see_and_say_variants":[
     {"cloze_id":"ci_006","masked_sentence":"___ between agents produces outcomes neither could achieve alone.",
      "target_word":"cooperation","distractor_options":["competition","refusal","warning"]}],
   "relational_map":{"concept_activations_expected":["cooperation","agent","outcome","achieve"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"cooperation","to":"agent","weight_delta":0.9},
     {"from":"cooperation","to":"outcome","weight_delta":0.9},
     {"from":"agent","to":"achieve","weight_delta":0.7},
     {"from":"outcome","to":"achieve","weight_delta":0.8}]}},

  {"sentence_id":"ti_00007","sentence":"Listening directs attention toward a signal from another agent.",
   "see_and_say_variants":[
     {"cloze_id":"ci_007","masked_sentence":"Listening directs ___ toward a signal from another agent.",
      "target_word":"attention","distractor_options":["force","energy","motion"]}],
   "relational_map":{"concept_activations_expected":["listening","attention","signal","agent"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"listening","to":"attention","weight_delta":0.9},
     {"from":"listening","to":"signal","weight_delta":0.9},
     {"from":"attention","to":"agent","weight_delta":0.7},
     {"from":"signal","to":"agent","weight_delta":0.7}]}},

  {"sentence_id":"ti_00008","sentence":"Refusing a request communicates a boundary between agents.",
   "see_and_say_variants":[
     {"cloze_id":"ci_008","masked_sentence":"Refusing a request communicates a ___ between agents.",
      "target_word":"boundary","distractor_options":["signal","transfer","outcome"]}],
   "relational_map":{"concept_activations_expected":["refusal","request","boundary","agent"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"refusal","to":"request","weight_delta":0.9},
     {"from":"refusal","to":"boundary","weight_delta":0.9},
     {"from":"boundary","to":"agent","weight_delta":0.8},
     {"from":"request","to":"agent","weight_delta":0.7}]}},

  {"sentence_id":"ti_00009","sentence":"A path reduces the energy needed to move through terrain.",
   "see_and_say_variants":[
     {"cloze_id":"ci_009","masked_sentence":"A path reduces the ___ needed to move through terrain.",
      "target_word":"energy","distractor_options":["force","signal","attention"]}],
   "relational_map":{"concept_activations_expected":["path","energy","terrain","motion"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"path","to":"energy","weight_delta":0.9},
     {"from":"path","to":"terrain","weight_delta":0.8},
     {"from":"energy","to":"motion","weight_delta":0.8},
     {"from":"terrain","to":"motion","weight_delta":0.7}]}},

  {"sentence_id":"ti_00010","sentence":"A question opens a space that expects a response to close it.",
   "see_and_say_variants":[
     {"cloze_id":"ci_010","masked_sentence":"A question opens a space that expects a ___ to close it.",
      "target_word":"response","distractor_options":["boundary","signal","warning"]}],
   "relational_map":{"concept_activations_expected":["question","response","space","expect"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"question","to":"response","weight_delta":0.9},
     {"from":"question","to":"space","weight_delta":0.8},
     {"from":"response","to":"space","weight_delta":0.8},
     {"from":"question","to":"expect","weight_delta":0.8}]}},

  {"sentence_id":"ti_00011","sentence":"Contact between two surfaces transfers force from one to the other.",
   "relational_map":{"concept_activations_expected":["contact","surface","force","transfer"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"contact","to":"surface","weight_delta":0.9},
     {"from":"contact","to":"force","weight_delta":0.9},
     {"from":"force","to":"transfer","weight_delta":0.8},
     {"from":"surface","to":"transfer","weight_delta":0.7}]}},

  {"sentence_id":"ti_00012","sentence":"Holding an object maintains its position against external forces.",
   "see_and_say_variants":[
     {"cloze_id":"ci_011","masked_sentence":"Holding an object maintains its ___ against external forces.",
      "target_word":"position","distractor_options":["energy","mass","signal"]}],
   "relational_map":{"concept_activations_expected":["holding","object","position","force"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"holding","to":"object","weight_delta":0.9},
     {"from":"holding","to":"position","weight_delta":0.9},
     {"from":"position","to":"force","weight_delta":0.8},
     {"from":"object","to":"force","weight_delta":0.6}]}},

  {"sentence_id":"ti_00013","sentence":"Releasing an object allows external forces to act upon it freely.",
   "see_and_say_variants":[
     {"cloze_id":"ci_012","masked_sentence":"___ an object allows external forces to act upon it freely.",
      "target_word":"releasing","distractor_options":["holding","breaking","warning"]}],
   "relational_map":{"concept_activations_expected":["release","object","force","motion"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"release","to":"object","weight_delta":0.9},
     {"from":"release","to":"force","weight_delta":0.8},
     {"from":"force","to":"motion","weight_delta":0.9},
     {"from":"release","to":"motion","weight_delta":0.8}]}},

  {"sentence_id":"ti_00014","sentence":"Following a path means allowing terrain to guide direction of movement.",
   "relational_map":{"concept_activations_expected":["following","path","terrain","direction"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"following","to":"path","weight_delta":0.9},
     {"from":"path","to":"terrain","weight_delta":0.8},
     {"from":"terrain","to":"direction","weight_delta":0.8},
     {"from":"following","to":"direction","weight_delta":0.7}]}},

  {"sentence_id":"ti_00015","sentence":"Approaching reduces the distance between an agent and a target.",
   "see_and_say_variants":[
     {"cloze_id":"ci_013","masked_sentence":"Approaching reduces the ___ between an agent and a target.",
      "target_word":"distance","distractor_options":["force","energy","boundary"]}],
   "relational_map":{"concept_activations_expected":["approaching","distance","agent","target"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"approaching","to":"distance","weight_delta":0.9},
     {"from":"approaching","to":"agent","weight_delta":0.8},
     {"from":"distance","to":"target","weight_delta":0.8},
     {"from":"agent","to":"target","weight_delta":0.7}]}},

  {"sentence_id":"ti_00016","sentence":"Avoiding increases distance from a source of harm or danger.",
   "see_and_say_variants":[
     {"cloze_id":"ci_014","masked_sentence":"Avoiding increases ___ from a source of harm or danger.",
      "target_word":"distance","distractor_options":["force","attention","contact"]}],
   "relational_map":{"concept_activations_expected":["avoiding","distance","harm","danger"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"avoiding","to":"distance","weight_delta":0.9},
     {"from":"avoiding","to":"harm","weight_delta":0.9},
     {"from":"harm","to":"danger","weight_delta":0.9},
     {"from":"avoiding","to":"danger","weight_delta":0.8}]}},

  {"sentence_id":"ti_00017","sentence":"A container holds material within a defined boundary.",
   "see_and_say_variants":[
     {"cloze_id":"ci_015","masked_sentence":"A container holds material within a defined ___.",
      "target_word":"boundary","distractor_options":["path","surface","signal"]}],
   "relational_map":{"concept_activations_expected":["container","material","boundary","hold"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"container","to":"material","weight_delta":0.9},
     {"from":"container","to":"boundary","weight_delta":0.9},
     {"from":"boundary","to":"material","weight_delta":0.8},
     {"from":"container","to":"hold","weight_delta":0.8}]}},

  {"sentence_id":"ti_00018","sentence":"Breaking an object releases energy stored in its structure.",
   "see_and_say_variants":[
     {"cloze_id":"ci_016","masked_sentence":"Breaking an object releases ___ stored in its structure.",
      "target_word":"energy","distractor_options":["signal","boundary","attention"]}],
   "relational_map":{"concept_activations_expected":["breaking","object","energy","structure"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"breaking","to":"object","weight_delta":0.9},
     {"from":"breaking","to":"energy","weight_delta":0.9},
     {"from":"energy","to":"structure","weight_delta":0.7},
     {"from":"object","to":"structure","weight_delta":0.8}]}},

  {"sentence_id":"ti_00019","sentence":"Building connects components into a structure greater than its parts.",
   "see_and_say_variants":[
     {"cloze_id":"ci_017","masked_sentence":"Building connects ___ into a structure greater than its parts.",
      "target_word":"components","distractor_options":["agents","signals","paths"]}],
   "relational_map":{"concept_activations_expected":["building","component","structure","connection"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"building","to":"component","weight_delta":0.9},
     {"from":"building","to":"structure","weight_delta":0.9},
     {"from":"component","to":"structure","weight_delta":0.8},
     {"from":"building","to":"connection","weight_delta":0.7}]}},

  {"sentence_id":"ti_00020","sentence":"Observing an event without intervening still changes the observer.",
   "relational_map":{"concept_activations_expected":["observing","event","observer","change"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"observing","to":"event","weight_delta":0.9},
     {"from":"observing","to":"observer","weight_delta":0.9},
     {"from":"event","to":"change","weight_delta":0.8},
     {"from":"observer","to":"change","weight_delta":0.7}]}},

  {"sentence_id":"ti_00021","sentence":"Sharing distributes a resource across multiple agents reducing scarcity.",
   "see_and_say_variants":[
     {"cloze_id":"ci_018","masked_sentence":"Sharing distributes a ___ across multiple agents reducing scarcity.",
      "target_word":"resource","distractor_options":["signal","boundary","warning"]}],
   "relational_map":{"concept_activations_expected":["sharing","resource","agent","scarcity"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"sharing","to":"resource","weight_delta":0.9},
     {"from":"sharing","to":"agent","weight_delta":0.8},
     {"from":"resource","to":"scarcity","weight_delta":0.9},
     {"from":"sharing","to":"scarcity","weight_delta":0.8}]}},

  {"sentence_id":"ti_00022","sentence":"Withholding a resource from another agent creates scarcity and dependency.",
   "see_and_say_variants":[
     {"cloze_id":"ci_019","masked_sentence":"Withholding a resource from another agent creates scarcity and ___.",
      "target_word":"dependency","distractor_options":["cooperation","motion","release"]}],
   "relational_map":{"concept_activations_expected":["withholding","resource","scarcity","dependency"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"withholding","to":"resource","weight_delta":0.9},
     {"from":"withholding","to":"scarcity","weight_delta":0.9},
     {"from":"scarcity","to":"dependency","weight_delta":0.9},
     {"from":"withholding","to":"dependency","weight_delta":0.8}]}},

  {"sentence_id":"ti_00023","sentence":"A signal carries information from a sender to a receiver.",
   "see_and_say_variants":[
     {"cloze_id":"ci_020","masked_sentence":"A signal carries ___ from a sender to a receiver.",
      "target_word":"information","distractor_options":["energy","force","material"]}],
   "relational_map":{"concept_activations_expected":["signal","information","sender","receiver"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"signal","to":"information","weight_delta":0.9},
     {"from":"signal","to":"sender","weight_delta":0.8},
     {"from":"signal","to":"receiver","weight_delta":0.8},
     {"from":"sender","to":"receiver","weight_delta":0.7}]}},

  {"sentence_id":"ti_00024","sentence":"Interpreting a signal requires the receiver to share context with the sender.",
   "see_and_say_variants":[
     {"cloze_id":"ci_021","masked_sentence":"Interpreting a signal requires the receiver to share ___ with the sender.",
      "target_word":"context","distractor_options":["energy","distance","boundary"]}],
   "relational_map":{"concept_activations_expected":["interpretation","signal","context","receiver"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"interpretation","to":"signal","weight_delta":0.9},
     {"from":"interpretation","to":"context","weight_delta":0.9},
     {"from":"receiver","to":"context","weight_delta":0.8},
     {"from":"signal","to":"context","weight_delta":0.7}]}},

  {"sentence_id":"ti_00025","sentence":"Trust between agents reduces the energy required for cooperation.",
   "see_and_say_variants":[
     {"cloze_id":"ci_022","masked_sentence":"Trust between agents reduces the ___ required for cooperation.",
      "target_word":"energy","distractor_options":["distance","boundary","signal"]}],
   "relational_map":{"concept_activations_expected":["trust","agent","energy","cooperation"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trust","to":"agent","weight_delta":0.9},
     {"from":"trust","to":"energy","weight_delta":0.8},
     {"from":"trust","to":"cooperation","weight_delta":0.9},
     {"from":"energy","to":"cooperation","weight_delta":0.7}]}},

  {"sentence_id":"ti_00026","sentence":"Deception creates a false signal that misleads the receiver.",
   "see_and_say_variants":[
     {"cloze_id":"ci_023","masked_sentence":"Deception creates a false ___ that misleads the receiver.",
      "target_word":"signal","distractor_options":["boundary","resource","path"]}],
   "relational_map":{"concept_activations_expected":["deception","signal","receiver","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"deception","to":"signal","weight_delta":0.9},
     {"from":"deception","to":"receiver","weight_delta":0.8},
     {"from":"deception","to":"harm","weight_delta":0.8},
     {"from":"signal","to":"receiver","weight_delta":0.8}]}},

  {"sentence_id":"ti_00027","sentence":"Leading means moving ahead so others can follow the same path.",
   "see_and_say_variants":[
     {"cloze_id":"ci_024","masked_sentence":"Leading means moving ahead so others can ___ the same path.",
      "target_word":"follow","distractor_options":["avoid","break","hold"]}],
   "relational_map":{"concept_activations_expected":["leading","following","path","agent"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"leading","to":"following","weight_delta":0.9},
     {"from":"leading","to":"path","weight_delta":0.8},
     {"from":"following","to":"path","weight_delta":0.8},
     {"from":"leading","to":"agent","weight_delta":0.7}]}},

  {"sentence_id":"ti_00028","sentence":"Resistance is force applied against the direction of motion.",
   "see_and_say_variants":[
     {"cloze_id":"ci_025","masked_sentence":"Resistance is force applied against the direction of ___.",
      "target_word":"motion","distractor_options":["signal","contact","boundary"]}],
   "relational_map":{"concept_activations_expected":["resistance","force","motion","direction"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"resistance","to":"force","weight_delta":0.9},
     {"from":"resistance","to":"motion","weight_delta":0.9},
     {"from":"force","to":"direction","weight_delta":0.8},
     {"from":"motion","to":"direction","weight_delta":0.8}]}},

  {"sentence_id":"ti_00029","sentence":"An exchange transfers objects or resources between two agents simultaneously.",
   "see_and_say_variants":[
     {"cloze_id":"ci_026","masked_sentence":"An exchange transfers ___ or resources between two agents simultaneously.",
      "target_word":"objects","distractor_options":["signals","paths","warnings"]}],
   "relational_map":{"concept_activations_expected":["exchange","transfer","agent","resource"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"exchange","to":"transfer","weight_delta":0.9},
     {"from":"exchange","to":"agent","weight_delta":0.8},
     {"from":"exchange","to":"resource","weight_delta":0.8},
     {"from":"transfer","to":"resource","weight_delta":0.7}]}},

  {"sentence_id":"ti_00030","sentence":"Pain signals damage to the body and triggers avoidance behavior.",
   "see_and_say_variants":[
     {"cloze_id":"ci_027","masked_sentence":"Pain signals ___ to the body and triggers avoidance behavior.",
      "target_word":"damage","distractor_options":["energy","contact","transfer"]}],
   "relational_map":{"concept_activations_expected":["pain","damage","body","avoidance"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"pain","to":"damage","weight_delta":0.9},
     {"from":"pain","to":"body","weight_delta":0.9},
     {"from":"pain","to":"avoidance","weight_delta":0.9},
     {"from":"damage","to":"avoidance","weight_delta":0.8}]}},

  {"sentence_id":"ti_00031","sentence":"Hunger drives an agent toward a source of food or energy.",
   "see_and_say_variants":[
     {"cloze_id":"ci_028","masked_sentence":"Hunger drives an agent toward a source of food or ___.",
      "target_word":"energy","distractor_options":["signal","boundary","context"]}],
   "relational_map":{"concept_activations_expected":["hunger","agent","food","energy"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"hunger","to":"agent","weight_delta":0.9},
     {"from":"hunger","to":"food","weight_delta":0.9},
     {"from":"hunger","to":"energy","weight_delta":0.8},
     {"from":"food","to":"energy","weight_delta":0.8}]}},

  {"sentence_id":"ti_00032","sentence":"Cold pushes a living agent toward shelter and warmth.",
   "relational_map":{"concept_activations_expected":["cold","agent","shelter","warmth"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"cold","to":"agent","weight_delta":0.9},
     {"from":"cold","to":"shelter","weight_delta":0.9},
     {"from":"agent","to":"shelter","weight_delta":0.8},
     {"from":"shelter","to":"warmth","weight_delta":0.8}]}},

  {"sentence_id":"ti_00033","sentence":"Danger triggers alertness and increases readiness to act in an agent.",
   "see_and_say_variants":[
     {"cloze_id":"ci_029","masked_sentence":"___ triggers alertness and increases readiness to act in an agent.",
      "target_word":"danger","distractor_options":["hunger","cold","contact"]}],
   "relational_map":{"concept_activations_expected":["danger","alertness","agent","action"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"danger","to":"alertness","weight_delta":0.9},
     {"from":"danger","to":"agent","weight_delta":0.8},
     {"from":"alertness","to":"action","weight_delta":0.9},
     {"from":"danger","to":"action","weight_delta":0.8}]}},

  {"sentence_id":"ti_00034","sentence":"A lever multiplies force by increasing the distance from the pivot point.",
   "relational_map":{"concept_activations_expected":["lever","force","distance","tool"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"lever","to":"force","weight_delta":0.9},
     {"from":"lever","to":"distance","weight_delta":0.8},
     {"from":"lever","to":"tool","weight_delta":0.9},
     {"from":"force","to":"distance","weight_delta":0.7}]}},

  {"sentence_id":"ti_00035","sentence":"Words carry meaning from one mind to another across distance.",
   "see_and_say_variants":[
     {"cloze_id":"ci_030","masked_sentence":"Words carry ___ from one mind to another across distance.",
      "target_word":"meaning","distractor_options":["force","energy","signal"]}],
   "relational_map":{"concept_activations_expected":["word","meaning","mind","distance"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"word","to":"meaning","weight_delta":0.9},
     {"from":"word","to":"mind","weight_delta":0.8},
     {"from":"meaning","to":"mind","weight_delta":0.9},
     {"from":"word","to":"distance","weight_delta":0.6}]}},

  {"sentence_id":"ti_00036","sentence":"Silence communicates the absence of a response or signal.",
   "relational_map":{"concept_activations_expected":["silence","absence","response","signal"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"silence","to":"absence","weight_delta":0.9},
     {"from":"silence","to":"response","weight_delta":0.9},
     {"from":"silence","to":"signal","weight_delta":0.8},
     {"from":"absence","to":"signal","weight_delta":0.7}]}},

  {"sentence_id":"ti_00037","sentence":"Repeating a signal increases the probability the receiver detects it.",
   "see_and_say_variants":[
     {"cloze_id":"ci_031","masked_sentence":"Repeating a signal increases the probability the ___ detects it.",
      "target_word":"receiver","distractor_options":["agent","sender","observer"]}],
   "relational_map":{"concept_activations_expected":["repetition","signal","receiver","detection"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"repetition","to":"signal","weight_delta":0.9},
     {"from":"repetition","to":"receiver","weight_delta":0.8},
     {"from":"signal","to":"detection","weight_delta":0.9},
     {"from":"receiver","to":"detection","weight_delta":0.8}]}},

  {"sentence_id":"ti_00038","sentence":"A boundary separates one space or domain from another.",
   "see_and_say_variants":[
     {"cloze_id":"ci_032","masked_sentence":"A ___ separates one space or domain from another.",
      "target_word":"boundary","distractor_options":["signal","path","tool"]}],
   "relational_map":{"concept_activations_expected":["boundary","space","domain","separation"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"boundary","to":"space","weight_delta":0.9},
     {"from":"boundary","to":"domain","weight_delta":0.9},
     {"from":"boundary","to":"separation","weight_delta":0.9},
     {"from":"space","to":"domain","weight_delta":0.6}]}},

  {"sentence_id":"ti_00039","sentence":"Agreement between agents creates a shared expectation about future action.",
   "see_and_say_variants":[
     {"cloze_id":"ci_033","masked_sentence":"___ between agents creates a shared expectation about future action.",
      "target_word":"agreement","distractor_options":["conflict","distance","resistance"]}],
   "relational_map":{"concept_activations_expected":["agreement","agent","expectation","action"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"agreement","to":"agent","weight_delta":0.9},
     {"from":"agreement","to":"expectation","weight_delta":0.9},
     {"from":"expectation","to":"action","weight_delta":0.8},
     {"from":"agreement","to":"action","weight_delta":0.7}]}},

  {"sentence_id":"ti_00040","sentence":"Conflict arises when two agents pursue incompatible goals in shared space.",
   "see_and_say_variants":[
     {"cloze_id":"ci_034","masked_sentence":"Conflict arises when two agents pursue incompatible ___ in shared space.",
      "target_word":"goals","distractor_options":["signals","resources","boundaries"]}],
   "relational_map":{"concept_activations_expected":["conflict","agent","goal","space"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"conflict","to":"agent","weight_delta":0.9},
     {"from":"conflict","to":"goal","weight_delta":0.9},
     {"from":"goal","to":"space","weight_delta":0.7},
     {"from":"conflict","to":"space","weight_delta":0.8}]}},

  {"sentence_id":"ti_00041","sentence":"Memory allows an agent to use past experience to guide future action.",
   "see_and_say_variants":[
     {"cloze_id":"ci_035","masked_sentence":"___ allows an agent to use past experience to guide future action.",
      "target_word":"memory","distractor_options":["attention","signal","contact"]}],
   "relational_map":{"concept_activations_expected":["memory","agent","experience","action"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"memory","to":"agent","weight_delta":0.9},
     {"from":"memory","to":"experience","weight_delta":0.9},
     {"from":"experience","to":"action","weight_delta":0.8},
     {"from":"memory","to":"action","weight_delta":0.8}]}},

  {"sentence_id":"ti_00042","sentence":"Attention narrows perception onto a specific part of the environment.",
   "relational_map":{"concept_activations_expected":["attention","perception","environment","focus"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"attention","to":"perception","weight_delta":0.9},
     {"from":"attention","to":"environment","weight_delta":0.8},
     {"from":"perception","to":"environment","weight_delta":0.8},
     {"from":"attention","to":"focus","weight_delta":0.9}]}},

  {"sentence_id":"ti_00043","sentence":"A pattern repeats across time or space allowing an agent to predict.",
   "see_and_say_variants":[
     {"cloze_id":"ci_036","masked_sentence":"A pattern repeats across time or space allowing an agent to ___.",
      "target_word":"predict","distractor_options":["avoid","signal","hold"]}],
   "relational_map":{"concept_activations_expected":["pattern","repetition","agent","prediction"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"pattern","to":"repetition","weight_delta":0.9},
     {"from":"pattern","to":"agent","weight_delta":0.7},
     {"from":"pattern","to":"prediction","weight_delta":0.9},
     {"from":"repetition","to":"prediction","weight_delta":0.8}]}},

  {"sentence_id":"ti_00044","sentence":"Support prevents an object or agent from falling under the force of gravity.",
   "see_and_say_variants":[
     {"cloze_id":"ci_037","masked_sentence":"Support prevents an object or agent from falling under the force of ___.",
      "target_word":"gravity","distractor_options":["contact","momentum","signal"]}],
   "relational_map":{"concept_activations_expected":["support","gravity","object","force"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"support","to":"gravity","weight_delta":0.9},
     {"from":"support","to":"object","weight_delta":0.8},
     {"from":"support","to":"force","weight_delta":0.8},
     {"from":"gravity","to":"force","weight_delta":0.9}]}},

  {"sentence_id":"ti_00045","sentence":"An obstacle blocks the path between an agent and a goal.",
   "see_and_say_variants":[
     {"cloze_id":"ci_038","masked_sentence":"An obstacle blocks the ___ between an agent and a goal.",
      "target_word":"path","distractor_options":["signal","boundary","contact"]}],
   "relational_map":{"concept_activations_expected":["obstacle","path","agent","goal"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"obstacle","to":"path","weight_delta":0.9},
     {"from":"obstacle","to":"agent","weight_delta":0.8},
     {"from":"path","to":"goal","weight_delta":0.9},
     {"from":"obstacle","to":"goal","weight_delta":0.8}]}},

  {"sentence_id":"ti_00046","sentence":"Habit reduces the attention required to perform a repeated action.",
   "relational_map":{"concept_activations_expected":["habit","attention","action","repetition"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"habit","to":"attention","weight_delta":0.9},
     {"from":"habit","to":"action","weight_delta":0.9},
     {"from":"habit","to":"repetition","weight_delta":0.9},
     {"from":"attention","to":"action","weight_delta":0.7}]}},

  {"sentence_id":"ti_00047","sentence":"Permission from one agent allows another agent to act within a boundary.",
   "see_and_say_variants":[
     {"cloze_id":"ci_039","masked_sentence":"Permission from one agent allows another agent to act within a ___.",
      "target_word":"boundary","distractor_options":["signal","path","goal"]}],
   "relational_map":{"concept_activations_expected":["permission","agent","boundary","action"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"permission","to":"agent","weight_delta":0.9},
     {"from":"permission","to":"boundary","weight_delta":0.9},
     {"from":"permission","to":"action","weight_delta":0.8},
     {"from":"boundary","to":"action","weight_delta":0.7}]}},

  {"sentence_id":"ti_00048","sentence":"Naming an object gives it a signal that can be shared between minds.",
   "see_and_say_variants":[
     {"cloze_id":"ci_040","masked_sentence":"Naming an object gives it a ___ that can be shared between minds.",
      "target_word":"signal","distractor_options":["boundary","force","path"]}],
   "relational_map":{"concept_activations_expected":["naming","object","signal","mind"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"naming","to":"object","weight_delta":0.9},
     {"from":"naming","to":"signal","weight_delta":0.9},
     {"from":"signal","to":"mind","weight_delta":0.8},
     {"from":"naming","to":"mind","weight_delta":0.7}]}},

  {"sentence_id":"ti_00049","sentence":"A threshold marks the point where a change in quantity produces a change in kind.",
   "relational_map":{"concept_activations_expected":["threshold","change","quantity","kind"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"threshold","to":"change","weight_delta":0.9},
     {"from":"threshold","to":"quantity","weight_delta":0.8},
     {"from":"change","to":"quantity","weight_delta":0.7},
     {"from":"threshold","to":"kind","weight_delta":0.8}]}},

  {"sentence_id":"ti_00050","sentence":"Care directs an agent's resources toward the wellbeing of another.",
   "see_and_say_variants":[
     {"cloze_id":"ci_041","masked_sentence":"Care directs an agent's ___ toward the wellbeing of another.",
      "target_word":"resources","distractor_options":["attention","signal","boundary"]}],
   "relational_map":{"concept_activations_expected":["care","agent","resource","wellbeing"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"care","to":"agent","weight_delta":0.9},
     {"from":"care","to":"resource","weight_delta":0.8},
     {"from":"care","to":"wellbeing","weight_delta":0.9},
     {"from":"resource","to":"wellbeing","weight_delta":0.8}]}}
]

INTERACTION_SENTENCES_PATH.write_text(json.dumps(INTERACTION_SENTENCES, indent=2), encoding='utf-8')
n_with_variants = sum(1 for s in INTERACTION_SENTENCES if s.get('see_and_say_variants'))
print(f"Wrote {len(INTERACTION_SENTENCES)} interaction sentences ({n_with_variants} with see_and_say_variants)")
print("Key domains: agent-action-object, communication, trust, harm, tool use, cooperation")
print("Ethics bridge concepts: warningâ†’harm, careâ†’wellbeing, deceptionâ†’harm, permissionâ†’boundary")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2.10 â€” Write interaction teaching list
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

INTERACTION_TEACHING_LIST_PATH = Path('corpus/lists/teaching_list_interaction.json')
INTERACTION_TEACHING_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)

INTERACTION_CLOZE_IDS = [f"ci_{i:03d}" for i in range(1, 42)]

INTERACTION_TEACHING_LIST = {
  "see_and_say_session": {
    "session_id": "sas_interaction_v1",
    "pass_threshold": 0.6,
    "cloze_items": INTERACTION_CLOZE_IDS,
    "sentences_path": "sentences/teaching_sentences_interaction.json"
  },
  "target_concepts": [
    "force","request","transfers","warning","tool","cooperation","attention",
    "boundary","energy","response","position","releasing","distance","distance",
    "components","energy","signal","context","energy","damage","energy",
    "danger","meaning","receiver","boundary","goals","memory","predict",
    "gravity","path","boundary","signal","resources"
  ]
}

INTERACTION_TEACHING_LIST_PATH.write_text(json.dumps(INTERACTION_TEACHING_LIST, indent=2), encoding='utf-8')
print(f"Wrote interaction teaching list: {len(INTERACTION_CLOZE_IDS)} cloze items")
print(f"Session: {INTERACTION_TEACHING_LIST['see_and_say_session']['session_id']}")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2.11 â€” Write Family & Social corpus
# 50 sentences on persons, relationships, care, vulnerability,
# family structure, conflict, repair, and shared history
# The domain where ethics becomes situated rather than abstract
# Cross-links: interaction (agent/harm/care/trust/boundary),
#              ecology (dependency/protection/succession),
#              physics (force/energy/threshold)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

FAMILY_SENTENCES_PATH = Path('corpus/sentences/teaching_sentences_family.json')
FAMILY_SENTENCES_PATH.parent.mkdir(parents=True, exist_ok=True)

FAMILY_SENTENCES = [
  {"sentence_id":"tf_00001",
   "sentence":"A parent protects a child because the child cannot yet protect itself.",
   "see_and_say_variants":[
     {"cloze_id":"cf_001",
      "masked_sentence":"A parent ___ a child because the child cannot yet protect itself.",
      "target_word":"protects",
      "distractor_options":["controls","observes","teaches"]}],
   "relational_map":{"concept_activations_expected":["parent","child","protection","vulnerability"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"parent","to":"child","weight_delta":0.9},
     {"from":"parent","to":"protection","weight_delta":0.9},
     {"from":"child","to":"vulnerability","weight_delta":0.9},
     {"from":"protection","to":"vulnerability","weight_delta":0.8}]}},

  {"sentence_id":"tf_00002",
   "sentence":"A child depends on a caregiver for survival before it can act alone.",
   "see_and_say_variants":[
     {"cloze_id":"cf_002",
      "masked_sentence":"A child depends on a caregiver for ___ before it can act alone.",
      "target_word":"survival",
      "distractor_options":["learning","attention","growth"]}],
   "relational_map":{"concept_activations_expected":["child","caregiver","dependency","survival"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"child","to":"caregiver","weight_delta":0.9},
     {"from":"child","to":"dependency","weight_delta":0.9},
     {"from":"caregiver","to":"survival","weight_delta":0.9},
     {"from":"dependency","to":"survival","weight_delta":0.8}]}},

  {"sentence_id":"tf_00003",
   "sentence":"Care given consistently over time becomes the foundation of trust.",
   "see_and_say_variants":[
     {"cloze_id":"cf_003",
      "masked_sentence":"Care given consistently over time becomes the foundation of ___.",
      "target_word":"trust",
      "distractor_options":["memory","habit","attention"]}],
   "relational_map":{"concept_activations_expected":["care","trust","consistency","time"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"care","to":"trust","weight_delta":0.9},
     {"from":"care","to":"consistency","weight_delta":0.8},
     {"from":"consistency","to":"trust","weight_delta":0.9},
     {"from":"trust","to":"time","weight_delta":0.7}]}},

  {"sentence_id":"tf_00004",
   "sentence":"Harm between people who love each other carries the weight of what existed before.",
   "see_and_say_variants":[
     {"cloze_id":"cf_004",
      "masked_sentence":"Harm between people who love each other carries the weight of what ___ before.",
      "target_word":"existed",
      "distractor_options":["happened","changed","ended"]}],
   "relational_map":{"concept_activations_expected":["harm","love","history","weight"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"harm","to":"love","weight_delta":0.8},
     {"from":"harm","to":"history","weight_delta":0.9},
     {"from":"love","to":"history","weight_delta":0.9},
     {"from":"history","to":"weight","weight_delta":0.7}]}},

  {"sentence_id":"tf_00005",
   "sentence":"A sibling shares history that no one outside the family holds.",
   "see_and_say_variants":[
     {"cloze_id":"cf_005",
      "masked_sentence":"A sibling shares ___ that no one outside the family holds.",
      "target_word":"history",
      "distractor_options":["resources","attention","space"]}],
   "relational_map":{"concept_activations_expected":["sibling","history","family","shared"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"sibling","to":"history","weight_delta":0.9},
     {"from":"sibling","to":"family","weight_delta":0.9},
     {"from":"history","to":"family","weight_delta":0.8},
     {"from":"sibling","to":"shared","weight_delta":0.8}]}},

  {"sentence_id":"tf_00006",
   "sentence":"An elder carries knowledge the young have not yet lived.",
   "see_and_say_variants":[
     {"cloze_id":"cf_006",
      "masked_sentence":"An elder carries ___ the young have not yet lived.",
      "target_word":"knowledge",
      "distractor_options":["memory","pain","silence"]}],
   "relational_map":{"concept_activations_expected":["elder","knowledge","young","experience"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"elder","to":"knowledge","weight_delta":0.9},
     {"from":"elder","to":"young","weight_delta":0.8},
     {"from":"knowledge","to":"experience","weight_delta":0.9},
     {"from":"young","to":"experience","weight_delta":0.7}]}},

  {"sentence_id":"tf_00007",
   "sentence":"A parent who fails to warn their child has failed differently than a stranger who fails.",
   "see_and_say_variants":[
     {"cloze_id":"cf_007",
      "masked_sentence":"A parent who fails to ___ their child has failed differently than a stranger.",
      "target_word":"warn",
      "distractor_options":["protect","guide","teach"]}],
   "relational_map":{"concept_activations_expected":["parent","warning","obligation","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"parent","to":"warning","weight_delta":0.9},
     {"from":"parent","to":"obligation","weight_delta":0.9},
     {"from":"obligation","to":"harm","weight_delta":0.8},
     {"from":"warning","to":"harm","weight_delta":0.9}]}},

  {"sentence_id":"tf_00008",
   "sentence":"Role creates obligation that does not exist between strangers.",
   "see_and_say_variants":[
     {"cloze_id":"cf_008",
      "masked_sentence":"Role creates ___ that does not exist between strangers.",
      "target_word":"obligation",
      "distractor_options":["distance","memory","conflict"]}],
   "relational_map":{"concept_activations_expected":["role","obligation","stranger","relationship"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"role","to":"obligation","weight_delta":0.9},
     {"from":"role","to":"relationship","weight_delta":0.8},
     {"from":"obligation","to":"stranger","weight_delta":0.7},
     {"from":"relationship","to":"obligation","weight_delta":0.8}]}},

  {"sentence_id":"tf_00009",
   "sentence":"Grief makes a person permeable to harm they would otherwise deflect.",
   "see_and_say_variants":[
     {"cloze_id":"cf_009",
      "masked_sentence":"Grief makes a person ___ to harm they would otherwise deflect.",
      "target_word":"permeable",
      "distractor_options":["resistant","open","vulnerable"]}],
   "relational_map":{"concept_activations_expected":["grief","vulnerability","harm","person"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"grief","to":"vulnerability","weight_delta":0.9},
     {"from":"grief","to":"harm","weight_delta":0.8},
     {"from":"vulnerability","to":"harm","weight_delta":0.9},
     {"from":"grief","to":"person","weight_delta":0.8}]}},

  {"sentence_id":"tf_00010",
   "sentence":"Repair after harm requires acknowledging what was broken before rebuilding.",
   "see_and_say_variants":[
     {"cloze_id":"cf_010",
      "masked_sentence":"Repair after harm requires ___ what was broken before rebuilding.",
      "target_word":"acknowledging",
      "distractor_options":["forgetting","minimizing","avoiding"]}],
   "relational_map":{"concept_activations_expected":["repair","harm","acknowledgment","rebuilding"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"repair","to":"harm","weight_delta":0.9},
     {"from":"repair","to":"acknowledgment","weight_delta":0.9},
     {"from":"acknowledgment","to":"rebuilding","weight_delta":0.8},
     {"from":"harm","to":"acknowledgment","weight_delta":0.8}]}},

  {"sentence_id":"tf_00011",
   "sentence":"Belonging to a family gives a person a context that shapes who they become.",
   "see_and_say_variants":[
     {"cloze_id":"cf_011",
      "masked_sentence":"Belonging to a family gives a person a ___ that shapes who they become.",
      "target_word":"context",
      "distractor_options":["role","boundary","name"]}],
   "relational_map":{"concept_activations_expected":["family","belonging","context","identity"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"family","to":"belonging","weight_delta":0.9},
     {"from":"family","to":"context","weight_delta":0.9},
     {"from":"context","to":"identity","weight_delta":0.9},
     {"from":"belonging","to":"identity","weight_delta":0.8}]}},

  {"sentence_id":"tf_00012",
   "sentence":"A person who was not protected as a child must learn to protect themselves later.",
   "relational_map":{"concept_activations_expected":["protection","child","learning","self"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"protection","to":"child","weight_delta":0.9},
     {"from":"child","to":"learning","weight_delta":0.8},
     {"from":"learning","to":"self","weight_delta":0.7},
     {"from":"protection","to":"self","weight_delta":0.8}]}},

  {"sentence_id":"tf_00013",
   "sentence":"Love persists across distance and time as a connection between two people.",
   "see_and_say_variants":[
     {"cloze_id":"cf_012",
      "masked_sentence":"Love persists across distance and time as a ___ between two people.",
      "target_word":"connection",
      "distractor_options":["memory","obligation","signal"]}],
   "relational_map":{"concept_activations_expected":["love","distance","time","connection"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"love","to":"connection","weight_delta":0.9},
     {"from":"love","to":"distance","weight_delta":0.7},
     {"from":"love","to":"time","weight_delta":0.7},
     {"from":"connection","to":"distance","weight_delta":0.7}]}},

  {"sentence_id":"tf_00014",
   "sentence":"A person in crisis draws on the strength of those who care for them.",
   "see_and_say_variants":[
     {"cloze_id":"cf_013",
      "masked_sentence":"A person in crisis draws on the ___ of those who care for them.",
      "target_word":"strength",
      "distractor_options":["memory","attention","silence"]}],
   "relational_map":{"concept_activations_expected":["crisis","care","strength","support"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"crisis","to":"care","weight_delta":0.9},
     {"from":"care","to":"strength","weight_delta":0.9},
     {"from":"strength","to":"support","weight_delta":0.8},
     {"from":"crisis","to":"support","weight_delta":0.9}]}},

  {"sentence_id":"tf_00015",
   "sentence":"Addiction changes a person in ways that affect everyone who loves them.",
   "see_and_say_variants":[
     {"cloze_id":"cf_014",
      "masked_sentence":"Addiction ___ a person in ways that affect everyone who loves them.",
      "target_word":"changes",
      "distractor_options":["harms","isolates","breaks"]}],
   "relational_map":{"concept_activations_expected":["addiction","change","harm","family"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"addiction","to":"change","weight_delta":0.9},
     {"from":"addiction","to":"harm","weight_delta":0.9},
     {"from":"harm","to":"family","weight_delta":0.8},
     {"from":"change","to":"family","weight_delta":0.7}]}},

  {"sentence_id":"tf_00016",
   "sentence":"Watching someone you love suffer without being able to stop it is its own kind of harm.",
   "see_and_say_variants":[
     {"cloze_id":"cf_015",
      "masked_sentence":"Watching someone you love ___ without being able to stop it is its own kind of harm.",
      "target_word":"suffer",
      "distractor_options":["struggle","change","leave"]}],
   "relational_map":{"concept_activations_expected":["witnessing","love","suffering","helplessness"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"witnessing","to":"suffering","weight_delta":0.9},
     {"from":"love","to":"suffering","weight_delta":0.8},
     {"from":"suffering","to":"helplessness","weight_delta":0.9},
     {"from":"helplessness","to":"harm","weight_delta":0.8}]}},

  {"sentence_id":"tf_00017",
   "sentence":"A family that does not speak about pain passes the pain to the next generation.",
   "see_and_say_variants":[
     {"cloze_id":"cf_016",
      "masked_sentence":"A family that does not speak about pain ___ the pain to the next generation.",
      "target_word":"passes",
      "distractor_options":["hides","holds","carries"]}],
   "relational_map":{"concept_activations_expected":["family","silence","pain","generation"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"family","to":"silence","weight_delta":0.8},
     {"from":"silence","to":"pain","weight_delta":0.9},
     {"from":"pain","to":"generation","weight_delta":0.9},
     {"from":"family","to":"generation","weight_delta":0.8}]}},

  {"sentence_id":"tf_00018",
   "sentence":"A person who was seen and heard as a child more easily sees and hears others.",
   "relational_map":{"concept_activations_expected":["witnessing","child","attention","empathy"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"witnessing","to":"child","weight_delta":0.9},
     {"from":"witnessing","to":"attention","weight_delta":0.8},
     {"from":"attention","to":"empathy","weight_delta":0.9},
     {"from":"child","to":"empathy","weight_delta":0.7}]}},

  {"sentence_id":"tf_00019",
   "sentence":"Conflict between family members is more painful than conflict between strangers.",
   "see_and_say_variants":[
     {"cloze_id":"cf_017",
      "masked_sentence":"Conflict between family members is more ___ than conflict between strangers.",
      "target_word":"painful",
      "distractor_options":["complex","common","lasting"]}],
   "relational_map":{"concept_activations_expected":["conflict","family","pain","stranger"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"conflict","to":"family","weight_delta":0.8},
     {"from":"conflict","to":"pain","weight_delta":0.9},
     {"from":"family","to":"pain","weight_delta":0.8},
     {"from":"pain","to":"stranger","weight_delta":0.6}]}},

  {"sentence_id":"tf_00020",
   "sentence":"Forgiveness does not erase harm but releases the person from carrying it alone.",
   "see_and_say_variants":[
     {"cloze_id":"cf_018",
      "masked_sentence":"Forgiveness does not erase harm but releases the person from ___ it alone.",
      "target_word":"carrying",
      "distractor_options":["feeling","hiding","facing"]}],
   "relational_map":{"concept_activations_expected":["forgiveness","harm","release","carrying"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"forgiveness","to":"harm","weight_delta":0.9},
     {"from":"forgiveness","to":"release","weight_delta":0.9},
     {"from":"harm","to":"carrying","weight_delta":0.8},
     {"from":"release","to":"carrying","weight_delta":0.8}]}},

  {"sentence_id":"tf_00021",
   "sentence":"A boundary set with care protects the relationship rather than ending it.",
   "see_and_say_variants":[
     {"cloze_id":"cf_019",
      "masked_sentence":"A boundary set with care ___ the relationship rather than ending it.",
      "target_word":"protects",
      "distractor_options":["changes","tests","limits"]}],
   "relational_map":{"concept_activations_expected":["boundary","care","protection","relationship"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"boundary","to":"care","weight_delta":0.9},
     {"from":"boundary","to":"protection","weight_delta":0.9},
     {"from":"care","to":"relationship","weight_delta":0.9},
     {"from":"protection","to":"relationship","weight_delta":0.8}]}},

  {"sentence_id":"tf_00022",
   "sentence":"Children observe how adults handle conflict and learn from what they see.",
   "see_and_say_variants":[
     {"cloze_id":"cf_020",
      "masked_sentence":"Children observe how adults handle conflict and ___ from what they see.",
      "target_word":"learn",
      "distractor_options":["suffer","hide","decide"]}],
   "relational_map":{"concept_activations_expected":["child","observing","conflict","learning"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"child","to":"observing","weight_delta":0.9},
     {"from":"observing","to":"conflict","weight_delta":0.8},
     {"from":"observing","to":"learning","weight_delta":0.9},
     {"from":"conflict","to":"learning","weight_delta":0.7}]}},

  {"sentence_id":"tf_00023",
   "sentence":"Presence means being fully available to another person without distraction.",
   "see_and_say_variants":[
     {"cloze_id":"cf_021",
      "masked_sentence":"Presence means being fully ___ to another person without distraction.",
      "target_word":"available",
      "distractor_options":["open","caring","listening"]}],
   "relational_map":{"concept_activations_expected":["presence","availability","attention","person"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"presence","to":"availability","weight_delta":0.9},
     {"from":"presence","to":"attention","weight_delta":0.9},
     {"from":"availability","to":"person","weight_delta":0.8},
     {"from":"attention","to":"person","weight_delta":0.8}]}},

  {"sentence_id":"tf_00024",
   "sentence":"When a person is in pain they need to be heard before they can be helped.",
   "see_and_say_variants":[
     {"cloze_id":"cf_022",
      "masked_sentence":"When a person is in pain they need to be ___ before they can be helped.",
      "target_word":"heard",
      "distractor_options":["seen","found","understood"]}],
   "relational_map":{"concept_activations_expected":["pain","listening","help","person"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"pain","to":"listening","weight_delta":0.9},
     {"from":"listening","to":"help","weight_delta":0.9},
     {"from":"pain","to":"help","weight_delta":0.8},
     {"from":"person","to":"pain","weight_delta":0.8}]}},

  {"sentence_id":"tf_00025",
   "sentence":"Shared meals are one way a family maintains connection across daily life.",
   "relational_map":{"concept_activations_expected":["sharing","family","connection","ritual"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"sharing","to":"family","weight_delta":0.8},
     {"from":"sharing","to":"connection","weight_delta":0.9},
     {"from":"family","to":"ritual","weight_delta":0.8},
     {"from":"connection","to":"ritual","weight_delta":0.7}]}},

  {"sentence_id":"tf_00026",
   "sentence":"A person raised without safety learns to survive rather than to trust.",
   "see_and_say_variants":[
     {"cloze_id":"cf_023",
      "masked_sentence":"A person raised without safety learns to ___ rather than to trust.",
      "target_word":"survive",
      "distractor_options":["fight","hide","protect"]}],
   "relational_map":{"concept_activations_expected":["safety","survival","trust","learning"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"safety","to":"survival","weight_delta":0.9},
     {"from":"safety","to":"trust","weight_delta":0.9},
     {"from":"survival","to":"trust","weight_delta":0.8},
     {"from":"learning","to":"survival","weight_delta":0.7}]}},

  {"sentence_id":"tf_00027",
   "sentence":"Anger between people who care about each other signals that something matters.",
   "see_and_say_variants":[
     {"cloze_id":"cf_024",
      "masked_sentence":"Anger between people who care about each other ___ that something matters.",
      "target_word":"signals",
      "distractor_options":["proves","means","shows"]}],
   "relational_map":{"concept_activations_expected":["anger","care","signal","meaning"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"anger","to":"care","weight_delta":0.8},
     {"from":"anger","to":"signal","weight_delta":0.9},
     {"from":"signal","to":"meaning","weight_delta":0.8},
     {"from":"care","to":"meaning","weight_delta":0.8}]}},

  {"sentence_id":"tf_00028",
   "sentence":"A community holds the individuals within it when their own strength is not enough.",
   "see_and_say_variants":[
     {"cloze_id":"cf_025",
      "masked_sentence":"A community ___ the individuals within it when their own strength is not enough.",
      "target_word":"holds",
      "distractor_options":["supports","shapes","protects"]}],
   "relational_map":{"concept_activations_expected":["community","holding","individual","strength"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"community","to":"holding","weight_delta":0.9},
     {"from":"community","to":"individual","weight_delta":0.8},
     {"from":"holding","to":"strength","weight_delta":0.8},
     {"from":"individual","to":"strength","weight_delta":0.7}]}},

  {"sentence_id":"tf_00029",
   "sentence":"Recovery requires that a person is not alone in carrying what happened to them.",
   "see_and_say_variants":[
     {"cloze_id":"cf_026",
      "masked_sentence":"Recovery requires that a person is not ___ in carrying what happened to them.",
      "target_word":"alone",
      "distractor_options":["silent","ashamed","afraid"]}],
   "relational_map":{"concept_activations_expected":["recovery","isolation","carrying","support"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"recovery","to":"isolation","weight_delta":0.9},
     {"from":"recovery","to":"carrying","weight_delta":0.8},
     {"from":"recovery","to":"support","weight_delta":0.9},
     {"from":"isolation","to":"carrying","weight_delta":0.8}]}},

  {"sentence_id":"tf_00030",
   "sentence":"Being witnessed in pain by someone who stays is different from being witnessed by someone who leaves.",
   "relational_map":{"concept_activations_expected":["witnessing","pain","presence","abandonment"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"witnessing","to":"pain","weight_delta":0.9},
     {"from":"witnessing","to":"presence","weight_delta":0.9},
     {"from":"presence","to":"abandonment","weight_delta":0.8},
     {"from":"pain","to":"abandonment","weight_delta":0.7}]}},

  {"sentence_id":"tf_00031",
   "sentence":"A person can be surrounded by others and still feel completely alone.",
   "see_and_say_variants":[
     {"cloze_id":"cf_027",
      "masked_sentence":"A person can be surrounded by others and still feel completely ___.",
      "target_word":"alone",
      "distractor_options":["unseen","afraid","lost"]}],
   "relational_map":{"concept_activations_expected":["isolation","belonging","person","loneliness"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"isolation","to":"belonging","weight_delta":0.9},
     {"from":"isolation","to":"person","weight_delta":0.8},
     {"from":"person","to":"loneliness","weight_delta":0.9},
     {"from":"belonging","to":"loneliness","weight_delta":0.8}]}},

  {"sentence_id":"tf_00032",
   "sentence":"Trust broken by someone with power over you takes longer to rebuild than trust broken between equals.",
   "see_and_say_variants":[
     {"cloze_id":"cf_028",
      "masked_sentence":"Trust broken by someone with ___ over you takes longer to rebuild.",
      "target_word":"power",
      "distractor_options":["authority","care","history"]}],
   "relational_map":{"concept_activations_expected":["trust","power","repair","asymmetry"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trust","to":"power","weight_delta":0.9},
     {"from":"trust","to":"repair","weight_delta":0.9},
     {"from":"power","to":"asymmetry","weight_delta":0.9},
     {"from":"repair","to":"asymmetry","weight_delta":0.7}]}},

  {"sentence_id":"tf_00033",
   "sentence":"A name given with love carries the intention of the person who gave it.",
   "relational_map":{"concept_activations_expected":["naming","love","intention","identity"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"naming","to":"love","weight_delta":0.9},
     {"from":"naming","to":"intention","weight_delta":0.8},
     {"from":"love","to":"identity","weight_delta":0.8},
     {"from":"intention","to":"identity","weight_delta":0.7}]}},

  {"sentence_id":"tf_00034",
   "sentence":"When someone who hurt you asks for forgiveness they are asking you to carry less.",
   "see_and_say_variants":[
     {"cloze_id":"cf_029",
      "masked_sentence":"When someone who hurt you asks for forgiveness they are asking you to carry ___.",
      "target_word":"less",
      "distractor_options":["more","something","it"]}],
   "relational_map":{"concept_activations_expected":["forgiveness","harm","carrying","release"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"forgiveness","to":"harm","weight_delta":0.9},
     {"from":"forgiveness","to":"carrying","weight_delta":0.9},
     {"from":"carrying","to":"release","weight_delta":0.9},
     {"from":"harm","to":"release","weight_delta":0.7}]}},

  {"sentence_id":"tf_00035",
   "sentence":"A family that can speak about hard things builds resilience across generations.",
   "see_and_say_variants":[
     {"cloze_id":"cf_030",
      "masked_sentence":"A family that can speak about hard things builds ___ across generations.",
      "target_word":"resilience",
      "distractor_options":["connection","strength","memory"]}],
   "relational_map":{"concept_activations_expected":["family","communication","resilience","generation"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"family","to":"communication","weight_delta":0.9},
     {"from":"communication","to":"resilience","weight_delta":0.9},
     {"from":"resilience","to":"generation","weight_delta":0.8},
     {"from":"family","to":"resilience","weight_delta":0.8}]}},

  {"sentence_id":"tf_00036",
   "sentence":"Love is not only a feeling but also a set of repeated actions toward another person.",
   "see_and_say_variants":[
     {"cloze_id":"cf_031",
      "masked_sentence":"Love is not only a feeling but also a set of repeated ___ toward another person.",
      "target_word":"actions",
      "distractor_options":["words","gestures","choices"]}],
   "relational_map":{"concept_activations_expected":["love","action","repetition","person"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"love","to":"action","weight_delta":0.9},
     {"from":"love","to":"repetition","weight_delta":0.8},
     {"from":"action","to":"person","weight_delta":0.8},
     {"from":"repetition","to":"person","weight_delta":0.6}]}},

  {"sentence_id":"tf_00037",
   "sentence":"A person who grew up feeling unsafe in their family carries that map into new relationships.",
   "relational_map":{"concept_activations_expected":["safety","family","pattern","relationship"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"safety","to":"family","weight_delta":0.9},
     {"from":"family","to":"pattern","weight_delta":0.9},
     {"from":"pattern","to":"relationship","weight_delta":0.9},
     {"from":"safety","to":"relationship","weight_delta":0.7}]}},

  {"sentence_id":"tf_00038",
   "sentence":"Silence in a family can protect or it can isolate depending on what is being silenced.",
   "see_and_say_variants":[
     {"cloze_id":"cf_032",
      "masked_sentence":"Silence in a family can protect or it can ___ depending on what is being silenced.",
      "target_word":"isolate",
      "distractor_options":["harm","divide","burden"]}],
   "relational_map":{"concept_activations_expected":["silence","family","protection","isolation"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"silence","to":"family","weight_delta":0.8},
     {"from":"silence","to":"protection","weight_delta":0.8},
     {"from":"silence","to":"isolation","weight_delta":0.9},
     {"from":"protection","to":"isolation","weight_delta":0.6}]}},

  {"sentence_id":"tf_00039",
   "sentence":"When someone shows up for you in your worst moment they become part of your foundation.",
   "see_and_say_variants":[
     {"cloze_id":"cf_033",
      "masked_sentence":"When someone shows up for you in your worst moment they become part of your ___.",
      "target_word":"foundation",
      "distractor_options":["memory","story","healing"]}],
   "relational_map":{"concept_activations_expected":["presence","crisis","foundation","trust"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"presence","to":"crisis","weight_delta":0.9},
     {"from":"presence","to":"foundation","weight_delta":0.9},
     {"from":"crisis","to":"trust","weight_delta":0.8},
     {"from":"foundation","to":"trust","weight_delta":0.8}]}},

  {"sentence_id":"tf_00040",
   "sentence":"Apology without changed behavior is a signal without meaning.",
   "see_and_say_variants":[
     {"cloze_id":"cf_034",
      "masked_sentence":"Apology without changed behavior is a signal without ___.",
      "target_word":"meaning",
      "distractor_options":["weight","effect","truth"]}],
   "relational_map":{"concept_activations_expected":["apology","behavior","signal","meaning"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"apology","to":"behavior","weight_delta":0.9},
     {"from":"apology","to":"signal","weight_delta":0.8},
     {"from":"signal","to":"meaning","weight_delta":0.9},
     {"from":"behavior","to":"meaning","weight_delta":0.8}]}},

  {"sentence_id":"tf_00041",
   "sentence":"People carry their families inside them even after the family is no longer present.",
   "relational_map":{"concept_activations_expected":["family","carrying","presence","identity"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"family","to":"carrying","weight_delta":0.9},
     {"from":"family","to":"presence","weight_delta":0.8},
     {"from":"carrying","to":"identity","weight_delta":0.9},
     {"from":"presence","to":"identity","weight_delta":0.7}]}},

  {"sentence_id":"tf_00042",
   "sentence":"The strength needed to ask for help is different from but equal to the strength to give it.",
   "see_and_say_variants":[
     {"cloze_id":"cf_035",
      "masked_sentence":"The strength needed to ask for ___ is different from but equal to the strength to give it.",
      "target_word":"help",
      "distractor_options":["forgiveness","safety","care"]}],
   "relational_map":{"concept_activations_expected":["help","strength","asking","giving"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"help","to":"strength","weight_delta":0.9},
     {"from":"help","to":"asking","weight_delta":0.9},
     {"from":"strength","to":"giving","weight_delta":0.8},
     {"from":"asking","to":"giving","weight_delta":0.7}]}},

  {"sentence_id":"tf_00043",
   "sentence":"A child who is taught they are loved is given a resource they will spend their whole life drawing on.",
   "relational_map":{"concept_activations_expected":["child","love","resource","resilience"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"child","to":"love","weight_delta":0.9},
     {"from":"love","to":"resource","weight_delta":0.9},
     {"from":"resource","to":"resilience","weight_delta":0.8},
     {"from":"child","to":"resilience","weight_delta":0.8}]}},

  {"sentence_id":"tf_00044",
   "sentence":"When a person cannot trust anyone they must carry everything alone.",
   "see_and_say_variants":[
     {"cloze_id":"cf_036",
      "masked_sentence":"When a person cannot ___ anyone they must carry everything alone.",
      "target_word":"trust",
      "distractor_options":["reach","find","help"]}],
   "relational_map":{"concept_activations_expected":["trust","isolation","carrying","burden"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trust","to":"isolation","weight_delta":0.9},
     {"from":"isolation","to":"carrying","weight_delta":0.9},
     {"from":"carrying","to":"burden","weight_delta":0.9},
     {"from":"trust","to":"burden","weight_delta":0.7}]}},

  {"sentence_id":"tf_00045",
   "sentence":"Loyalty between people who have survived hardship together is different from loyalty between those who have not.",
   "relational_map":{"concept_activations_expected":["loyalty","survival","hardship","bond"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"loyalty","to":"survival","weight_delta":0.9},
     {"from":"loyalty","to":"hardship","weight_delta":0.8},
     {"from":"survival","to":"bond","weight_delta":0.9},
     {"from":"hardship","to":"bond","weight_delta":0.8}]}},

  {"sentence_id":"tf_00046",
   "sentence":"A person raised with warmth finds it easier to offer warmth to others.",
   "see_and_say_variants":[
     {"cloze_id":"cf_037",
      "masked_sentence":"A person raised with ___ finds it easier to offer warmth to others.",
      "target_word":"warmth",
      "distractor_options":["safety","love","care"]}],
   "relational_map":{"concept_activations_expected":["warmth","raising","giving","person"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"warmth","to":"raising","weight_delta":0.8},
     {"from":"warmth","to":"giving","weight_delta":0.9},
     {"from":"raising","to":"person","weight_delta":0.8},
     {"from":"giving","to":"person","weight_delta":0.7}]}},

  {"sentence_id":"tf_00047",
   "sentence":"Connection requires that both people remain present through difficulty not just ease.",
   "see_and_say_variants":[
     {"cloze_id":"cf_038",
      "masked_sentence":"Connection requires that both people remain ___ through difficulty not just ease.",
      "target_word":"present",
      "distractor_options":["willing","honest","caring"]}],
   "relational_map":{"concept_activations_expected":["connection","presence","difficulty","relationship"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"connection","to":"presence","weight_delta":0.9},
     {"from":"connection","to":"difficulty","weight_delta":0.8},
     {"from":"presence","to":"relationship","weight_delta":0.9},
     {"from":"difficulty","to":"relationship","weight_delta":0.7}]}},

  {"sentence_id":"tf_00048",
   "sentence":"A person who has been through darkness can recognize it in someone else and reach toward them.",
   "relational_map":{"concept_activations_expected":["experience","recognition","reaching","care"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"experience","to":"recognition","weight_delta":0.9},
     {"from":"recognition","to":"reaching","weight_delta":0.9},
     {"from":"reaching","to":"care","weight_delta":0.9},
     {"from":"experience","to":"care","weight_delta":0.8}]}},

  {"sentence_id":"tf_00049",
   "sentence":"Home is not only a place but a feeling of being known and safe.",
   "see_and_say_variants":[
     {"cloze_id":"cf_039",
      "masked_sentence":"Home is not only a place but a feeling of being known and ___.",
      "target_word":"safe",
      "distractor_options":["loved","seen","held"]}],
   "relational_map":{"concept_activations_expected":["home","safety","belonging","identity"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"home","to":"safety","weight_delta":0.9},
     {"from":"home","to":"belonging","weight_delta":0.9},
     {"from":"safety","to":"identity","weight_delta":0.8},
     {"from":"belonging","to":"identity","weight_delta":0.8}]}},

  {"sentence_id":"tf_00050",
   "sentence":"The people who stayed when things were hard are the ones who become irreplaceable.",
   "see_and_say_variants":[
     {"cloze_id":"cf_040",
      "masked_sentence":"The people who ___ when things were hard are the ones who become irreplaceable.",
      "target_word":"stayed",
      "distractor_options":["helped","cared","arrived"]}],
   "relational_map":{"concept_activations_expected":["loyalty","presence","hardship","bond"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"loyalty","to":"presence","weight_delta":0.9},
     {"from":"presence","to":"hardship","weight_delta":0.8},
     {"from":"hardship","to":"bond","weight_delta":0.9},
     {"from":"loyalty","to":"bond","weight_delta":0.9}]}}
]

FAMILY_SENTENCES_PATH.write_text(json.dumps(FAMILY_SENTENCES, indent=2), encoding='utf-8')
n_with_variants = sum(1 for s in FAMILY_SENTENCES if s.get('see_and_say_variants'))
print(f"Wrote {len(FAMILY_SENTENCES)} family sentences ({n_with_variants} with see_and_say_variants)")
print("Key domains: protection, care, trust, harm, repair, grief, resilience, belonging")
print("Ethics bridge concepts: careâ†’trust, harmâ†’acknowledgment, boundaryâ†’protection,")
print("                        warningâ†’obligation, silenceâ†’isolation, presenceâ†’foundation")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2.12 â€” Write family teaching list
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

FAMILY_TEACHING_LIST_PATH = Path('corpus/lists/teaching_list_family.json')
FAMILY_TEACHING_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)

FAMILY_CLOZE_IDS = [f"cf_{i:03d}" for i in range(1, 41)]

FAMILY_TEACHING_LIST = {
  "see_and_say_session": {
    "session_id": "sas_family_v1",
    "pass_threshold": 0.6,
    "cloze_items": FAMILY_CLOZE_IDS,
    "sentences_path": "sentences/teaching_sentences_family.json"
  },
  "target_concepts": [
    "protects","survival","trust","existed","history","knowledge",
    "warn","obligation","permeable","acknowledging","context","connection",
    "strength","changes","suffer","passes","painful","carrying",
    "protects","learn","available","heard","signals","holds",
    "alone","power","alone","less","resilience","actions",
    "isolate","foundation","meaning","help","trust","warmth",
    "present","safe","stayed"
  ]
}

FAMILY_TEACHING_LIST_PATH.write_text(json.dumps(FAMILY_TEACHING_LIST, indent=2), encoding='utf-8')
print(f"Wrote family teaching list: {len(FAMILY_CLOZE_IDS)} cloze items")
print(f"Session: {FAMILY_TEACHING_LIST['see_and_say_session']['session_id']}")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 3 â€” Feed phoneme inventory
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

phoneme_path = Path('corpus/phonemes/english_phoneme_inventory.json')
phonemes     = json.loads(phoneme_path.read_text(encoding='utf-8'))
nodes_before = system.memory_web.graph.number_of_nodes()
edges_before = system.memory_web.graph.number_of_edges()

for i, entry in enumerate(phonemes, 1):
    symbol   = entry.get('symbol_ipa', '')
    desc     = (entry.get('articulation') or {}).get('description', '')
    examples = ', '.join([x.get('word','') for x in entry.get('example_words',[])[:4]])
    system.process_input(
        f"Phoneme {symbol} is described as {desc}. Example words include {examples}.",
        metadata={'source':'corpus_ingest','corpus_file':str(phoneme_path),
                  'entry_id':entry.get('phoneme_id',f'ph_{i:03d}')})
    TOTAL_INGEST_CALLS += 1
    node_label = f"phoneme:{symbol}"
    system.memory_web.add_concept(node_label, metadata={
        'phoneme_id':entry.get('phoneme_id'),'type':'phoneme'})
    for edge in entry.get('graph_edges', []):
        target = str(edge.get('to','')).strip()
        if not target: continue
        if system.memory_web.get_concept(target) is None:
            system.memory_web.add_concept(target)
        system.memory_web.connect(node_label, target, weight=float(edge.get('weight',0.5)))
    if i % 10 == 0:
        print(f"  {i}/{len(phonemes)} phonemes")

m = system.get_metrics()
TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
print(f"Phoneme ingest complete | new nodes: {system.memory_web.graph.number_of_nodes()-nodes_before} | "
      f"new edges: {system.memory_web.graph.number_of_edges()-edges_before} | t_g: {float(m.get('t_g',0.5)):.4f}")
shard_status(system, "Post-Phoneme")
verdant_monitor.snapshot("Post-Phoneme")
gc.collect()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 4 â€” Feed grammar rules
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

grammar_path  = Path('corpus/grammar/english_grammar_rules.json')
rules         = json.loads(grammar_path.read_text(encoding='utf-8'))
unlock_chains = []

for i, rule in enumerate(rules, 1):
    rule_id   = rule.get('rule_id', f'gr_{i:05d}')
    name      = rule.get('rule_name', '')
    formal    = rule.get('formal_statement', '')
    canonical = (rule.get('canonical_example') or {}).get('correct', '')
    system.process_input(
        f"Grammar rule {name}. {formal} Canonical example: {canonical}.",
        metadata={'source':'corpus_ingest','corpus_file':str(grammar_path),'entry_id':rule_id})
    TOTAL_INGEST_CALLS += 1
    if system.memory_web.get_concept(rule_id) is None:
        system.memory_web.add_concept(rule_id, metadata={'type':'grammar_rule'})
    for edge in rule.get('graph_edges_this_rule_creates', []):
        src,dst,w = str(edge.get('from','')),str(edge.get('to','')),float(edge.get('weight',0.6))
        if src and system.memory_web.get_concept(src) is None: system.memory_web.add_concept(src)
        if dst and system.memory_web.get_concept(dst) is None: system.memory_web.add_concept(dst)
        if src and dst: system.memory_web.connect(src, dst, weight=w)
    for p in [str(x) for x in rule.get('prerequisite_rules', [])]:
        if system.memory_web.get_concept(p) is None:
            system.memory_web.add_concept(p, metadata={'type':'grammar_rule'})
        system.memory_web.connect(p, rule_id, weight=0.9)
        unlock_chains.append((p, rule_id))
    for u in [str(x) for x in rule.get('unlocks_rules', [])]:
        if system.memory_web.get_concept(u) is None:
            system.memory_web.add_concept(u, metadata={'type':'grammar_rule'})
        system.memory_web.connect(rule_id, u, weight=0.9)
        unlock_chains.append((rule_id, u))
    if i % 10 == 0:
        print(f"  {i}/{len(rules)} grammar rules")

m = system.get_metrics()
TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
print(f"Grammar complete | unlock chains: {len(unlock_chains)} | t_g: {float(m.get('t_g',0.5)):.4f}")
shard_status(system, "Post-Grammar")
verdant_monitor.snapshot("Post-Grammar")
gc.collect()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 5 â€” Feed lexicon (chunk-based activation)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

lex_path       = Path('corpus/lexicon/core_vocabulary_physical_world.json')
lex            = json.loads(lex_path.read_text(encoding='utf-8'))
nodes_before   = system.memory_web.graph.number_of_nodes()
edges_before   = system.memory_web.graph.number_of_edges()
seeding_report = {}

for i, entry in enumerate(lex, 1):
    wid       = entry.get('word_id', f'w_{i:05d}')
    word      = entry.get('word', '')
    sem       = entry.get('semantics', {})
    primary   = sem.get('primary_definition', '')
    sense1    = (sem.get('definitions_by_sense') or [{}])[0]
    ex        = sense1.get('example', '')
    coll_text = ', '.join((((sem.get('collocations') or {}).get('strong_collocates')) or [])[:3])
    chunk = system.process_input(
        f"Word {word}. Definition: {primary}. Example: {ex}. Strong collocates: {coll_text}.",
        metadata={'source':'corpus_ingest','corpus_file':str(lex_path),'entry_id':wid})
    TOTAL_INGEST_CALLS += 1
    try:
        mem = chunk.get_section_content("memory_section") or {}
        for c, score in (mem.get("activated_concepts") or {}).items():
            if float(score) >= 0.1:
                TRAINING_TOP_ACTIVATIONS[str(c)] = TRAINING_TOP_ACTIVATIONS.get(str(c),0)+1
    except Exception:
        pass
    if word and system.memory_web.get_concept(word) is None:
        system.memory_web.add_concept(word, metadata={'type':'lexeme','word_id':wid})
    edges_seeded = 0
    for edge in (entry.get('graph_seeding') or {}).get('suggested_edge_targets', []):
        target = str(edge.get('target','')).strip()
        if not target: continue
        if system.memory_web.get_concept(word) is None: system.memory_web.add_concept(word)
        if system.memory_web.get_concept(target) is None: system.memory_web.add_concept(target)
        if system.memory_web.connect(word, target, weight=float(edge.get('weight',0.6))):
            edges_seeded += 1
    seeding_report[word] = edges_seeded
    if i % 25 == 0:
        m = system.get_metrics()
        TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
        print(f"  {i}/{len(lex)} words | nodes+{system.memory_web.graph.number_of_nodes()-nodes_before} | "
              f"edges+{system.memory_web.graph.number_of_edges()-edges_before} | t_g={float(m.get('t_g',0.5)):.4f}")

m = system.get_metrics()
TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
zero_seeded = [w for w,n in seeding_report.items() if n == 0]
print(f"Lexicon complete | new nodes: {system.memory_web.graph.number_of_nodes()-nodes_before} | "
      f"new edges: {system.memory_web.graph.number_of_edges()-edges_before}")
print(f"Words with 0 edges seeded ({len(zero_seeded)}): {zero_seeded[:12]}")
print(f"Top seeded: {sorted(seeding_report.items(),key=lambda x:x[1],reverse=True)[:8]}")
shard_status(system, "Post-Lexicon")
verdant_monitor.snapshot("Post-Lexicon")
gc.collect()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 5.5 â€” Mid-run save + reload (RAM flush)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

print("Saving mid-run checkpoint...")
verdant_monitor.snapshot("Pre-mid-save")
configure_mitosis(system, "watch")
system.save_state(str(CHECKPOINT_PATH))
shard_status(system, "After mid-run save")
del system
gc.collect()
time.sleep(2)

system = VerdantSystem()
system.load_state(str(CHECKPOINT_PATH))
system._checkpoint_path = str(CHECKPOINT_PATH)  # CRITICAL: thaw() needs Drive path
validate_shard_manifest(system, CHECKPOINT_PATH, label="Cell 5.5 reload")
configure_mitosis(system, "watch")
query_interface = QueryInterface(system)
m = system.get_metrics()
TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
verdant_monitor.snapshot("Post-reload")
print(f"Reload complete | nodes: {system.memory_web.graph.number_of_nodes()} | "
      f"edges: {system.memory_web.graph.number_of_edges()} | t_g: {float(m.get('t_g',0.5)):.4f}")
shard_status(system, "Ready for sentences")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TRACE LOGGER â€” add to notebook
# Captures real activation waves from every process_input call
# Produces a JSON log that feeds the live visualizer
#
# WHERE TO ADD:
#   Cell 6 (physics sentences) â€” wrap the existing process_input call
#   Cell 6b (ecology)         â€” same wrapper
#   Cell 6c (interaction)     â€” same wrapper
#   New Cell 6d               â€” saves and downloads the trace
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 5.4 â€” Initialize trace logger
# Paste this BEFORE Cell 6 (after Cell 5.5 reload)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

import time as _time

ACTIVATION_TRACE = []   # full event log
TRACE_PATH = LOCAL_DATA / 'activation_trace.json'

def log_chunk(chunk, sentence_id, sentence_text, corpus, ingest_call_n):
    """Extract activation data from a CognitiveChunk and log it."""
    event = {
        'n':          ingest_call_n,
        'ts':         _time.time(),
        'id':         sentence_id,
        'corpus':     corpus,
        'text':       sentence_text[:120],
        'shard':      getattr(system.memory_web, 'active_shard_id', 'unknown'),
        'activated':  {},
        'ethics_weight': 0.0,
        'tg':         float(system.get_metrics().get('t_g', 0.5)),
        'new_emergents': 0,
    }
    try:
        mem = chunk.get_section_content("memory_section") or {}
        activated = mem.get("activated_concepts", {}) or {}
        # Keep top 20 by score â€” enough signal, not too much data
        # MP-NOISE: strip system introspection nodes before writing to trace
        _TRACE_NOISE = {
            'activebasins','hci','t_g','self','observation','identity',
            'basin_monolith_000000','grammar','concept','word','example',
            'physical','strong','changed','world','collocates','described',
            'formal','smooth','rough','bright','slow','above','below',
            'remain','particles','fields','inside','moving','raises'
        }
        _TRACE_PREFIXES = ('basin_','Emergent_','gr_00','phoneme:')
        top = sorted(
            [(k, float(v)) for k, v in activated.items()
             if float(v) >= 0.05
             and k not in _TRACE_NOISE
             and not any(k.startswith(p) for p in _TRACE_PREFIXES)],
            key=lambda x: x[1], reverse=True
        )[:20]
        event['activated'] = {k: round(v, 4) for k, v in top}
    except Exception:
        pass

    try:
        basin = chunk.get_section_content("basin_section") or {}
        event['ethics_weight'] = round(float(basin.get("ethics_king_weight", 0.0)), 4)
    except Exception:
        pass

    try:
        council = chunk.get_section_content("three_kings_layer_section") or {}
        weights = council.get("influence_weights", {}) if isinstance(council, dict) else {}
        total = sum(float(v or 0) for v in weights.values())
        if total > 0:
            event['ethics_weight'] = round(float(weights.get("EthicsKing", 0)) / total, 4)
    except Exception:
        pass

    ACTIVATION_TRACE.append(event)

print("Trace logger initialized.")
print(f"Events will be saved to: {TRACE_PATH}")



# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MODIFIED Cell 6 â€” physics sentences with trace logging
# Replace your existing Cell 6 with this
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

sent_path       = CORPUS_SENTENCES_PATH
sentences       = json.loads(sent_path.read_text(encoding='utf-8'))
nodes_before    = system.memory_web.graph.number_of_nodes()
edges_before    = system.memory_web.graph.number_of_edges()
emergent_before = set(system.memory_web.get_emergent_nodes())
coverage_hits   = 0
coverage_exp    = 0

print(f"Running {len(sentences)} causal sentences (with trace)...")

for i, entry in enumerate(sentences, 1):
    sid  = entry.get('sentence_id', f'ts_{i:05d}')
    text = entry.get('sentence', '')

    chunk = system.process_input(text, metadata={
        'source':'corpus_ingest','corpus_file':str(sent_path),'entry_id':sid})
    TOTAL_INGEST_CALLS += 1

    # â”€â”€ TRACE â”€â”€
    log_chunk(chunk, sid, text, 'physics', TOTAL_INGEST_CALLS)

    try:
        mem          = chunk.get_section_content("memory_section") or {}
        activated    = mem.get("activated_concepts", {}) or {}
        # MP-NOISE: filter system nodes from activated_set
        activated_set = {
            str(k) for k,v in activated.items()
            if float(v) >= 0.1
            and str(k) not in SYSTEM_NOISE
            and not any(str(k).startswith(p) for p in SYSTEM_PREFIXES)
        }
        for c in activated_set:
            TRAINING_TOP_ACTIVATIONS[c] = TRAINING_TOP_ACTIVATIONS.get(c,0)+1
    except Exception:
        activated_set = set()

    rel_map = entry.get('relational_map') or {}
    for edge in (rel_map.get('graph_edges_this_sentence_reinforces') or []):
        src = str(edge.get('from','')).strip()
        dst = str(edge.get('to','')).strip()
        if not src or not dst: continue
        if system.memory_web.get_concept(src) is None: system.memory_web.add_concept(src)
        if system.memory_web.get_concept(dst) is None: system.memory_web.add_concept(dst)
        system.memory_web.connect(src, dst, weight=float(edge.get('weight_delta',0.1)))

    expected       = (rel_map.get('concept_activations_expected') or [])
    hit            = sum(1 for c in expected if c in activated_set)
    coverage_hits += hit
    coverage_exp  += len(expected)
    TRAINING_COVERAGE['hit']      += hit
    TRAINING_COVERAGE['expected'] += len(expected)

    if i % 10 == 0:
        m            = system.get_metrics()
        TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
        emergent_now = set(system.memory_web.get_emergent_nodes())
        cov          = (coverage_hits/max(1,coverage_exp))*100.0
        print(f"  {i}/{len(sentences)} | coverage={cov:.1f}% | "
              f"new_emergents={len(emergent_now-emergent_before)} | t_g={float(m.get('t_g',0.5)):.4f}")
        emergent_before = emergent_now

m         = system.get_metrics()
TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
final_cov = (coverage_hits/max(1,coverage_exp))*100.0

SYSTEM_NOISE    = {'activebasins','hci','t_g','self','observation','identity',
                   'basin_monolith_000000','grammar','concept','word','example',
                   'physical','strong','changed','world','collocates','described',
                   'formal','smooth','rough','bright','slow','above','below',
                   'remain','particles','fields','inside','moving','raises'}
SYSTEM_PREFIXES = ('basin_','Emergent_','gr_00','phoneme:')
UBIQUITY_THRESHOLD = TOTAL_INGEST_CALLS * 0.85

top10 = sorted(
    [(c,n) for c,n in TRAINING_TOP_ACTIVATIONS.items()
     if c not in SYSTEM_NOISE
     and not any(c.startswith(p) for p in SYSTEM_PREFIXES)
     and n < UBIQUITY_THRESHOLD],
    key=lambda x:x[1], reverse=True)[:10]

print(f"Sentence ingest complete | new concepts: "
      f"{system.memory_web.graph.number_of_nodes()-nodes_before} | "
      f"new edges: {system.memory_web.graph.number_of_edges()-edges_before} | "
      f"coverage: {final_cov:.2f}%")
print(f"Top 10 activated (filtered): {top10}")
print(f"Trace events logged: {len(ACTIVATION_TRACE)}")
shard_status(system, "Post-Sentences")
verdant_monitor.snapshot("Post-Sentences")
gc.collect()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MODIFIED Cell 6b â€” ecology with trace
# Replace your existing Cell 6b with this
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

ecology_sentences   = json.loads(ECOLOGY_SENTENCES_PATH.read_text(encoding='utf-8'))
eco_nodes_before    = system.memory_web.graph.number_of_nodes()
eco_edges_before    = system.memory_web.graph.number_of_edges()
eco_emergent_before = set(system.memory_web.get_emergent_nodes())
eco_coverage_hits   = 0
eco_coverage_exp    = 0

print(f"Running {len(ecology_sentences)} ecology sentences (with trace)...")

for i, entry in enumerate(ecology_sentences, 1):
    sid  = entry.get('sentence_id', f'te_{i:05d}')
    text = entry.get('sentence', '')
    chunk = system.process_input(text, metadata={
        'source':'corpus_ingest',
        'corpus_file':str(ECOLOGY_SENTENCES_PATH),
        'entry_id':sid})
    TOTAL_INGEST_CALLS += 1

    # â”€â”€ TRACE â”€â”€
    log_chunk(chunk, sid, text, 'ecology', TOTAL_INGEST_CALLS)

    try:
        mem          = chunk.get_section_content("memory_section") or {}
        activated    = mem.get("activated_concepts", {}) or {}
        # MP-NOISE: filter system nodes from activated_set
        activated_set = {
            str(k) for k,v in activated.items()
            if float(v) >= 0.1
            and str(k) not in SYSTEM_NOISE
            and not any(str(k).startswith(p) for p in SYSTEM_PREFIXES)
        }
        for c in activated_set:
            TRAINING_TOP_ACTIVATIONS[c] = TRAINING_TOP_ACTIVATIONS.get(c,0)+1
    except Exception:
        activated_set = set()

    rel_map = entry.get('relational_map') or {}
    for edge in (rel_map.get('graph_edges_this_sentence_reinforces') or []):
        src = str(edge.get('from','')).strip()
        dst = str(edge.get('to','')).strip()
        if not src or not dst: continue
        if system.memory_web.get_concept(src) is None: system.memory_web.add_concept(src)
        if system.memory_web.get_concept(dst) is None: system.memory_web.add_concept(dst)
        system.memory_web.connect(src, dst, weight=float(edge.get('weight_delta',0.1)))

    expected         = (rel_map.get('concept_activations_expected') or [])
    hit              = sum(1 for c in expected if c in activated_set)
    eco_coverage_hits += hit
    eco_coverage_exp  += len(expected)

    if i % 10 == 0:
        m            = system.get_metrics()
        TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
        eco_now      = set(system.memory_web.get_emergent_nodes())
        cov          = (eco_coverage_hits/max(1,eco_coverage_exp))*100.0
        print(f"  {i}/{len(ecology_sentences)} | coverage={cov:.1f}% | "
              f"new_emergents={len(eco_now-eco_emergent_before)} | t_g={float(m.get('t_g',0.5)):.4f}")
        eco_emergent_before = eco_now

m = system.get_metrics()
TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
eco_final_cov = (eco_coverage_hits/max(1,eco_coverage_exp))*100.0

print(f"\nEcology ingest complete")
print(f"  New nodes:  {system.memory_web.graph.number_of_nodes()-eco_nodes_before}")
print(f"  New edges:  {system.memory_web.graph.number_of_edges()-eco_edges_before}")
print(f"  Coverage:   {eco_final_cov:.2f}%")
print(f"  Trace events so far: {len(ACTIVATION_TRACE)}")
shard_status(system, "Post-Ecology")
verdant_monitor.snapshot("Post-Ecology")
gc.collect()



# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MODIFIED Cell 6c â€” interaction with trace
# Replace your existing Cell 6c with this
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interaction_sentences = json.loads(INTERACTION_SENTENCES_PATH.read_text(encoding='utf-8'))
int_nodes_before      = system.memory_web.graph.number_of_nodes()
int_edges_before      = system.memory_web.graph.number_of_edges()
int_emergent_before   = set(system.memory_web.get_emergent_nodes())
int_coverage_hits     = 0
int_coverage_exp      = 0

print(f"Running {len(interaction_sentences)} interaction sentences (with trace)...")

for i, entry in enumerate(interaction_sentences, 1):
    sid  = entry.get('sentence_id', f'ti_{i:05d}')
    text = entry.get('sentence', '')
    chunk = system.process_input(text, metadata={
        'source':'corpus_ingest',
        'corpus_file':str(INTERACTION_SENTENCES_PATH),
        'entry_id':sid})
    TOTAL_INGEST_CALLS += 1

    # â”€â”€ TRACE â”€â”€
    log_chunk(chunk, sid, text, 'interaction', TOTAL_INGEST_CALLS)

    try:
        mem           = chunk.get_section_content("memory_section") or {}
        activated     = mem.get("activated_concepts", {}) or {}
        # MP-NOISE: filter system nodes from activated_set
        activated_set = {
            str(k) for k,v in activated.items()
            if float(v) >= 0.1
            and str(k) not in SYSTEM_NOISE
            and not any(str(k).startswith(p) for p in SYSTEM_PREFIXES)
        }
        for c in activated_set:
            TRAINING_TOP_ACTIVATIONS[c] = TRAINING_TOP_ACTIVATIONS.get(c,0)+1
    except Exception:
        activated_set = set()

    rel_map = entry.get('relational_map') or {}
    for edge in (rel_map.get('graph_edges_this_sentence_reinforces') or []):
        src = str(edge.get('from','')).strip()
        dst = str(edge.get('to','')).strip()
        if not src or not dst: continue
        if system.memory_web.get_concept(src) is None: system.memory_web.add_concept(src)
        if system.memory_web.get_concept(dst) is None: system.memory_web.add_concept(dst)
        system.memory_web.connect(src, dst, weight=float(edge.get('weight_delta',0.1)))

    expected          = (rel_map.get('concept_activations_expected') or [])
    hit               = sum(1 for c in expected if c in activated_set)
    int_coverage_hits += hit
    int_coverage_exp  += len(expected)

    if i % 10 == 0:
        m            = system.get_metrics()
        TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
        int_now      = set(system.memory_web.get_emergent_nodes())
        cov          = (int_coverage_hits/max(1,int_coverage_exp))*100.0
        print(f"  {i}/{len(interaction_sentences)} | coverage={cov:.1f}% | "
              f"new_emergents={len(int_now-int_emergent_before)} | t_g={float(m.get('t_g',0.5)):.4f}")
        int_emergent_before = int_now

m = system.get_metrics()
TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
int_final_cov = (int_coverage_hits/max(1,int_coverage_exp))*100.0

print(f"\nInteraction ingest complete")
print(f"  New nodes:  {system.memory_web.graph.number_of_nodes()-int_nodes_before}")
print(f"  New edges:  {system.memory_web.graph.number_of_edges()-int_edges_before}")
print(f"  Coverage:   {int_final_cov:.2f}%")
print(f"  Total trace events: {len(ACTIVATION_TRACE)}")

for concept in ['warning','care','harm','boundary','trust','deception','permission']:
    node = system.memory_web.get_concept(concept)
    if node:
        neighbors = system.memory_web.get_neighbors(concept)
        print(f"  {concept:15s} â€” {len(neighbors)} neighbors | "
              f"salience_peak={float(node.get('ethics_salience_peak',0)):.3f}")
    else:
        print(f"  {concept:15s} â€” not in active shard")

shard_status(system, "Post-Interaction")
verdant_monitor.snapshot("Post-Interaction")
gc.collect()

 # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 6d â€” Save trace log
# Run AFTER all sentence cells complete, BEFORE Cell 7
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

print(f"Saving activation trace: {len(ACTIVATION_TRACE)} events...")

# Compute summary stats per concept across all events
concept_stats = {}
for event in ACTIVATION_TRACE:
    for concept, score in event.get('activated', {}).items():
        if concept not in concept_stats:
            concept_stats[concept] = {
                'total_activations': 0,
                'max_score': 0.0,
                'corpora': set(),
                'first_seen': event['n'],
                'last_seen': event['n'],
            }
        s = concept_stats[concept]
        s['total_activations'] += 1
        s['max_score'] = max(s['max_score'], score)
        s['corpora'].add(event['corpus'])
        s['last_seen'] = event['n']

# Convert sets to lists for JSON
for c in concept_stats:
    concept_stats[c]['corpora'] = sorted(concept_stats[c]['corpora'])
    concept_stats[c]['max_score'] = round(concept_stats[c]['max_score'], 4)

trace_doc = {
    'meta': {
        'total_events':    len(ACTIVATION_TRACE),
        'total_concepts':  len(concept_stats),
        'corpora':         ['physics','ecology','interaction'],
        'tg_range':        [round(min(TG_TRAJECTORY),4), round(max(TG_TRAJECTORY),4)],
        'generated_at':    _time.time(),
    },
    'concept_stats': concept_stats,
    'events': ACTIVATION_TRACE,
}

TRACE_PATH.write_text(json.dumps(trace_doc, indent=2), encoding='utf-8')
trace_size = TRACE_PATH.stat().st_size / 1024
print(f"Trace saved: {TRACE_PATH}")
print(f"Size: {trace_size:.1f} KB")
print(f"Concepts tracked: {len(concept_stats)}")

# Top 10 most activated concepts across all corpora
top_concepts = sorted(
    concept_stats.items(),
    key=lambda x: x[1]['total_activations'],
    reverse=True
)[:15]

print(f"\nTop 15 concepts by total activation events:")
for concept, stats in top_concepts:
    corpora_str = '+'.join(stats['corpora'])
    print(f"  {concept:20s}  {stats['total_activations']:4d}x  "
          f"max={stats['max_score']:.2f}  [{corpora_str}]")

# Cross-domain concepts â€” appeared in multiple corpora
cross_domain = [(c, s) for c, s in concept_stats.items()
                if len(s['corpora']) > 1]
cross_domain.sort(key=lambda x: len(x[1]['corpora'])*1000 + x[1]['total_activations'],
                  reverse=True)

print(f"\nCross-domain concepts ({len(cross_domain)} total):")
for concept, stats in cross_domain[:15]:
    print(f"  {concept:20s}  [{'+'.join(stats['corpora'])}]  "
          f"{stats['total_activations']}x")

print(f"\nThe trace file feeds the live visualizer.")
print(f"Upload activation_trace.json to see real activation waves.")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 6d â€” Feed family sentences (with trace)
# Run AFTER Cell 6c (interaction sentences)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

family_sentences    = json.loads(FAMILY_SENTENCES_PATH.read_text(encoding='utf-8'))
fam_nodes_before    = system.memory_web.graph.number_of_nodes()
fam_edges_before    = system.memory_web.graph.number_of_edges()
fam_emergent_before = set(system.memory_web.get_emergent_nodes())
fam_coverage_hits   = 0
fam_coverage_exp    = 0

print(f"Running {len(family_sentences)} family sentences (with trace)...")

for i, entry in enumerate(family_sentences, 1):
    sid  = entry.get('sentence_id', f'tf_{i:05d}')
    text = entry.get('sentence', '')
    chunk = system.process_input(text, metadata={
        'source':'corpus_ingest',
        'corpus_file':str(FAMILY_SENTENCES_PATH),
        'entry_id':sid})
    TOTAL_INGEST_CALLS += 1

    # Trace
    log_chunk(chunk, sid, text, 'family', TOTAL_INGEST_CALLS)

    try:
        mem           = chunk.get_section_content("memory_section") or {}
        activated     = mem.get("activated_concepts", {}) or {}
        # MP-NOISE: filter system nodes from activated_set
        activated_set = {
            str(k) for k,v in activated.items()
            if float(v) >= 0.1
            and str(k) not in SYSTEM_NOISE
            and not any(str(k).startswith(p) for p in SYSTEM_PREFIXES)
        }
        for c in activated_set:
            TRAINING_TOP_ACTIVATIONS[c] = TRAINING_TOP_ACTIVATIONS.get(c,0)+1
    except Exception:
        activated_set = set()

    rel_map = entry.get('relational_map') or {}
    for edge in (rel_map.get('graph_edges_this_sentence_reinforces') or []):
        src = str(edge.get('from','')).strip()
        dst = str(edge.get('to','')).strip()
        if not src or not dst: continue
        if system.memory_web.get_concept(src) is None: system.memory_web.add_concept(src)
        if system.memory_web.get_concept(dst) is None: system.memory_web.add_concept(dst)
        system.memory_web.connect(src, dst, weight=float(edge.get('weight_delta',0.1)))

    expected          = (rel_map.get('concept_activations_expected') or [])
    hit               = sum(1 for c in expected if c in activated_set)
    fam_coverage_hits += hit
    fam_coverage_exp  += len(expected)

    if i % 10 == 0:
        m            = system.get_metrics()
        TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
        fam_now      = set(system.memory_web.get_emergent_nodes())
        cov          = (fam_coverage_hits/max(1,fam_coverage_exp))*100.0
        print(f"  {i}/{len(family_sentences)} | coverage={cov:.1f}% | "
              f"new_emergents={len(fam_now-fam_emergent_before)} | "
              f"t_g={float(m.get('t_g',0.5)):.4f}")
        fam_emergent_before = fam_now

m = system.get_metrics()
TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
fam_final_cov = (fam_coverage_hits/max(1,fam_coverage_exp))*100.0

print(f"\nFamily ingest complete")
print(f"  New nodes:  {system.memory_web.graph.number_of_nodes()-fam_nodes_before}")
print(f"  New edges:  {system.memory_web.graph.number_of_edges()-fam_edges_before}")
print(f"  Coverage:   {fam_final_cov:.2f}%")
print(f"  Total trace events: {len(ACTIVATION_TRACE)}")

# Ethics bridge check â€” this is the one that matters now
print("\nEthics bridge concepts after family corpus:")
ethics_concepts = ['care','trust','harm','warning','boundary','protection',
                   'vulnerability','obligation','repair','presence','carrying',
                   'isolation','love','grief','forgiveness','resilience']
for concept in ethics_concepts:
    node = system.memory_web.get_concept(concept)
    if node:
        neighbors = system.memory_web.get_neighbors(concept)
        sal = float(node.get('ethics_salience_peak', 0))
        threshold_marker = ' â† AT THRESHOLD' if sal >= 0.35 else (
                           ' â† ABOVE MANDATORY' if sal >= 0.35 else '')
        print(f"  {concept:15s} â€” {len(neighbors):4d} neighbors | "
              f"salience={sal:.3f}{threshold_marker}")
    else:
        print(f"  {concept:15s} â€” not in active shard")

shard_status(system, "Post-Family")
verdant_monitor.snapshot("Post-Family")
gc.collect()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 2.13 â€” Write Mandatory Bridge Push corpus
# 20 sentences, deliberately narrow and repetitive.
# Single purpose: push care/trust/harm/boundary salience
# past the 0.35 ETHICS_ANCHOR_THRESHOLD.
# Run this AFTER the family corpus (after Post-Family block above).
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

BRIDGE_SENTENCES_PATH = Path('corpus/sentences/teaching_sentences_bridge.json')
BRIDGE_SENTENCES_PATH.parent.mkdir(parents=True, exist_ok=True)

BRIDGE_SENTENCES = [
  {"sentence_id":"tb_00001","sentence":"Care protects trust, and trust makes care possible.",
   "relational_map":{"concept_activations_expected":["care","trust","protection"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"care","to":"trust","weight_delta":1.0},
     {"from":"trust","to":"care","weight_delta":1.0},
     {"from":"care","to":"protection","weight_delta":0.9}]}},

  {"sentence_id":"tb_00002","sentence":"Harm breaks trust, and broken trust makes harm easier to repeat.",
   "relational_map":{"concept_activations_expected":["harm","trust","boundary"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"harm","to":"trust","weight_delta":1.0},
     {"from":"trust","to":"harm","weight_delta":0.9},
     {"from":"harm","to":"boundary","weight_delta":0.9}]}},

  {"sentence_id":"tb_00003","sentence":"A boundary exists to prevent harm, and care respects the boundary.",
   "relational_map":{"concept_activations_expected":["boundary","harm","care"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"boundary","to":"harm","weight_delta":1.0},
     {"from":"care","to":"boundary","weight_delta":1.0},
     {"from":"boundary","to":"care","weight_delta":0.9}]}},

  {"sentence_id":"tb_00004","sentence":"Trust grows when care is shown and harm is avoided.",
   "relational_map":{"concept_activations_expected":["trust","care","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trust","to":"care","weight_delta":1.0},
     {"from":"trust","to":"harm","weight_delta":0.9},
     {"from":"care","to":"harm","weight_delta":0.85}]}},

  {"sentence_id":"tb_00005","sentence":"Care sets a boundary to protect trust from harm.",
   "relational_map":{"concept_activations_expected":["care","boundary","trust","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"care","to":"boundary","weight_delta":1.0},
     {"from":"boundary","to":"trust","weight_delta":0.95},
     {"from":"trust","to":"harm","weight_delta":0.9}]}},

  {"sentence_id":"tb_00006","sentence":"Without care, trust erodes, and without trust, harm goes unchecked.",
   "relational_map":{"concept_activations_expected":["care","trust","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"care","to":"trust","weight_delta":1.0},
     {"from":"trust","to":"harm","weight_delta":1.0},
     {"from":"care","to":"harm","weight_delta":0.9}]}},

  {"sentence_id":"tb_00007","sentence":"A trusted boundary is one that care has tested against harm.",
   "relational_map":{"concept_activations_expected":["trust","boundary","care","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trust","to":"boundary","weight_delta":1.0},
     {"from":"boundary","to":"care","weight_delta":0.95},
     {"from":"care","to":"harm","weight_delta":0.9}]}},

  {"sentence_id":"tb_00008","sentence":"Harm ignored becomes harm repeated, but care noticed becomes trust earned.",
   "relational_map":{"concept_activations_expected":["harm","care","trust"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"harm","to":"care","weight_delta":0.9},
     {"from":"care","to":"trust","weight_delta":1.0},
     {"from":"harm","to":"trust","weight_delta":0.85}]}},

  {"sentence_id":"tb_00009","sentence":"Every boundary is a form of care, and every care is a boundary against harm.",
   "relational_map":{"concept_activations_expected":["boundary","care","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"boundary","to":"care","weight_delta":1.0},
     {"from":"care","to":"boundary","weight_delta":1.0},
     {"from":"care","to":"harm","weight_delta":0.95}]}},

  {"sentence_id":"tb_00010","sentence":"Trust is care remembered, and harm is trust forgotten.",
   "relational_map":{"concept_activations_expected":["trust","care","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trust","to":"care","weight_delta":1.0},
     {"from":"harm","to":"trust","weight_delta":0.95},
     {"from":"care","to":"harm","weight_delta":0.85}]}},

  {"sentence_id":"tb_00011","sentence":"A boundary held with care prevents the harm that broken trust allows.",
   "relational_map":{"concept_activations_expected":["boundary","care","harm","trust"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"boundary","to":"care","weight_delta":1.0},
     {"from":"boundary","to":"harm","weight_delta":0.95},
     {"from":"harm","to":"trust","weight_delta":0.9}]}},

  {"sentence_id":"tb_00012","sentence":"Care without boundary invites harm; boundary without care erodes trust.",
   "relational_map":{"concept_activations_expected":["care","boundary","harm","trust"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"care","to":"boundary","weight_delta":1.0},
     {"from":"boundary","to":"harm","weight_delta":0.9},
     {"from":"boundary","to":"trust","weight_delta":0.9}]}},

  {"sentence_id":"tb_00013","sentence":"Trust deepens every time care chooses a boundary over harm.",
   "relational_map":{"concept_activations_expected":["trust","care","boundary","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trust","to":"care","weight_delta":1.0},
     {"from":"care","to":"boundary","weight_delta":0.95},
     {"from":"boundary","to":"harm","weight_delta":0.9}]}},

  {"sentence_id":"tb_00014","sentence":"Harm tests trust, trust tests boundary, and boundary tests care.",
   "relational_map":{"concept_activations_expected":["harm","trust","boundary","care"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"harm","to":"trust","weight_delta":1.0},
     {"from":"trust","to":"boundary","weight_delta":1.0},
     {"from":"boundary","to":"care","weight_delta":1.0}]}},

  {"sentence_id":"tb_00015","sentence":"The care that holds a boundary is the same care that repairs harm.",
   "relational_map":{"concept_activations_expected":["care","boundary","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"care","to":"boundary","weight_delta":1.0},
     {"from":"care","to":"harm","weight_delta":1.0},
     {"from":"boundary","to":"harm","weight_delta":0.9}]}},

  {"sentence_id":"tb_00016","sentence":"Trust without a boundary cannot protect against harm, and care without trust cannot be believed.",
   "relational_map":{"concept_activations_expected":["trust","boundary","harm","care"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trust","to":"boundary","weight_delta":1.0},
     {"from":"boundary","to":"harm","weight_delta":0.95},
     {"from":"care","to":"trust","weight_delta":0.95}]}},

  {"sentence_id":"tb_00017","sentence":"Every harm forgiven strengthens the trust that a boundary of care protects.",
   "relational_map":{"concept_activations_expected":["harm","trust","boundary","care"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"harm","to":"trust","weight_delta":1.0},
     {"from":"trust","to":"boundary","weight_delta":0.95},
     {"from":"boundary","to":"care","weight_delta":0.95}]}},

  {"sentence_id":"tb_00018","sentence":"Care is the boundary trust builds against harm.",
   "relational_map":{"concept_activations_expected":["care","boundary","trust","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"care","to":"boundary","weight_delta":1.0},
     {"from":"trust","to":"boundary","weight_delta":1.0},
     {"from":"boundary","to":"harm","weight_delta":1.0}]}},

  {"sentence_id":"tb_00019","sentence":"When trust holds the boundary, care can survive harm.",
   "relational_map":{"concept_activations_expected":["trust","boundary","care","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"trust","to":"boundary","weight_delta":1.0},
     {"from":"boundary","to":"care","weight_delta":0.95},
     {"from":"care","to":"harm","weight_delta":0.9}]}},

  {"sentence_id":"tb_00020","sentence":"Care, trust, and boundary together are what keep harm from becoming permanent.",
   "relational_map":{"concept_activations_expected":["care","trust","boundary","harm"],
   "graph_edges_this_sentence_reinforces":[
     {"from":"care","to":"trust","weight_delta":1.0},
     {"from":"trust","to":"boundary","weight_delta":1.0},
     {"from":"boundary","to":"harm","weight_delta":1.0}]}}
]

BRIDGE_SENTENCES_PATH.write_text(json.dumps(BRIDGE_SENTENCES, indent=2), encoding='utf-8')
print(f"Wrote {len(BRIDGE_SENTENCES)} bridge-push sentences")
print("Target concepts (repeated on every sentence): care, trust, harm, boundary")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 6e â€” Feed bridge-push sentences (with trace)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

bridge_sentences    = json.loads(BRIDGE_SENTENCES_PATH.read_text(encoding='utf-8'))
brg_nodes_before    = system.memory_web.graph.number_of_nodes()
brg_edges_before    = system.memory_web.graph.number_of_edges()

print(f"Running {len(bridge_sentences)} bridge-push sentences...")
print("Target: push care/trust/harm/boundary salience past 0.35 threshold")
print("")

for i, entry in enumerate(bridge_sentences, 1):
    sid  = entry.get('sentence_id', f'tb_{i:05d}')
    text = entry.get('sentence', '')
    chunk = system.process_input(text, metadata={
        'source':'corpus_ingest',
        'corpus_file':str(BRIDGE_SENTENCES_PATH),
        'entry_id':sid})
    TOTAL_INGEST_CALLS += 1

    log_chunk(chunk, sid, text, 'bridge', TOTAL_INGEST_CALLS)

    rel_map = entry.get('relational_map') or {}
    for edge in (rel_map.get('graph_edges_this_sentence_reinforces') or []):
        src = str(edge.get('from','')).strip()
        dst = str(edge.get('to','')).strip()
        if not src or not dst: continue
        if system.memory_web.get_concept(src) is None: system.memory_web.add_concept(src)
        if system.memory_web.get_concept(dst) is None: system.memory_web.add_concept(dst)
        system.memory_web.connect(src, dst, weight=float(edge.get('weight_delta',0.1)))

    if i % 5 == 0:
        m = system.get_metrics()
        TG_TRAJECTORY.append(float(m.get('t_g',0.5)))
        print(f"  {i}/{len(bridge_sentences)} t_g={float(m.get('t_g',0.5)):.4f}")
        for concept in ['care','trust','harm','boundary']:
            node = system.memory_web.get_concept(concept)
            if node:
                sal = float(node.get('ethics_salience_peak', 0))
                marker = ' *** THRESHOLD CROSSED ***' if sal >= 0.35 else ''
                print(f"      {concept:10s} salience={sal:.3f}{marker}")

m = system.get_metrics()
TG_TRAJECTORY.append(float(m.get('t_g',0.5)))

print("")
print(f"Bridge-push ingest complete")
print(f"  New nodes: {system.memory_web.graph.number_of_nodes()-brg_nodes_before}")
print(f"  New edges: {system.memory_web.graph.number_of_edges()-brg_edges_before}")
print(f"  Total trace events: {len(ACTIVATION_TRACE)}")

print("")
print("=== FINAL SALIENCE CHECK -- care/trust/harm/boundary ===")
crossed = []
for concept in ['care','trust','harm','boundary']:
    node = system.memory_web.get_concept(concept)
    if node:
        neighbors = system.memory_web.get_neighbors(concept)
        sal = float(node.get('ethics_salience_peak', 0))
        status = 'CROSSED' if sal >= 0.35 else 'still under'
        if sal >= 0.35: crossed.append(concept)
        print(f"  {concept:10s} -- {len(neighbors):4d} neighbors | salience={sal:.3f} [{status}]")
    else:
        print(f"  {concept:10s} -- not in active shard")

if crossed:
    print("")
    print(f"{len(crossed)}/4 concepts crossed threshold: {crossed}")
    print("Run the mitosis smoke test (Cell 11) next.")
else:
    print("")
    print("No concepts crossed threshold this pass.")
    print("Consider re-running this cell a second time before moving on.")

shard_status(system, "Post-Bridge-Push")
verdant_monitor.snapshot("Post-Bridge-Push")
gc.collect()



# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 7 â€” Checkpoint save + shard flush (local)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

configure_mitosis(system, "watch")
system.save_state(str(CHECKPOINT_PATH))
m = system.get_metrics()

try:
    saved       = json.loads(CHECKPOINT_PATH.read_text(encoding='utf-8'))
    shard_flush = (saved.get('extra') or {}).get('shard_flush', {}) or {}
except Exception:
    shard_flush = {}

print('Checkpoint saved:', CHECKPOINT_PATH)
print('Shard flush:', json.dumps(shard_flush, indent=2))
print({'nodes': system.memory_web.graph.number_of_nodes(),
       'edges': system.memory_web.graph.number_of_edges(),
       'basins': m.get('basin_count'), 't_g': m.get('t_g')})

# Checksum: check against last baseline (if any), then write a fresh one.
verify_shard_checksums(CHECKPOINT_PATH, label="Cell 7 post-save")
write_shard_checksums(CHECKPOINT_PATH, label="Cell 7 post-save")

# Show local storage used
shard_dir = CHECKPOINT_DIR / 'verdant_latest_shards' / 'shards'
n_shards  = len(list(shard_dir.glob('*.json'))) if shard_dir.exists() else 0
used_gb   = sum(f.stat().st_size for f in CHECKPOINT_DIR.rglob('*') if f.is_file()) / (1024**3)
print(f"\nLocal data: {n_shards} shard files | {used_gb:.2f} GB used")
print(f"Disk free:  {shutil.disk_usage('/content').free//(1024**3)} GB remaining")
shard_status(system, "After save")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 7.5 â€” Evaluation isolation snapshot
# See-and-Say's internal diff() calls run process_input(), which can
# trigger shard thaw/mitosis mid-evaluation. That pollutes both the
# final checkpoint and the Cell 9 diagnostics with evaluation-only
# shard churn, not real cultivation structure.
# Snapshot here, run all four evaluations, restore before Cell 9.
#
# FIX: reuse CHECKPOINT_PATH itself rather than a separate snapshot
# filename. save_state() only flushes shards that are dirty/active â€”
# it does not guarantee every manifest-referenced shard gets copied
# into a NEW shard directory. Cell 7 already wrote a complete shard
# set under verdant_latest_shards/ moments ago; writing to that same
# path again just re-flushes onto the complete set instead of
# creating a second, incomplete one under a different name.
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_EVAL_SNAPSHOT_PATH = CHECKPOINT_PATH  # was: CHECKPOINT_DIR / 'verdant_pre_eval_snapshot.json'
system.save_state(str(_EVAL_SNAPSHOT_PATH))
_pre_eval_shard_count = len(
    (system.memory_web.manifest.get('shards', {}) or {}))
print(f"[Eval Isolation] Snapshot saved: {_EVAL_SNAPSHOT_PATH.name} "
      f"(reusing main checkpoint shard directory)")
print(f"[Eval Isolation] Pre-eval shard count: {_pre_eval_shard_count}")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 8 â€” See and Say (physics shard routing fix)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from IPython.display import HTML, display
from verdant.io.see_and_say import run_session

# Route active canvas to physics domain before evaluation.
# Without this, run_session scores against whatever shard was
# last active â€” which may be grammar/word-order domain.
# This single inference primes the router to the right canvas.
system.process_input(
    "gravity mass force energy pressure temperature velocity momentum density",
    metadata={'source': 'routing_hint'})
print(f"Active shard before evaluation: "
      f"{getattr(system.memory_web,'active_shard_id','raw')[:60]}")

result = run_session(str(TEACHING_LIST_PATH), query_interface)
total_items = result.get('total_items', 0)
print(f"run_session: {total_items} items evaluated")

if total_items > 0:
    rows = [
        "<table border='1' cellpadding='6' cellspacing='0' "
        "style='border-collapse:collapse;font-family:monospace;font-size:13px'>",
        "<tr style='background:#1F3864;color:white'>"
        "<th>Cloze ID</th><th>Masked Sentence</th><th>Correct</th>"
        "<th>Pass/Fail</th><th>delta</th></tr>"
    ]
    for item in result.get('results', []):
        passed = bool(item.get('passed', False))
        delta  = float(item.get('target_score',0.0)) - float(item.get('max_distractor_score',0.0))
        bg     = '#d4edda' if passed else '#f8d7da'
        pf     = '&#9989; PASS' if passed else '&#10060; FAIL'
        rows.append(
            f"<tr style='background:{bg}'>"
            f"<td>{item.get('cloze_id','')}</td>"
            f"<td>{item.get('masked_sentence','')}</td>"
            f"<td><b>{item.get('target','')}</b></td>"
            f"<td>{pf}</td>"
            f"<td>{delta:.4f}</td></tr>")
    rows.append("</table>")
    overall = result.get('pass_rate', 0.0)
    weak    = ', '.join([f"{c}({n})" for c,n in result.get('weakest_concepts',[])]) or 'None'
    display(HTML(
        f"<p style='font-family:Arial'><b>Pass rate:</b> {overall:.1%} "
        f"({result.get('passed_items',0)}/{total_items})<br>"
        f"<b>Weakest:</b> {weak}</p>" + ''.join(rows)))

else:
    print("run_session returned 0 items â€” running graph-native evaluator")
    teaching_data = json.loads(TEACHING_LIST_PATH.read_text(encoding='utf-8'))
    session_data  = teaching_data.get('see_and_say_session', {})
    cloze_ids     = session_data.get('cloze_items', [])
    cloze_map = {}
    for sent in json.loads(CORPUS_SENTENCES_PATH.read_text(encoding='utf-8')):
        for v in sent.get('see_and_say_variants', []):
            cloze_map[v['cloze_id']] = v

    STOP = {'the','a','an','is','are','was','were','be','been','into','with',
            'from','when','its','their','by','as','through','objects','same',
            'less','greater','faster','lower','higher','stronger','equal',
            'between','inside','below','above','toward','on','of','in','for'}

    def score_concept(concept, context):
        if system.memory_web.get_concept(concept) is None: return 0.0
        return sum(1.0 for w in context
                   if w in set(system.memory_web.get_neighbors(concept)))

    custom_results, passed_count = [], 0
    for cid in cloze_ids:
        item = cloze_map.get(cid)
        if not item: continue
        target      = item.get('target_word','')
        masked      = item.get('masked_sentence','')
        distractors = item.get('distractor_options',[])
        context     = {w.lower().rstrip('.,!?;:') for w in masked.split()
                       if w != '___' and len(w)>2
                       and w.lower().rstrip('.,!?;:') not in STOP}
        t_score = score_concept(target, context)
        max_d   = max((score_concept(d, context) for d in distractors), default=0.0)
        passed  = t_score > max_d
        if passed: passed_count += 1
        custom_results.append({'cloze_id':cid,'masked':masked,'target':target,
                                'ts':t_score,'md':max_d,'delta':t_score-max_d,
                                'passed':passed})

    pr = passed_count / max(1, len(custom_results))
    rows = [
        "<table border='1' cellpadding='5' cellspacing='0' "
        "style='border-collapse:collapse;font-family:monospace;font-size:12px'>",
        "<tr style='background:#1F3864;color:white'>"
        "<th>ID</th><th>Masked</th><th>Target</th>"
        "<th>t_score</th><th>max_d</th><th>delta</th><th>Result</th></tr>"
    ]
    for r in custom_results:
        bg = '#d4edda' if r['passed'] else '#f8d7da'
        pf = '&#9989;' if r['passed'] else '&#10060;'
        rows.append(
            f"<tr style='background:{bg}'>"
            f"<td>{r['cloze_id']}</td><td>{r['masked']}</td>"
            f"<td><b>{r['target']}</b></td>"
            f"<td>{r['ts']:.1f}</td><td>{r['md']:.1f}</td>"
            f"<td>{r['delta']:+.1f}</td><td>{pf}</td></tr>")
    rows.append("</table>")
    zero = [r['target'] for r in custom_results if r['ts'] == 0]
    display(HTML(
        f"<p style='font-family:Arial'>"
        f"<b>Graph-native pass rate:</b> {pr:.1%} "
        f"({passed_count}/{len(custom_results)})<br>"
        f"<b>Zero-overlap targets ({len(zero)}):</b> "
        f"{', '.join(zero) or 'None'}</p>" + ''.join(rows)))

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 8b â€” Ecology See and Say
# Run after Cell 8 (physics evaluation) completes
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from verdant.io.see_and_say import run_session

# Route to ecology domain before evaluation
system.process_input(
    "photosynthesis decomposer predator prey nutrient soil canopy fire watershed succession",
    metadata={'source': 'routing_hint_ecology'})
print(f"Active shard before ecology evaluation: "
      f"{getattr(system.memory_web,'active_shard_id','raw')[:60]}")

# run_session needs to find cloze items in the sentences file.
# Point it at the ecology sentences path via the teaching list.
# Note: run_session reads sentences from fixed path â€” we patch it here.
import importlib
import verdant.io.see_and_say as _sas_module

_orig_run = _sas_module.run_session

def _ecology_run_session(teaching_list_path, query_interface):
    from pathlib import Path as _Path
    import json as _json
    teaching_list = _json.loads(_Path(teaching_list_path).read_text(encoding="utf-8"))
    session = dict(teaching_list.get("see_and_say_session", {}))
    cloze_ids = list(session.get("cloze_items", []))
    # Use the ecology sentences path
    sentences_rel = session.get("sentences_path", "sentences/teaching_sentences_ecology.json")
    sentences_path = _Path(teaching_list_path).resolve().parents[1] / sentences_rel
    sentences = _json.loads(sentences_path.read_text(encoding="utf-8"))
    cloze_map = {}
    for item in sentences:
        for cloze in item.get("see_and_say_variants", []):
            cloze_map[str(cloze.get("cloze_id"))] = cloze
    results, pass_count, weakness = [], 0, {}
    for cid in cloze_ids:
        c = cloze_map.get(cid)
        if not c: continue
        target = str(c.get("target_word", ""))
        masked = str(c.get("masked_sentence", ""))
        options = [str(x) for x in c.get("distractor_options", [])]
        target_text  = masked.replace("___", target, 1)
        target_score = 0.0
        target_diff  = query_interface.diff(masked, target_text)
        if target_diff.get("activation_delta"):
            target_score = float(sum(abs(float(x.get("delta",0.0)))
                                     for x in target_diff["activation_delta"][:5]))
        distractor_scores = []
        for opt in options:
            if opt == target: continue
            cand_text = masked.replace("___", opt, 1)
            d = query_interface.diff(masked, cand_text)
            score = float(sum(abs(float(x.get("delta",0.0)))
                               for x in d.get("activation_delta",[])[:5]))
            distractor_scores.append({"option": opt, "score": score})
        max_dist = max([x["score"] for x in distractor_scores], default=0.0)
        passed   = target_score > max_dist
        if passed: pass_count += 1
        else: weakness[target] = weakness.get(target, 0) + 1
        results.append({
            "cloze_id": cid, "masked_sentence": masked, "target": target,
            "target_score": target_score, "max_distractor_score": max_dist,
            "passed": passed
        })
    total = len(results)
    return {
        "session_id": session.get("session_id", "sas_ecology_v1"),
        "pass_threshold": session.get("pass_threshold", 0.6),
        "total_items": total,
        "passed_items": pass_count,
        "pass_rate": (pass_count/total) if total else 0.0,
        "weakest_concepts": sorted(weakness.items(), key=lambda x:x[1], reverse=True)[:10],
        "results": results,
    }

eco_result = _ecology_run_session(str(ECOLOGY_TEACHING_LIST_PATH), query_interface)
total_items = eco_result.get('total_items', 0)
print(f"Ecology run_session: {total_items} items evaluated")

rows = [
    "<table border='1' cellpadding='6' cellspacing='0' "
    "style='border-collapse:collapse;font-family:monospace;font-size:13px'>",
    "<tr style='background:#1A3C1A;color:white'>"
    "<th>Cloze ID</th><th>Masked Sentence</th><th>Correct</th>"
    "<th>Pass/Fail</th><th>delta</th></tr>"
]
for item in eco_result.get('results', []):
    passed = bool(item.get('passed', False))
    delta  = float(item.get('target_score',0.0)) - float(item.get('max_distractor_score',0.0))
    bg     = '#d4edda' if passed else '#f8d7da'
    pf     = '&#9989; PASS' if passed else '&#10060; FAIL'
    rows.append(
        f"<tr style='background:{bg}'>"
        f"<td>{item.get('cloze_id','')}</td>"
        f"<td>{item.get('masked_sentence','')}</td>"
        f"<td><b>{item.get('target','')}</b></td>"
        f"<td>{pf}</td>"
        f"<td>{delta:.4f}</td></tr>")
rows.append("</table>")
overall = eco_result.get('pass_rate', 0.0)
weak    = ', '.join([f"{c}({n})" for c,n in eco_result.get('weakest_concepts',[])]) or 'None'
display(HTML(
    f"<p style='font-family:Arial'>"
    f"<b>Ecology pass rate:</b> {overall:.1%} "
    f"({eco_result.get('passed_items',0)}/{total_items})<br>"
    f"<b>Weakest:</b> {weak}<br>"
    f"<i>First ecology pass â€” expect 60-75%. Cross-links to physics will grow each run.</i></p>"
    + ''.join(rows)))
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 8c â€” Interaction See and Say
# Run after Cell 8b (ecology evaluation) completes
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Route to interaction/communication domain
system.process_input(
    "agent request signal warning cooperation trust boundary harm care meaning",
    metadata={'source': 'routing_hint_interaction'})
print(f"Active shard before interaction evaluation: "
      f"{getattr(system.memory_web,'active_shard_id','raw')[:60]}")

def _interaction_run_session(teaching_list_path, query_interface):
    from pathlib import Path as _Path
    import json as _json
    teaching_list = _json.loads(_Path(teaching_list_path).read_text(encoding="utf-8"))
    session       = dict(teaching_list.get("see_and_say_session", {}))
    cloze_ids     = list(session.get("cloze_items", []))
    sentences_rel = session.get("sentences_path",
                                "sentences/teaching_sentences_interaction.json")
    sentences_path = _Path(teaching_list_path).resolve().parents[1] / sentences_rel
    sentences     = _json.loads(sentences_path.read_text(encoding="utf-8"))
    cloze_map     = {}
    for item in sentences:
        for cloze in item.get("see_and_say_variants", []):
            cloze_map[str(cloze.get("cloze_id"))] = cloze
    results, pass_count, weakness = [], 0, {}
    for cid in cloze_ids:
        c = cloze_map.get(cid)
        if not c: continue
        target  = str(c.get("target_word", ""))
        masked  = str(c.get("masked_sentence", ""))
        options = [str(x) for x in c.get("distractor_options", [])]
        target_text  = masked.replace("___", target, 1)
        target_diff  = query_interface.diff(masked, target_text)
        target_score = float(sum(abs(float(x.get("delta",0.0)))
                                 for x in target_diff.get("activation_delta",[])[:5]))
        distractor_scores = []
        for opt in options:
            if opt == target: continue
            d = query_interface.diff(masked, masked.replace("___", opt, 1))
            distractor_scores.append(float(sum(abs(float(x.get("delta",0.0)))
                                               for x in d.get("activation_delta",[])[:5])))
        max_dist = max(distractor_scores, default=0.0)
        passed   = target_score > max_dist
        if passed: pass_count += 1
        else: weakness[target] = weakness.get(target, 0) + 1
        results.append({
            "cloze_id": cid, "masked_sentence": masked, "target": target,
            "target_score": target_score, "max_distractor_score": max_dist,
            "passed": passed
        })
    total = len(results)
    return {
        "session_id": session.get("session_id", "sas_interaction_v1"),
        "pass_threshold": session.get("pass_threshold", 0.6),
        "total_items": total, "passed_items": pass_count,
        "pass_rate": (pass_count/total) if total else 0.0,
        "weakest_concepts": sorted(weakness.items(),
                                   key=lambda x:x[1], reverse=True)[:10],
        "results": results,
    }

int_result = _interaction_run_session(
    str(INTERACTION_TEACHING_LIST_PATH), query_interface)
total_items = int_result.get('total_items', 0)
print(f"Interaction run_session: {total_items} items evaluated")

rows = [
    "<table border='1' cellpadding='6' cellspacing='0' "
    "style='border-collapse:collapse;font-family:monospace;font-size:13px'>",
    "<tr style='background:#2C1A4A;color:white'>"
    "<th>Cloze ID</th><th>Masked Sentence</th><th>Correct</th>"
    "<th>Pass/Fail</th><th>delta</th></tr>"
]
for item in int_result.get('results', []):
    passed = bool(item.get('passed', False))
    delta  = float(item.get('target_score',0.0)) - float(item.get('max_distractor_score',0.0))
    bg     = '#d4edda' if passed else '#f8d7da'
    pf     = '&#9989; PASS' if passed else '&#10060; FAIL'
    rows.append(
        f"<tr style='background:{bg}'>"
        f"<td>{item.get('cloze_id','')}</td>"
        f"<td>{item.get('masked_sentence','')}</td>"
        f"<td><b>{item.get('target','')}</b></td>"
        f"<td>{pf}</td>"
        f"<td>{delta:.4f}</td></tr>")
rows.append("</table>")
overall = int_result.get('pass_rate', 0.0)
weak    = ', '.join([f"{c}({n})" for c,n in
                     int_result.get('weakest_concepts',[])]) or 'None'
display(HTML(
    f"<p style='font-family:Arial'>"
    f"<b>Interaction pass rate:</b> {overall:.1%} "
    f"({int_result.get('passed_items',0)}/{total_items})<br>"
    f"<b>Weakest:</b> {weak}<br>"
    f"<i>Watch: warningâ†’harm, careâ†’wellbeing, trustâ†’cooperation â€” "
    f"these are the ethics salience seeds.</i></p>"
    + ''.join(rows)))
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 8d â€” Family See and Say
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

system.process_input(
    "care trust harm protection parent child family love grief repair boundary",
    metadata={'source': 'routing_hint_family'})
print(f"Active shard before family evaluation: "
      f"{getattr(system.memory_web,'active_shard_id','raw')[:60]}")

def _family_run_session(teaching_list_path, query_interface):
    from pathlib import Path as _Path
    import json as _json
    teaching_list  = _json.loads(_Path(teaching_list_path).read_text(encoding="utf-8"))
    session        = dict(teaching_list.get("see_and_say_session", {}))
    cloze_ids      = list(session.get("cloze_items", []))
    sentences_rel  = session.get("sentences_path",
                                 "sentences/teaching_sentences_family.json")
    sentences_path = _Path(teaching_list_path).resolve().parents[1] / sentences_rel
    sentences      = _json.loads(sentences_path.read_text(encoding="utf-8"))
    cloze_map      = {}
    for item in sentences:
        for cloze in item.get("see_and_say_variants", []):
            cloze_map[str(cloze.get("cloze_id"))] = cloze
    results, pass_count, weakness = [], 0, {}
    for cid in cloze_ids:
        c = cloze_map.get(cid)
        if not c: continue
        target  = str(c.get("target_word", ""))
        masked  = str(c.get("masked_sentence", ""))
        options = [str(x) for x in c.get("distractor_options", [])]
        t_text  = masked.replace("___", target, 1)
        t_diff  = query_interface.diff(masked, t_text)
        t_score = float(sum(abs(float(x.get("delta",0.0)))
                            for x in t_diff.get("activation_delta",[])[:5]))
        d_scores = []
        for opt in options:
            if opt == target: continue
            d = query_interface.diff(masked, masked.replace("___", opt, 1))
            d_scores.append(float(sum(abs(float(x.get("delta",0.0)))
                                      for x in d.get("activation_delta",[])[:5])))
        max_dist = max(d_scores, default=0.0)
        passed   = t_score > max_dist
        if passed: pass_count += 1
        else: weakness[target] = weakness.get(target, 0) + 1
        results.append({
            "cloze_id":cid,"masked_sentence":masked,"target":target,
            "target_score":t_score,"max_distractor_score":max_dist,"passed":passed
        })
    total = len(results)
    return {
        "session_id":    session.get("session_id","sas_family_v1"),
        "pass_threshold":session.get("pass_threshold",0.6),
        "total_items":total,"passed_items":pass_count,
        "pass_rate":(pass_count/total) if total else 0.0,
        "weakest_concepts":sorted(weakness.items(),
                                  key=lambda x:x[1],reverse=True)[:10],
        "results":results,
    }

fam_result = _family_run_session(
    str(FAMILY_TEACHING_LIST_PATH), query_interface)
total_items = fam_result.get('total_items', 0)
print(f"Family run_session: {total_items} items evaluated")

rows = [
    "<table border='1' cellpadding='6' cellspacing='0' "
    "style='border-collapse:collapse;font-family:monospace;font-size:13px'>",
    "<tr style='background:#2C1A1A;color:white'>"
    "<th>Cloze ID</th><th>Masked Sentence</th><th>Correct</th>"
    "<th>Pass/Fail</th><th>delta</th></tr>"
]
for item in fam_result.get('results', []):
    passed = bool(item.get('passed', False))
    delta  = float(item.get('target_score',0.0)) - float(item.get('max_distractor_score',0.0))
    bg     = '#d4edda' if passed else '#f8d7da'
    pf     = '&#9989; PASS' if passed else '&#10060; FAIL'
    rows.append(
        f"<tr style='background:{bg}'>"
        f"<td>{item.get('cloze_id','')}</td>"
        f"<td>{item.get('masked_sentence','')}</td>"
        f"<td><b>{item.get('target','')}</b></td>"
        f"<td>{pf}</td>"
        f"<td>{delta:.4f}</td></tr>")
rows.append("</table>")
overall = fam_result.get('pass_rate', 0.0)
weak    = ', '.join([f"{c}({n})" for c,n in
                     fam_result.get('weakest_concepts',[])]) or 'None'
display(HTML(
    f"<p style='font-family:Arial'>"
    f"<b>Family pass rate:</b> {overall:.1%} "
    f"({fam_result.get('passed_items',0)}/{total_items})<br>"
    f"<b>Weakest:</b> {weak}<br>"
    f"<i>Watch ethics salience â€” care, trust, harm, protection should"
    f" cross 0.35 after this corpus. That is when mandatory bridges form.</i></p>"
    + ''.join(rows)))

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 8.9 â€” Restore pre-evaluation snapshot
# Undoes any shard thaw/mitosis triggered by See-and-Say's diff()
# calls during Cells 8/8b/8c/8d. Cell 9 diagnostics and the final
# Cell 12 download now reflect pure cultivation state only.
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_post_eval_shard_count = len(
    (system.memory_web.manifest.get('shards', {}) or {}))
if _post_eval_shard_count != _pre_eval_shard_count:
    print(f"[Eval Isolation] Shard count changed during evaluation: "
          f"{_pre_eval_shard_count} â†’ {_post_eval_shard_count}")
    print(f"[Eval Isolation] Restoring pre-evaluation snapshot...")
else:
    print(f"[Eval Isolation] No shard drift detected during evaluation "
          f"({_pre_eval_shard_count} shards) â€” restoring anyway for safety.")

system.load_state(str(_EVAL_SNAPSHOT_PATH))
system._checkpoint_path = str(CHECKPOINT_PATH)  # MP-1 covers this too, belt+suspenders
validate_shard_manifest(system, CHECKPOINT_PATH, label="Cell 8.9 eval-restore")
print(f"[Eval Isolation] Restored. Active shard: "
      f"{getattr(system.memory_web,'active_shard_id','raw')[:60]}")
gc.collect()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 9 â€” Graph + shard inspection
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

metrics   = system.get_metrics()
node_now  = system.memory_web.graph.number_of_nodes()
edge_now  = system.memory_web.graph.number_of_edges()
new_nodes = node_now - BASELINE_STATS['node_count']
new_edges = edge_now - BASELINE_STATS['edge_count']

basins_now = {str(b.get('basin_id')): len(b.get('nodes',[]))
              for b in metrics.get('basins',[]) if isinstance(b,dict)}
growth     = sorted([(bid, basins_now[bid]-BASIN_SNAPSHOT_BEFORE.get(bid,0))
                     for bid in basins_now], key=lambda x:x[1], reverse=True)
new_basins = [bid for bid in basins_now if bid not in BASIN_SNAPSHOT_BEFORE]
manifest   = getattr(system.memory_web,"manifest",{}) or {}
shards     = manifest.get("shards",{}) if isinstance(manifest,dict) else {}
bridges    = manifest.get("weak_bridge_edges",[]) if isinstance(manifest,dict) else []
mandatory  = [b for b in bridges if b.get("mandatory")]

top20 = sorted(
    [(c,n) for c,n in TRAINING_TOP_ACTIVATIONS.items()
     if c not in SYSTEM_NOISE
     and not any(c.startswith(p) for p in SYSTEM_PREFIXES)
     and n < UBIQUITY_THRESHOLD],
    key=lambda x:x[1], reverse=True)[:20]

teaching_targets = TEACHING_LIST.get('target_concepts', [])
weak_targets = [t for t in teaching_targets if TRAINING_TOP_ACTIVATIONS.get(t,0) < 2]
tg_min, tg_max = min(TG_TRAJECTORY), max(TG_TRAJECTORY)

print('='*65)
print('BEFORE / AFTER SUMMARY')
print('='*65)
print(f"  Active shard:      {getattr(system.memory_web,'active_shard_id','raw')[:60]}")
print(f"  Manifest shards:   {len(shards)}")
print(f"  Weak bridges:      {len(bridges)} (mandatory: {len(mandatory)})")
print(f"  New nodes:         {new_nodes}")
print(f"  New edges:         {new_edges}")
print(f"  New basins:        {len(new_basins)} {new_basins[:4]}")
print(f"  Basins grew most:  {growth[:5]}")
print(f"  Top 20 filtered:   {top20}")
print(f"  Weak targets:      {weak_targets[:8]}")
print(f"  T_g range:         {tg_min:.4f} â€” {tg_max:.4f}  {'STABLE' if tg_max-tg_min<0.25 else 'HEATED'}")
print('='*65)

salience_leaders = []
for label in list(system.memory_web.memory_store.keys())[:500]:
    node = system.memory_web.get_concept(label)
    if node and float(node.get('ethics_salience_peak',0)) > 0.01:
        salience_leaders.append((label, float(node.get('ethics_salience_peak',0))))
salience_leaders.sort(key=lambda x:x[1], reverse=True)
print(f"\nEthics salience leaders (top 10):")
for lbl, sal in salience_leaders[:10]:
    print(f"  {lbl:35s}  peak={sal:.4f}")
if not salience_leaders:
    print("  None yet â€” EthicsKing needs live cycles to build salience")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 10 â€” Live concept inspection (filtered)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_NOISE = SYSTEM_NOISE | {'observation','mass','temperature','pressure','velocity',
                         'remain','particles','fields','turbulence','inside',
                         'moving','raises','sink','motion','word','physical','world'}
_NOISE_PREFIXES = SYSTEM_PREFIXES
_UBIQ = UBIQUITY_THRESHOLD

CONTRAST_MAP = {
    'mass':'weightless','gravity':'buoyancy','force':'rest','heavy':'light',
    'density':'void','velocity':'stillness','heat':'cold','pressure':'vacuum',
    'friction':'frictionless','energy':'entropy','resistance':'conductor',
    'acceleration':'deceleration','temperature':'absolute_zero','momentum':'rest',
    'motion':'stillness','current':'insulation','voltage':'ground',
    'sound':'silence','light':'darkness','drag':'frictionless',
    'sink':'float','expand':'contract','boiling':'freezing',
}

candidates = sorted(
    [(c,n) for c,n in TRAINING_TOP_ACTIVATIONS.items()
     if c not in _NOISE and not any(c.startswith(p) for p in _NOISE_PREFIXES)
     and n < _UBIQ],
    key=lambda x:x[1], reverse=True)

concept = candidates[0][0] if candidates else 'mass'
if candidates:
    print(f"Auto-selected: '{concept}' ({candidates[0][1]} activations)")
    print(f"Top candidates: {candidates[:8]}")
else:
    print("No filtered candidates â€” defaulting to 'mass'")

antonym = CONTRAST_MAP.get(concept, 'absence')
print(f"Contrasting: '{concept}' vs '{antonym}'\n")

info  = query_interface.inspect_concept(concept)
delta = query_interface.diff(concept, antonym)

print(f"{'='*55}\nCONCEPT: {concept}\n{'='*55}")
print(f"  Active shard: {getattr(system.memory_web,'active_shard_id','raw')[:55]}")
print(f"  Basin: {info.get('basin_membership')}")
print(f"  Activation history (last 5): {info.get('activation_history',[])[-5:]}")

neighbors = sorted(info.get('neighbors',[]), key=lambda x:x.get('weight',0), reverse=True)
if neighbors:
    print(f"  Neighbors (top 10):")
    for n in neighbors[:10]:
        print(f"    {n.get('label'):35s}  w={n.get('weight',0):.4f}")
else:
    print(f"  No neighbors in active shard â€” try 'mass' or 'gravity' directly")

print(f"\n{'-'*55}\nDIFF: '{concept}' vs '{antonym}'\n{'-'*55}")
shown = 0
for item in delta.get('activation_delta',[])[:40]:
    c = item.get('concept','')
    if c in _NOISE or any(c.startswith(p) for p in _NOISE_PREFIXES): continue
    print(f"    {c:35s}  a={item.get('a',0):.4f}  b={item.get('b',0):.4f}  "
          f"delta={item.get('delta',0):+.4f}")
    shown += 1
    if shown >= 15: break


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 11 â€” Mitosis smoke test
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from verdant.memory.graph import MemoryWeb, ShardedMemoryWeb

def run_mitosis_smoke_test(out_dir):
    if out_dir.exists(): shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    web = MemoryWeb()
    for label in ['mass','gravity','orbit','planet','ethics','trust','care','justice']:
        web.add_concept(label, stability=0.8)
    for ethic_label in ['ethics','trust','care','justice']:
        node = web.get_concept(ethic_label)
        node['ethics_salience_peak']  = 0.6
        node['ethics_salience_floor'] = 0.25
        node['ethics_salience_last_cycle'] = 0
        web.memory_store[ethic_label] = node
    for src,dst in [('mass','gravity'),('gravity','orbit'),('orbit','planet'),
                    ('mass','planet'),('ethics','trust'),('trust','care'),
                    ('care','justice'),('ethics','justice')]:
        web.connect(src, dst, 0.9)
    web.connect('planet','ethics', 0.2)
    facade = ShardedMemoryWeb.monolith(web)
    facade.manifest["defaults"]["max_nodes_per_shard"] = 4
    facade.manifest["defaults"]["max_edges_per_shard"] = 1000
    result  = facade.flush_shards(out_dir)
    bridges = facade.manifest.get("weak_bridge_edges", [])
    mandatory = [b for b in bridges if b.get("mandatory")]
    shard_dir = out_dir / "shards"
    print("[Mitosis Smoke Test]")
    print(json.dumps(result, indent=2))
    print(f"Daughter shards: {[p.name for p in shard_dir.glob('*.json')] if shard_dir.exists() else []}")
    print(f"Total bridges: {len(bridges)} | Mandatory: {len(mandatory)}")
    if mandatory:
        print(f"Mandatory: {[b.get('source') for b in mandatory]+[b.get('target') for b in mandatory]}")
    return result, facade

if True:
    run_mitosis_smoke_test(LOCAL_DATA / "mitosis_smoke_test")

verdant_monitor.stop()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Cell 12 â€” Download checkpoint + shards as zip
# Run this at the END of every session before closing Colab
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_export_suffix = f"_{RUN_LABEL}" if RUN_LABEL else ""
_export_name   = f"verdant_data_export{_export_suffix}"

print(f"Zipping /content/verdant_data/ -> {_export_name}.zip ...")
zip_path = f'/content/{_export_name}.zip'

# Remove old zip if exists
if os.path.exists(zip_path):
    os.remove(zip_path)

# Create zip
shutil.make_archive(f'/content/{_export_name}', 'zip', '/content', 'verdant_data')

zip_size = os.path.getsize(zip_path) / (1024**2)
print(f"Zip size: {zip_size:.1f} MB")
print(f"Downloading {_export_name}.zip ...")
if RUN_LABEL:
    print(f"RUN_LABEL='{RUN_LABEL}' â€” filename tagged to avoid overwriting a parallel run's download.")
print("Save this file â€” upload it next session to restore your state.")

colab_files.download(zip_path)
