# Verdant V4 Routing Registry Manifest Schema

The shard manifest is the always-resident routing registry for the planned
Dual-Store memory architecture. It is intentionally small enough to stay in RAM
while the basin shards remain independently loadable JSON documents on disk.

## Location

```text
<memory_root>/manifest.json
<memory_root>/shards/<shard_id>.json
```

## Manifest Structure

```json
{
  "version": 1,
  "schema": "verdant.routing_registry.v1",
  "created_at": 1779990000.0,
  "updated_at": 1779990300.0,
  "memory_root": ".",
  "active_shards": ["basin_monolith_000000"],
  "defaults": {
    "max_nodes_per_shard": 512,
    "max_edges_per_shard": 20000,
    "thaw_penalty": 0.35,
    "thaw_threshold": 0.12,
    "noise_floor": 0.01,
    "max_bridge_edges_per_pair": 12,
    "centroid_dimensions": 64
  },
  "shards": {
    "basin_monolith_000000": {
      "shard_id": "basin_monolith_000000",
      "path": "shards/basin_monolith_000000.json",
      "state": "active",
      "node_count": 1364,
      "edge_count": 82000,
      "dirty": false,
      "created_at": 1779990000.0,
      "updated_at": 1779990300.0,
      "last_accessed": 1779990300.0,
      "access_count": 1,
      "anchors": [
        {
          "label": "soil",
          "centrality": 0.91,
          "access_count": 321,
          "stability": 0.88
        },
        {
          "label": "water",
          "centrality": 0.87,
          "access_count": 284,
          "stability": 0.83
        }
      ],
      "anchor_labels": ["soil", "water", "growth"],
      "top_terms": ["soil", "water", "growth", "root", "plant"],
      "centroid": {
        "space": "verdant.anchor_hash.v1",
        "dimensions": 64,
        "values": [0.0, 0.0, 0.0]
      },
      "thermal_summary": {
        "mean_stability": 0.62,
        "mean_activation": 0.0,
        "last_t_g": 0.5
      },
      "ecwf_summary": {
        "mapping_count": 1364,
        "dominant_cognitive_dims": [2, 7, 11],
        "dominant_ethical_dims": [1]
      },
      "mitosis": {
        "eligible": true,
        "last_checked_cycle": 0,
        "parent_shard_id": null,
        "daughter_shard_ids": []
      }
    }
  },
  "concept_index": {
    "soil": [
      {
        "shard_id": "basin_monolith_000000",
        "role": "anchor",
        "score": 0.91
      }
    ],
    "water": [
      {
        "shard_id": "basin_monolith_000000",
        "role": "anchor",
        "score": 0.87
      }
    ]
  },
  "weak_bridge_edges": [
    {
      "bridge_id": "bridge_soil_stewardship_000001",
      "source_shard": "basin_soil_water_growth",
      "source": "root",
      "target_shard": "basin_ethics_stewardship",
      "target": "stewardship",
      "weight": 0.17,
      "resonance": 0.42,
      "thaw_penalty": 0.35,
      "last_energy_out": 0.02499,
      "last_traversed": 1779990250.0,
      "traversal_count": 4,
      "status": "ghost"
    }
  ],
  "routing_stats": {
    "total_thaws": 1,
    "total_flushes": 0,
    "boundary_absorbs": 0,
    "boundary_echoes": 0,
    "boundary_prefetches": 0
  }
}
```

## Boundary Energy Rule

For an unloaded bridge target, propagation records boundary energy instead of
blocking the active ECWF loop:

```text
E_out = E_in * bridge_weight * target_basin_resonance * thaw_penalty
```

Recommended status assignment:

| Status | Condition | Runtime behavior |
| --- | --- | --- |
| `absorbed` | `E_out < noise_floor` | Drop activation and increment `boundary_absorbs`. |
| `ghost` | `noise_floor <= E_out < thaw_threshold` | Keep explainable ghost activation only. |
| `prefetch` | `E_out >= thaw_threshold` | Queue target shard for asynchronous thaw. |

## Initial Single-Shard Bootstrap

Before physical mitosis exists, the manifest should contain exactly one active
shard whose shard file is exported from the current monolithic `MemoryWeb`.
This lets `ShardedMemoryWeb` satisfy the existing bridge and pipeline contracts
while keeping the routing registry in place for later shard splits.
