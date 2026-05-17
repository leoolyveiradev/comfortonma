"""
engrossar_comfortaa.py — Gerador da Comfortonma Black
======================================================
Transforma a Comfortaa Bold em uma versão Black (900) expandindo
os contornos de cada glifo para fora de forma inteligente:

  - Calcula a normal perpendicular nos pontos on-curve
  - Interpola a normal nos pontos off-curve (pontos de controle das curvas)
  - Move todos os pontos na direção da normal calculada

Isso preserva muito melhor as curvas arredondadas da Comfortaa
do que simplesmente escalar a partir do centroide.

Autor: Leonardo Oliveira
Email: leoolyveiradev@gmail.com
GitHub: https://github.com/leoolyveiradev

Como usar:
----------
1. Instale as dependências:
       pip install fonttools Pillow

2. Coloque este script na raiz do repositório e certifique-se de que
   o arquivo sources/Comfortaa-Bold.ttf está presente.

3. Execute:
       python engrossar_comfortaa.py

4. Os arquivos gerados serão:
       fonts/ttf/Comfortonma-Black.ttf   ← a fonte
       preview/Comfortonma-preview.png   ← imagem de prévia

Parâmetros ajustáveis
---------------------
  EXPAND_AMOUNT  →  espessura extra em unidades da fonte (UPM=1000).
                    55 = Black (900). Tente 40–80 para variar.
"""

import math
import os
from fontTools.ttLib import TTFont

# -----------------------------------------------------------------
# Caminhos
# -----------------------------------------------------------------
INPUT_FILE   = os.path.join("sources", "Comfortaa-Bold.ttf")
OUTPUT_FILE  = os.path.join("fonts", "ttf", "Comfortonma-Black.ttf")
PREVIEW_FILE = os.path.join("preview", "Comfortonma-preview.png")

# -----------------------------------------------------------------
# Parâmetros
# -----------------------------------------------------------------
EXPAND_AMOUNT = 55   # unidades de expansão (55 ≈ peso Black/900)


# ─────────────────────────────────────────────────────────────────
# Funções de expansão
# ─────────────────────────────────────────────────────────────────

def _normal_at_point(prev, curr, next_pt):
    """
    Calcula a normal média entre os dois segmentos que chegam e saem
    de um ponto. Retorna um vetor unitário (nx, ny).
    """
    dx1, dy1 = curr[0] - prev[0],    curr[1] - prev[1]
    dx2, dy2 = next_pt[0] - curr[0], next_pt[1] - curr[1]
    l1 = math.hypot(dx1, dy1)
    l2 = math.hypot(dx2, dy2)

    nx = ny = 0.0
    if l1 > 0:
        nx += -dy1 / l1
        ny +=  dx1 / l1
    if l2 > 0:
        nx += -dy2 / l2
        ny +=  dx2 / l2

    length = math.hypot(nx, ny)
    return (nx / length, ny / length) if length > 0 else (0.0, 0.0)


def expand_contours(coords, flags, end_pts, expand):
    """
    Expande todos os contornos de um glifo para fora em `expand` unidades.

    Estratégia:
      1. Para pontos on-curve (flag bit 0 = 1): calcula a normal real.
      2. Para pontos off-curve (pontos de controle Bézier): interpola
         a normal entre os dois vizinhos on-curve mais próximos.
         Isso mantém a suavidade das curvas após a expansão.

    Args:
        coords:   lista de tuplas (x, y)
        flags:    lista de flags TrueType por ponto
        end_pts:  lista de índices de fim de cada contorno
        expand:   quantidade de unidades para deslocar

    Returns:
        Lista de novas tuplas (x, y) expandidas.
    """
    coords  = list(coords)
    flags   = list(flags)
    normals = [(0.0, 0.0)] * len(coords)

    start = 0
    for end in end_pts:
        seg = list(range(start, end + 1))
        ns  = len(seg)

        # Passo 1 — normais nos pontos on-curve
        for ii, idx in enumerate(seg):
            if flags[idx] & 1:
                prev_idx = seg[(ii - 1) % ns]
                next_idx = seg[(ii + 1) % ns]
                normals[idx] = _normal_at_point(
                    coords[prev_idx], coords[idx], coords[next_idx]
                )

        # Passo 2 — normais interpoladas nos pontos off-curve
        for ii, idx in enumerate(seg):
            if not (flags[idx] & 1):
                prev_on = next_on = None
                for d in range(1, ns):
                    p = seg[(ii - d) % ns]
                    if flags[p] & 1:
                        prev_on = p
                        break
                for d in range(1, ns):
                    p = seg[(ii + d) % ns]
                    if flags[p] & 1:
                        next_on = p
                        break
                if prev_on is not None and next_on is not None:
                    nx = (normals[prev_on][0] + normals[next_on][0]) / 2
                    ny = (normals[prev_on][1] + normals[next_on][1]) / 2
                    length = math.hypot(nx, ny)
                    normals[idx] = (nx / length, ny / length) if length > 0 else (0.0, 0.0)

        start = end + 1

    # Aplica o deslocamento em todos os pontos
    return [
        (round(x + nx * expand), round(y + ny * expand))
        for (x, y), (nx, ny) in zip(coords, normals)
    ]


# ─────────────────────────────────────────────────────────────────
# Geração da fonte
# ─────────────────────────────────────────────────────────────────

def build_font():
    if not os.path.exists(INPUT_FILE):
        print(f"\n✗ Arquivo de entrada não encontrado: {INPUT_FILE}")
        print("  Coloque 'Comfortaa-Bold.ttf' dentro da pasta 'sources/'.\n")
        return False

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    print(f"→ Abrindo: {INPUT_FILE}")
    font       = TTFont(INPUT_FILE)
    glyf_table = font["glyf"]
    hmtx       = font["hmtx"]

    print(f"→ Expandindo contornos ({EXPAND_AMOUNT} unidades)...")
    processed = skipped = 0

    for name in font.getGlyphOrder():
        g = glyf_table[name]

        if g.isComposite() or not hasattr(g, "coordinates") or g.numberOfContours <= 0:
            skipped += 1
            continue

        new_coords = expand_contours(
            g.coordinates, g.flags, g.endPtsOfContours, EXPAND_AMOUNT
        )
        g.coordinates = g.coordinates.__class__(new_coords)
        g.recalcBounds(glyf_table)

        adv, lsb = hmtx[name]
        hmtx[name] = (
            adv + round(EXPAND_AMOUNT * 1.5),
            lsb + round(EXPAND_AMOUNT * 0.3),
        )
        processed += 1

    print(f"  ✓ {processed} glifos expandidos | {skipped} compostos mantidos")

    # Metadados
    print("→ Atualizando metadados...")
    font["OS/2"].usWeightClass = 900
    font["hhea"].advanceWidthMax += round(EXPAND_AMOUNT * 1.5)

    copyright_str = (
        "Copyright 2011 The Comfortaa Project Authors "
        "(https://github.com/googlefonts/comfortaa), "
        "with Reserved Font Name \"Comfortonma\".\n"
        "Comfortonma Black copyright 2024 Leonardo Oliveira "
        "(leoolyveiradev@gmail.com, https://github.com/leoolyveiradev)."
    )

    for rec in font["name"].names:
        try:
            val = rec.toUnicode()
            if rec.nameID == 0:
                rec.string = copyright_str.encode(rec.getEncoding())
            elif "Comfortaa" in val or "Bold" in val:
                new_val = (
                    val.replace("Comfortaa", "Comfortonma")
                       .replace("Bold", "Black")
                       .strip()
                )
                rec.string = new_val.encode(rec.getEncoding())
        except Exception:
            pass

    print(f"→ Salvando: {OUTPUT_FILE}")
    font.save(OUTPUT_FILE)
    size_kb = os.path.getsize(OUTPUT_FILE) // 1024
    print(f"  ✓ {size_kb} KB")
    return True


# ─────────────────────────────────────────────────────────────────
# Preview (requer Pillow: pip install Pillow)
# ─────────────────────────────────────────────────────────────────

def build_preview():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  (Pillow não instalado — preview ignorado)")
        return

    os.makedirs(os.path.dirname(PREVIEW_FILE), exist_ok=True)

    W, H = 1000, 620
    img  = Image.new("RGB", (W, H), "#F7F7F5")
    draw = ImageDraw.Draw(img)

    def card(x, y, w, h, fill="#FFFFFF"):
        draw.rounded_rectangle([x, y, x+w, y+h], radius=14, fill=fill)

    lbl      = ImageFont.truetype(INPUT_FILE, 14)
    fo_orig  = ImageFont.truetype(INPUT_FILE, 72)
    fo_new   = ImageFont.truetype(OUTPUT_FILE, 72)
    fo_big   = ImageFont.truetype(OUTPUT_FILE, 108)
    fo_mid   = ImageFont.truetype(OUTPUT_FILE, 46)
    fo_small = ImageFont.truetype(OUTPUT_FILE, 26)

    # Card 1 — original
    card(30, 28, W-60, 128)
    draw.text((52, 44), "Comfortaa Bold — original", font=lbl, fill="#AAAAAA")
    draw.text((52, 64), "AaBbCcDd  Olá Mundo  123", font=fo_orig, fill="#1A1A1A")

    # Card 2 — nova fonte
    card(30, 178, W-60, 128)
    draw.text((52, 194), "Comfortonma Black — nova fonte", font=lbl, fill="#534AB7")
    draw.text((52, 214), "AaBbCcDd  Olá Mundo  123", font=fo_new, fill="#1A1A1A")

    # Card 3 — showcase escuro
    card(30, 328, W-60, 262, fill="#111111")
    draw.text((48, 338), "Design",                                  font=fo_big,   fill="#FFFFFF")
    draw.text((48, 458), "Tipografia  •  Branding  •  Arte",        font=fo_mid,   fill="#9D94E8")
    draw.text((48, 518), "ABCDEFGHIJKLMNOPQRSTUVWXYZ  0123456789", font=fo_small, fill="#555555")
    draw.text((48, 556), "abcdefghijklmnopqrstuvwxyz  !@#&?%",     font=fo_small, fill="#444444")

    img.save(PREVIEW_FILE, quality=97)
    print(f"  ✓ Preview salvo: {PREVIEW_FILE}")


# ─────────────────────────────────────────────────────────────────
# Execução
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 52)
    print("  Comfortonma Black — engrossar_comfortaa.py")
    print("=" * 52)

    ok = build_font()

    if ok:
        print("→ Gerando preview...")
        build_preview()
        print("\n✓ Tudo pronto!")
        print(f"  Fonte:   {OUTPUT_FILE}")
        print(f"  Preview: {PREVIEW_FILE}")

    print("=" * 52)
