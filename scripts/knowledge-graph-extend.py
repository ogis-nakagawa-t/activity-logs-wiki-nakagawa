#!/usr/bin/env python3
"""understand-anything の scan-manifest.json を、このリポジトリの構成に合わせて補う。

understand-anything プラグインの /understand-knowledge は、一次資料を
`<wiki>/raw/` から探し、wiki の外を指すリンクを解決しない。また、記事への
リンクを wiki ディレクトリからの相対パス（`[[topic/slug]]`）で探すため、
このリポジトリのパス付き wikilink（`[[90_Wiki/topic/slug]]`）も解決しない。
プラグインのファイルは編集せず、プラグインの parse-knowledge-base.py が
書いた scan-manifest.json をこのスクリプトで補う。

補う内容:
1. 月ごとのログ（`<wiki>/YYYY/MM.md`）を記事ノードから外す（log.md と同じ扱い）。
2. `80_Raw/` の全ファイルを `source` ノードにする（プラグインが `raw/` に対して
   作るノードと同じ形）。
3. 記事の wikilink を解決する。
   - `[[90_Wiki/...]]` → 記事ノードへの `related` の辺。
   - `[[10_Daily/...]]`・`[[80_Raw/...]]`・`[[40_Notes/...]]` の既存ファイル
     → `source` ノードと、記事からの `cites` の辺。
4. 記事の frontmatter `sources` に書かれた同じディレクトリの既存ファイルも、
   `source` ノードと `cites` の辺にする。
5. index.md の `##` 節に `[[90_Wiki/...]]` で並んだ記事に、カテゴリと
   `categorized_under` の辺を付ける。記事のタグは frontmatter から読み直す。
6. 未解決のリンクの警告と件数、被リンク（backlinks）を数え直す。

何度実行しても結果は変わらない。使い方（procedures/knowledge-graph.md）:
    python -I scripts/knowledge-graph-extend.py 90_Wiki
"""

import json
import re
import sys
from pathlib import Path

SOURCE_DIRS = ("10_Daily", "80_Raw", "40_Notes")
DAILY_RE = re.compile(r"^10_Daily/(\d{4})/(\d{2})/(\d{2})$")
MONTHLY_LOG_RE = re.compile(r"^\d{4}/\d{2}\.md$")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
RELATED_WEIGHT = 0.7  # プラグインの wikilink の辺と同じ
CITE_WEIGHT = 0.7
CATEGORY_WEIGHT = 0.6
MAX_WARNINGS = 50


def resolve_ua_dir(wiki: Path) -> Path:
    """プラグインと同じく、古い .understand-anything/ があればそちらを使う。"""
    legacy = wiki / ".understand-anything"
    return legacy if legacy.is_dir() else wiki / ".ua"


def _scalar(value: str) -> str:
    value = value.strip()
    if value[:1] in {'"', "'"}:
        quote = value[0]
        end = value.find(quote, 1)
        return value[1:end] if end > 0 else value[1:]
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def read_frontmatter(path: Path) -> dict:
    """先頭の YAML frontmatter を簡易に解析する（llm-wiki の check_evidence.py と同じ範囲）。

    対応するのは `key: value`、`key: [a, b]`、`key:` に続く `  - item` だけ。
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict = {}
    current_list = None
    for line in lines[1:]:
        if line.strip() in {"---", "..."}:
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s*(.*)$", line)
        if item and current_list is not None:
            value = _scalar(item.group(1))
            if value:
                meta[current_list].append(value)
            continue
        kv = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not kv:
            current_list = None
            continue
        key, rest = kv.group(1), kv.group(2).strip()
        if rest.startswith("["):
            inner = rest[1 : rest.rfind("]")] if "]" in rest else rest[1:]
            meta[key] = [v for v in (_scalar(p) for p in inner.split(",")) if v]
            current_list = None
        elif not _scalar(rest):
            meta[key] = []
            current_list = key
        else:
            meta[key] = _scalar(rest)
            current_list = None
    return meta


def normalize_target(target: str) -> str:
    """wikilink や sources の値を、`/` 区切りのルート相対パスの候補にする。"""
    target = target.split("#", 1)[0].strip().replace("\\", "/").lstrip("/")
    while target.startswith("./"):
        target = target[2:]
    return target


def find_repo_file(root: Path, target: str) -> str | None:
    """SOURCE_DIRS の下の既存ファイルなら、ルート相対のパス（拡張子付き）を返す。"""
    target = normalize_target(target)
    if not target.startswith(tuple(d + "/" for d in SOURCE_DIRS)) or ".." in target.split("/"):
        return None
    for candidate in (target, target + ".md"):
        if (root / candidate).is_file():
            return candidate
    return None


def article_stem(node: dict) -> str:
    return node["id"].split(":", 1)[1]


class PluginResolver:
    """プラグインの resolve_wikilink と同じ規則で、プラグインが解決できるリンクを判定する。"""

    def __init__(self, stems: list[str]):
        self.name_map: dict[str, str] = {}
        counts: dict[str, int] = {}
        for stem in stems:
            self.name_map[stem.lower()] = stem
            base = stem.rsplit("/", 1)[-1].lower()
            counts[base] = counts.get(base, 0) + 1
            self.name_map[base] = stem
        for base, count in counts.items():
            if count > 1:
                self.name_map.pop(base, None)

    def resolve(self, target: str) -> str | None:
        key = target.lower().strip()
        if key.startswith("-"):
            return None
        if key in self.name_map:
            return self.name_map[key]
        for stored_key, stem in self.name_map.items():
            if stored_key.endswith("/" + key) or stored_key == key:
                return stem
        return None


def source_node(root: Path, rel: str) -> dict:
    """ルート相対のパスから source ノードを作る。"""
    path = root / rel
    stem = rel[: -len(path.suffix)] if path.suffix else rel
    ext = path.suffix.lower()
    node = {
        "id": f"source:{stem}",
        "type": "source",
        "filePath": f"../{rel}",
        "complexity": "simple",
    }
    daily = DAILY_RE.match(stem)
    if daily:
        date = "-".join(daily.groups())
        node.update(name=f"{date} 日次ノート", summary=f"日次ノート（{date}）", tags=["daily"])
        return node
    title = read_frontmatter(path).get("title") if ext == ".md" else None
    if not isinstance(title, str) or not title:
        title = path.name
    if rel.startswith("80_Raw/"):
        size_kb = path.stat().st_size / 1024
        node.update(
            name=title,
            summary=f"Raw source ({ext or 'unknown'}, {size_kb:.0f} KB)",
            tags=["raw", ext.lstrip(".") or "unknown"],
        )
    else:
        node.update(name=title, summary=f"Note: {title}", tags=["note"])
    return node


def parse_index_sections(index_path: Path) -> list[tuple[str, list[str]]]:
    """index.md の `##` 節ごとに、節の名前とその中の wikilink の行き先を返す。"""
    if not index_path.is_file():
        return []
    sections: list[tuple[str, list[str]]] = []
    for line in index_path.read_text(encoding="utf-8", errors="replace").splitlines():
        heading = re.match(r"^##\s+(.+)$", line)
        if heading:
            sections.append((heading.group(1).strip(), []))
        elif sections:
            sections[-1][1].extend(m.group(1).strip() for m in WIKILINK_RE.finditer(line))
    return sections


def extend(wiki: Path) -> dict:
    root = wiki.parent
    wiki_prefix = wiki.name.lower() + "/"
    manifest_path = resolve_ua_dir(wiki) / "intermediate" / "scan-manifest.json"
    if not manifest_path.is_file():
        print(f"[extend] Error: {manifest_path} がない。先にプラグインの parse-knowledge-base.py を実行する。",
              file=sys.stderr)
        sys.exit(1)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stats = manifest.setdefault("stats", {})

    # 1. 月ごとのログを外す
    dropped = {n["id"] for n in manifest.get("nodes", [])
               if n.get("type") == "article"
               and MONTHLY_LOG_RE.match(n.get("filePath", "").replace("\\", "/"))}
    nodes = [n for n in manifest.get("nodes", []) if n.get("id") not in dropped]
    edges = [e for e in manifest.get("edges", [])
             if e.get("source") not in dropped and e.get("target") not in dropped]

    node_ids = {n.get("id") for n in nodes}
    edge_keys = {(e.get("source"), e.get("target"), e.get("type")) for e in edges}
    articles = [n for n in nodes if n.get("type") == "article"]
    article_by_stem = {article_stem(n).lower(): n["id"] for n in articles}
    plugin_resolver = PluginResolver([article_stem(n) for n in articles])
    added = {"raw": 0, "daily": 0, "notes": 0, "related": 0, "cites": 0, "categorized": 0}

    def ensure_node(rel: str) -> str:
        node = source_node(root, rel)
        if node["id"] not in node_ids:
            nodes.append(node)
            node_ids.add(node["id"])
            kind = "daily" if rel.startswith("10_Daily/") else "raw" if rel.startswith("80_Raw/") else "notes"
            added[kind] += 1
        return node["id"]

    def ensure_edge(src: str, tgt: str, edge_type: str, weight: float) -> None:
        key = (src, tgt, edge_type)
        if key in edge_keys or src == tgt:
            return
        edges.append({"source": src, "target": tgt, "type": edge_type,
                      "direction": "forward", "weight": weight})
        edge_keys.add(key)
        added["cites" if edge_type == "cites" else "categorized" if edge_type == "categorized_under"
              else "related"] += 1

    def wiki_article(target: str) -> str | None:
        """`[[90_Wiki/topic/slug]]` の形なら、記事ノードの id を返す。"""
        t = normalize_target(target)
        if not t.lower().startswith(wiki_prefix):
            return None
        stem = t[len(wiki_prefix):]
        if stem.lower().endswith(".md"):
            stem = stem[:-3]
        return article_by_stem.get(stem.lower())

    # 2. 80_Raw/ の全ファイル
    raw_root = root / "80_Raw"
    if raw_root.is_dir():
        for path in sorted(raw_root.rglob("*")):
            rel_parts = path.relative_to(raw_root).parts
            if path.is_file() and not any(p.startswith(".") for p in rel_parts):
                ensure_node(path.relative_to(root).as_posix())

    # 3・4・6. 記事の wikilink と frontmatter sources
    warnings: list[str] = []
    unresolved = 0
    for node in articles:
        meta = node.get("knowledgeMeta", {})
        file_path = node.get("filePath", "")
        for target in meta.get("wikilinks", []):
            article_id = wiki_article(target)
            if article_id:
                ensure_edge(node["id"], article_id, "related", RELATED_WEIGHT)
                continue
            rel = find_repo_file(root, target)
            if rel:
                ensure_edge(node["id"], ensure_node(rel), "cites", CITE_WEIGHT)
                continue
            if plugin_resolver.resolve(target):
                continue  # プラグインが related の辺を作り済み
            unresolved += 1
            warnings.append(f"Unresolved wikilink: [[{target}]] in {file_path}")
        frontmatter = read_frontmatter(wiki / file_path)
        # プラグインは `tags: ["a", "b"]` を1つの文字列として読むので、読み直したタグに置き換える。
        fm_tags = frontmatter.get("tags", [])
        if isinstance(fm_tags, str):
            fm_tags = [fm_tags]
        tags = {t for t in node.get("tags", []) if not t.startswith("[")} | set(fm_tags)
        node["tags"] = sorted(tags)
        sources = frontmatter.get("sources", [])
        if isinstance(sources, str):
            sources = [s for s in (_scalar(p) for p in sources.split(";")) if s]
        for entry in sources:
            rel = find_repo_file(root, entry)
            if rel:
                ensure_edge(node["id"], ensure_node(rel), "cites", CITE_WEIGHT)

    # 5. index.md のカテゴリ
    article_nodes = {n["id"]: n for n in articles}
    for name, targets in parse_index_sections(wiki / "index.md"):
        topic_id = f"topic:{name.lower().replace(' ', '-')}"
        if topic_id not in node_ids:
            continue
        for target in targets:
            article_id = wiki_article(target)
            if not article_id or article_id in dropped:
                continue
            ensure_edge(article_id, topic_id, "categorized_under", CATEGORY_WEIGHT)
            article = article_nodes[article_id]
            article.setdefault("knowledgeMeta", {}).setdefault("category", name)
            tags = article.setdefault("tags", [])
            if name.lower() not in tags:
                tags.append(name.lower())
                tags.sort()

    # 6. 被リンクを数え直す
    backlinks: dict[str, list[str]] = {}
    for edge in edges:
        if edge.get("type") == "related":
            backlinks.setdefault(edge["target"], []).append(edge["source"])
    for node in articles:
        node.setdefault("knowledgeMeta", {})["backlinks"] = backlinks.get(node["id"], [])

    manifest["nodes"] = nodes
    manifest["edges"] = edges
    manifest["warnings"] = warnings[:MAX_WARNINGS]
    stats["articles"] = len(articles)
    stats["unresolved"] = unresolved
    stats["sources"] = sum(1 for n in nodes if n.get("type") == "source")
    stats["daily"] = sum(1 for n in nodes if n.get("id", "").startswith("source:10_Daily/"))

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[extend] -{len(dropped)} monthly logs; +{added['raw']} raw, +{added['daily']} daily, "
          f"+{added['notes']} notes; +{added['related']} related, +{added['cites']} cites, "
          f"+{added['categorized']} categorized; articles {stats['articles']}, "
          f"sources {stats['sources']}, unresolved {stats['unresolved']}", file=sys.stderr)
    print(f"[extend] Output: {manifest_path}", file=sys.stderr)
    return manifest


def main() -> None:
    wiki = Path(sys.argv[1] if len(sys.argv) > 1 else "90_Wiki").resolve()
    if not wiki.is_dir():
        print(f"[extend] Error: {wiki} is not a directory", file=sys.stderr)
        sys.exit(1)
    extend(wiki)


if __name__ == "__main__":
    main()
