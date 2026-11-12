#!/usr/bin/env python3
"""LLM wiki（activity-logs-wiki 版）の機械的な根拠チェック。

レポートだけを出力し、ファイルは一切変更しない。次の4つを調べる。

1. 資料への忠実さ: 各 wiki 記事から候補リテラル（具体的な数値、ISO 形式の
   日付、直接の引用）を抜き出し、その記事の frontmatter `sources` にある
   ファイルの本文に、そのままの形で載っているかを確かめる。見つからない
   ものを「疑い」として一覧にする。自分で計算した値、製品名、意図的な
   言い換えも疑いに出る。それをどう判断するかは読み手の仕事で、この
   スクリプトの仕事ではない。
2. 根拠エラー: そもそも確かめられない記事。アーカイブ以外の記事で
   `sources` がない、パスが解決できない、許可された情報源ディレクトリ
   （80_Raw/・10_Daily/・40_Notes/）の外を指している、のいずれか。
3. 図の点検: 記事が画像リンク（`![...](*.svg)`）で参照する図について、
   ファイルがあるか、直後に `> [図の説明]` ブロックがあるか、SVG に中身の
   ある `<title>` と `<desc>` があるかを調べる。どの記事からも参照されて
   いない 90_Wiki/ の SVG も一覧にする。図の `<title>`・`<desc>`・`<text>`
   にある数値・日付は、記事本文と同じく `sources` と照合し、見つからない
   ものは「忠実さの疑い」に出す（アーカイブページは照合しない）。
4. 一覧: どの記事の `sources` からも参照されていない 80_Raw/ のファイル。
   ログで「新規知見なし」とした取り込みのファイルは除く。

候補の範囲（閉じた集合として固定）:
- 15 文字以上の引用（"…"、“…”、「…」、『…』で囲んだ部分と、本文の引用ブロック）
- ISO 形式の日付（YYYY-MM-DD、YYYY-MM）
- 具体的な数値: 3 桁区切り（10,000）、ドット区切り（2.1.80、3.14）、
  接尾辞付き（42K、99.9%）、4 桁以上（2026）
小さな整数（"42"、"500"）や特殊な形（符号、通貨、文章で書いた日付、
漢数字や「万」などの単位）はあえて調べない。それらは「書く前に確かめる」
規則と、判断によるレビューで扱う。新しい書き方への対応は、正規表現では
なくこの docstring の一覧を広げて行う。

照合の前に、記事と資料の両方を Unicode NFKC で正規化する（全角数字や
全角カンマを半角にそろえる）。HTML コメント、インラインコード、wikilink、
状態ブロック（> **要確認…** / > **更新済み…** / > **仮説…**）、
補足ブロック（> [Claude補足] …）は候補から除く。図の説明ブロック
（> [図の説明] …）は原文の引用ではないので、ブロック全体を引用の候補に
しない。ただし中の数値・日付・括弧付きの引用は、段落と同じく候補にする。

終了コードは情報を持たない。レポートが唯一の出力である。

使い方: check_evidence.py [project-root] [article.md ...]
既定: project-root はカレントディレクトリ。90_Wiki/**/*.md のうち
index.md・log.md・月ごとのログ（YYYY/MM.md）を除くすべての記事を調べる。記事のパスは絶対パスでも
project-root からの相対パスでもよい。

元の実装: https://github.com/astro-han/karpathy-llm-wiki（MIT License）
"""

import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

WIKI_DIR = "90_Wiki"
RAW_DIR = "80_Raw"
SOURCE_DIRS = ("80_Raw", "10_Daily", "40_Notes")

NUMBER_TOKEN_RE = re.compile(
    r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)*(?:\s*[KMB%](?![A-Za-z]))?"
    r"|\d+(?:\.\d+)*(?:\s*[KMB%](?![A-Za-z]))?)(?![A-Za-z])"
)
SUFFIX_RE = re.compile(r"[KMB%]$")
DATE_RE = re.compile(r"\d{4}-\d{2}(?:-\d{2})?")
QUOTE_RES = [
    re.compile(r'"([^"\n]*)"'),
    re.compile(r"“([^”\n]*)”"),
    re.compile(r"「([^」\n]*)」"),
    re.compile(r"『([^』\n]*)』"),
]
STATUS_LINE_RE = re.compile(r"^>\s*(?:\*\*\s*(?:要確認|更新済み|仮説)|\[Claude補足\])")
FIGURE_LINE_RE = re.compile(r"^>\s*\[図の説明\]")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SVG_NS = "{http://www.w3.org/2000/svg}"
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
WIKILINK_RE = re.compile(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
NO_MATERIAL_HEADING_RE = re.compile(
    r"^## \[[^\]]*\]\s*ingest\s*\|\s*新規知見なし[:：]\s*(\S+)", re.IGNORECASE
)
FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
WS_RE = re.compile(r"\s+")

SKIP_FILES = {"index.md", "log.md"}
MONTHLY_LOG_RE = re.compile(r"^\d{4}/\d{2}\.md$")


@dataclass(frozen=True)
class Document:
    meta: dict
    title: str | None
    body: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    kind: str
    value: str


def nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def normalize(text: str) -> str:
    return WS_RE.sub(" ", nfkc(text)).strip()


def _scalar(value: str) -> str:
    value = value.strip()
    if value[:1] in {'"', "'"}:
        quote = value[0]
        end = value.find(quote, 1)
        return value[1:end] if end > 0 else value[1:]
    # 引用符で囲まれていない値は、" #" 以降をコメントとして捨てる
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def split_frontmatter(text: str) -> tuple[dict, str]:
    """先頭の YAML frontmatter を簡易に解析し、(meta, 本文) を返す。

    PyYAML には頼らない。対応するのは `key: value`、
    `key: [a, b]`、`key:` に続く `  - item` のブロックリストだけ。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in {"---", "..."}:
            end = i
            break
    if end is None:
        return {}, text

    meta: dict = {}
    current_list: str | None = None
    for line in lines[1:end]:
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
        rest_no_comment = _scalar(rest) if rest[:1] not in {"["} else rest
        if not rest_no_comment:
            meta[key] = []
            current_list = key
        elif rest.startswith("["):
            inner = rest[1 : rest.rfind("]")] if "]" in rest else rest[1:]
            meta[key] = [v for v in (_scalar(p) for p in inner.split(",")) if v]
            current_list = None
        else:
            meta[key] = rest_no_comment
            current_list = None
    return meta, "\n".join(lines[end + 1 :])


def fence_opener(line: str) -> tuple[str, int] | None:
    m = FENCE_OPEN_RE.match(line)
    if not m:
        return None
    marker, info = m.groups()
    if marker[0] == "`" and "`" in info:
        return None
    return marker[0], len(marker)


def is_fence_closer(line: str, char: str, length: int) -> bool:
    m = FENCE_CLOSE_RE.match(line)
    return bool(m and m.group(1)[0] == char and len(m.group(1)) >= length)


def parse_document(text: str) -> Document:
    """frontmatter、表示上のタイトル（最初の H1）、本文を返す。

    HTML コメントとフェンス付きコードブロックは本文から除く。
    """
    meta, rest = split_frontmatter(text)
    rest = HTML_COMMENT_RE.sub("", rest)
    title = None
    body = []
    fence_char = None
    fence_len = 0
    for line in rest.splitlines():
        if fence_char:
            if is_fence_closer(line, fence_char, fence_len):
                fence_char = None
            continue
        opener = fence_opener(line)
        if opener:
            fence_char, fence_len = opener
            continue
        if title is None and line.startswith("# "):
            title = line
            continue
        body.append(line)
    return Document(meta, title, tuple(body))


def strip_fences(text: str) -> str:
    """標準的な Markdown のフェンス付きコードブロックを除く。"""
    out = []
    fence_char = None
    fence_len = 0
    for line in text.splitlines():
        if fence_char:
            if is_fence_closer(line, fence_char, fence_len):
                fence_char = None
            continue
        opener = fence_opener(line)
        if opener:
            fence_char, fence_len = opener
            continue
        out.append(line)
    return "\n".join(out)


def strip_noise(text: str) -> str:
    text = INLINE_CODE_RE.sub(" ", text)
    # wikilink はパス（10_Daily/2026/10/20 など）を候補にしないよう除く。
    # 別名（[[path|別名]]）があれば別名だけを残す。
    text = WIKILINK_RE.sub(lambda m: m.group(2) or " ", text)
    text = LINK_RE.sub(r"\1", text)
    return text


def keep_number(token: str) -> bool:
    token = token.strip()
    if SUFFIX_RE.search(token) or "," in token or "." in token:
        return True
    return len(token) >= 4


def extract_numeric_date_candidates(line: str) -> list[Candidate]:
    line = strip_noise(line)
    date_matches = list(DATE_RE.finditer(line))
    candidates = [Candidate("date", m.group(0)) for m in date_matches]
    number_text = list(line)
    for match in date_matches:
        number_text[match.start() : match.end()] = " " * (match.end() - match.start())
    candidates.extend(
        Candidate("number", m.group(0))
        for m in NUMBER_TOKEN_RE.finditer("".join(number_text))
        if keep_number(m.group(0))
    )
    return candidates


def extract_candidates(text: str) -> list[Candidate]:
    document = parse_document(nfkc(text))
    lines = ([document.title] if document.title else []) + list(document.body)
    candidates: list[Candidate] = []
    skip_status_block = False
    blockquote: list[str] = []
    paragraph: list[str] = []

    def flush_blockquote():
        if blockquote:
            joined = normalize(" ".join(blockquote))
            if len(joined) >= 15:
                candidates.append(Candidate("quote", joined))
            blockquote.clear()

    def flush_paragraph():
        if paragraph:
            joined = normalize(" ".join(paragraph))
            for quote_re in QUOTE_RES:
                candidates.extend(
                    Candidate("quote", m.group(1))
                    for m in quote_re.finditer(joined)
                    if len(m.group(1).strip()) >= 15
                )
            paragraph.clear()

    in_figure_block = False
    for line in lines:
        stripped = line.strip()
        if STATUS_LINE_RE.match(stripped):
            flush_blockquote()
            flush_paragraph()
            in_figure_block = False
            skip_status_block = True
            continue
        if skip_status_block:
            if stripped.startswith(">"):
                continue
            skip_status_block = False
        # 図の説明は原文の引用ではない。段落として扱い、数値・日付・
        # 括弧付きの引用だけを候補にする。
        if FIGURE_LINE_RE.match(stripped):
            flush_blockquote()
            flush_paragraph()
            in_figure_block = True
            figure_text = FIGURE_LINE_RE.sub("", stripped).strip()
        elif in_figure_block and stripped.startswith(">"):
            figure_text = stripped.lstrip(">").strip()
        else:
            if in_figure_block:
                flush_paragraph()
                in_figure_block = False
            figure_text = None
        if figure_text is not None:
            if figure_text:
                content = strip_noise(figure_text)
                candidates.extend(extract_numeric_date_candidates(content))
                paragraph.append(content)
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            content = strip_noise(stripped.lstrip(">").strip())
            blockquote.append(content)
            candidates.extend(extract_numeric_date_candidates(content))
            continue
        flush_blockquote()
        if not stripped:
            flush_paragraph()
            continue
        line = strip_noise(line)
        candidates.extend(extract_numeric_date_candidates(line))
        paragraph.append(line)
    flush_blockquote()
    flush_paragraph()
    seen = set()
    unique = []
    for candidate in candidates:
        value = candidate.value.strip().strip(".,;:()[]、。")
        candidate = Candidate(candidate.kind, value)
        if value and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def sources_of(meta: dict) -> list[str]:
    value = meta.get("sources", [])
    if isinstance(value, str):
        value = [v for v in (_scalar(p) for p in value.split(";")) if v]
    return [v.strip().strip("[]").replace("\\", "/") for v in value if v.strip()]


def resolve_source(root: Path, entry: str) -> Path:
    """sources の1件を絶対パスにする。拡張子がなければ .md を補う。"""
    path = Path(entry)
    if not path.is_absolute():
        path = root / path
    if path.suffix == "":
        path = path.with_suffix(".md")
    return path.resolve()


def contains(haystack: str, candidate: Candidate) -> bool:
    if candidate.kind == "quote":
        return candidate.value in haystack
    # 値は単独で現れなければならない。文の句読点は前後にあってよい。
    # 月（YYYY-MM）が完全な ISO 日付の先頭部分として一致してはいけない。
    right = r"(?!-\d{2})" if candidate.kind == "date" and len(candidate.value) == 7 else ""
    pattern = (
        r"(?<![\d.,])" + re.escape(candidate.value) + right + r"(?![A-Za-z0-9]|[.,]\d|%)"
    )
    return re.search(pattern, haystack) is not None


def source_content(path: Path) -> str:
    """frontmatter を除いた資料の本文。収集情報（source / collected /
    published）は記録用であって根拠ではない。これと一致させると、日付や
    年を誤って合格にしてしまう。"""
    _, body = split_frontmatter(path.read_text(encoding="utf-8"))
    return normalize(body)


def is_archive(meta: dict) -> bool:
    return str(meta.get("type", "")).strip().lower() == "archive"


@dataclass(frozen=True)
class Figure:
    target: str  # 記事に書かれたリンク先
    path: Path
    described: bool  # 直後に > [図の説明] があるか


def figure_refs(article: Path, text: str) -> list[Figure]:
    """記事が画像リンクで参照する SVG 図の一覧。リンク先は記事からの相対パス。"""
    lines = list(parse_document(text).body)
    figures = []
    for i, line in enumerate(lines):
        for m in IMAGE_RE.finditer(INLINE_CODE_RE.sub(" ", line)):
            target = m.group(1)
            if URL_SCHEME_RE.match(target) or not target.lower().endswith(".svg"):
                continue
            following = next((l.strip() for l in lines[i + 1 :] if l.strip()), "")
            figures.append(
                Figure(
                    target,
                    (article.parent / unquote(target)).resolve(),
                    bool(FIGURE_LINE_RE.match(following)),
                )
            )
    return figures


def svg_text(element: ET.Element) -> str:
    return normalize("".join(element.itertext()))


def inspect_figure(figure: Figure) -> tuple[list[str], list[str]]:
    """1つの図について (問題, 照合する文字列) を返す。

    照合する文字列は `<title>`・`<desc>`・`<text>` の中身。
    """
    if not figure.path.is_file():
        return [f"{figure.target}: ファイルがない"], []
    problems = []
    if not figure.described:
        problems.append(f"{figure.target}: 直後に > [図の説明] がない")
    try:
        svg = ET.parse(figure.path).getroot()
    except (ET.ParseError, OSError) as e:
        return problems + [f"{figure.target}: SVG として読めない（{e}）"], []
    texts = []
    for tag in ("title", "desc"):
        element = svg.find(SVG_NS + tag)
        if element is None or not svg_text(element):
            problems.append(f"{figure.target}: <{tag}> がない、または空")
        else:
            texts.append(svg_text(element))
    texts.extend(t for t in (svg_text(e) for e in svg.iter(SVG_NS + "text")) if t)
    return problems, texts


def check_article(article: Path, root: Path) -> tuple[list[str], list[str], list[str]]:
    """1つの記事について (忠実さの疑い, 根拠エラー, 図の問題) を返す。"""
    text = article.read_text(encoding="utf-8")
    meta, _ = split_frontmatter(text)
    figure_problems = []
    figure_texts = []
    for figure in figure_refs(article, text):
        problems, texts = inspect_figure(figure)
        figure_problems.extend(problems)
        figure_texts.extend((figure.target, t) for t in texts)
    if is_archive(meta):
        return [], [], figure_problems
    entries = sources_of(meta)
    if not entries:
        return [], ["sources がない"], figure_problems
    allowed = [(root / d).resolve() for d in SOURCE_DIRS]
    raws = []
    errors = []
    for entry in entries:
        target = resolve_source(root, entry)
        if not any(target.is_relative_to(d) for d in allowed):
            errors.append(f"情報源ディレクトリ外を指している: {entry}")
        elif not target.is_file():
            errors.append(f"解決できないパス: {entry}")
        else:
            raws.append(source_content(target))
    misses = []
    if raws:
        for candidate in extract_candidates(text):
            candidate = Candidate(candidate.kind, normalize(candidate.value))
            if not any(contains(raw, candidate) for raw in raws):
                misses.append(candidate.value)
        seen = set()
        for target, figure_text in figure_texts:
            for candidate in extract_numeric_date_candidates(figure_text):
                value = candidate.value.strip().strip(".,;:()[]、。")
                candidate = Candidate(candidate.kind, value)
                if not value or (target, candidate) in seen:
                    continue
                seen.add((target, candidate))
                if not any(contains(raw, candidate) for raw in raws):
                    misses.append(f"{value}（図 {target}）")
    return misses, errors, figure_problems


def is_log_file(rel: str) -> bool:
    """90_Wiki/ からの相対パスが log.md か月ごとのログ（YYYY/MM.md）なら True。"""
    return rel == "log.md" or bool(MONTHLY_LOG_RE.match(rel))


def iter_articles(wiki_dir: Path):
    for path in sorted(wiki_dir.rglob("*.md")):
        rel = path.relative_to(wiki_dir).as_posix()
        if rel not in SKIP_FILES and not is_log_file(rel):
            yield path


def no_material_paths(log_file: Path) -> set[str]:
    if not log_file.is_file():
        return set()
    paths = set()
    text = strip_fences(log_file.read_text(encoding="utf-8"))
    for line in text.splitlines():
        m = NO_MATERIAL_HEADING_RE.match(line)
        if m:
            paths.add(m.group(1).strip("`,;.").replace("\\", "/"))
    return paths


def referenced_sources(root: Path) -> set[Path]:
    referenced = set()
    for article in iter_articles(root / WIKI_DIR):
        meta, _ = split_frontmatter(article.read_text(encoding="utf-8"))
        for entry in sources_of(meta):
            referenced.add(resolve_source(root, entry))
    return referenced


def unreferenced_raws(root: Path) -> list[str]:
    raw_dir = root / RAW_DIR
    if not raw_dir.is_dir():
        return []
    referenced = referenced_sources(root)
    wiki_dir = root / WIKI_DIR
    disposed = set()
    for log_file in sorted(wiki_dir.rglob("*.md")):
        if is_log_file(log_file.relative_to(wiki_dir).as_posix()):
            disposed |= no_material_paths(log_file)
    missing = []
    for path in sorted(raw_dir.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if path.resolve() not in referenced and rel not in disposed:
            missing.append(rel)
    return missing


def unreferenced_figures(root: Path) -> list[str]:
    """どの記事からも画像リンクで参照されていない 90_Wiki/ の SVG。"""
    wiki_dir = root / WIKI_DIR
    referenced = set()
    for article in iter_articles(wiki_dir):
        text = article.read_text(encoding="utf-8")
        referenced.update(figure.path for figure in figure_refs(article, text))
    return [
        path.relative_to(root).as_posix()
        for path in sorted(wiki_dir.rglob("*.svg"))
        if path.resolve() not in referenced
    ]


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    wiki_dir = root / WIKI_DIR
    if not wiki_dir.is_dir():
        print(f"{root} の下に {WIKI_DIR}/ ディレクトリがない")
        return 1

    articles = []
    for arg in argv[2:]:
        path = Path(arg)
        if not path.is_absolute():
            path = root / path
        try:
            if path.resolve().relative_to(wiki_dir.resolve()).as_posix() in SKIP_FILES:
                print(f"警告: {arg} は索引かログなので飛ばす", file=sys.stderr)
                continue
        except ValueError:
            pass
        if not path.is_file():
            print(f"警告: 記事が見つからない: {arg}", file=sys.stderr)
            continue
        articles.append(path)
    if len(argv) <= 2:
        articles = list(iter_articles(wiki_dir))

    results = {}
    for article in articles:
        results[article] = check_article(article, root)

    def label(article: Path) -> str:
        try:
            return article.resolve().relative_to(root).as_posix()
        except ValueError:
            return str(article)

    print("# 根拠チェック\n")
    print("## 忠実さの疑い")
    suspect_count = 0
    for article, (misses, _, _) in results.items():
        if misses:
            print(f"\n{label(article)}")
            for miss in misses:
                print(f"- {miss}")
                suspect_count += 1
    if suspect_count == 0:
        print("\n(なし)")

    print("\n## 根拠エラー")
    error_count = 0
    for article, (_, errors, _) in results.items():
        if errors:
            print(f"\n{label(article)}")
            for error in errors:
                print(f"- {error}")
                error_count += 1
    if error_count == 0:
        print("(なし)")

    print("\n## 図の点検")
    figure_count = 0
    for article, (_, _, problems) in results.items():
        if problems:
            print(f"\n{label(article)}")
            for problem in problems:
                print(f"- {problem}")
                figure_count += 1
    unused_figures = unreferenced_figures(root)
    if unused_figures:
        print("\nどの記事からも参照されていない図")
        for path in unused_figures:
            print(f"- {path}")
            figure_count += 1
    if figure_count == 0:
        print("(なし)")

    print(f"\n## 参照されていない {RAW_DIR} ファイル")
    orphans = unreferenced_raws(root)
    for path in orphans:
        print(f"- {path}")
    if not orphans:
        print("(なし)")

    print(
        f"\n## まとめ\n忠実さの疑い {suspect_count} 件、"
        f"根拠エラー {error_count} 件、図の問題 {figure_count} 件、"
        f"参照されていない資料 {len(orphans)} 件"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
