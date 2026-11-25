#!/usr/bin/env python3
"""
Tutor.ai — 课件内容提取脚本
提取文本 + 截图"图重页"(diagram/flowchart 等 OCR 无法覆盖的内容)。

用法:
    python extract.py <input_dir> <output_dir>

产出:
    output_dir/
    ├── *.txt              # 每个源文件的逐页文本
    ├── visuals/           # 图重页的截图 PNG
    │   └── <file>_p<N>.png
    ├── _manifest.json     # 提取记录 + 图重页清单
    └── _visual_pages.json # 需要 LLM 视觉描述的页面索引

支持: .pdf, .docx, .pptx, .md, .txt
约定: references/ books/ textbooks/ 子目录视为参考书，跳过提取但记入 manifest.skipped
依赖: pymupdf (自动安装)
"""

import sys
import os
import subprocess
import importlib
import json

# ---------------------------------------------------------------------------
# 依赖
# ---------------------------------------------------------------------------

DEPENDENCIES = {
    "fitz": "pymupdf",
    "docx": "python-docx",
    "pptx": "python-pptx",
}


def ensure_dependency(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        pip_name = DEPENDENCIES.get(import_name, import_name)
        print(f"  [setup] Installing {pip_name} ...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pip_name, "-q"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            importlib.import_module(import_name)
            return True
        except Exception as e:
            print(f"  [warn] Failed to install {pip_name}: {e}")
            return False


# ---------------------------------------------------------------------------
# PDF: 文本 + 图重页检测 + 截图
# ---------------------------------------------------------------------------

# 一页的"正文"字符数(剔除页眉页脚模板行后)低于此阈值且有图 → 判定为"图重页"，需要截图。
# 不能用原始字符数: beamer 类模板的页脚样板自身就 ≈90+ 字符，会让最图重的课件永不触发。
VISUAL_CONTENT_THRESHOLD = 300
# 模板行检测最少页数(太短的文档无法统计重复行)
BOILERPLATE_MIN_PAGES = 6
# 矢量绘图路径数达到此值视为"有图"(架构图/流程图常为纯矢量, get_images 看不见)
VECTOR_DRAWINGS_MIN = 5
# 平均每页字符低于此值 → 疑似扫描版(无文本层), 文本不可信
SCANNED_PDF_CHARS_PER_PAGE = 20
# 公式坍缩检测: 数学课件的公式页文本层常碎成一行一个符号(∑ 变 X、上下标断行、矩阵成竖排数字流),
# 字符数不少但内容不可读, 上面的正文密度判据抓不到。正文行中 ≤2 字符的短行占比达到此值 → 也视为图重页截图。
FORMULA_COLLAPSE_LINE_RATIO = 0.4
FORMULA_COLLAPSE_MIN_LINES = 8


def extract_pdf(filepath: str, visuals_dir: str, file_stem: str):
    """
    返回 (full_text, visual_pages, warnings)
    visual_pages: [{"file": "xxx_p3.png", "page": 3, "reason": "..."}]
    """
    if not ensure_dependency("fitz"):
        # fallback: 纯文本
        text = _pdf_fallback_text(filepath)
        return text, [], []

    import fitz
    import re
    from collections import Counter

    doc = fitz.open(filepath)
    raw_pages = [page.get_text().strip() for page in doc]
    n_pages = len(raw_pages)

    # 模板行 = 在 ≥50% 页面重复出现的行(页眉/页脚/作者/水印), 外加页码行。
    # 这些行不计入"正文密度"，否则图重页判定被模板字符淹没。
    page_lines = [[ln.strip() for ln in t.splitlines() if ln.strip()] for t in raw_pages]
    line_freq = Counter()
    for lines in page_lines:
        line_freq.update(set(lines))
    boilerplate = set()
    if n_pages >= BOILERPLATE_MIN_PAGES:
        boilerplate = {ln for ln, c in line_freq.items() if c >= n_pages * 0.5}
    pagenum_re = re.compile(r"^\d+\s*(/\s*\d+)?$")

    pages_text = []
    visual_pages = []
    warnings = []

    for i, page in enumerate(doc):
        page_num = i + 1
        text = raw_pages[i]
        pages_text.append(f"\n--- Page {page_num} ---\n{text}")

        content_lines = [
            ln for ln in page_lines[i]
            if ln not in boilerplate and not pagenum_re.match(ln)
        ]
        content_len = sum(len(ln) for ln in content_lines)
        has_bitmap = len(page.get_images(full=True)) > 0
        has_vector = len(page.get_drawings()) >= VECTOR_DRAWINGS_MIN
        short_lines = sum(1 for ln in content_lines if len(ln) <= 2)
        formula_collapsed = (
            len(content_lines) >= FORMULA_COLLAPSE_MIN_LINES
            and short_lines / len(content_lines) >= FORMULA_COLLAPSE_LINE_RATIO
        )
        is_visual = (
            (content_len < VISUAL_CONTENT_THRESHOLD) and (has_bitmap or has_vector)
        ) or formula_collapsed

        if is_visual:
            # 渲染为 PNG (2x 缩放保证清晰度)
            png_name = f"{file_stem}_p{page_num}.png"
            png_path = os.path.join(visuals_dir, png_name)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            pix.save(png_path)

            reason = (f"content={content_len} chars (raw {len(text)}), "
                      f"bitmap={has_bitmap}, vector={has_vector}, "
                      f"formula_collapse={formula_collapsed}")
            visual_pages.append({
                "file": png_name,
                "page": page_num,
                "source": os.path.basename(filepath),
                "text_extracted": text[:200] if text else "",
                "reason": reason,
            })

    total_chars = sum(len(t) for t in raw_pages)
    if n_pages >= 3 and total_chars / n_pages < SCANNED_PDF_CHARS_PER_PAGE:
        warnings.append(
            f"疑似扫描版 PDF (无文本层): 平均每页 {total_chars // n_pages} 字符, "
            f"提取文本不可信, 需 OCR 或依赖逐页截图"
        )

    doc.close()
    return "".join(pages_text), visual_pages, warnings


def _pdf_fallback_text(filepath: str) -> str:
    """pymupdf 不可用时的纯文本 fallback。"""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", filepath, "-"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if ensure_dependency("pdfminer"):
        from pdfminer.high_level import extract_text
        return extract_text(filepath)

    return f"[ERROR] Cannot extract PDF: {filepath}"


# ---------------------------------------------------------------------------
# DOCX / PPTX / TXT
# ---------------------------------------------------------------------------

def extract_docx(filepath: str, **_):
    if not ensure_dependency("docx"):
        return f"[ERROR] Cannot extract DOCX: {filepath}", []
    import docx
    doc = docx.Document(filepath)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return text, []


def extract_pptx(filepath: str, visuals_dir: str = "", file_stem: str = "", **_):
    """PPTX: 提取文本。注意 PPTX 无法像 PDF 一样高效截图，标记图重 slide。"""
    if not ensure_dependency("pptx"):
        return f"[ERROR] Cannot extract PPTX: {filepath}", []
    from pptx import Presentation
    prs = Presentation(filepath)
    slides = []
    visual_pages = []

    for i, slide in enumerate(prs.slides):
        slide_num = i + 1
        texts = []
        has_picture = False
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = para.text.strip()
                    if t:
                        texts.append(t)
            if shape.shape_type is not None and shape.shape_type == 13:  # picture
                has_picture = True

        text = "\n".join(texts)
        slides.append(f"\n--- Slide {slide_num} ---\n{text}")

        if has_picture and len(text) < VISUAL_CONTENT_THRESHOLD:
            visual_pages.append({
                "file": None,  # PPTX 截图需要 LibreOffice，标记但不截
                "page": slide_num,
                "source": os.path.basename(filepath),
                "text_extracted": text[:200],
                "reason": f"text={len(text)} chars, has_picture=True (PPTX, no screenshot)",
            })

    return "".join(slides), visual_pages


def extract_text_file(filepath: str, **_):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read(), []


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

EXTRACTORS = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".pptx": extract_pptx,
    ".md": extract_text_file,
    ".txt": extract_text_file,
}

SUPPORTED_EXTENSIONS = set(EXTRACTORS.keys())


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_dir> <output_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.isdir(input_dir):
        print(f"[ERROR] Input dir not found: {input_dir}")
        sys.exit(1)

    # 课件多了以后课程目录会长出 lecture/ 和 assignment*/ 两类子目录。
    # 直接递归会给 stem 加上 "lecture_" 前缀 —— 于是 raw/*.txt 和 raw/figures/*.png
    # 全部改名, 已写好的 teach MD 里的图片路径集体失效。
    # 所以: 有 lecture/ 就把它当课件根, stem 保持跟平铺时一模一样。
    lecture_dir = os.path.join(input_dir, "lecture")
    if os.path.isdir(lecture_dir):
        print(f"[INFO] 发现 lecture/ 子目录, 以它为课件根 (assignment*/ 等同级目录不进管线)")
        input_dir = lecture_dir

    os.makedirs(output_dir, exist_ok=True)
    visuals_dir = os.path.join(output_dir, "visuals")
    os.makedirs(visuals_dir, exist_ok=True)

    # 递归扫描全部子目录。此前用非递归 listdir，漏跑一个子目录就静默漏一批课件。
    # 不支持的文件也记入 manifest，保证"没进管线的文件"可审计而不是消失。
    LLM_READABLE_EXTS = {".ipynb", ".py", ".java", ".js", ".ts", ".yml", ".yaml", ".json", ".toml"}
    # 参考书/教材放这些子目录: 几百页的书不是课件，不进教学管线（只作深度提示指向），但要记入 manifest 可审计
    REFERENCE_DIRS = {"references", "reference", "books", "textbooks"}
    # 作业目录是待完成的代码/题面, 归 assignment 命令管; 混进 lecture 管线会
    # 被当成课件建 KP、截图, 而且指导书页码会污染「课件对照表」的页码溯源。
    def _is_assignment_dir(name):
        return name.lower().startswith("assignment") or name.lower() in {"labs", "lab"}
    files = []
    skipped = []
    for root, dirs, fnames in os.walk(input_dir):
        kept = []
        for d in sorted(dirs):
            if d.startswith("."):
                continue
            if d.lower() in REFERENCE_DIRS:
                for rf in sorted(os.listdir(os.path.join(root, d))):
                    rel = os.path.relpath(os.path.join(root, d, rf), input_dir)
                    skipped.append({"file": rel, "reason": "参考书目录, 不进教学管线 (只作深度提示指向)"})
                continue
            if _is_assignment_dir(d):
                rel = os.path.relpath(os.path.join(root, d), input_dir)
                skipped.append({"file": rel + "/", "reason": "作业目录, 归 assignment 命令管, 不进 lecture 管线"})
                continue
            kept.append(d)
        dirs[:] = kept
        for f in sorted(fnames):
            if f.startswith(".") or "Zone.Identifier" in f:
                continue
            rel = os.path.relpath(os.path.join(root, f), input_dir)
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(rel)
            elif ext in LLM_READABLE_EXTS:
                skipped.append({"file": rel, "reason": f"{ext} 不走提取, LLM 直接 Read (scan Phase 1.A)"})
            else:
                skipped.append({"file": rel, "reason": f"unsupported extension: {ext or '(none)'}"})

    if not files:
        print(f"[WARN] No supported files found")
        sys.exit(0)

    print(f"Found {len(files)} files ({len(skipped)} skipped), extracting...\n")

    results = []
    all_visual_pages = []

    for rel in files:
        filepath = os.path.join(input_dir, rel)
        ext = os.path.splitext(rel)[1].lower()
        extractor = EXTRACTORS[ext]
        # 子目录文件的 stem 带上路径前缀，避免不同目录同名文件的 txt/截图互相覆盖
        file_stem = os.path.splitext(rel)[0].replace(os.sep, "_")

        try:
            res = extractor(filepath, visuals_dir=visuals_dir, file_stem=file_stem)
            text, visual_pages = res[0], res[1]
            warnings = list(res[2]) if len(res) > 2 else []
            out_path = os.path.join(output_dir, file_stem + ".txt")
            with open(out_path, "w", encoding="utf-8") as fout:
                fout.write(text)

            char_count = len(text)
            vis_count = len(visual_pages)
            all_visual_pages.extend(visual_pages)

            entry = {
                "file": rel, "chars": char_count,
                "visual_pages": vis_count, "status": "ok"
            }
            if warnings:
                entry["status"] = "warn"
                entry["warnings"] = warnings
            results.append(entry)
            vis_info = f", {vis_count} visual pages" if vis_count else ""
            print(f"  [OK] {rel} -> {char_count} chars{vis_info}")
            for w in warnings:
                print(f"  [WARN] {rel}: {w}")
        except Exception as e:
            results.append({"file": rel, "chars": 0, "visual_pages": 0, "status": f"error: {e}"})
            print(f"  [FAIL] {rel} -> ERROR: {e}")

    ok = sum(1 for r in results if r["status"] in ("ok", "warn"))
    total_chars = sum(r["chars"] for r in results)
    total_visuals = len(all_visual_pages)

    print(f"\nDone: {ok}/{len(files)} ok, {total_chars} chars, {total_visuals} visual pages")
    if skipped:
        print(f"Skipped {len(skipped)} files (recorded in manifest)")

    # Manifest
    manifest_path = os.path.join(output_dir, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fout:
        json.dump({
            "input_dir": os.path.abspath(input_dir),
            "output_dir": os.path.abspath(output_dir),
            "recursive": True,
            "files": results,
            "skipped": skipped,
            "total_chars": total_chars,
            "total_visual_pages": total_visuals,
        }, fout, ensure_ascii=False, indent=2)

    # Visual pages index (供 LLM 视觉描述使用)
    if all_visual_pages:
        vp_path = os.path.join(output_dir, "_visual_pages.json")
        with open(vp_path, "w", encoding="utf-8") as fout:
            json.dump(all_visual_pages, fout, ensure_ascii=False, indent=2)
        print(f"Visual pages index: {vp_path}")

    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
