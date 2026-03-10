# Cell 9 — Full scaffold analysis + visualization
# Point STATE_PATH at any seed's state.json

import json, random, math
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

STATE_PATH = "/content/Verdant-Minds/outputs_baseline/run_*/seed_0/state.json"
# Resolve glob
import glob
matches = sorted(glob.glob(STATE_PATH))
if matches:
    STATE_PATH = matches[-1]
    print(f"Using: {STATE_PATH}")

TOPK = 6
SHUFFLE_TRIALS = 500

with open(STATE_PATH, "r") as f:
    state = json.load(f)

memory_store = state["memory_web"]["memory_store"]

def is_emergent(name):
    return isinstance(name, str) and name.startswith("Emergent_")

def get_timestamp(data):
    if not isinstance(data, dict):
        return None
    for key in ("created_at", "creation_time", "first_seen", "timestamp_created"):
        v = data.get(key)
        if v is not None:
            try: return float(v)
            except: pass
    return None

def parse_conn(conn):
    if isinstance(conn, (list, tuple)) and len(conn) >= 1:
        return conn[0], float(conn[1]) if len(conn) >= 2 else 1.0
    if isinstance(conn, dict):
        t = conn.get("target") or conn.get("node") or conn.get("concept") or conn.get("name")
        return t, float(conn.get("weight", conn.get("strength", 1.0)))
    if isinstance(conn, str):
        return conn, 1.0
    return None, None

G = nx.Graph()
for u, data in memory_store.items():
    if not isinstance(data, dict): continue
    ts = get_timestamp(data)
    G.add_node(u, emergent=is_emergent(u), ts=ts,
               access_count=data.get("access_count", 0))
    for conn in data.get("connections", []):
        v, w = parse_conn(conn)
        if not isinstance(v, str) or not v or v == u: continue
        if v not in G: G.add_node(v, emergent=is_emergent(v), ts=None)
        if G.has_edge(u, v):
            G[u][v]["weight"] = max(G[u][v]["weight"], w)
        else:
            G.add_edge(u, v, weight=w)

H = nx.Graph()
H.add_nodes_from(G.nodes(data=True))
for u in G.nodes():
    nbrs = sorted([(v, G[u][v]["weight"]) for v in G[u]], key=lambda x: -x[1])
    for v, w in nbrs[:TOPK]:
        if H.has_edge(u, v):
            H[u][v]["weight"] = max(H[u][v]["weight"], w)
        else:
            H.add_edge(u, v, weight=w)

D = nx.DiGraph()
ee_edges = []
age_gaps = []
emergents = [n for n in H if H.nodes[n].get("emergent") and H.nodes[n].get("ts") is not None]
for n in emergents:
    D.add_node(n, **H.nodes[n])
for u, v, ed in H.edges(data=True):
    if not (H.nodes[u].get("emergent") and H.nodes[v].get("emergent")): continue
    tu, tv = H.nodes[u].get("ts"), H.nodes[v].get("ts")
    if tu is None or tv is None or tu == tv: continue
    ee_edges.append((u, v))
    age_gaps.append(abs(tu - tv))
    src, dst = (u, v) if tu < tv else (v, u)
    D.add_edge(src, dst, weight=ed.get("weight", 1.0))

earlier = sum(1 for u, v in ee_edges if H.nodes[u]["ts"] < H.nodes[v]["ts"])
later = sum(1 for u, v in ee_edges if H.nodes[u]["ts"] > H.nodes[v]["ts"])
observed = earlier / max(1, earlier + later)

em_nodes = list(D.nodes())
em_times = [D.nodes[n]["ts"] for n in em_nodes]
shuf = []
for _ in range(SHUFFLE_TRIALS):
    st = em_times[:]
    random.shuffle(st)
    m = dict(zip(em_nodes, st))
    e = sum(1 for u, v in ee_edges if m[u] < m[v])
    l = sum(1 for u, v in ee_edges if m[u] > m[v])
    shuf.append(e / max(1, e + l))
shuf = np.array(shuf)
z = (observed - shuf.mean()) / (shuf.std() + 1e-9)

print(f"Full graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
print(f"Backbone: {H.number_of_nodes()} nodes, {H.number_of_edges()} edges")
print(f"Scaffold: {D.number_of_nodes()} nodes, {D.number_of_edges()} edges")
print(f"Earlier-share: {observed:.3f}  shuffle: {shuf.mean():.3f}±{shuf.std():.3f}  z={z:.2f}")

if D.number_of_nodes() > 0:
    pos = nx.spring_layout(D, seed=42, k=0.75, iterations=300)
    tvals = np.array([D.nodes[n]["ts"] for n in D])
    tnorm = (tvals - tvals.min()) / (tvals.max() - tvals.min() + 1e-9)
    plt.figure(figsize=(14, 9))
    nx.draw_networkx_edges(D, pos, arrows=True, arrowstyle="-|>", alpha=0.3)
    nx.draw_networkx_nodes(D, pos, node_color=tnorm, node_size=100, cmap=plt.cm.viridis)
    plt.title(f"Scaffold: earlier-share={observed:.3f}, z={z:.2f}")
    plt.axis("off")
    plt.tight_layout()
    plt.show()

if age_gaps:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4))
    a1.hist(age_gaps, bins=25, color='#4ecdc4')
    a1.set_title("EE age gaps"); a1.set_xlabel("Δt (s)")
    a2.hist(np.log(np.array(age_gaps)+1e-9), bins=30, color='#ffa726')
    a2.set_title("log(EE age gaps)"); a2.set_xlabel("log(Δt)")
    plt.tight_layout(); plt.show()
