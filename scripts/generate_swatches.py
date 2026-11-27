"""Generate original, deterministic SVG catalog swatches (stdlib only)."""
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parents[1] / "static" / "images"
PALETTES = {
    "sand": ("#b89271", "#d7b99b", "#ead4b9"), "chalk": ("#b8ab97", "#e3dbca", "#fff8e9"),
    "sage": ("#405b51", "#648073", "#9cae92"), "clay": ("#813b2b", "#b26046", "#df9676"),
    "ink": ("#252d37", "#414d57", "#7e8a8c"), "terrazzo": ("#bdab9b", "#e5d7c2", "#f5ead8"),
    "mosaic": ("#33565b", "#5a7f7b", "#a0aca0"), "grout": ("#87817b", "#afa9a2", "#ded9d4"),
}


def swatch(name, dark, mid, light):
    random = Random(name)
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 440" width="620" height="440">',
        (
            f'<defs><linearGradient id="tile" x2=".9" y2="1"><stop stop-color="{light}"/>'
            f'<stop offset=".49" stop-color="{mid}"/><stop offset="1" stop-color="{dark}"/>'
            '</linearGradient></defs>'
        ),
        f'<path fill="url(#tile)" d="M0 0h620v440H0z"/><path fill="{mid}" opacity=".25" d="M0 0h620v440H0z"/>',
    ]
    if name in ("sage", "clay", "mosaic"):
        width, height = (60, 55) if name == "mosaic" else (135, 83)
        svg.append(f'<path fill="{light}" opacity=".45" d="M0 0h620v440H0z"/>')
        for i, y in enumerate(range(-26, 440, height)):
            for x in range(-width // 2 * (i % 2), 620, width):
                color = random.choice((dark, mid, mid))
                svg.append(f'<rect x="{x}" y="{y}" width="{width - 3}" height="{height - 3}" rx="2" fill="{color}"/>')
                svg.append(f'<path d="M{x + 4} {y + 4}h{width - 12}" stroke="{light}" opacity=".25"/>')
    if name == "terrazzo":
        for _ in range(190):
            x, y = random.randrange(620), random.randrange(440)
            r = random.randrange(3, 15)
            color = random.choice((dark, light, "#5b7772", "#ae6b53", "#b99580"))
            svg.append(f'<path d="M{x} {y}l{r} -{r // 2} {r // 2} {r} -{r} {r // 2}z" fill="{color}" opacity=".65"/>')
    elif name not in ("sage", "clay", "mosaic"):
        for _ in range(28):
            y = random.randrange(440)
            wobble = random.randrange(-70, 50)
            svg.append(f'<path d="M-10 {y}q110 {wobble} 230 0t410 {wobble}" fill="none" stroke="{light}" '
                       f'stroke-width="{random.randint(1, 4)}" opacity=".15"/>')
    for _ in range(75):
        x, y = random.randrange(620), random.randrange(440)
        svg.append(f'<circle cx="{x}" cy="{y}" r="{random.choice((.7, 1, 2))}" fill="{dark}" opacity=".23"/>')
    svg.append("</svg>")
    (ROOT / f"{name}.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for key, palette in PALETTES.items():
        swatch(key, *palette)
