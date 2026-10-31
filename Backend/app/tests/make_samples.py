"""Generates printed English invoices (ruled table + plain text) for testing."""
from PIL import Image, ImageDraw, ImageFont
import random, math

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
ROWS = [("Coca-Cola 330ml", 24, 0.45), ("Angkor Beer can", 48, 0.60),
        ("Instant Noodles Mama", 30, 0.18), ("Mineral Water 1.5L", 20, 0.35)]


def make(path, grid=True, angle=0.0):
    img = Image.new("L", (1000, 700), 255)
    d = ImageDraw.Draw(img)
    f, fb = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 26)
    d.text((40, 30), "Sok Wholesale Co.", font=fb, fill=0)
    d.text((620, 30), "Invoice No. INV-20418", font=f, fill=0)
    d.text((620, 65), "Date: 12/10/2026", font=f, fill=0)
    xs = [40, 90, 520, 650, 800, 960]
    ys = [140 + 55 * i for i in range(len(ROWS) + 2)]
    hdr = ["No", "Description", "Quantity", "Unit Price", "Amount"]
    if grid:
        for y in ys: d.line([(xs[0], y), (xs[-1], y)], fill=0, width=2)
        for x in xs: d.line([(x, ys[0]), (x, ys[-1])], fill=0, width=2)
    for i, h in enumerate(hdr): d.text((xs[i] + 10, ys[0] + 14), h, font=f, fill=0)
    for r, (n, q, u) in enumerate(ROWS, 1):
        cells = [str(r), n, str(q), f"${u:.2f}", f"${q * u:.2f}"]
        for i, c in enumerate(cells): d.text((xs[i] + 10, ys[r] + 14), c, font=f, fill=0)
    if angle: img = img.rotate(angle, expand=False, fillcolor=255)
    img.save(path)


if __name__ == "__main__":
    make("sample_grid.png")
    make("sample_grid_tilted.png", angle=2.5)
    make("sample_text.png", grid=False)
