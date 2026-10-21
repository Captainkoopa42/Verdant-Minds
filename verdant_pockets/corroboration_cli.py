"""Run v2.3 provenance and synthetic scaling controls."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from .corroboration import assess_corroboration, run_scaling_benchmark

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,help="New JSON report path; must not already exist")
    parser.add_argument("--observations",help="Optional JSON file containing a list of declared observation records")
    parser.add_argument("--sizes",default="32,64,128,256",help="Comma-separated synthetic graph sizes")
    parser.add_argument("--irrelevant-per-node",type=int,default=4)
    args=parser.parse_args(argv)
    sizes=tuple(int(x.strip()) for x in args.sizes.split(",") if x.strip())
    if args.observations:
        records=json.loads(Path(args.observations).read_text(encoding="utf-8"))
        if not isinstance(records,list): parser.error("observations file must contain a JSON list")
    else:
        records=[
          {"observation_id":"demo-1","source_ref":"declared:field-notes-A","source_family":"field-team-A","source_record_id":"record-A-17","subject":"r4","predicate":"precedes","object":"s1","direction":"forward"},
          {"observation_id":"demo-2","source_ref":"declared:field-notes-A-copy","source_family":"field-team-A","source_record_id":"record-A-17","subject":"r4","predicate":"precedes","object":"s1","direction":"forward"},
          {"observation_id":"demo-3","source_ref":"declared:independent-lab-B","source_family":"lab-B","source_record_id":"lab-record-B-9","subject":"r4","predicate":"precedes","object":"s1","direction":"forward"},
          {"observation_id":"demo-4","source_ref":"declared:challenge-C","source_family":"team-C","source_record_id":"record-C-3","subject":"s1","predicate":"precedes","object":"r4","direction":"forward"},
        ]
    report={"schema":"verdant.cognitive_pocket_v2_3_report","corroboration":assess_corroboration(records),
            "scaling":run_scaling_benchmark(sizes,args.irrelevant_per_node),
            "native_memory_modified":False,"canonical_writeback":False}
    path=Path(args.out); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(report,stream,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False);stream.write("\n")
    print(json.dumps({"report":str(path.resolve()),"observations":len(records),
                      "benchmark_rows":len(report["scaling"]["rows"]),
                      "native_memory_modified":False,"canonical_writeback":False},indent=2))
if __name__=="__main__": main()
