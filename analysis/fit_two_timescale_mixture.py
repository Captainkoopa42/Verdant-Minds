#!/usr/bin/env python3
import argparse, json, math, os
from extract_scaffolding_metrics import load_graph


def norm_pdf(x, mu, sig):
    sig = max(sig, 1e-6)
    return math.exp(-0.5 * ((x - mu) / sig) ** 2) / (sig * math.sqrt(2 * math.pi))


def fit_1g(xs):
    n = len(xs)
    mu = sum(xs) / n
    var = sum((x - mu) ** 2 for x in xs) / n
    sig = math.sqrt(max(var, 1e-9))
    ll = sum(math.log(max(norm_pdf(x, mu, sig), 1e-300)) for x in xs)
    bic = -2 * ll + 2 * math.log(n)
    return {"mu": mu, "sigma": sig, "ll": ll, "bic": bic}


def fit_2g(xs, iters=100):
    n = len(xs)
    m1, m2 = min(xs), max(xs)
    s1 = s2 = max((m2 - m1) / 4, 1e-3)
    w = 0.5
    for _ in range(iters):
        r1, r2 = [], []
        for x in xs:
            p1 = w * norm_pdf(x, m1, s1)
            p2 = (1 - w) * norm_pdf(x, m2, s2)
            z = max(p1 + p2, 1e-300)
            r1.append(p1 / z)
            r2.append(p2 / z)
        n1, n2 = sum(r1), sum(r2)
        w = n1 / n
        m1 = sum(r1[i] * xs[i] for i in range(n)) / max(n1, 1e-9)
        m2 = sum(r2[i] * xs[i] for i in range(n)) / max(n2, 1e-9)
        s1 = math.sqrt(sum(r1[i] * (xs[i] - m1) ** 2 for i in range(n)) / max(n1, 1e-9))
        s2 = math.sqrt(sum(r2[i] * (xs[i] - m2) ** 2 for i in range(n)) / max(n2, 1e-9))
        s1, s2 = max(s1, 1e-3), max(s2, 1e-3)
    ll = sum(math.log(max(w * norm_pdf(x, m1, s1) + (1 - w) * norm_pdf(x, m2, s2), 1e-300)) for x in xs)
    bic = -2 * ll + 5 * math.log(n)
    return {"weight1": w, "mu1": m1, "sigma1": s1, "mu2": m2, "sigma2": s2, "ll": ll, "bic": bic}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    nmap, edges = load_graph(args.state)
    ts = {k: v.get("timestamp") for k, v in nmap.items()}
    dts = []
    for e in edges:
        a, b = ts.get(e["source"]), ts.get(e["target"])
        if a is None or b is None:
            continue
        dt = abs(a - b)
        if dt > 0:
            dts.append(math.log(dt))
    if len(dts) < 10:
        raise SystemExit("Not enough timestamped edges for mixture fitting.")

    g1 = fit_1g(dts)
    g2 = fit_2g(dts)
    out = {"one_component": g1, "two_component": g2, "delta_bic_two_minus_one": g2["bic"] - g1["bic"]}
    with open(os.path.join(args.outdir, "two_timescale_mixture.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
