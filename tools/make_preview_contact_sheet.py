from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT / "outputs" / "gold_standard_validation" / "_xlsx_previews"


def main() -> None:
    files = sorted(PREVIEWS.rglob("*.png"))
    thumb_width = 760
    label_height = 34
    margin = 20
    cards = []
    font = ImageFont.load_default(size=18)
    for file in files:
        image = Image.open(file).convert("RGB")
        ratio = thumb_width / image.width
        thumb = image.resize((thumb_width, max(1, int(image.height * ratio))))
        cards.append((file.relative_to(PREVIEWS).as_posix(), thumb))

    columns = 2
    rows = (len(cards) + columns - 1) // columns
    row_heights = []
    for row in range(rows):
        group = cards[row * columns : (row + 1) * columns]
        row_heights.append(max(card.height for _, card in group) + label_height + margin)
    canvas = Image.new(
        "RGB",
        (columns * (thumb_width + margin) + margin, sum(row_heights) + margin),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    y = margin
    for row in range(rows):
        group = cards[row * columns : (row + 1) * columns]
        for col, (label, card) in enumerate(group):
            x = margin + col * (thumb_width + margin)
            draw.text((x, y), label, fill="#17365D", font=font)
            canvas.paste(card, (x, y + label_height))
            draw.rectangle(
                (x, y + label_height, x + card.width, y + label_height + card.height),
                outline="#B4C6E7",
                width=2,
            )
        y += row_heights[row]
    output = PREVIEWS / "contact_sheet.png"
    canvas.save(output)
    print(output)


if __name__ == "__main__":
    main()
