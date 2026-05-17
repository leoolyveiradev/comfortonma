"""
build.py — Comfortonma Black
=============================
Script que gera a fonte Comfortonma Black a partir da Comfortaa Bold.

Autor: Leonardo Oliveira
Email: leoolyveiradev@gmail.com
GitHub: https://github.com/leoolyveiradev

Como usar:
----------
1. Instale a dependência:
   pip install fonttools

2. Certifique-se de que o arquivo sources/Comfortaa-Bold.ttf está presente.

3. Execute na raiz do repositório:
   python build.py

4. O arquivo fonts/ttf/Comfortonma-Black.ttf será gerado.
"""

import math
import os
from fontTools.ttLib import TTFont

# -----------------------------------------------------------------
# Caminhos
# -----------------------------------------------------------------
INPUT_FILE  = os.path.join("sources", "Comfortaa-Bold.ttf")
OUTPUT_FILE = os.path.join("fonts", "ttf", "Comfortonma-Black.ttf")

# -----------------------------------------------------------------
# Parâmetros de geração
# -----------------------------------------------------------------
# Quantidade de expansão dos contornos em unidades da fonte (UPM = 1000).
# Valor atual equivale a um peso Black (900).
EXPAND_AMOUNT = 55


def offset_contour(coords, end_pts, expand):
    """
    Expande cada contorno do glifo para fora, calculando a normal
    perpendicular em cada ponto. Preserva as curvas arredondadas originais.

    Args:
        coords:   lista de tuplas (x, y) com as coordenadas do glifo
        end_pts:  lista de índices de fim de cada contorno
        expand:   quantidade de unidades para expandir

    Returns:
        Lista de novas coordenadas expandidas.
    """
    new_coords = list(coords)
    start = 0

    for end in end_pts:
        contour = list(coords[start:end + 1])
        n = len(contour)

        if n < 2:
            start = end + 1
            continue

        # Calcula a normal perpendicular de cada ponto
        normals = []
        for i in range(n):
            prev  = contour[(i - 1) % n]
            next_ = contour[(i + 1) % n]
            dx = next_[0] - prev[0]
            dy = next_[1] - prev[1]
            length = math.hypot(dx, dy)
            if length == 0:
                normals.append((0, 0))
            else:
                normals.append((-dy / length, dx / length))

        # Aplica o deslocamento
        for i in range(n):
            nx, ny = normals[i]
            x, y   = contour[i]
            new_coords[start + i] = (
                round(x + nx * expand),
                round(y + ny * expand),
            )

        start = end + 1

    return new_coords


def build():
    print("=" * 50)
    print("  Comfortonma Black — build.py")
    print("=" * 50)

    # Verifica se o arquivo de entrada existe
    if not os.path.exists(INPUT_FILE):
        print(f"\n✗ Arquivo de entrada não encontrado: {INPUT_FILE}")
        print("  Certifique-se de que Comfortaa-Bold.ttf está em sources/")
        return

    # Cria as pastas de saída se não existirem
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    print(f"\n→ Abrindo: {INPUT_FILE}")
    font       = TTFont(INPUT_FILE)
    glyf_table = font["glyf"]
    hmtx       = font["hmtx"]

    # --- Expansão dos glifos ---
    print(f"→ Expandindo contornos ({EXPAND_AMOUNT} unidades)...")
    processed = 0
    skipped   = 0

    for name in font.getGlyphOrder():
        g = glyf_table[name]

        if g.isComposite() or not hasattr(g, "coordinates") or g.numberOfContours <= 0:
            skipped += 1
            continue

        coords  = list(g.coordinates)
        end_pts = list(g.endPtsOfContours)

        new_coords = offset_contour(coords, end_pts, EXPAND_AMOUNT)
        g.coordinates = g.coordinates.__class__(new_coords)
        g.recalcBounds(glyf_table)

        adv, lsb = hmtx[name]
        hmtx[name] = (adv + round(EXPAND_AMOUNT * 1.5), lsb + round(EXPAND_AMOUNT * 0.3))

        processed += 1

    print(f"  ✓ {processed} glifos expandidos, {skipped} compostos ignorados")

    # --- Metadados ---
    print("→ Atualizando metadados...")

    font["OS/2"].usWeightClass = 900
    font["hhea"].advanceWidthMax += round(EXPAND_AMOUNT * 1.5)

    for rec in font["name"].names:
        try:
            val = rec.toUnicode()
            if rec.nameID == 0:
                rec.string = (
                    "Copyright 2011 The Comfortaa Project Authors "
                    "(https://github.com/googlefonts/comfortaa), "
                    "with Reserved Font Name \"Comfortonma\".\n"
                    "Comfortonma Black copyright 2024 Leonardo Oliveira "
                    "(leoolyveiradev@gmail.com, https://github.com/leoolyveiradev)."
                ).encode(rec.getEncoding())
            elif "Comfortaa" in val or "Bold" in val:
                new_val = val.replace("Comfortaa", "Comfortonma").replace("Bold", "Black").strip()
                rec.string = new_val.encode(rec.getEncoding())
        except Exception:
            pass

    # --- Salva ---
    print(f"→ Salvando: {OUTPUT_FILE}")
    font.save(OUTPUT_FILE)

    size_kb = os.path.getsize(OUTPUT_FILE) // 1024
    print(f"\n✓ Fonte gerada com sucesso! ({size_kb} KB)")
    print(f"  {OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    build()
