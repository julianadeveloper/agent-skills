#!/usr/bin/env python3
"""Consulta blast radius via graphify (skill risk-scaled-code-review).

Graphify é opcional. Use este script SÓ quando triage.py reportar
graphify_available: true. Sem grafo, o blast radius usa o tool Grep nativo
do agente (aproximação sem acoplamento transitivo).

O script extrai apenas os consumidores relevantes — não joga o grafo inteiro
no contexto do LLM.

Uso:
    python query_graph.py --detect-only
    python query_graph.py UserService
    python query_graph.py src/services/UserService.js
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

GRAPHIFY_MARKERS = (
    "graphify-out/graph.json",
    "graphify/graph.json",
    "graphify-export.json",
    "graphify.json",
    ".graphify/graph.json",
)

CONSUMER_RELATIONS = frozenset({
    "imports_from", "imports", "calls", "indirect_call",
    "references", "re_exports", "uses", "shares_data_with",
})


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def detect_graphify(root: Path) -> dict:
    found: list[str] = []
    for marker in GRAPHIFY_MARKERS:
        p = root / marker
        if p.exists():
            try:
                found.append(str(p.relative_to(root)))
            except ValueError:
                found.append(str(p))
    env_path = os.environ.get("GRAPHIFY_PATH")
    if env_path:
        found.append(f"env:GRAPHIFY_PATH={env_path}")
    return {"available": bool(found), "markers": found}


def _graph_path(root: Path) -> Path | None:
    for marker in GRAPHIFY_MARKERS:
        p = root / marker
        if p.is_file() and p.name == "graph.json":
            return p
    env_path = os.environ.get("GRAPHIFY_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file() and p.name == "graph.json":
            return p
        if (p / "graph.json").is_file():
            return p / "graph.json"
    return None


def _load_graph_index(graph_path: Path) -> dict | None:
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[query_graph] erro ao ler {graph_path}: {exc}", file=sys.stderr)
        return None

    by_id: dict[str, dict] = {}
    by_source_file: dict[str, list[str]] = {}
    for node in data.get("nodes") or []:
        nid = str(node.get("id") or "")
        if not nid:
            continue
        by_id[nid] = node
        sf = normalize_path(str(node.get("source_file") or ""))
        if sf:
            by_source_file.setdefault(sf, []).append(nid)

    reverse: dict[str, set[str]] = {}
    for link in data.get("links") or data.get("edges") or []:
        if str(link.get("relation") or "") not in CONSUMER_RELATIONS:
            continue
        src = str(link.get("source") or link.get("from") or "")
        tgt = str(link.get("target") or link.get("to") or "")
        if src and tgt:
            reverse.setdefault(tgt, set()).add(src)

    return {"by_id": by_id, "by_source_file": by_source_file, "reverse": reverse}


def _symbol_variants(symbol: str) -> list[str]:
    sym = symbol.strip()
    base = Path(sym.replace("\\", "/")).name
    return {v for v in (sym, normalize_path(sym), base, Path(base).stem) if v}


def _match_seed_ids(index: dict, symbol: str) -> set[str]:
    seeds: set[str] = set()
    sym_norm = normalize_path(symbol).lower()
    variants = {v.lower() for v in _symbol_variants(symbol)}

    for sf, ids in index["by_source_file"].items():
        sf_low = sf.lower()
        if sym_norm == sf_low or sf_low.endswith(sym_norm) or sym_norm.endswith(sf_low):
            seeds.update(ids)
        elif any(v in sf_low for v in variants if len(v) > 3):
            seeds.update(ids)

    for nid, node in index["by_id"].items():
        hay = " ".join(
            str(node.get(k) or "") for k in ("id", "label", "source_file")
        ).lower()
        if any(v in hay for v in variants if len(v) > 2) or (sym_norm and sym_norm in hay):
            seeds.add(nid)

    return seeds


def query_consumers(symbol: str, index: dict, max_depth: int = 4, limit: int = 40) -> list[str]:
    seeds = _match_seed_ids(index, symbol)
    if not seeds:
        return []

    reverse = index["reverse"]
    by_id = index["by_id"]
    seen: set[str] = set(seeds)
    results: list[str] = []
    frontier = list(seeds)

    for _depth in range(max_depth):
        if not frontier or len(results) >= limit:
            break
        nxt: list[str] = []
        for node_id in frontier:
            for consumer_id in sorted(reverse.get(node_id, ())):
                if consumer_id in seen:
                    continue
                seen.add(consumer_id)
                node = by_id.get(consumer_id)
                if not node:
                    continue
                sf = normalize_path(str(node.get("source_file") or ""))
                label = str(node.get("label") or consumer_id)
                entry = f"{sf} — {label}" if sf else label
                if entry not in results:
                    results.append(entry)
                if len(results) >= limit:
                    break
                nxt.append(consumer_id)
        frontier = nxt

    return results[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Blast radius via graphify (opcional).")
    parser.add_argument("symbol", nargs="?", help="símbolo, função, classe ou path")
    parser.add_argument("--detect-only", action="store_true")
    parser.add_argument("--cwd", default=".", help="raiz do repositório")
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args(argv)

    root = Path(args.cwd).resolve()
    detection = detect_graphify(root)

    if args.detect_only:
        print(json.dumps(detection, ensure_ascii=False))
        return 0
    if not args.symbol:
        parser.error("informe o símbolo ou use --detect-only")

    graph_path = _graph_path(root)
    index = _load_graph_index(graph_path) if graph_path else None

    seed_count = len(_match_seed_ids(index, args.symbol)) if index else 0
    consumers = query_consumers(args.symbol, index) if index else []

    payload = {
        "symbol": args.symbol,
        "graphify_available": detection["available"],
        "mode": "graphify" if consumers else ("seed-no-match" if index else "no-graph"),
        "seed_count": seed_count,
        "consumers": consumers,
        "degraded": index is None,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
