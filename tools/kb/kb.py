#!/usr/bin/env python3
"""Minimal policy façade for an OKF knowledge vault."""
from __future__ import annotations

import argparse
import difflib
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from functools import lru_cache

import yaml

SCHEMA = "kb.v1"
DEFAULT_VAULT = Path(os.environ.get("KB_VAULT", Path.home() / "workspaces"))
CONFIG = Path.home() / ".config/kb/config.yml"
CACHE = Path.home() / ".cache/kb"
STATE = Path.home() / ".local/state/kb"
PRIORITY = {"canonical": 0, "decisions": 1, "evidence": 2, "working": 3, "raw": 4, "unclassified": 5}
SENSITIVITY = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
PRUNE = {".git", "node_modules", "vendor", ".venv", "venv", ".cache", "dist", "build", "coverage", "target", ".next", ".nuxt", "storybook-static", ".agents", ".agents-global", ".pi", ".pi-global", ".pi-subagents", ".obsidian"}
PATH_PRUNE: set[str] = set()
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
TOKEN_RE = re.compile(r"[\wÀ-ÿ.-]+", re.UNICODE)

class KBError(Exception):
    code = 9

class Invalid(KBError):
    code = 2

class ConfigError(KBError):
    code = 3

class NotFound(KBError):
    code = 5

class Denied(KBError):
    code = 6

class Conflict(KBError):
    code = 7

class MutationDenied(KBError):
    code = 8

@dataclass
class Note:
    path: Path
    rel: str
    meta: dict[str, Any]
    body: str
    body_start: int
    bundle: Path | None = None
    layer: str = "unclassified"


def config() -> dict[str, Any]:
    data: dict[str, Any] = {}
    try:
        if CONFIG.exists():
            data = yaml.safe_load(CONFIG.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"invalid configuration: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("configuration must be a mapping")
    data.setdefault("vault", str(DEFAULT_VAULT))
    if os.environ.get("KB_VAULT"):
        data["vault"] = os.environ["KB_VAULT"]
    data.setdefault("clearance", "internal")
    data.setdefault("selected_docs", [])
    if not isinstance(data["vault"], str) or not isinstance(data["clearance"], str) or data["clearance"] not in SENSITIVITY or not isinstance(data.get("selected_docs"), list) or not all(isinstance(x, str) for x in data["selected_docs"]):
        raise ConfigError("invalid configuration values")
    return data


def vault() -> Path:
    return Path(config()["vault"]).expanduser().resolve()


def envelope(data: Any = None, *, ok: bool = True, mode: str = "read", coverage: str = "sufficient", sources: list[Any] | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {"schema": SCHEMA, "ok": ok, "mode": mode, "coverage": coverage, "data": data if data is not None else {}, "sources": sources or [], "warnings": warnings or []}


def emit(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, default=str))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(value: str | Path, *, must_exist: bool = True) -> Path:
    root = vault()
    raw = Path(value).expanduser()
    p = raw if raw.is_absolute() else root / raw
    if must_exist:
        try:
            resolved = p.resolve(strict=True)
        except FileNotFoundError as exc:
            raise NotFound(str(value)) from exc
    else:
        parent = p.parent.resolve(strict=True)
        resolved = parent / p.name
    if resolved != root and root not in resolved.parents:
        raise Denied("path escapes vault")
    if p.is_symlink() or (must_exist and resolved.is_symlink()):
        raise Denied("symlink targets are not allowed")
    return resolved


def parse_text(text: str) -> tuple[dict[str, Any], str, int]:
    if not text.startswith("---\n"):
        return {}, text, 1
    end = text.find("\n---", 4)
    if end < 0:
        raise Invalid("unclosed YAML frontmatter")
    try:
        meta = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as exc:
        raise Invalid(f"invalid YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise Invalid("frontmatter must be a mapping")
    close = text.find("\n", end + 4)
    if close < 0:
        return meta, "", text.count("\n", 0, end + 4) + 1
    return meta, text[close + 1 :], text.count("\n", 0, close + 1) + 1


def read_note(path: str | Path) -> Note:
    p = safe_path(path)
    if p.suffix.lower() != ".md":
        raise Invalid("not a Markdown file")
    text = p.read_text(encoding="utf-8")
    meta, body, body_start = parse_text(text)
    note = Note(p, p.relative_to(vault()).as_posix(), meta, body, body_start)
    attach_layer(note)
    return note


def walk_markdown(base: Path) -> Iterable[Path]:
    root = vault()
    for current, dirs, files in os.walk(base, followlinks=False):
        cur = Path(current)
        rel_cur = cur.relative_to(root).as_posix() if cur != root else ""
        dirs[:] = [d for d in dirs if d not in PRUNE and not (cur / d).is_symlink() and f"{rel_cur}/{d}".strip("/") not in PATH_PRUNE]
        for name in files:
            p = cur / name
            if name.endswith(".md") and not p.is_symlink():
                yield p


@lru_cache(maxsize=16)
def _bundles(root_value: str) -> tuple[tuple[Path, dict[str, Any]], ...]:
    found = []
    for p in walk_markdown(Path(root_value)):
        if p.name != "index.md":
            continue
        try:
            meta, _, _ = parse_text(p.read_text(encoding="utf-8"))
        except (OSError, KBError):
            continue
        if isinstance(meta.get("knowledge_layers"), dict):
            found.append((p.parent, meta))
    return tuple(sorted(found, key=lambda item: len(item[0].parts), reverse=True))


def bundles() -> list[tuple[Path, dict[str, Any]]]:
    return list(_bundles(str(vault())))


def attach_layer(note: Note) -> None:
    explicit = str(note.meta.get("authority", "")).lower()
    layer = explicit if explicit in {"canonical", "evidence", "working", "raw"} else "unclassified"
    for root, meta in bundles():
        if note.path != root and root not in note.path.parents:
            continue
        note.bundle = root
        rel = note.path.relative_to(root).as_posix()
        matches: list[tuple[int, str]] = []
        for candidate, entries in (meta.get("knowledge_layers") or {}).items():
            for entry in entries or []:
                e = str(entry).lstrip("./")
                if rel == e.rstrip("/") or (e.endswith("/") and rel.startswith(e)):
                    matches.append((len(e), candidate))
        mapped = max(matches)[1] if matches else None
        if mapped == "decisions":
            layer = "decisions"
        elif explicit not in {"canonical", "evidence", "working", "raw"} and mapped:
            layer = mapped
        break
    note.layer = layer


def effective_policy(note: Note) -> tuple[str, str]:
    bundle_meta: dict[str, Any] = {}
    if note.bundle:
        bundle_meta = next((meta for root, meta in bundles() if root == note.bundle), {})
    bundle_access = str(bundle_meta.get("agent_access", "read"))
    note_access = str(note.meta.get("agent_access", bundle_access))
    access = "deny" if bundle_access == "deny" or note_access == "deny" else note_access
    bundle_level = SENSITIVITY.get(str(bundle_meta.get("sensitivity", "internal")), 1)
    note_level = SENSITIVITY.get(str(note.meta.get("sensitivity", bundle_meta.get("sensitivity", "internal"))), 1)
    sensitivity = next(name for name, level in SENSITIVITY.items() if level == max(bundle_level, note_level))
    return access, sensitivity


def clearance_allows(value: Note | dict[str, Any]) -> bool:
    if isinstance(value, Note):
        access, sensitivity = effective_policy(value)
    else:
        access = str(value.get("agent_access", "read"))
        sensitivity = str(value.get("sensitivity", "internal"))
    if access == "deny":
        return False
    return SENSITIVITY.get(sensitivity, 1) <= SENSITIVITY.get(str(config().get("clearance", "internal")), 1)


def enforce(note: Note, *, body: bool = True) -> None:
    access, _ = effective_policy(note)
    if not clearance_allows(note):
        raise Denied(note.rel)
    if body and access == "metadata-only":
        raise Denied("body access denied")


def is_expired(note: Note) -> bool:
    until = note.meta.get("valid_until")
    if not until:
        return False
    try:
        return date.fromisoformat(str(until)[:10]) < datetime.now(timezone.utc).date()
    except ValueError:
        return False


def status_current(note: Note) -> bool:
    status = str(note.meta.get("status", "")).lower()
    if note.layer == "decisions" and status != "accepted":
        return False
    if status in {"superseded", "deprecated", "archived", "rejected"}:
        return False
    return not is_expired(note)


def eligible_paths() -> Iterable[Path]:
    seen: set[Path] = set()
    for root, _ in bundles():
        for p in walk_markdown(root):
            if p not in seen:
                seen.add(p)
                yield p
    for rel in config().get("selected_docs", []):
        try:
            p = safe_path(rel)
            if p not in seen:
                yield p
        except KBError:
            continue


def eligible_notes() -> Iterable[Note]:
    for p in eligible_paths():
        try:
            yield read_note(p)
        except (OSError, KBError):
            continue


def tokens(query: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(query) if len(x) > 1]


def lexical(query: str, *, layers: set[str] | None = None, limit: int = 20, current: bool = True) -> list[dict[str, Any]]:
    terms = tokens(query)
    results = []
    for note in eligible_notes():
        if layers and note.layer not in layers:
            continue
        if current and not status_current(note):
            continue
        access, _ = effective_policy(note)
        if not clearance_allows(note) or access == "metadata-only":
            continue
        hay = (str(note.meta.get("title", "")) + "\n" + note.body).lower()
        score = sum(hay.count(t) for t in terms)
        if terms and score == 0:
            continue
        first_line = 1
        if terms:
            lines = note.body.splitlines()
            for i, line in enumerate(lines):
                if any(t in line.lower() for t in terms):
                    first_line = note.body_start + i
                    break
        results.append({"path": note.rel, "title": note.meta.get("title") or note.path.stem, "layer": note.layer, "status": note.meta.get("status"), "score": score, "line": first_line})
    results.sort(key=lambda r: (PRIORITY.get(r["layer"], 5), -r["score"], r["path"]))
    return results[:limit]


def source_items(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"path": r["path"], "line": r.get("line"), "authority": r.get("layer")} for r in rows]


def qmd_normalized(path: str) -> str:
    return "/".join(part.lstrip("_").replace("_", "-") for part in path.split("/"))


def qmd_collection(kind: str = "agent") -> str:
    qmd = config().get("qmd") or {}
    if not isinstance(qmd, dict):
        raise ConfigError("qmd configuration must be a mapping")
    key = "lexical_collection" if kind == "agent" else "full_collection"
    return str(qmd.get(key, f"knowledge-{kind}"))


def map_qmd_rows(rows: list[dict[str, Any]], kind: str = "agent") -> list[dict[str, Any]]:
    projection = projection_root(kind)
    mapping_file = projection / "mapping.jsonl"
    if not mapping_file.exists():
        return []
    mappings = [json.loads(line) for line in mapping_file.read_text().splitlines() if line]
    by_path = {m["projected"]: m for m in mappings}
    by_normalized: dict[str, list[dict[str, Any]]] = {}
    for m in mappings:
        by_normalized.setdefault(qmd_normalized(m["projected"]), []).append(m)
    mapped = []
    prefix = f"qmd://{qmd_collection(kind)}/"
    for row in rows:
        shown = str(row.get("file", ""))
        rel = shown[len(prefix):] if shown.startswith(prefix) else shown
        if rel.startswith(str(projection) + "/"):
            rel = rel[len(str(projection)) + 1:]
        match = by_path.get(rel)
        if match is None:
            candidates = by_normalized.get(qmd_normalized(rel), [])
            match = candidates[0] if len(candidates) == 1 else None
        if match is None:
            continue
        try:
            source = safe_path(match["source"])
        except KBError:
            continue
        if sha256(source.read_bytes()) != match.get("source_sha256"):
            continue
        source_line = int(match["body_start_line"]) + max(int(row.get("line", 1)) - 1, 0)
        mapped.append({"path": source.relative_to(vault()).as_posix(), "line": source_line, "qmd_score": row.get("score", 0), "snippet": row.get("snippet", ""), "authority": match.get("authority", "unclassified")})
    return mapped


def qmd_lexical(query: str, limit: int) -> list[dict[str, Any]]:
    binary = shutil.which("qmd")
    if not binary:
        return []
    try:
        run = subprocess.run([binary, "search", query, "-c", qmd_collection("agent"), "--json", "-n", str(limit)], text=True, capture_output=True, timeout=30)
        if run.returncode != 0:
            return []
        return map_qmd_rows(json.loads(run.stdout), "agent")
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, json.JSONDecodeError):
        return []


def cmd_doctor(_: argparse.Namespace) -> dict[str, Any]:
    root = vault()
    obsidian = shutil.which("obsidian")
    qmd = shutil.which("qmd")
    def version(cmd: list[str]) -> str | None:
        try:
            return subprocess.run(cmd, text=True, capture_output=True, timeout=10).stdout.strip() or None
        except Exception:
            return None
    invalid = []
    for path in eligible_paths():
        try:
            parse_text(path.read_text(encoding="utf-8"))
        except (OSError, KBError) as exc:
            invalid.append({"path": path.relative_to(root).as_posix(), "error": str(exc)})
    data = {"vault": str(root), "root_config": (root / ".obsidian").is_dir(), "bundles": [str(p.relative_to(root)) for p, _ in bundles()], "obsidian": {"path": obsidian, "connected": bool(version([obsidian, "version"])) if obsidian else False}, "qmd": {"path": qmd, "version": version([qmd, "--version"]) if qmd else None, "models_present": (Path.home()/".cache/qmd/models").exists()}, "invalid_yaml": invalid, "cache_writable": os.access(CACHE.parent, os.W_OK), "state_writable": os.access(STATE.parent, os.W_OK)}
    warnings = [] if data["obsidian"]["connected"] else ["Obsidian closed or CLI unavailable; direct parser fallback active"]
    return envelope(data, warnings=warnings)


def cmd_status(_: argparse.Namespace) -> dict[str, Any]:
    notes = list(eligible_notes())
    return envelope({"vault": str(vault()), "bundle_count": len(bundles()), "note_count": len(notes), "review_count": sum("review/human-required" in (n.meta.get("tags") or []) for n in notes), "layers": {k: sum(n.layer == k for n in notes) for k in PRIORITY}})


def cmd_meta(args: argparse.Namespace) -> dict[str, Any]:
    n = read_note(args.path); enforce(n, body=False)
    return envelope({"path": n.rel, "metadata": n.meta, "layer": n.layer})


def cmd_read(args: argparse.Namespace) -> dict[str, Any]:
    n = read_note(args.path); enforce(n, body=True)
    return envelope({"path": n.rel, "metadata": n.meta, "layer": n.layer, "body": n.body, "body_start_line": n.body_start}, sources=[{"path": n.rel, "line": n.body_start, "authority": n.layer}])


def query_result(query: str, *, layers: set[str] | None = None, limit: int = 20) -> dict[str, Any]:
    direct = lexical(query, layers=layers, limit=max(limit, 20))
    qmd_rows = qmd_lexical(query, max(limit, 20))
    merged = {row["path"]: row for row in direct}
    for qrow in qmd_rows:
        try:
            note = read_note(qrow["path"])
        except KBError:
            continue
        access, _ = effective_policy(note)
        if (layers and note.layer not in layers) or not clearance_allows(note) or access == "metadata-only" or not status_current(note):
            continue
        row = merged.setdefault(qrow["path"], {"path": qrow["path"], "title": note.meta.get("title") or note.path.stem, "layer": note.layer, "status": note.meta.get("status"), "score": 0, "line": qrow["line"]})
        row["qmd_score"] = qrow["qmd_score"]
        row["line"] = qrow["line"]
    rows = sorted(merged.values(), key=lambda r: (PRIORITY.get(r["layer"], 5), -float(r.get("qmd_score", 0)), -int(r.get("score", 0)), r["path"]))[:limit]
    stale = not rows and bool(lexical(query, layers=layers, limit=limit, current=False))
    coverage = "sufficient" if rows and rows[0]["layer"] in {"canonical", "decisions"} else "partial" if rows else "stale" if stale else "absent"
    warning = "QMD BM25 merged with governed metadata; no implicit web search" if qmd_rows else "Lexical/direct-parser fallback used; no implicit web search"
    return envelope({"query": query, "results": rows}, coverage=coverage, sources=source_items(rows), warnings=[warning])


def cmd_query(args: argparse.Namespace) -> dict[str, Any]: return query_result(args.query, limit=args.limit)
def cmd_truth(args: argparse.Namespace) -> dict[str, Any]: return query_result(args.query, layers={"canonical"}, limit=args.limit)
def cmd_decisions(args: argparse.Namespace) -> dict[str, Any]: return query_result(args.query, layers={"decisions"}, limit=args.limit)
def cmd_evidence(args: argparse.Namespace) -> dict[str, Any]: return query_result(args.query, layers={"evidence", "raw"}, limit=args.limit)

def cmd_semantic(args: argparse.Namespace) -> dict[str, Any]:
    result = query_result(args.query, limit=args.limit)
    result["warnings"].insert(0, "Semantic models unavailable or disabled; lexical fallback used")
    return result


def resolve_link(source: Note, target: str) -> str | None:
    candidates = []
    for n in eligible_notes():
        access, _ = effective_policy(n)
        if not clearance_allows(n) or access == "metadata-only":
            continue
        stem = n.path.stem
        rel_no_suffix = n.rel[:-3] if n.rel.endswith(".md") else n.rel
        if target in {stem, rel_no_suffix, n.rel} or rel_no_suffix.endswith("/" + target):
            candidates.append(n.rel)
    return sorted(candidates)[0] if candidates else None


def cmd_related(args: argparse.Namespace) -> dict[str, Any]:
    n = read_note(args.path); enforce(n)
    outgoing = sorted({x for t in LINK_RE.findall(n.body) if (x := resolve_link(n, t))})
    backlinks = []
    for other in eligible_notes():
        if other.rel == n.rel or not clearance_allows(other) or effective_policy(other)[0] == "metadata-only": continue
        if any(resolve_link(other, target) == n.rel for target in LINK_RE.findall(other.body)): backlinks.append(other.rel)
    return envelope({"path": n.rel, "outgoing": outgoing, "backlinks": sorted(backlinks)})


def cmd_provenance(args: argparse.Namespace) -> dict[str, Any]:
    n=read_note(args.path); enforce(n)
    refs=[]
    for value in n.meta.get("evidence",[]) or []:
        target=str(value).strip('[]').split('#',1)[0]
        resolved=resolve_link(n,target)
        refs.append({"reference":value,"path":resolved})
    return envelope({"path":n.rel,"evidence":refs,"supersedes":n.meta.get("supersedes",[])},sources=[{"path":n.rel,"line":1,"authority":n.layer}])


def canvas_data(path: str) -> tuple[Path, dict[str, Any], list[str]]:
    p=safe_path(path)
    if p.suffix != ".canvas": raise Invalid("not a Canvas")
    try: data=json.loads(p.read_text())
    except json.JSONDecodeError as exc: raise Invalid(str(exc)) from exc
    if not isinstance(data,dict) or not isinstance(data.get("nodes",[]),list) or not isinstance(data.get("edges",[]),list): raise Invalid("invalid JSON Canvas")
    missing=[]
    for node in data.get("nodes",[]):
        if node.get("type")=="file" and not (vault()/str(node.get("file",""))).exists(): missing.append(str(node.get("file")))
    return p,data,missing


def cmd_canvas(args: argparse.Namespace) -> dict[str, Any]:
    p,data,missing=canvas_data(args.path)
    bundle_meta = next((meta for root, meta in bundles() if p == root or root in p.parents), {})
    access = str(bundle_meta.get("agent_access", "read")); sensitivity = str(bundle_meta.get("sensitivity", "internal"))
    if access == "deny" or SENSITIVITY.get(sensitivity, 1) > SENSITIVITY.get(str(config().get("clearance", "internal")), 1):
        raise Denied(p.relative_to(vault()).as_posix())
    companion = p.with_suffix(".md")
    if companion.exists():
        enforce(read_note(companion), body=True)
    return envelope({"path":p.relative_to(vault()).as_posix(),"nodes":data.get("nodes",[]),"edges":data.get("edges",[]),"missing_files":missing},coverage="partial" if missing else "sufficient")


def cmd_conflicts(_: argparse.Namespace) -> dict[str, Any]:
    groups: dict[str,list[Note]]={}
    for n in eligible_notes():
        if n.layer=="canonical" and status_current(n) and clearance_allows(n) and effective_policy(n)[0] != "metadata-only":
            key=str(n.meta.get("conflict_key") or n.meta.get("title") or "").strip().lower()
            if key: groups.setdefault(key,[]).append(n)
    conflicts=[]
    for key,items in groups.items():
        hashes={sha256(n.body.encode()) for n in items}
        if len(items)>1 and len(hashes)>1: conflicts.append({"key":key,"paths":[n.rel for n in items]})
    return envelope({"conflicts":conflicts},coverage="conflicting" if conflicts else "sufficient")


def cmd_assess(args: argparse.Namespace) -> dict[str, Any]: return query_result(args.query,limit=args.limit)


def cmd_validate(_: argparse.Namespace) -> dict[str, Any]:
    issues=[]; count=0
    for path in eligible_paths():
        count+=1
        try:
            n=read_note(path)
        except (OSError, KBError) as exc:
            issues.append({"path":path.relative_to(vault()).as_posix(),"issue":str(exc)})
            continue
        if n.layer != "unclassified" and not n.meta.get("type"): issues.append({"path":n.rel,"issue":"missing type"})
        if n.meta.get("agent_access") not in {None,"deny","metadata-only","read","propose","write"}: issues.append({"path":n.rel,"issue":"invalid agent_access"})
    return envelope({"validated":count,"issues":issues},coverage="partial" if issues else "sufficient")


def cmd_review(_: argparse.Namespace) -> dict[str, Any]:
    rows=[{"path":n.rel,"type":n.meta.get("type"),"layer":n.layer} for n in eligible_notes() if "review/human-required" in (n.meta.get("tags") or []) and clearance_allows(n)]
    return envelope({"count":len(rows),"notes":rows})


def ensure_review(text: str) -> str:
    meta,_,_=parse_text(text)
    if not meta:
        return "---\ntags:\n  - review/human-required\n---\n\n"+text
    end=text.find("\n---",4); fm=text[4:end]
    if "review/human-required" in (meta.get("tags") or []): return text
    lines=fm.splitlines(); idx=next((i for i,x in enumerate(lines) if x.startswith("tags:")),None)
    if idx is None:
        lines += ["tags:","  - review/human-required"]
    elif lines[idx].strip()=="tags:": lines.insert(idx+1,"  - review/human-required")
    else:
        tags=meta.get("tags") or []
        lines[idx:idx+1]=["tags:","  - review/human-required"]+[f"  - {x}" for x in tags]
    return "---\n"+"\n".join(lines)+text[end:]


def proposal_dir() -> Path:
    p=STATE/"proposals"; p.mkdir(parents=True,exist_ok=True); p.chmod(0o700); return p


def make_proposal(kind: str, target: str, content_file: str) -> dict[str, Any]:
    p=safe_path(target,must_exist=False)
    existing=p.exists()
    if existing:
        n=read_note(p); enforce(n,body=False)
        if effective_policy(n)[0] != "write": raise MutationDenied("target is not writable by agents")
    else:
        if not any(p==b or b in p.parents for b,_ in bundles()): raise MutationDenied("target outside registered bundle")
    content=Path(content_file).read_text(encoding="utf-8")
    parse_text(ensure_review(content))
    expected=sha256(p.read_bytes()) if existing else None
    ident=hashlib.sha256(f"{time.time_ns()}:{p}".encode()).hexdigest()[:16]
    payload={"schema":"kb.proposal.v1","id":ident,"kind":kind,"target":p.relative_to(vault()).as_posix(),"expected_sha256":expected,"content":content,"created_at":datetime.now(timezone.utc).isoformat()}
    proposal = proposal_dir()/f"{ident}.json"
    proposal.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    proposal.chmod(0o600)
    return payload


def cmd_capture(args: argparse.Namespace) -> dict[str, Any]:
    if not args.dry_run: raise MutationDenied("capture requires --dry-run")
    p=make_proposal("capture",args.path,args.content_file)
    return envelope({k:v for k,v in p.items() if k!="content"},mode="propose")


def cmd_promote(args: argparse.Namespace) -> dict[str, Any]:
    if not args.dry_run: raise MutationDenied("promote requires --dry-run")
    p=make_proposal("promote",args.path,args.content_file)
    return envelope({k:v for k,v in p.items() if k!="content"},mode="propose")


def cmd_apply(args: argparse.Namespace) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{16}", args.proposal_id):
        raise Invalid("invalid proposal id")
    proposals = proposal_dir().resolve()
    proposal = (proposals / f"{args.proposal_id}.json").resolve()
    if proposal.parent != proposals or not proposal.is_file():
        raise NotFound(args.proposal_id)
    try:
        data = json.loads(proposal.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise Invalid("invalid proposal") from exc
    required = {"schema", "id", "kind", "target", "expected_sha256", "content"}
    if (not isinstance(data, dict) or not required <= data.keys() or data["schema"] != "kb.proposal.v1" or data["id"] != args.proposal_id or not isinstance(data["kind"], str) or data["kind"] not in {"capture", "promote"}
        or not isinstance(data["target"], str) or not data["target"] or not isinstance(data["content"], str)
        or (data["expected_sha256"] is not None and (not isinstance(data["expected_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", data["expected_sha256"])) )):
        raise Invalid("invalid proposal payload")
    p = safe_path(data["target"], must_exist=False)
    if not any(p == root or root in p.parents for root, _ in bundles()):
        raise MutationDenied("target outside registered bundle")
    content = ensure_review(str(data["content"]))
    new_meta, _, _ = parse_text(content)
    locks = STATE / "locks"; locks.mkdir(parents=True, exist_ok=True); locks.chmod(0o700)
    lock_path = locks / (hashlib.sha256(str(p).encode()).hexdigest() + ".lock")
    with lock_path.open("a+") as lock:
        lock_path.chmod(0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = p.exists()
        before = p.read_text(encoding="utf-8") if existing else ""
        actual = sha256(p.read_bytes()) if existing else None
        if actual != data.get("expected_sha256"):
            raise Conflict("stale proposal: source hash mismatch")
        if existing:
            current = read_note(p); enforce(current, body=False)
            if effective_policy(current)[0] != "write":
                raise MutationDenied("target is not writable by agents")
            if str(current.meta.get("status", "")).lower() != "accepted" and str(new_meta.get("status", "")).lower() == "accepted" and str(new_meta.get("type", "")).lower() == "decision":
                raise MutationDenied("an agent cannot accept a decision")
        elif str(new_meta.get("status", "")).lower() == "accepted" and str(new_meta.get("type", "")).lower() == "decision":
            raise MutationDenied("an agent cannot create an accepted decision")
        if p.parent.resolve() != p.parent:
            raise Denied("symlink parent")
        fd, tmp = tempfile.mkstemp(prefix=f".{p.name}.", dir=p.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content); f.flush(); os.fsync(f.fileno())
            if (sha256(p.read_bytes()) if p.exists() else None) != data.get("expected_sha256"):
                raise Conflict("concurrent write detected")
            os.replace(tmp, p)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    diff = "".join(difflib.unified_diff(before.splitlines(True), content.splitlines(True), fromfile=data["target"], tofile=data["target"]))
    return envelope({"proposal_id":args.proposal_id,"changed_paths":[data["target"]],"sha256":sha256(content.encode()),"diff":diff},mode="apply")


def projection_root(kind: str) -> Path: return CACHE/"projections"/qmd_collection(kind)


def cmd_projection(args: argparse.Namespace) -> dict[str, Any]:
    kind=args.kind
    if kind not in {"full","agent"}: raise Invalid("projection kind")
    target=projection_root(kind); target.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix=f".{target.name}.",dir=target.parent)); mappings=[]; excluded=[]
    try:
        for n in eligible_notes():
            access, sensitivity = effective_policy(n)
            clearance = SENSITIVITY.get(str(config().get("clearance", "internal")), 1)
            if access == "deny" or (kind=="agent" and (access == "metadata-only" or SENSITIVITY.get(sensitivity,1)>clearance)):
                excluded.append(n.rel); continue
            out=staging/n.rel; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(n.body)
            mappings.append({"projected":n.rel,"source":str(n.path),"source_sha256":sha256(n.path.read_bytes()),"body_start_line":n.body_start,"authority":n.layer})
        (staging/"mapping.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in mappings))
        old=target.with_name(target.name+".old")
        if old.exists(): shutil.rmtree(old)
        if target.exists(): os.replace(target,old)
        os.replace(staging,target)
        if old.exists(): shutil.rmtree(old)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    return envelope({"kind":kind,"path":str(target),"documents":len(mappings),"excluded":len(excluded)})


class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise Invalid(message)


def parser() -> argparse.ArgumentParser:
    p=JSONArgumentParser(prog="kb"); sub=p.add_subparsers(dest="command",required=True)
    for name,func in (("doctor",cmd_doctor),("status",cmd_status),("conflicts",cmd_conflicts)):
        q=sub.add_parser(name); q.set_defaults(func=func)
    for name,func in (("meta",cmd_meta),("read",cmd_read),("related",cmd_related),("provenance",cmd_provenance),("canvas",cmd_canvas)):
        q=sub.add_parser(name); q.add_argument("path"); q.set_defaults(func=func)
    for name,func in (("query",cmd_query),("semantic",cmd_semantic),("truth",cmd_truth),("decisions",cmd_decisions),("evidence",cmd_evidence),("assess",cmd_assess)):
        q=sub.add_parser(name); q.add_argument("query"); q.add_argument("--limit",type=int,default=20); q.set_defaults(func=func)
    okf=sub.add_parser("okf"); oks=okf.add_subparsers(dest="okf_command",required=True); q=oks.add_parser("validate"); q.set_defaults(func=cmd_validate)
    review=sub.add_parser("review"); rs=review.add_subparsers(dest="review_command",required=True); q=rs.add_parser("list"); q.set_defaults(func=cmd_review)
    for name,func in (("capture",cmd_capture),("promote",cmd_promote)):
        q=sub.add_parser(name); q.add_argument("--dry-run",action="store_true"); q.add_argument("--path",required=True); q.add_argument("--content-file",required=True); q.set_defaults(func=func)
    q=sub.add_parser("apply"); q.add_argument("proposal_id"); q.set_defaults(func=cmd_apply)
    proj=sub.add_parser("projection"); ps=proj.add_subparsers(dest="projection_command",required=True); q=ps.add_parser("build"); q.add_argument("--kind",required=True); q.set_defaults(func=cmd_projection)
    return p


def main(argv: list[str] | None=None) -> int:
    try:
        args=parser().parse_args(argv); emit(args.func(args)); return 0
    except KBError as exc:
        emit(envelope({"error":str(exc),"exit_code":exc.code},ok=False,coverage="absent")); return exc.code
    except Exception as exc:
        print(f"kb: {exc}",file=sys.stderr); emit(envelope({"error":"internal error","exit_code":9},ok=False,coverage="absent")); return 9

if __name__=="__main__": raise SystemExit(main())
