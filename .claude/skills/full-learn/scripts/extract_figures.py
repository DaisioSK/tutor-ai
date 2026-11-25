#!/usr/bin/env python3
"""
extract_figures.py — 从课件 PDF 里裁出"图"(不是整页截图), 供 teach 正文直接嵌入。

与 extract.py 的分工:
  extract.py       → 文本层 + 图重页整页截图 (raw/visuals/), 服务于 scan 的知识提取
  extract_figures  → 逐页定位图形区域(位图 / 矢量簇 + 贴边标签文字), 裁成独立 PNG (raw/figures/),
                     服务于 story 的"课件原图优先于自绘"

用法:
  extract_figures.py <course_dir> <output_raw_dir> [--only <子串>] [--dpi 220]

产出:
  raw/figures/<stem>_p<N>_f<k>.png
  raw/_figures.json  — 每张图: 源文件/页码/序号/类型/bbox/占页比/框内文字/是否疑似表格
只读 PDF, 不改 raw/*.txt 与 _manifest.json, 可随时重跑。
"""
import json
import os
import re
import sys
from collections import Counter

# 判定阈值 (单位: 页面面积比例 或 pt)
MIN_FIGURE_AREA_RATIO = 0.03      # 小于页面 3% 的区域不算图 (logo / 项目符号 / 小图标)
FULLPAGE_AREA_RATIO = 0.85        # 大于 85% 视为整页即一张图
TEMPLATE_PAGE_RATIO = 0.5         # 同一位置在 ≥50% 页面重复出现的位图/路径 = 模板 (logo / 页脚线)
BOILERPLATE_MIN_PAGES = 6
CLUSTER_GAP_PT = 14               # 矢量路径间距 ≤ 此值视为同一张图
LABEL_GAP_PT = 10                 # 文字块与图形距离 ≤ 此值视为图内标签
LABEL_MAX_AREA_RATIO = 0.12       # 大于此面积的文字块是正文/标题, 不并入图
LABEL_MAX_WIDTH_RATIO = 0.3       # 窄于页宽 30% 的文字块只要贴边就并入图 (标签/图注)
LABEL_MIN_OVERLAP = 0.5           # 更宽的文字块须有 ≥50% 面积落在图内才并入 (防吞掉标题/正文行)
TEXTBOX_MAX_PATHS = 6             # 矢量路径 < 此值、且一条路径就占了簇面积 ≥85%、且文字多 → 带边框的文字框, 不是图
TEXTBOX_MIN_CHARS = 80
TEXTBOX_DOMINANT_PATH = 0.85
MIN_VECTOR_PATHS = 3              # 独立矢量簇至少几条路径才算图 (排除单条分隔线)
TABLE_TEXT_DENSITY = 0.0035       # 框内 字符数/面积(pt²) 超过此值 → 疑似表格, 提示改抄成 Markdown 表
PAD_PT = 6
MERGE_PASSES = 3


def _round_rect(r, q=4):
    return tuple(int(round(v / q)) for v in r)


def _expand(r, d):
    return (r[0] - d, r[1] - d, r[2] + d, r[3] + d)


def _intersects(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _union(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _merge_clusters(items, gap):
    """items: [(rect, payload_list)] → 反复合并相距 ≤gap 的矩形。"""
    changed = True
    while changed:
        changed = False
        out = []
        while items:
            r, pl = items.pop()
            merged = False
            for j, (r2, pl2) in enumerate(out):
                if _intersects(_expand(r, gap), r2):
                    out[j] = (_union(r, r2), pl + pl2)
                    merged = changed = True
                    break
            if not merged:
                out.append((r, pl))
        items = out
    return items


def _subtract(box, blockers):
    """从 box 里挖掉所有 blockers, 返回剩下的若干矩形 (可能为空)。
    用来保证"涂白只发生在空白处": 页脚那条横带照涂, 但压在图形上的那一段会被挖掉。"""
    parts = [box]
    for bl in blockers:
        nxt = []
        for p in parts:
            if not _intersects(p, bl):
                nxt.append(p)
                continue
            ix0, iy0 = max(p[0], bl[0]), max(p[1], bl[1])
            ix1, iy1 = min(p[2], bl[2]), min(p[3], bl[3])
            if p[1] < iy0:  nxt.append((p[0], p[1], p[2], iy0))   # 上
            if iy1 < p[3]:  nxt.append((p[0], iy1, p[2], p[3]))   # 下
            if p[0] < ix0:  nxt.append((p[0], iy0, ix0, iy1))     # 左
            if ix1 < p[2]:  nxt.append((ix1, iy0, p[2], iy1))     # 右
        parts = [q for q in nxt if q[2] - q[0] > 0.5 and q[3] - q[1] > 0.5]
        if not parts:
            break
    return parts


def _mask_foreign_text(png_path, clip, rect, blocks, page_width, dpi, boilerplate=(), ink=()):
    """把裁框里不属于这张图的文字涂白:
    ① 邻栏正文露出的半个字 (宽块, 落在图形边界之外);
    ② 被裁框切断的宽文字块 (常见于页面标题的下半行) —— 它本来就已经残缺, 留着更糟;
    ③ 页眉页脚模板行 (在 ≥50% 页面重复出现)。
    窄块是图内标签, 一律不动。

    **涂白只许发生在空白处**: `ink` 是这张图自己的矢量/位图矩形, 任何与它相交的涂白框
    一律丢弃。没有这道闸门时, 一个"宽且被裁框切断"的图内标签块 (如 L3 p15 那张
    arrival rate → CPU 图里横跨整图的标注行) 会让 ② 把大半张图刷成白色矩形 ——
    读者看到的就是图被一块实心白挡住。宁可漏掉一个边角的脏字, 不可盖住图。"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    clip_t = tuple(clip)
    scale = dpi / 72.0
    ink = [tuple(r) for r in ink]
    boxes = []
    for br, txt in blocks:
        if not _intersects(clip_t, br):
            continue
        inter = (max(clip_t[0], br[0]), max(clip_t[1], br[1]), min(clip_t[2], br[2]), min(clip_t[3], br[3]))
        if any(ln.strip() in boilerplate for ln in txt.splitlines() if ln.strip()):
            boxes.append(inter)                       # ③ 页眉页脚模板行
            continue
        if (br[2] - br[0]) <= page_width * LABEL_MAX_WIDTH_RATIO:
            continue                                  # 窄块 = 图内标签
        cut = (br[0] < clip_t[0] - 0.5 or br[1] < clip_t[1] - 0.5
               or br[2] > clip_t[2] + 0.5 or br[3] > clip_t[3] + 0.5)
        if cut:
            boxes.append(inter)                       # ② 被裁框切断的宽块
            continue
        if _area(inter) >= _area(br) * 0.5:
            continue                                  # 已并入图的块
        cx, cy = (br[0] + br[2]) / 2, (br[1] + br[3]) / 2
        # 涂白整条边距带 (裁框边 → 图形边), 字形常溢出文字块的报告边界
        if cx < rect[0]:   boxes.append((clip_t[0], inter[1], rect[0], inter[3]))
        elif cx > rect[2]: boxes.append((rect[2], inter[1], clip_t[2], inter[3]))
        elif cy < rect[1]: boxes.append((inter[0], clip_t[1], inter[2], rect[1]))
        elif cy > rect[3]: boxes.append((inter[0], rect[3], inter[2], clip_t[3]))
    boxes = [b for b in boxes if b[2] > b[0] and b[3] > b[1]]
    # 闸门 1: 把压在图自己墨迹上的部分挖掉 (页脚横带只剩图形之外的两段)
    boxes = [p for b in boxes for p in _subtract(b, ink)]
    # 闸门 2: 挖完之后涂白总面积仍超过裁框 25% —— 说明判断本身出错了, 什么都不涂
    if sum(_area(b) for b in boxes) > _area(clip_t) * 0.25:
        print(f"  ⚠ 跳过涂白 (面积超 25%): {os.path.basename(png_path)}", file=sys.stderr)
        return
    if not boxes:
        return
    im = Image.open(png_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    for b in boxes:
        draw.rectangle([(b[0] - clip_t[0]) * scale, (b[1] - clip_t[1]) * scale,
                        (b[2] - clip_t[0]) * scale, (b[3] - clip_t[1]) * scale], fill="white")
    im.save(png_path)


def slugify_stem(rel):
    """PDF 相对路径 -> 可安全放进 Markdown 图片路径的文件名前缀。

    课件文件名常带空格和连字符 (「CS1234 -- Lecture 2.pdf」), 直接拼进
    `![](../raw/figures/…)` 会被 Markdown 解析断掉, 图就不显示。
    这里统一压成 [A-Za-z0-9_-]: 空白折成一个 _, 其余非法字符丢掉,
    再把重复的 _ / - 收敛。已经安全的名字 (lectures_L1-Introduction) 原样不变。
    """
    stem = os.path.splitext(rel)[0].replace(os.sep, "_")
    stem = re.sub(r"\s+", "_", stem.strip())
    stem = re.sub(r"[^A-Za-z0-9_-]", "", stem)
    stem = re.sub(r"_{2,}", "_", stem)
    stem = re.sub(r"-{2,}", "-", stem)
    return stem.strip("_-") or "fig"


def extract_pdf_figures(filepath, figures_dir, stem, dpi):
    import fitz
    doc = fitz.open(filepath)
    n_pages = len(doc)
    page_rect = doc[0].rect
    page_area = _area(tuple(page_rect))

    # 第一遍: 统计模板元素 (同位置重复出现的位图/路径)
    page_bitmaps, page_paths = [], []
    bm_freq, path_freq = Counter(), Counter()
    for page in doc:
        bms = [tuple(info["bbox"]) for info in page.get_image_info()]
        paths = [tuple(d["rect"]) for d in page.get_drawings()]
        page_bitmaps.append(bms)
        page_paths.append(paths)
        bm_freq.update({_round_rect(r) for r in bms})
        path_freq.update({_round_rect(r) for r in paths})
    line_freq = Counter()
    for page in doc:
        line_freq.update({ln.strip() for b in page.get_text("blocks") if b[6] == 0
                          for ln in b[4].splitlines() if ln.strip()})
    boilerplate = {ln for ln, c in line_freq.items()
                   if c >= n_pages * TEMPLATE_PAGE_RATIO} if n_pages >= BOILERPLATE_MIN_PAGES else set()

    template_bm, template_path = set(), set()
    if n_pages >= BOILERPLATE_MIN_PAGES:
        template_bm = {k for k, c in bm_freq.items() if c >= n_pages * TEMPLATE_PAGE_RATIO}
        template_path = {k for k, c in path_freq.items() if c >= n_pages * TEMPLATE_PAGE_RATIO}

    figures = []
    for pno, page in enumerate(doc):
        page_num = pno + 1
        items = []
        for r in page_bitmaps[pno]:
            if _round_rect(r) in template_bm or _area(r) < page_area * 0.002:
                continue
            items.append((r, [("bitmap", r)]))
        for r in page_paths[pno]:
            if _round_rect(r) in template_path:
                continue
            if _area(r) > page_area * 0.9:          # 整页背景色块
                continue
            if (r[2] - r[0]) > page_rect.width * 0.7 or (r[3] - r[1]) > page_rect.height * 0.7:
                continue                              # 跨页宽/高的分隔线、装饰边框, 会把不相干的元素连成一簇
            items.append((r, [("path", r)]))
        if not items:
            continue

        clusters = _merge_clusters(items, CLUSTER_GAP_PT)

        # 吸附贴边标签文字 (小文字块), 多轮直到稳定
        blocks = [(tuple(b[:4]), b[4]) for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
        final = []
        for rect, payload in clusters:
            n_bitmap = sum(1 for k, _ in payload if k == "bitmap")
            n_path = sum(1 for k, _ in payload if k == "path")
            max_path_area = max((_area(r) for k, r in payload if k == "path"), default=0.0)
            if n_bitmap == 0 and n_path < MIN_VECTOR_PATHS:
                continue
            for _ in range(MERGE_PASSES):
                grown = False
                for br, _txt in blocks:
                    if _area(br) > page_area * LABEL_MAX_AREA_RATIO:
                        continue
                    grown_rect = _expand(rect, LABEL_GAP_PT)
                    if not _intersects(grown_rect, br):
                        continue
                    if (br[2] - br[0]) > page_rect.width * LABEL_MAX_WIDTH_RATIO:
                        inter = (max(grown_rect[0], br[0]), max(grown_rect[1], br[1]),
                                 min(grown_rect[2], br[2]), min(grown_rect[3], br[3]))
                        # 坐标轴刻度 / 图下标题: 横向居中于图、不高于两行、不比图宽多少
                        cx = (br[0] + br[2]) / 2
                        axis_like = (rect[0] <= cx <= rect[2] and (br[3] - br[1]) < 30
                                     and (br[2] - br[0]) <= (rect[2] - rect[0]) + 2 * LABEL_GAP_PT)
                        if _area(inter) < _area(br) * LABEL_MIN_OVERLAP and not axis_like:
                            continue
                    if True:
                        new = _union(rect, br)
                        if new != rect:
                            rect, grown = new, True
                if not grown:
                    break
            if _area(rect) < page_area * MIN_FIGURE_AREA_RATIO:
                continue
            final.append((rect, n_bitmap, n_path, max_path_area, [r for _k, r in payload]))

        # 吸附文字后簇可能重叠 → 再合一次
        final = _merge_clusters([(r, [(nb, np_, mpa, own)]) for r, nb, np_, mpa, own in final], 0)

        for k, (rect, pl) in enumerate(sorted(final, key=lambda x: (x[0][1], x[0][0])), 1):
            n_bitmap = sum(a for a, _, _, _ in pl)
            n_path = sum(b for _, b, _, _ in pl)
            max_path_area = max(c for _, _, c, _ in pl)
            ink = [r for _, _, _, own in pl for r in own]
            clip = fitz.Rect(*_expand(rect, PAD_PT)) & page.rect
            if clip.is_empty or clip.width < 20 or clip.height < 20:
                continue
            ratio = _area(tuple(clip)) / page_area
            clip_t = tuple(clip)
            inner_text = " ".join(
                txt.strip().replace("\n", " ") for br, txt in blocks
                if _area((max(clip_t[0], br[0]), max(clip_t[1], br[1]), min(clip_t[2], br[2]), min(clip_t[3], br[3]))) >= _area(br) * 0.5
            )
            if (n_bitmap == 0 and n_path < TEXTBOX_MAX_PATHS and len(inner_text) >= TEXTBOX_MIN_CHARS
                    and max_path_area >= _area(rect) * TEXTBOX_DOMINANT_PATH):
                continue                              # 带边框的文字框, 不是图
            kind = "fullpage" if ratio >= FULLPAGE_AREA_RATIO else ("bitmap" if n_bitmap else "vector")
            density = len(inner_text) / max(_area(tuple(clip)), 1.0)
            png = f"{stem}_p{page_num}_f{k}.png"
            pix = page.get_pixmap(clip=clip, dpi=dpi)
            out_path = os.path.join(figures_dir, png)
            pix.save(out_path)
            _mask_foreign_text(out_path, clip, rect, blocks, page_rect.width, dpi, boilerplate, ink)
            figures.append({
                "file": png, "source": os.path.basename(filepath), "page": page_num, "index": k,
                "kind": kind, "bitmaps": n_bitmap, "vector_paths": n_path,
                "bbox": [round(v, 1) for v in clip], "page_ratio": round(ratio, 3),
                "px": [pix.width, pix.height],
                "looks_like_table": bool(n_path >= 8 and density > TABLE_TEXT_DENSITY),
                "text_inside": inner_text[:300],
            })
    doc.close()
    return figures


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course_dir")
    ap.add_argument("raw_dir")
    ap.add_argument("--only", default=None, help="只处理文件名含此子串的 PDF (其余保留旧记录)")
    ap.add_argument("--dpi", type=int, default=220)
    ns = ap.parse_args()
    only, dpi = ns.only, ns.dpi
    course_dir, raw_dir = ns.course_dir, ns.raw_dir
    figures_dir = os.path.join(raw_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "_figures.json")
    existing = []
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            existing = json.load(f)

    # 跟 extract.py 保持同一套目录约定, 否则两边的 stem 对不上, teach 里的图片路径会断。
    lecture_dir = os.path.join(course_dir, "lecture")
    if os.path.isdir(lecture_dir):
        course_dir = lecture_dir

    REFERENCE_DIRS = {"references", "reference", "books", "textbooks"}
    def _is_assignment_dir(name):
        return name.lower().startswith("assignment") or name.lower() in {"labs", "lab"}
    pdfs = []
    for root, dirs, fnames in os.walk(course_dir):
        dirs[:] = [d for d in sorted(dirs)
                   if not d.startswith(".") and d.lower() not in REFERENCE_DIRS
                   and not _is_assignment_dir(d)]
        for f in sorted(fnames):
            if f.lower().endswith(".pdf") and (only is None or only in f):
                pdfs.append(os.path.relpath(os.path.join(root, f), course_dir))

    all_figs = [e for e in existing if only is not None and only not in e["source"]]
    for rel in pdfs:
        stem = slugify_stem(rel)
        for old in [f for f in os.listdir(figures_dir) if f.startswith(stem + "_p")]:
            os.remove(os.path.join(figures_dir, old))
        figs = extract_pdf_figures(os.path.join(course_dir, rel), figures_dir, stem, dpi)
        all_figs.extend(figs)
        pages = sorted({f["page"] for f in figs})
        tables = sum(1 for f in figs if f["looks_like_table"])
        print(f"  {rel}: {len(figs)} figures on {len(pages)} pages ({tables} look like tables)")

    all_figs.sort(key=lambda f: (f["source"], f["page"], f["index"]))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_figs, f, ensure_ascii=False, indent=1)
    print(f"\n→ {json_path} ({len(all_figs)} figures)")


if __name__ == "__main__":
    main()
