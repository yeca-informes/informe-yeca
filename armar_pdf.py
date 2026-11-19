#!/usr/bin/env python3
"""Generador del informe semanal de Instagram de YECA (@dameyeca).

Uso: python armar_pdf.py datos.json salida.pdf
Solo usa reportlab, matplotlib y Pillow.
"""
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

# ----------------------------------------------------------------- PALETA
ACENTO = "#B0148F"      # magenta/violeta fuerte (unico color de acento)
TEXTO = "#1B1B1F"
GRIS = "#6B6B76"
POSITIVO = "#1E8E4E"
NEGATIVO = "#D32F2F"
# derivados (neutros)
GRIS_CLARO = "#E4E2E8"
FONDO_TARJETA = "#F6F4F8"

FUENTE = "Datos: API de Instagram (Meta)"
F_REG, F_BOLD, F_ITA = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"

PW, PH = A4
M = 48
CW = PW - 2 * M
TZ_AR = timezone(timedelta(hours=-3))
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS_ABR = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
FORMATOS = {"CAROUSEL_ALBUM": "Carrusel", "VIDEO": "Video", "IMAGE": "Imagen",
            "REELS": "Reel", "REEL": "Reel"}


# --------------------------------------------------------------- UTILIDADES
def clean(s):
    """Texto seguro para Helvetica (cp1252): sin emojis ni saltos de linea."""
    s = re.sub(r"\s+", " ", str(s if s is not None else "")).strip()
    return s.encode("cp1252", "ignore").decode("cp1252")


def num(x, default=0.0):
    try:
        if x is None or isinstance(x, bool):
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def fmt_int(n):
    return f"{int(round(num(n))):,}".replace(",", ".")


def fmt_dec(x, dec=1):
    s = f"{abs(num(x)):,.{dec}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if num(x) < 0 and float(s.replace(".", "").replace(",", ".")) != 0 else "") + s


def fmt_signed_int(n):
    n = int(round(num(n)))
    return ("+" if n > 0 else "-" if n < 0 else "") + fmt_int(abs(n))


def fmt_signed_dec(x, dec=1):
    v = num(x)
    s = fmt_dec(abs(v), dec)
    return ("+" if v > 0 else "-" if v < 0 else "") + s


def parse_dt(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if d.tzinfo is not None:
        d = d.astimezone(TZ_AR)
    return d


def fecha_corta(d):
    return f"{d.day}/{d.month}" if d else "s/f"


def fecha_larga_post(d):
    if not d:
        return "Fecha no disponible"
    return f"{DIAS_ABR[d.weekday()]} {d.day} de {MESES[d.month - 1]} · {d.hour:02d}:{d.minute:02d} h"


def rango_semana(sem):
    try:
        a = datetime.strptime(sem.get("desde"), "%Y-%m-%d")
        b = datetime.strptime(sem.get("hasta"), "%Y-%m-%d")
    except (TypeError, ValueError, AttributeError):
        return "Semana sin fecha"
    if a.year == b.year and a.month == b.month:
        return f"{a.day} al {b.day} de {MESES[b.month - 1]} de {b.year}"
    if a.year == b.year:
        return f"{a.day} de {MESES[a.month - 1]} al {b.day} de {MESES[b.month - 1]} de {b.year}"
    return (f"{a.day} de {MESES[a.month - 1]} de {a.year} al "
            f"{b.day} de {MESES[b.month - 1]} de {b.year}")


def trunc(s, n):
    s = clean(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def fit_text(s, font, size, width):
    s = clean(s)
    if stringWidth(s, font, size) <= width:
        return s
    while s and stringWidth(s + "…", font, size) > width:
        s = s[:-1]
    return s + "…"


def formato(t):
    return FORMATOS.get(str(t or "").upper(), clean(t).title() or "Sin dato")


def mezclar(hex_color, t):
    """Mezcla un color con blanco (t=0 blanco, 1 color)."""
    c = hex_color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    f = lambda v: int(255 - (255 - v) * t)
    return "#%02X%02X%02X" % (f(r), f(g), f(b))


# ----------------------------------------------------------------- GRAFICOS
def estilo_ejes(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRIS_CLARO)
    ax.tick_params(colors=GRIS, labelsize=8.5, length=0)


def grafico_ranking(posts, ruta):
    n = len(posts)
    fig, ax = plt.subplots(figsize=(6.93, max(1.6, 0.42 * n + 0.5)))
    orden = sorted(posts, key=lambda p: -p["eng"])
    etiquetas = [f"{fecha_corta(p['dt'])} · {trunc(p['caption'], 30)}" for p in orden]
    vals = [p["eng"] for p in orden]
    if n:
        colores = [ACENTO if i == 0 else mezclar(ACENTO, 0.5) for i in range(n)]
        ax.barh(range(n), vals, color=colores, height=0.62)
        ax.set_yticks(range(n))
        ax.set_yticklabels(etiquetas)
        ax.invert_yaxis()
        mx = max(max(vals), 0.0001)
        ax.set_xlim(0, mx * 1.18)
        for i, v in enumerate(vals):
            ax.text(v + mx * 0.015, i, f"{fmt_dec(v)} %", va="center", fontsize=9,
                    color=TEXTO, fontweight="bold" if i == 0 else "normal")
    else:
        ax.text(0.5, 0.5, "sin posteos esta semana", ha="center", va="center",
                color=GRIS, fontsize=11, transform=ax.transAxes)
        ax.set_yticks([])
    ax.set_xticks([])
    estilo_ejes(ax)
    ax.spines["bottom"].set_visible(False)
    fig.subplots_adjust(left=0.47, right=0.96, top=0.97, bottom=0.04)
    fig.savefig(ruta, dpi=200, facecolor="white")
    plt.close(fig)
    return fig.get_size_inches()


def matriz_heatmap(h):
    filas = (h or {}).get("valores") or []
    out = []
    for r in range(7):
        fila = filas[r] if r < len(filas) and isinstance(filas[r], list) else []
        out.append([num(fila[c]) if c < len(fila) else 0.0 for c in range(24)])
    return out


def grafico_heatmap(h, ruta):
    dias = (h or {}).get("dias") or []
    dias = [clean(dias[i]) if i < len(dias) else "" for i in range(7)]
    mat = matriz_heatmap(h)
    mx = max(max(f) for f in mat)
    fig, ax = plt.subplots(figsize=(6.93, 2.7))
    cmap = LinearSegmentedColormap.from_list("acento", ["#FBF7FA", ACENTO])
    ax.pcolormesh(mat, cmap=cmap, vmin=0, vmax=mx if mx > 0 else 1,
                  edgecolors="white", linewidth=0.8)
    ax.set_xlim(0, 24)
    ax.set_ylim(7, 0)
    ax.set_yticks([i + 0.5 for i in range(7)])
    ax.set_yticklabels(dias)
    ax.set_xticks([i + 0.5 for i in range(0, 24, 2)])
    ax.set_xticklabels([f"{i} h" for i in range(0, 24, 2)])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=GRIS, labelsize=8.5, length=0)
    mejor = None
    if mx > 0:
        for r in range(7):
            for c in range(24):
                if mat[r][c] == mx and mejor is None:
                    mejor = (r, c)
        ax.add_patch(plt.Rectangle((mejor[1], mejor[0]), 1, 1, fill=False,
                                   edgecolor=TEXTO, linewidth=1.6))
    else:
        ax.text(12, 3.5, "sin datos", ha="center", va="center", color=GRIS, fontsize=11)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.98, bottom=0.1)
    fig.savefig(ruta, dpi=200, facecolor="white")
    plt.close(fig)
    return mejor, dias, mx


def grafico_formatos(fm, ruta):
    fig, axs = plt.subplots(1, 2, figsize=(6.93, max(1.7, 0.55 * len(fm) + 0.9)))
    cats = [f"{formato(f.get('tipo'))} ({int(num(f.get('posts')))})" for f in fm]
    series = [("Engagement promedio (%)", [num(f.get("engagement_promedio")) for f in fm], True),
              ("Alcance promedio", [num(f.get("alcance_promedio")) for f in fm], False)]
    for k, (ax, (tit, vals, pct)) in enumerate(zip(axs, series)):
        ax.barh(range(len(vals)), vals, color=ACENTO if k == 0 else mezclar(ACENTO, 0.55), height=0.58)
        ax.set_yticks(range(len(vals)))
        ax.set_yticklabels(cats if k == 0 else [""] * len(vals))
        ax.invert_yaxis()
        mx = max(max(vals), 0.0001)
        ax.set_xlim(0, mx * 1.3)
        for i, v in enumerate(vals):
            ax.text(v + mx * 0.02, i, f"{fmt_dec(v)} %" if pct else fmt_int(v),
                    va="center", fontsize=9, color=TEXTO)
        ax.set_xticks([])
        ax.set_title(tit, loc="left", fontsize=9.5, color=GRIS, pad=8)
        estilo_ejes(ax)
        ax.spines["bottom"].set_visible(False)
    fig.subplots_adjust(left=0.2, right=0.98, top=0.82, bottom=0.04, wspace=0.12)
    fig.savefig(ruta, dpi=200, facecolor="white")
    plt.close(fig)
    return fig.get_size_inches()


# --------------------------------------------------------------- IMAGENES
def preparar_imagen(ruta, ancho_pt, alto_pt, tmp, nombre):
    """Recorte centrado al aspecto del recuadro. Devuelve ruta o None."""
    if not ruta or not os.path.isfile(ruta):
        return None
    try:
        im = Image.open(ruta).convert("RGB")
        ar = ancho_pt / alto_pt
        w, h = im.size
        if w / h > ar:
            nw = int(h * ar)
            im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = int(w / ar)
            im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        px = int(ancho_pt * 3)
        im = im.resize((px, int(px / ar)), Image.LANCZOS)
        out = os.path.join(tmp, nombre)
        im.save(out, "JPEG", quality=88)
        return out
    except Exception:
        return None


# ------------------------------------------------------------------- PDF
class Informe:
    def __init__(self, ruta, tmp):
        self.c = canvas.Canvas(ruta, pagesize=A4)
        self.c.setTitle("Informe semanal de Instagram — YECA")
        self.c.setAuthor("YECA")
        self.tmp = tmp
        self.pag = 0

    # -- marco de pagina
    def nueva(self, kicker):
        if self.pag:
            self.c.showPage()
        self.pag += 1
        c = self.c
        c.setFillColor(HexColor(ACENTO))
        c.rect(0, PH - 14, PW, 14, stroke=0, fill=1)
        c.setFont(F_BOLD, 9)
        c.setFillColor(HexColor(TEXTO))
        c.drawString(M, PH - 38, "YECA")
        c.setFont(F_REG, 9)
        c.setFillColor(HexColor(GRIS))
        c.drawRightString(PW - M, PH - 38, "Informe semanal de Instagram · @dameyeca")
        c.setStrokeColor(HexColor(GRIS_CLARO))
        c.setLineWidth(0.6)
        c.line(M, 50, PW - M, 50)
        c.setFont(F_REG, 8.5)
        c.drawString(M, 36, FUENTE)
        c.drawRightString(PW - M, 36, f"Página {self.pag}")
        return PH - 78

    def titulo(self, y, kicker, texto, size=26):
        c = self.c
        c.setFont(F_BOLD, 9.5)
        c.setFillColor(HexColor(ACENTO))
        c.drawString(M, y, kicker.upper())
        y -= size + 4
        c.setFont(F_BOLD, size)
        c.setFillColor(HexColor(TEXTO))
        for ln in simpleSplit(texto, F_BOLD, size, CW):
            c.drawString(M, y, ln)
            y -= size * 1.12
        return y - 6

    def parrafo(self, x, y, texto, font, size, width, color=TEXTO, lead=None, max_lines=None):
        lead = lead or size * 1.45
        lines = simpleSplit(clean(texto), font, size, width)
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = fit_text(lines[-1] + " …", font, size, width)
        self.c.setFont(font, size)
        self.c.setFillColor(HexColor(color))
        for ln in lines:
            self.c.drawString(x, y, ln)
            y -= lead
        return y

    def flecha(self, x, y, up, color, s=5):
        """Triangulo con base en y; (x,y) = esquina inferior izquierda."""
        p = self.c.beginPath()
        if up:
            p.moveTo(x, y); p.lineTo(x + 2 * s, y); p.lineTo(x + s, y + 1.7 * s)
        else:
            p.moveTo(x, y + 1.7 * s); p.lineTo(x + 2 * s, y + 1.7 * s); p.lineTo(x + s, y)
        p.close()
        self.c.setFillColor(HexColor(color))
        self.c.drawPath(p, stroke=0, fill=1)

    def delta(self, x, y, valor, texto, size=11):
        """Variacion con flecha. valor None => sin dato."""
        c = self.c
        if valor is None:
            c.setFont(F_REG, size)
            c.setFillColor(HexColor(GRIS))
            c.drawString(x, y, "sin dato de la semana anterior")
            return
        v = num(valor)
        if round(v, 2) == 0:
            col, up = GRIS, None
        else:
            col, up = (POSITIVO, True) if v > 0 else (NEGATIVO, False)
        tx = x
        if up is not None:
            self.flecha(x, y - 0.5, up, col, s=4.5)
            tx = x + 14
        c.setFont(F_BOLD, size)
        c.setFillColor(HexColor(col))
        c.drawString(tx, y, texto if up is not None else "sin cambios")

    def tarjeta(self, x, y_top, w, h, etiqueta, valor, vsize, valor_delta, texto_delta):
        c = self.c
        c.setFillColor(HexColor(FONDO_TARJETA))
        c.roundRect(x, y_top - h, w, h, 6, stroke=0, fill=1)
        c.setFillColor(HexColor(ACENTO))
        c.rect(x, y_top - 3, w, 3, stroke=0, fill=1)
        c.setFont(F_BOLD, 9)
        c.setFillColor(HexColor(GRIS))
        c.drawString(x + 14, y_top - 24, etiqueta.upper())
        c.setFont(F_BOLD, vsize)
        c.setFillColor(HexColor(TEXTO))
        c.drawString(x + 14, y_top - 30 - vsize, valor)
        if texto_delta is not False:
            self.delta(x + 14, y_top - h + 14, valor_delta, texto_delta, size=10.5)

    def sin_imagen(self, x, y, w, h):
        c = self.c
        c.setFillColor(HexColor(GRIS_CLARO))
        c.rect(x, y, w, h, stroke=0, fill=1)
        c.setFont(F_REG, 10)
        c.setFillColor(HexColor(GRIS))
        c.drawCentredString(x + w / 2, y + h / 2 - 3, "sin imagen")

    def imagen_post(self, post, x, y, w, h, nombre):
        ruta = preparar_imagen(post.get("img_abs"), w, h, self.tmp, nombre) if post else None
        if ruta:
            self.c.drawImage(ruta, x, y, w, h)
        else:
            self.sin_imagen(x, y, w, h)

    # -- P1
    def p1(self, d, rs):
        c = self.c
        y = self.nueva("")
        y = self.titulo(y, "Informe semanal", "Informe semanal de Instagram — YECA", 30)
        c.setFont(F_BOLD, 15)
        c.setFillColor(HexColor(TEXTO))
        c.drawString(M, y - 4, rango_semana(d.get("semana") or {}))
        c.setFont(F_REG, 11)
        c.setFillColor(HexColor(GRIS))
        c.drawString(M, y - 22, "@" + (clean(d.get("cuenta")) or "dameyeca"))
        y -= 52
        gap = 14
        w2 = (CW - gap) / 2
        h1 = 112
        self.tarjeta(M, y, w2, h1, "Seguidores", fmt_int(rs["seguidores"]), 34,
                     rs["seguidores_delta"], fmt_signed_int(rs["seguidores_delta"]) + " en la semana")
        ad = rs["alcance_delta_pct"]
        self.tarjeta(M + w2 + gap, y, w2, h1, "Alcance", fmt_int(rs["alcance"]), 34, ad,
                     fmt_signed_dec(ad) + " % vs. semana anterior" if ad is not None else "")
        y -= h1 + gap
        w3 = (CW - 2 * gap) / 3
        h2 = 100
        self.tarjeta(M, y, w3, h2, "Interacciones", fmt_int(rs["interacciones"]), 26, None, False)
        ed = rs["engagement_delta_pp"]
        self.tarjeta(M + w3 + gap, y, w3, h2, "Engagement", fmt_dec(rs["engagement_pct"]) + " %", 26, ed,
                     fmt_signed_dec(ed) + " pp" if ed is not None else "")
        self.tarjeta(M + 2 * (w3 + gap), y, w3, h2, "Publicaciones", fmt_int(rs["publicaciones"]), 26, None, False)
        y -= h2 + 34
        # resumen editorial
        c.setFont(F_BOLD, 9.5)
        c.setFillColor(HexColor(ACENTO))
        c.drawString(M, y, "RESUMEN EDITORIAL")
        y -= 8
        c.setStrokeColor(HexColor(ACENTO))
        c.setLineWidth(1.2)
        c.line(M, y, M + 40, y)
        y -= 22
        texto = clean((d.get("recomendaciones") or {}).get("resumen_editorial"))
        if not texto:
            texto = "Sin resumen editorial para esta semana."
        disp = y - 62
        for size in (12, 11.5, 11, 10.5, 10):
            lead = size * 1.5
            if len(simpleSplit(texto, F_REG, size, CW)) * lead <= disp:
                break
        self.parrafo(M, y, texto, F_REG, size, CW, lead=lead, max_lines=int(disp // lead))

    # -- P2
    def p2(self, mejor, peor):
        c = self.c
        y = self.nueva("")
        y = self.titulo(y, "Qué funcionó y qué no", "Mejor vs. peor posteo")
        gap = 22
        cw = (CW - gap) / 2
        iw, ih = cw, cw * 1.25
        top = y - 6
        for k, (post, rot, col) in enumerate(((mejor, "MEJOR POSTEO", POSITIVO), (peor, "PEOR POSTEO", NEGATIVO))):
            x = M + k * (cw + gap)
            c.setFillColor(HexColor(col))
            c.rect(x, top - 3, 26, 3, stroke=0, fill=1)
            c.setFont(F_BOLD, 10)
            c.drawString(x, top - 18, rot)
            iy = top - 28 - ih
            self.imagen_post(post, x, iy, iw, ih, f"p2_{k}.jpg")
            yy = iy - 20
            if not post:
                c.setFont(F_REG, 10.5)
                c.setFillColor(HexColor(GRIS))
                c.drawString(x, yy, "No hay posteos en esta semana.")
                continue
            c.setFont(F_BOLD, 10.5)
            c.setFillColor(HexColor(TEXTO))
            c.drawString(x, yy, fit_text(fecha_larga_post(post["dt"]), F_BOLD, 10.5, cw))
            yy -= 15
            c.setFont(F_REG, 10.5)
            c.setFillColor(HexColor(GRIS))
            c.drawString(x, yy, "Formato: " + formato(post["tipo"]))
            yy -= 18
            cap = trunc(post["caption"], 120) or "(sin texto)"
            yy = self.parrafo(x, yy, cap, F_ITA, 10.5, cw, lead=14, max_lines=4)
            yy -= 8
            mets = [("Alcance", fmt_int(post["alcance"])), ("Engagement", fmt_dec(post["eng"]) + " %"),
                    ("Likes", fmt_int(post["likes"])), ("Comentarios", fmt_int(post["comentarios"])),
                    ("Guardados", fmt_int(post["guardados"])), ("Compartidos", fmt_int(post["compartidos"]))]
            for i, (lab, val) in enumerate(mets):
                mx_ = x + (i % 2) * (cw / 2)
                my = yy - (i // 2) * 34
                c.setFont(F_REG, 9)
                c.setFillColor(HexColor(GRIS))
                c.drawString(mx_, my, lab)
                c.setFont(F_BOLD, 14)
                c.setFillColor(HexColor(TEXTO))
                c.drawString(mx_, my - 16, val)
            yy -= 3 * 34 + 4
            link = post["permalink"]
            if link:
                c.setFont(F_REG, 9.5)
                c.setFillColor(HexColor(ACENTO))
                txt = fit_text(link, F_REG, 9.5, cw)
                c.drawString(x, yy, txt)
                c.linkURL(link, (x, yy - 3, x + stringWidth(txt, F_REG, 9.5), yy + 10), relative=0)
            else:
                c.setFont(F_REG, 9.5)
                c.setFillColor(HexColor(GRIS))
                c.drawString(x, yy, "sin enlace")

    # -- P3
    def p3(self, posts):
        c = self.c
        y = self.nueva("")
        y = self.titulo(y, "Ranking de la semana", "Engagement por posteo")
        orden = sorted(posts, key=lambda p: -p["eng"])[:12]
        ruta = os.path.join(self.tmp, "ranking.png")
        w_in, h_in = grafico_ranking(orden, ruta)
        gh = h_in * 72
        c.drawImage(ruta, M, y - gh, CW, gh)
        y -= gh + 22
        c.setFont(F_BOLD, 9.5)
        c.setFillColor(HexColor(ACENTO))
        c.drawString(M, y, "TODOS LOS POSTEOS, DE MAYOR A MENOR ENGAGEMENT")
        y -= 14
        n = len(orden)
        if not n:
            return
        cols = 4 if n <= 8 else 6
        gap = 10
        tw = (CW - (cols - 1) * gap) / cols
        filas = -(-n // cols)
        disp = y - 62
        th = tw * 1.25
        if filas * (th + 30) > disp:
            th = disp / filas - 30
            tw2 = th / 1.25
            gap = (CW - cols * tw2) / (cols - 1) if cols > 1 else 0
            tw = tw2
        off = (CW - (cols * tw + (cols - 1) * gap)) / 2
        for i, p in enumerate(orden):
            r, k = divmod(i, cols)
            x = M + off + k * (tw + gap)
            ty = y - r * (th + 30) - th
            self.imagen_post(p, x, ty, tw, th, f"th_{i}.jpg")
            c.setFillColor(HexColor(ACENTO))
            c.circle(x + 11, ty + th - 11, 8, stroke=0, fill=1)
            c.setFont(F_BOLD, 8.5)
            c.setFillColor(white)
            c.drawCentredString(x + 11, ty + th - 14, str(i + 1))
            c.setFont(F_BOLD, 11)
            c.setFillColor(HexColor(TEXTO))
            c.drawString(x, ty - 14, fmt_dec(p["eng"]) + " %")
            c.setFont(F_REG, 8.5)
            c.setFillColor(HexColor(GRIS))
            c.drawRightString(x + tw, ty - 14, fecha_corta(p["dt"]))

    # -- P4
    def p4(self, d):
        c = self.c
        y = self.nueva("")
        y = self.titulo(y, "Cuándo publicar", "Mejores momentos y formatos")
        h = d.get("heatmap") or {}
        tit = clean(h.get("titulo")) or "Engagement según día y hora de publicación"
        y = self.parrafo(M, y - 4, tit, F_BOLD, 11, CW, lead=15)
        ruta = os.path.join(self.tmp, "heatmap.png")
        mejor, dias, mx = grafico_heatmap(h, ruta)
        gh = 2.7 * 72
        c.drawImage(ruta, M, y - gh - 2, CW, gh)
        y -= gh + 22
        if mejor:
            c.setFont(F_REG, 10.5)
            c.setFillColor(HexColor(TEXTO))
            dia = dias[mejor[0]] or "—"
            c.drawString(M, y, f"Franja más fuerte (recuadrada): {dia}, {mejor[1]} h, con "
                               f"{fmt_int(mx)} de alcance típico. Más oscuro = mejor rendimiento.")
        y -= 44
        c.setFont(F_BOLD, 9.5)
        c.setFillColor(HexColor(ACENTO))
        c.drawString(M, y, "RENDIMIENTO POR FORMATO")
        y -= 12
        fm = [f for f in (d.get("por_formato") or []) if isinstance(f, dict)][:6]
        if not fm:
            c.setFont(F_REG, 10.5)
            c.setFillColor(HexColor(GRIS))
            c.drawString(M, y - 14, "Sin datos por formato esta semana.")
            return
        ruta2 = os.path.join(self.tmp, "formatos.png")
        _, h2 = grafico_formatos(fm, ruta2)
        gh2 = h2 * 72
        c.drawImage(ruta2, M, y - gh2, CW, gh2)
        c.setFont(F_REG, 9)
        c.setFillColor(HexColor(GRIS))
        c.drawString(M, y - gh2 - 14, "Últimas 4 semanas. Entre paréntesis, cantidad de posteos de cada formato.")

    # -- P5
    def p5(self, rec):
        c = self.c
        y = self.nueva("")
        y = self.titulo(y, "Qué hacer la semana próxima", "Recomendaciones")
        bloques = [("Contenido", [clean(s) for s in (rec.get("contenido") or []) if clean(s)]),
                   ("Horarios", [clean(s) for s in (rec.get("horarios") or []) if clean(s)])]
        disp = y - 70
        ind = 18
        for size in (11.5, 11, 10.5, 10):
            lead = size * 1.45
            tot = 0
            for _, its in bloques:
                tot += 46
                if not its:
                    tot += lead
                for it in its:
                    tot += len(simpleSplit(it, F_REG, size, CW - ind)) * lead + 9
            if tot <= disp:
                break
        for nombre, its in bloques:
            c.setFont(F_BOLD, 15)
            c.setFillColor(HexColor(TEXTO))
            c.drawString(M, y, nombre)
            y -= 8
            c.setStrokeColor(HexColor(ACENTO))
            c.setLineWidth(1.6)
            c.line(M, y, M + 34, y)
            y -= 24
            if not its:
                c.setFont(F_REG, size)
                c.setFillColor(HexColor(GRIS))
                c.drawString(M, y, "Sin recomendaciones esta semana.")
                y -= lead
            for it in its:
                lines = simpleSplit(it, F_REG, size, CW - ind)
                if y - len(lines) * lead < 64:
                    break
                c.setFillColor(HexColor(ACENTO))
                c.rect(M + 1, y + 1.5, 5, 5, stroke=0, fill=1)
                y = self.parrafo(M + ind, y, it, F_REG, size, CW - ind, lead=lead)
                y -= 9
            y -= 22

    def cerrar(self):
        self.c.save()


# ----------------------------------------------------------------- DATOS
def normalizar(d, base):
    d = d if isinstance(d, dict) else {}
    r = d.get("resumen") or {}
    rs = {k: num(r.get(k)) for k in ("seguidores", "seguidores_delta", "alcance", "interacciones",
                                     "engagement_pct", "publicaciones")}
    rs["alcance_delta_pct"] = None if r.get("alcance_delta_pct") is None else num(r.get("alcance_delta_pct"))
    rs["engagement_delta_pp"] = None if r.get("engagement_delta_pp") is None else num(r.get("engagement_delta_pp"))
    posts = []
    for p in d.get("posts") or []:
        if not isinstance(p, dict):
            continue
        img = p.get("imagen")
        posts.append({
            "id": str(p.get("id", "")), "dt": parse_dt(p.get("fecha")), "tipo": p.get("tipo"),
            "caption": clean(p.get("caption")), "permalink": str(p.get("permalink") or "").strip(),
            "img_abs": os.path.normpath(os.path.join(base, img)) if img else None,
            "alcance": num(p.get("alcance")), "likes": num(p.get("likes")),
            "comentarios": num(p.get("comentarios")), "guardados": num(p.get("guardados")),
            "compartidos": num(p.get("compartidos")), "interacciones": num(p.get("interacciones")),
            "eng": num(p.get("engagement_pct")),
        })
    return d, rs, posts


def elegir(posts, pid, mayor):
    for p in posts:
        if pid and p["id"] == str(pid):
            return p
    if not posts:
        return None
    return (max if mayor else min)(posts, key=lambda p: p["eng"])


def main():
    if len(sys.argv) != 3:
        print("Uso: python armar_pdf.py datos.json salida.pdf")
        sys.exit(1)
    entrada, salida = sys.argv[1], sys.argv[2]
    with open(entrada, encoding="utf-8-sig") as f:
        datos = json.load(f)
    d, rs, posts = normalizar(datos, os.path.dirname(os.path.abspath(entrada)))
    tmp = tempfile.mkdtemp(prefix="yeca_")
    try:
        inf = Informe(salida, tmp)
        inf.p1(d, rs)
        inf.p2(elegir(posts, d.get("mejor_post_id"), True), elegir(posts, d.get("peor_post_id"), False))
        inf.p3(posts)
        inf.p4(d)
        inf.p5(d.get("recomendaciones") or {})
        inf.cerrar()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"PDF generado: {salida} ({inf.pag} páginas)")


if __name__ == "__main__":
    main()


