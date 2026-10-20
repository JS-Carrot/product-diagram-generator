#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""product-diagram-generator · draw.io 结构校验与预览渲染。

用法：
    python3 check_drawio.py path/to/diagram.drawio            # 只校验
    python3 check_drawio.py path/to/diagram.drawio --preview  # 校验并生成 -preview.svg

校验项：
    根单元格 / id 唯一 / parent 引用 / source-target 引用 / 空几何
    子节点越出父容器 / 同父兄弟重叠 / 横向泳道压住标题栏 / 连边缺端点
    连边穿过无关节点 / 连边相互交叉（重叠段记为警告）

退出码：0 = 全部通过；1 = 存在错误；2 = 仅存在警告。
"""

import html
import os
import re
import sys
import xml.etree.ElementTree as ET

FONT = "PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif"


class Cell(object):
    __slots__ = ("id", "value", "style", "parent", "vertex", "edge",
                 "source", "target", "x", "y", "w", "h", "points")

    def __init__(self, el):
        self.id = el.get("id") or ""
        self.value = el.get("value") or ""
        self.style = el.get("style") or ""
        self.parent = el.get("parent") or ""
        self.vertex = el.get("vertex") == "1"
        self.edge = el.get("edge") == "1"
        self.source = el.get("source") or ""
        self.target = el.get("target") or ""
        self.x = self.y = self.w = self.h = None
        self.points = []
        geo = el.find("mxGeometry")
        if geo is not None and geo.get("width") is not None:
            self.x = float(geo.get("x", 0))
            self.y = float(geo.get("y", 0))
            self.w = float(geo.get("width"))
            self.h = float(geo.get("height"))
        if geo is not None:
            arr = geo.find("Array[@as='points']")
            if arr is not None:
                for pt in arr.findall("mxPoint"):
                    try:
                        self.points.append((float(pt.get("x", 0)),
                                            float(pt.get("y", 0))))
                    except (TypeError, ValueError):
                        pass

    # ---- 样式解析 ----
    def style_val(self, key, default=None):
        m = re.search(r"(?:^|;)\s*%s=([^;]+)" % re.escape(key), self.style)
        return m.group(1) if m else default

    def color(self, key, default):
        v = self.style_val(key)
        if v and re.match(r"^#[0-9A-Fa-f]{3,8}$", v.strip()):
            return v.strip()
        return default

    def num(self, key, default):
        v = self.style_val(key)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def is_lane(self):
        return self.vertex and "swimlane" in self.style

    def horizontal(self):
        return self.style_val("horizontal", "1") != "0"


def load(path):
    tree = ET.parse(path)
    cells = [Cell(el) for el in tree.getroot().iter("mxCell")]
    return cells


def abs_pos(cell, by_id, cache):
    """返回绝对坐标 (x, y)，沿 parent 链累加。"""
    if cell.id in cache:
        return cache[cell.id]
    x = cell.x or 0.0
    y = cell.y or 0.0
    seen = set()
    p = by_id.get(cell.parent) if cell.parent else None
    while p is not None and p.id not in seen and p.x is not None:
        seen.add(p.id)
        x += p.x
        y += p.y
        p = by_id.get(p.parent) if p.parent else None
    cache[cell.id] = (x, y)
    return x, y


def validate(cells):
    errors = []
    warnings = []
    by_id = {}
    for c in cells:
        if not c.id:
            errors.append("存在没有 id 的 mxCell")
            continue
        if c.id in by_id:
            errors.append("mxCell id 重复：%s" % c.id)
        by_id[c.id] = c

    for need in ("0", "1"):
        if need not in by_id:
            errors.append('缺少根单元格 id="%s"，draw.io 将无法打开' % need)

    for c in cells:
        if c.parent and c.parent not in by_id:
            errors.append("单元格 %s 的 parent=%s 不存在" % (c.id, c.parent))
        for attr, ref in (("source", c.source), ("target", c.target)):
            if ref and ref not in by_id:
                errors.append("连边 %s 的 %s=%s 不存在" % (c.id, attr, ref))
        if c.edge and (not c.source or not c.target):
            warnings.append("连边 %s 缺少 source 或 target" % c.id)
        if c.vertex and not c.is_lane() and c.style.startswith("text") is False and c.w is None:
            errors.append("图形 %s 缺少几何尺寸" % c.id)

    cache = {}
    # 子节点越界 + 泳道标题栏遮挡
    for c in cells:
        if not c.vertex or c.w is None or not c.parent:
            continue
        p = by_id.get(c.parent)
        if p is None or not p.vertex or p.w is None:
            continue
        cx, cy = abs_pos(c, by_id, cache)
        px, py = abs_pos(p, by_id, cache)
        if cx + c.w > px + p.w + 0.5 or cy + c.h > py + p.h + 0.5:
            errors.append(
                "%s 越出父容器 %s：子 (%.0f,%.0f)+%.0fx%.0f / 父 %.0fx%.0f"
                % (c.id, p.id, cx - px, cy - py, c.w, c.h, p.w, p.h))
        if p.is_lane():
            start = p.num("startSize", 30)
            off = c.x if p.horizontal() else c.y
            axis = "x" if p.horizontal() else "y"
            if off is not None and off < start - 0.5:
                errors.append(
                    "节点 %s 的 %s=%.0f 小于泳道 startSize=%.0f，会压住标题栏"
                    % (c.id, axis, off, start))

    # 同父兄弟重叠
    groups = {}
    for c in cells:
        if c.vertex and c.w is not None and c.parent:
            groups.setdefault(c.parent, []).append(c)
    for pid, kids in groups.items():
        if len(kids) < 2:
            continue
        if any(k.is_lane() for k in kids if k.id != pid):
            continue  # 嵌套泳道另算，不做重叠判定
        for i in range(len(kids)):
            for j in range(i + 1, len(kids)):
                a, b = kids[i], kids[j]
                ax, ay = abs_pos(a, by_id, cache)
                bx, by_b = abs_pos(b, by_id, cache)
                if (ax < bx + b.w and bx < ax + a.w and
                        ay < by_b + b.h and by_b < ay + a.h):
                    errors.append("同父节点重叠：%s 与 %s" % (a.id, b.id))

    lanes = [c for c in cells if c.is_lane()]
    if not lanes:
        warnings.append("未发现 swimlane 容器，未形成泳道或层带结构")

    return errors, warnings, by_id, cache


# ---------------------------------------------------------------- 预览渲染

def strip_html(value):
    v = value.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    v = re.sub(r"<[^>]+>", "", v)
    return html.unescape(v).replace("&nbsp;", " ")


def esc_text(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------- 走线计算
# 锚点约定：exitX/exitY/entryX/entryY（0~1 分数）。显式锚点优先；
# 未给锚点时按源/目标相对方位自动选相互面对的边（方向感知，向上走线从顶边出）。

SIDES = {"T": (0.5, 0.0), "B": (0.5, 1.0), "L": (0.0, 0.5), "R": (1.0, 0.5)}
MIN_CLR = 14  # 走线与无关框的最小间距


def node_boxes(cells, by_id, cache):
    """所有普通节点（不含泳道）的绝对包围盒，作为走线障碍。"""
    boxes = []
    for v in cells:
        if not v.vertex or v.is_lane() or v.w is None:
            continue
        vx, vy = abs_pos(v, by_id, cache)
        boxes.append((vx, vy, v.w, v.h, v.id))
    return boxes


def route_edges(cells, by_id, cache, boxes):
    """把每条连边算成折线点列。渲染与几何校验共用这一份结果。"""

    def anchor_abs(cell, frac):
        x, y = abs_pos(cell, by_id, cache)
        return (x + frac[0] * cell.w, y + frac[1] * cell.h)

    def parse_anchor(c, prefix):
        fx = c.style_val(prefix + "X")
        fy = c.style_val(prefix + "Y")
        if fx is None or fy is None:
            return None
        try:
            return (float(fx), float(fy))
        except ValueError:
            return None

    def nearest_side(frac):
        return min(SIDES, key=lambda k: abs(SIDES[k][0] - frac[0])
                   + abs(SIDES[k][1] - frac[1]))

    def blocked_v(x, y0, y1, skip):
        """竖直走线 x 穿过 [y0,y1] 时是否贴近某个障碍框"""
        lo, hi = min(y0, y1), max(y0, y1)
        for bx, by, bw, bh, bid in boxes:
            if bid in skip:
                continue
            if by < hi + MIN_CLR and by + bh > lo - MIN_CLR and \
                    bx - MIN_CLR < x < bx + bw + MIN_CLR:
                return True
        return False

    def blocked_h(y, x0, x1, skip):
        lo, hi = min(x0, x1), max(x0, x1)
        for bx, by, bw, bh, bid in boxes:
            if bid in skip:
                continue
            if bx < hi + MIN_CLR and bx + bw > lo - MIN_CLR and \
                    by - MIN_CLR < y < by + bh + MIN_CLR:
                return True
        return False

    def _pick(segs, lo, hi):
        """在 [lo,hi] 内避开已占区间，选离中点最近的可用坐标"""
        merged = []
        for a, b in sorted(segs):
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        free, cur = [], lo
        for a, b in merged:
            if a > cur:
                free.append((cur, min(a, hi)))
            cur = max(cur, b)
        if cur < hi:
            free.append((cur, hi))
        free = [f for f in free if f[1] - f[0] > 0.5]
        if not free:
            return None
        prefer = (lo + hi) / 2.0
        best = min(free, key=lambda f: abs((f[0] + f[1]) / 2 - prefer))
        return min(max(prefer, best[0]), best[1])

    def free_channel_x(y0, y1, x_lo, x_hi, skip):
        """竖直走线通道：穿过 [y0,y1]、限制在 [x_lo,x_hi]，避开障碍框"""
        lo, hi = min(y0, y1), max(y0, y1)
        segs = [(bx - MIN_CLR, bx + bw + MIN_CLR)
                for bx, by, bw, bh, bid in boxes
                if bid not in skip and by < hi + MIN_CLR and by + bh > lo - MIN_CLR]
        return _pick(segs, x_lo, x_hi)

    def free_channel_y(x0, x1, y_lo, y_hi, skip):
        lo, hi = min(x0, x1), max(x0, x1)
        segs = [(by - MIN_CLR, by + bh + MIN_CLR)
                for bx, by, bw, bh, bid in boxes
                if bid not in skip and bx < hi + MIN_CLR and bx + bw > lo - MIN_CLR]
        return _pick(segs, y_lo, y_hi)

    routes = {}
    for c in cells:
        if not c.edge:
            continue
        s = by_id.get(c.source)
        t = by_id.get(c.target)
        if s is None or t is None or s.w is None or t.w is None:
            continue
        sx, sy = abs_pos(s, by_id, cache)
        tx, ty = abs_pos(t, by_id, cache)
        scx, scy = sx + s.w / 2, sy + s.h / 2
        tcx, tcy = tx + t.w / 2, ty + t.h / 2
        skip = {s.id, t.id}

        exit_a = parse_anchor(c, "exit")
        entry_a = parse_anchor(c, "entry")
        if exit_a and entry_a:
            side0 = nearest_side(exit_a)
            side1 = nearest_side(entry_a)
        else:
            # 方向感知自动选边：同行水平直连；同列竖直时按上下行选底/顶；
            # 斜向时横向余量够走 Z，否则纵向优先出肘，再不行走竖直通道绕行
            if abs(scy - tcy) < 8:
                side0, side1 = ("R", "L") if tcx >= scx else ("L", "R")
            elif abs(scx - tcx) < 8:
                side0, side1 = ("B", "T") if tcy > scy else ("T", "B")
            elif tcx > scx:
                hgap = tx - (sx + s.w)
                vgap = (ty - (sy + s.h)) if tcy > scy else (sy - (ty + t.h))
                if hgap >= 30:
                    side0, side1 = ("R", "L")
                elif vgap >= 16 or hgap >= 8:
                    side0, side1 = ("B", "L") if tcy > scy else ("T", "L")
                else:
                    side0, side1 = ("B", "T") if tcy > scy else ("T", "B")
            else:
                hgap = sx - (tx + t.w)
                vgap = (ty - (sy + s.h)) if tcy > scy else (sy - (ty + t.h))
                if hgap >= 30:
                    side0, side1 = ("L", "R")
                elif vgap >= 16 or hgap >= 8:
                    side0, side1 = ("B", "R") if tcy > scy else ("T", "R")
                else:
                    side0, side1 = ("B", "T") if tcy > scy else ("T", "B")
        p0 = anchor_abs(s, exit_a) if exit_a else anchor_abs(s, SIDES[side0])
        p1 = anchor_abs(t, entry_a) if entry_a else anchor_abs(t, SIDES[side1])

        # 固定折点（draw.io 原生 <Array as="points">）：写了就按折点走，不再自动选路
        if c.points:
            px = py = 0.0
            pm = by_id.get(c.parent)
            if pm is not None and pm.x is not None:
                px, py = abs_pos(pm, by_id, cache)
            routes[c.id] = ([p0] + [(qx + px, qy + py) for qx, qy in c.points]
                            + [p1])
            continue

        if side0 in ("T", "B"):
            if side1 in ("T", "B"):
                # 竖直出 + 竖直入：对齐且无遮挡走直线，否则经水平通道绕行
                if abs(p0[0] - p1[0]) < 0.6 and not blocked_v(p0[0], p0[1],
                                                              p1[1], skip):
                    pts = [p0, p1]
                else:
                    cy = free_channel_y(p0[0], p1[0], p0[1], p1[1], skip)
                    if cy is None:
                        cy = (p0[1] + p1[1]) / 2
                    pts = [p0, (p0[0], cy), (p1[0], cy), p1]
            else:
                # 竖直出 + 横向入：L 形（先纵向后横向）
                if abs(p0[0] - p1[0]) < 0.6 and not blocked_v(p0[0], p0[1],
                                                              p1[1], skip):
                    pts = [p0, p1]
                else:
                    pts = [p0, (p0[0], p1[1]), p1]
        elif side1 in ("L", "R"):
            # 横向出 + 横向入：同行且无遮挡走直线，否则经竖直通道绕行
            if abs(p0[1] - p1[1]) < 0.6 and not blocked_h(p0[1], p0[0],
                                                          p1[0], skip):
                pts = [p0, p1]
            else:
                mx = free_channel_x(p0[1], p1[1], p0[0], p1[0], skip)
                if mx is None:
                    mx = (p0[0] + p1[0]) / 2
                pts = [p0, (mx, p0[1]), (mx, p1[1]), p1]
        else:
            # 横向出 + 纵向入：L 形（先横向后纵向）
            pts = [p0, (p1[0], p0[1]), p1]

        routes[c.id] = pts
    return routes


def _segments(pts):
    return [(a, b) for a, b in zip(pts, pts[1:]) if abs(a[0] - b[0]) > 0.5
            or abs(a[1] - b[1]) > 0.5]


def check_geometry(cells, by_id, cache, routes, boxes):
    """连边几何校验：线段不得穿过无关节点，两条边不得在内部交叉。"""
    errors = []
    warnings = []
    ends = {c.id: {c.source, c.target} for c in cells if c.edge}

    # 1) 线段穿过无关节点（视觉上就是"箭头指空"）
    for eid, pts in routes.items():
        for (x0, y0), (x1, y1) in _segments(pts):
            for bx, by, bw, bh, bid in boxes:
                if bid in ends.get(eid, ()):
                    continue
                if abs(x0 - x1) < 0.5:
                    if (bx + 0.5 < x0 < bx + bw - 0.5 and
                            max(y0, y1) > by + 0.5 and
                            min(y0, y1) < by + bh - 0.5):
                        errors.append(
                            "连边 %s 竖直穿过节点 %s（x=%.0f），需改锚点或挪节点位置"
                            % (eid, bid, x0))
                elif abs(y0 - y1) < 0.5:
                    if (by + 0.5 < y0 < by + bh - 0.5 and
                            max(x0, x1) > bx + 0.5 and
                            min(x0, x1) < bx + bw - 0.5):
                        errors.append(
                            "连边 %s 水平穿过节点 %s（y=%.0f），需改锚点或挪节点位置"
                            % (eid, bid, y0))

    # 2) 两条边交叉 / 重叠
    ids = sorted(routes)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            ea, eb = ids[i], ids[j]
            cross = overlap = None
            for (ax0, ay0), (ax1, ay1) in _segments(routes[ea]):
                av = abs(ax0 - ax1) < 0.5
                for (bx0, by0), (bx1, by1) in _segments(routes[eb]):
                    bv = abs(bx0 - bx1) < 0.5
                    if av and bv:
                        if (abs(ax0 - bx0) < 0.5 and
                                min(max(ay0, ay1), max(by0, by1)) -
                                max(min(ay0, ay1), min(by0, by1)) > 0.5):
                            overlap = ("竖", ax0)
                    elif not av and not bv:
                        if (abs(ay0 - by0) < 0.5 and
                                min(max(ax0, ax1), max(bx0, bx1)) -
                                max(min(ax0, ax1), min(bx0, bx1)) > 0.5):
                            overlap = ("横", ay0)
                    else:
                        if av:
                            vx = ax0
                            vy0, vy1 = sorted([ay0, ay1])
                            hy = by0
                            hx0, hx1 = sorted([bx0, bx1])
                        else:
                            vx = bx0
                            vy0, vy1 = sorted([by0, by1])
                            hy = ay0
                            hx0, hx1 = sorted([ax0, ax1])
                        if (hx0 + 0.5 < vx < hx1 - 0.5 and
                                vy0 + 0.5 < hy < vy1 - 0.5):
                            cross = (vx, hy)
            if cross:
                errors.append("连边 %s 与 %s 交叉（%.0f,%.0f），需错开走线通道"
                              % (ea, eb, cross[0], cross[1]))
            elif overlap:
                warnings.append("连边 %s 与 %s 有重叠段（%s=%.0f）"
                                % (ea, eb, overlap[0], overlap[1]))
    return errors, warnings


def render(cells, by_id, cache, out_path, routes=None, boxes=None):
    parts = []
    ext = [0.0, 0.0]

    def track(x, y):
        ext[0] = max(ext[0], x)
        ext[1] = max(ext[1], y)

    def paint_rect(x, y, w, h, fill, stroke, rx, sw=1.4, dash=None):
        d = ' stroke-dasharray="5 4"' if dash else ""
        parts.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" '
            'fill="%s" stroke="%s" stroke-width="%s"%s/>'
            % (x, y, w, h, rx, fill, stroke, sw, d))
        track(x + w, y + h)

    def paint_text(x, y, text, size, color, anchor="middle", bold=False, rotate=None):
        if not text:
            return
        weight = ' font-weight="700"' if bold else ""
        rot = (' transform="rotate(%.0f %.1f %.1f)"' % (rotate, x, y)) if rotate else ""
        parts.append(
            '<text x="%.1f" y="%.1f" font-size="%.1f" fill="%s" text-anchor="%s" '
            'font-family="%s"%s%s>%s</text>'
            % (x, y, size, color, anchor, FONT, weight, rot, esc_text(text)))

    def draw_vertex(c):
        x, y = abs_pos(c, by_id, cache)
        w, h = c.w or 0, c.h or 0
        st = c.style
        if st.startswith("text"):
            txt = strip_html(c.value)
            size = c.num("fontSize", 12)
            color = c.color("fontColor", "#1F2937")
            align = c.style_val("align", "left")
            bold = c.style_val("fontStyle", "0") in ("1", "3")
            lines = [l for l in txt.split("\n") if l.strip()]
            lh = size * 1.45
            total = lh * len(lines)
            base = y + (h - total) / 2 + size * 0.95
            for i, line in enumerate(lines):
                if align == "right":
                    paint_text(x + w - 4, base + i * lh, line, size, color,
                               anchor="end", bold=bold)
                else:
                    paint_text(x + 2, base + i * lh, line, size, color,
                               anchor="start", bold=bold)
            track(x + w, y + h)
            return

        fill = c.color("fillColor", "#FFFFFF")
        stroke = c.color("strokeColor", "#C9CDD4")
        font = c.color("fontColor", "#1F2937")
        size = c.num("fontSize", 12)
        dash = "dashed=1" in st

        if c.is_lane():
            start = c.num("startSize", 30)
            rx = 4
            paint_rect(x, y, w, h, fill, stroke, rx, sw=1.2, dash=dash)
            inner = c.color("swimlaneFillColor", "#FFFFFF")
            if c.horizontal():
                paint_rect(x + start, y, w - start, h, inner, "none", 0, sw=0)
            else:
                paint_rect(x, y + start, w, h - start, inner, "none", 0, sw=0)
            label = strip_html(c.value).replace("\n", " ")
            if c.horizontal():
                paint_text(x + start / 2, y + h / 2, label, size, font,
                           rotate=-90, bold=True)
            else:
                paint_text(x + w / 2, y + start / 2 + size * 0.35, label, size,
                           font, bold=True)
            return

        if "rhombus" in st:
            pts = "%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" % (
                x + w / 2, y, x + w, y + h / 2, x + w / 2, y + h, x, y + h / 2)
            parts.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="1.4"%s/>'
                         % (pts, fill, stroke, ' stroke-dasharray="5 4"' if dash else ""))
            track(x + w, y + h)
        else:
            rx = min(8.0, h / 2) if ("rounded=1" in st or "arcSize=50" in st) else 0
            paint_rect(x, y, w, h, fill, stroke, rx, dash=dash)

        txt = strip_html(c.value)
        lines = [l for l in txt.split("\n") if l.strip()]
        if len(lines) >= 2:
            paint_text(x + w / 2, y + h / 2 - 3, lines[0], size, font, bold=True)
            paint_text(x + w / 2, y + h / 2 + 13, " ".join(lines[1:]),
                       max(9, size - 2), "#6B7280")
        elif lines:
            paint_text(x + w / 2, y + h / 2 + size * 0.35, lines[0], size, font)

    lanes = [c for c in cells if c.is_lane()]
    others = [c for c in cells if c.vertex and not c.is_lane()]
    edges = [c for c in cells if c.edge]

    # ---------------- 连线渲染 ----------------
    # 走线几何统一由 route_edges 计算（与几何校验共用同一份结果）
    if routes is None:
        routes = route_edges(cells, by_id, cache,
                             boxes or node_boxes(cells, by_id, cache))

    marker_defs = []
    marker_ids = {}

    def marker_for(color):
        mid = marker_ids.get(color)
        if mid is None:
            mid = "arrow-%d" % len(marker_ids)
            marker_ids[color] = mid
            marker_defs.append(
                '<marker id="%s" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                '<path d="M 0 0 L 10 5 L 0 10 z" fill="%s"/></marker>'
                % (mid, color))
        return mid

    def poly_at(pts, t):
        """折线上弧长参数 t∈[0,1] 处的坐标（labelT 用）"""
        segs = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:])]
        total = sum(segs) or 1.0
        target = max(0.0, min(1.0, t)) * total
        acc = 0.0
        for a, b, seg in zip(pts, pts[1:], segs):
            if acc + seg >= target:
                r = (target - acc) / seg if seg else 0
                return (a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r)
            acc += seg
        return pts[-1]

    def paint_label(x, y, text, size, color):
        lines = [l for l in text.split("\n") if l]
        if not lines:
            return
        widths = [size * sum(1.0 if ord(ch) > 0x2E80 else 0.62 for ch in l)
                  for l in lines]
        w = max(widths)
        lh = size * 1.35
        h = lh * len(lines)
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                     'fill="#FFFFFF" opacity="0.92"/>'
                     % (x - w / 2 - 3, y - size * 0.9, w + 6, h + 3))
        base = y - h / 2 + size * 0.95
        for i, line in enumerate(lines):
            paint_text(x, base + i * lh, line, size, color)
        track(x + w / 2 + 3, y + h / 2 + 2)

    def draw_edge(c):
        pts = routes.get(c.id)
        if not pts:
            return
        s = by_id.get(c.source)
        t = by_id.get(c.target)
        dash = ("dashed=1" in c.style or (s is not None and "dashed=1" in s.style)
                or (t is not None and "dashed=1" in t.style))
        color = c.color("strokeColor", "#1F2937")

        d = "M " + " L ".join("%.1f %.1f" % p for p in pts)
        dash_attr = ' stroke-dasharray="5 4"' if dash else ""
        parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.3" '
                     'marker-end="url(#%s)"%s/>'
                     % (d, color, marker_for(color), dash_attr))
        for p in pts:
            track(p[0], p[1])

        label = strip_html(c.value).strip()
        if label:
            lx, ly = poly_at(pts, c.num("labelT", 0.5))
            paint_label(lx, ly, label, 9.5, c.color("fontColor", "#6B7280"))

    for c in lanes:
        draw_vertex(c)
    for c in others:
        draw_vertex(c)
    for c in edges:
        draw_edge(c)

    W = int(ext[0] + 32)
    H = int(ext[1] + 32)
    head = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d">' % (W, H, W, H),
        '<defs>%s</defs>' % "".join(marker_defs),
        '<rect width="%d" height="%d" fill="#FFFFFF"/>' % (W, H),
    ]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(head + parts + ["</svg>"]))
    return W, H


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    path = argv[1]
    want_preview = "--preview" in argv[2:]

    if not os.path.exists(path):
        print("[ERROR] 文件不存在：%s" % path)
        return 1
    try:
        cells = load(path)
    except ET.ParseError as exc:
        print("[FAIL] XML 解析失败：%s" % exc)
        return 1

    errors, warnings, by_id, cache = validate(cells)
    lanes = [c for c in cells if c.is_lane()]
    modules = [c for c in cells if c.vertex and not c.is_lane()
               and "text" not in c.style[:4]]
    edges = [c for c in cells if c.edge]

    # 连边几何：与渲染共用同一份走线结果
    boxes = node_boxes(cells, by_id, cache)
    routes = route_edges(cells, by_id, cache, boxes)
    g_err, g_warn = check_geometry(cells, by_id, cache, routes, boxes)
    errors += g_err
    warnings += g_warn

    print("文件: %s" % path)
    print("单元格 %d | 泳道/层带 %d | 图形 %d | 连边 %d"
          % (len(cells), len(lanes), len(modules), len(edges)))

    if errors:
        print("\n错误 %d 条：" % len(errors))
        for e in errors:
            print("  ✗ %s" % e)
    if warnings:
        print("\n警告 %d 条：" % len(warnings))
        for w in warnings:
            print("  ! %s" % w)
    if not errors and not warnings:
        print("结构校验：全部通过（根单元格 / id 唯一 / parent / source-target / "
              "不越界 / 不重叠 / 标题栏 / 连边不穿框 / 连边不交叉）")

    if want_preview:
        out = path.rsplit(".", 1)[0] + "-preview.svg"
        W, H = render(cells, by_id, cache, out, routes, boxes)
        print("预览已生成：%s（%d x %d）" % (out, W, H))

    if errors:
        return 1
    if warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
