#!/usr/bin/env python3
"""Triage determinístico de diff para risk-scaled-code-review.

Decide tier (lite/standard/deep/split) e especialistas.

Uso:
    git diff origin/main...HEAD | python triage.py --input -
    python triage.py --range origin/main...HEAD
    python triage.py --input mudanca.diff --force-tier deep
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

LITE_MAX_FILES = 8
LITE_MAX_LINES = 200
DEEP_MIN_LINES = 600
DEEP_MIN_FILES = 20
SPLIT_MAX_LINES = 1500
SPLIT_MAX_FILES = 40

SIGNAL_PATTERNS: list[tuple[str, list[re.Pattern[str]]]] = [
    (
        "observability",
        [
            re.compile(r"\b(console\.(log|info|warn|error|debug)|graylog|winston|pino|bunyan)\b", re.I),
            re.compile(r"\b(logger|log\.(info|warn|error|debug)|createLogger|node-logger)\b", re.I),
            re.compile(r"\b(metric|histogram|counter|gauge|tracing|span|traceId|datadog|opentelemetry|otel)\b", re.I),
            re.compile(r"(observability|logging-observability|cogs)", re.I),
        ],
    ),
    (
        "security",
        [
            re.compile(r"\b(password|passwd|secret|api[_-]?key|private[_-]?key|jwt|bearer|oauth)\b", re.I),
            re.compile(r"\b(auth|authorize|permission|rbac|acl|sanitize|encrypt|decrypt|crypto)\b", re.I),
            re.compile(r"\b(cpf|cnpj|lgpd|pii|gdpr|ssn)\b", re.I),
            re.compile(r"(jwtAuthMiddleware|permissionsMiddleware|tokenDecode)", re.I),
        ],
    ),
    (
        "async",
        [
            re.compile(r"\b(kafka|pubsub|pub.?sub|bull|bee-queue|sqs|rabbitmq|amqp|consumer|producer|subscriber)\b", re.I),
            re.compile(r"\b(queue|worker|cron|agenda|sidekiq)\b", re.I),
        ],
    ),
    (
        "data",
        [
            re.compile(r"\b(migration|mongoose|sequelize|prisma|typeorm|knex)\b", re.I),
            re.compile(r"\b(transaction|idempoten|mongodb|postgres|mysql|redis)\b", re.I),
            re.compile(r"(migrations?/|\.sql\b)", re.I),
        ],
    ),
]

# Sinais fracos: genéricos demais para disparar o especialista sozinho.
# Entram só com sinal forte, path hint ou >= 2 ocorrências no blob.
WEAK_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "security": [re.compile(r"\btoken\b", re.I)],
    "async": [re.compile(r"\bjob\b", re.I)],
    "data": [re.compile(r"\bschema\b", re.I)],
}

PATH_HINTS: list[tuple[str, list[re.Pattern[str]]]] = [
    ("observability", [re.compile(r"(logger|logging|observab|metric|telemetry)", re.I)]),
    ("security", [re.compile(r"(auth|security|middleware|permission|crypto|token)", re.I)]),
    ("async", [re.compile(r"(worker|consumer|producer|queue|job|pubsub|kafka)", re.I)]),
    ("data", [re.compile(r"(migration|repository|model|schema|entity)", re.I)]),
]

CRITICAL_HINTS = re.compile(
    r"\b(critical|crítico|hotfix|incident|sev-?[0-9]|breaking|security|CVE)\b",
    re.I,
)

# Contrato entre camadas (front↔back) — flag, não especialista.
CROSS_REPO_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(fetch|axios|apiClient|useQuery|useMutation|graphql|gql`)\b", re.I),
    re.compile(r"\b(openapi|swagger|zod|joi|yup|class-validator)\b", re.I),
    re.compile(r"\b(req\.body|res\.(json|status)|requestBody|responseBody)\b", re.I),
    re.compile(r"@(Get|Post|Put|Patch|Delete|Controller|Router|app\.(get|post|put|patch|delete))\b", re.I),
    re.compile(r"\b(router\.(get|post|put|patch|delete)|app\.(get|post|put|patch|delete))\b", re.I),
    re.compile(r"/api/[A-Za-z0-9_\-/{}\.]+", re.I),
    re.compile(r"\b(DTO|serializer|deserialize|payload|contract)\b", re.I),
]

CROSS_REPO_PATH_HINTS: list[re.Pattern[str]] = [
    re.compile(r"(controllers?|handlers?|routes?|api/|services?/api|graphql|dto|schemas?)/", re.I),
    re.compile(r"(hooks?/use|services?/api|api[_-]?client|clients?/)", re.I),
]

_TRIAGE_EXCLUDES = [
    "--", ".",
    ":!*.lock",
    ":!package-lock.json",
    ":!yarn.lock",
    ":!pnpm-lock.yaml",
    ":!composer.lock",
    ":!Gemfile.lock",
    ":!poetry.lock",
    ":!dist/**",
    ":!build/**",
    ":!*.min.js",
    ":!*.min.css",
]


def _diff_from_range(rng: str, no_filter: bool = False) -> str:
    cmd = ["git", "diff", "--no-color", rng]
    if not no_filter:
        cmd += _TRIAGE_EXCLUDES
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("git não encontrado no PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git diff falhou: {exc.stderr.strip() or exc}") from exc
    return out.stdout


def _read_diff(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def analyze_diff(diff_text: str) -> dict:
    files: set[str] = set()
    added = removed = 0
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            parts = line.split(" b/")
            if len(parts) == 2:
                files.add(parts[1].strip())
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return {
        "files": sorted(files),
        "file_count": len(files),
        "added": added,
        "removed": removed,
        "changed_lines": added + removed,
    }


def detect_signals(diff_text: str, files: list[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    blob = diff_text
    path_map = dict(PATH_HINTS)
    strong_map = dict(SIGNAL_PATTERNS)

    def _first(patterns: list[re.Pattern[str]]):
        for pat in patterns:
            m = pat.search(blob)
            if m:
                yield m.group(0)

    for specialist in sorted(set(strong_map) | set(WEAK_PATTERNS)):
        strong_hits = list(_first(strong_map.get(specialist, [])))
        weak_hits: list[str] = []
        for pat in WEAK_PATTERNS.get(specialist, []):
            weak_hits.extend(m.group(0) for m in pat.finditer(blob))
        path_hits = [f"path:{f}" for f in files if any(pat.search(f) for pat in path_map.get(specialist, []))]
        if strong_hits or path_hits or len(weak_hits) >= 2:
            merged = strong_hits + weak_hits + path_hits
            seen: set[str] = set()
            uniq: list[str] = []
            for item in merged:
                key = item.lower()
                if key not in seen:
                    seen.add(key)
                    uniq.append(item)
            hits[specialist] = uniq[:12]
    return hits


def detect_cross_repo(diff_text: str, files: list[str]) -> list[str]:
    """Sinais de contrato entre camadas — não entram em `specialists`."""
    matched: list[str] = []
    for pat in CROSS_REPO_PATTERNS:
        m = pat.search(diff_text)
        if m:
            matched.append(m.group(0))
    for f in files:
        for pat in CROSS_REPO_PATH_HINTS:
            if pat.search(f):
                matched.append(f"path:{f}")
                break
    seen: set[str] = set()
    uniq: list[str] = []
    for item in matched:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(item)
    return uniq[:12]


def choose_tier(stats: dict, signals: dict, meta_text: str, force_tier: str | None) -> tuple[str, list[str]]:
    if force_tier:
        return force_tier, [f"tier forçado: {force_tier}"]

    reasons: list[str] = []
    fc = stats["file_count"]
    lines = stats["changed_lines"]
    sig_count = len(signals)

    if lines > SPLIT_MAX_LINES or fc > SPLIT_MAX_FILES:
        return "split", [f"diff grande: {fc} arquivos, {lines} linhas"]

    if CRITICAL_HINTS.search(meta_text):
        reasons.append("hint crítico no meta/título")
        return "deep", reasons

    if lines >= DEEP_MIN_LINES:
        reasons.append(f"linhas ≥ {DEEP_MIN_LINES}")
        return "deep", reasons

    if fc >= DEEP_MIN_FILES:
        reasons.append(f"arquivos ≥ {DEEP_MIN_FILES}")
        return "deep", reasons

    if sig_count >= 3 and lines >= 300:
        reasons.append("≥3 sinais e linhas ≥ 300")
        return "deep", reasons

    combo = {"security", "data", "async"}
    if combo.intersection(signals) and lines >= 300:
        reasons.append("security+data/async com linhas ≥ 300")
        return "deep", reasons

    if fc <= LITE_MAX_FILES and lines <= LITE_MAX_LINES and sig_count == 0:
        return "lite", ["PR pontual"]

    return "standard", ["default"]


def triage_plan(
    diff_text: str,
    meta_text: str = "",
    force_tier: str | None = None,
) -> dict:
    stats = analyze_diff(diff_text)
    signals = detect_signals(diff_text, stats["files"])
    cross_hits = detect_cross_repo(diff_text, stats["files"])
    tier, reasons = choose_tier(stats, signals, meta_text, force_tier)

    return {
        "tier": tier,
        "reasons": reasons,
        "specialists": sorted(signals.keys()),
        "signals": signals,
        "needs_cross_repo_check": bool(cross_hits),
        "cross_repo_signals": cross_hits,
        "stats": {
            "file_count": stats["file_count"],
            "added": stats["added"],
            "removed": stats["removed"],
            "changed_lines": stats["changed_lines"],
            "files": stats["files"],
        },
        "core_investigators": [] if tier == "lite" else ["diff-reviewer", "logic-reviewer"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Triage de diff → tier + especialistas.")
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--range", help="git range, ex.: origin/main...HEAD")
    src.add_argument("--input", help="arquivo diff ou '-' para stdin")
    parser.add_argument("--meta", default="", help="título/corpo da task para hints")
    parser.add_argument("--force-tier", choices=["lite", "standard", "deep", "split"])
    parser.add_argument(
        "--no-filter", action="store_true",
        help="não excluir lockfiles/dist ao ler diff via --range",
    )
    parser.add_argument(
        "--human", action="store_true",
        help="JSON indentado (legível por humano); padrão é compacto para consumo por LLM",
    )
    args = parser.parse_args(argv)

    try:
        if args.range:
            diff_text = _diff_from_range(args.range, no_filter=getattr(args, "no_filter", False))
        elif args.input:
            diff_text = _read_diff(args.input)
        else:
            parser.error("informe --range ou --input")
    except (RuntimeError, OSError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1

    result = triage_plan(diff_text, args.meta, args.force_tier)
    indent = 2 if args.human else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))
    print(
        f"[triage] tier={result['tier']} specialists={result['specialists']} "
        f"cross_repo={result['needs_cross_repo_check']} "
        f"lines={result['stats']['changed_lines']} files={result['stats']['file_count']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
