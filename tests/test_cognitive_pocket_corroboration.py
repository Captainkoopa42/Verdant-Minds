"""v2.3 declared provenance and graph scaling controls."""
import pytest
from verdant_pockets.corroboration import assess_corroboration, run_scaling_benchmark

def obs(oid, source, family, record, subject="A", predicate="precedes", obj="B", direction="forward"):
    return {"observation_id":oid,"source_ref":source,"source_family":family,
            "source_record_id":record,"subject":subject,"predicate":predicate,
            "object":obj,"direction":direction}

def test_different_labels_same_provenance_do_not_count_as_independent():
    result=assess_corroboration([
        obs("o1","sensor-A-copy1","same-family","record-7"),
        obs("o2","sensor-A-copy2","same-family","record-7"),
    ])
    claim=result["claims"][0]
    assert claim["declared_independent_source_family_count"] == 1
    assert claim["status"] == "single_provenance_family"
    assert claim["source_authenticity_verified"] is False

def test_distinct_declared_families_can_only_provisionally_corroborate():
    result=assess_corroboration([
        obs("o1","source-A","family-A","record-A"),
        obs("o2","source-B","family-B","record-B"),
    ])
    assert result["claims"][0]["status"] == "provisionally_corroborated"
    assert result["authenticity_or_truth_verified"] is False
    assert result["canonical_writeback"] is False

def test_conflicting_reverse_claims_are_flagged_not_majority_voted():
    result=assess_corroboration([
        obs("o1","source-A","family-A","record-A"),
        obs("o2","source-B","family-B","record-B",subject="B",obj="A"),
        obs("o3","source-C","family-C","record-C",subject="B",obj="A"),
    ])
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["status"] == "conflicting_claims_require_review"
    assert result["claims"][1]["status"] == "provisionally_corroborated"

def test_duplicate_ids_and_missing_provenance_fail_closed():
    with pytest.raises(ValueError,match="duplicate observation_id"):
        assess_corroboration([obs("o1","a","a","1"),obs("o1","b","b","2")])
    bad=obs("o2","b","b","2"); del bad["source_family"]
    with pytest.raises(ValueError,match="missing"):
        assess_corroboration([bad])

def test_source_record_reuse_prevents_independence_even_if_family_label_changes():
    result=assess_corroboration([
        obs("o1","a","family-A","same-record"),
        obs("o2","b","family-B","same-record"),
    ])
    assert result["claims"][0]["declared_independent_source_family_count"] == 1

def test_scaling_baselines_receive_same_graph_and_find_same_witness():
    result=run_scaling_benchmark(sizes=(8,16,32),irrelevant_per_node=5)
    assert all(row["same_result"] for row in result["rows"])
    assert all(row["flat"]["found"] and row["indexed"]["found"] for row in result["rows"])
    assert all(row["flat"]["edge_inspections"] == row["indexed"]["edge_inspections"] for row in result["rows"])
    assert all(row["irrelevant_edge_count"] > 0 for row in result["rows"])
    assert result["performance_advantage_demonstrated"] is False

def test_scaling_bounds_reject_unbounded_inputs():
    with pytest.raises(ValueError):
        run_scaling_benchmark(sizes=(10001,))
    with pytest.raises(ValueError):
        run_scaling_benchmark(sizes=(8,),irrelevant_per_node=101)
