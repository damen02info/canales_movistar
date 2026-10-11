import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def generate_icons() -> None:
    scale = 4
    canvas_size = 256 * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

    margin = 18 * scale
    rect_box = [margin, margin, canvas_size - margin, canvas_size - margin]
    radius = 54 * scale

    # Ambient glow
    glow = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.rounded_rectangle(rect_box, radius=radius, fill=(0, 180, 240, 50))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=10 * scale))
    img.alpha_composite(glow)

    # Dark background gradient
    gradient = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gradient)
    y_min, y_max = margin, canvas_size - margin
    total_h = y_max - y_min
    for y in range(y_min, y_max):
        t = (y - y_min) / float(total_h)
        r = int(12 * (1 - t) + 7 * t)
        g = int(16 * (1 - t) + 8 * t)
        b = int(24 * (1 - t) + 11 * t)
        g_draw.line([(margin, y), (canvas_size - margin, y)], fill=(r, g, b, 255))

    mask = Image.new("L", (canvas_size, canvas_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(rect_box, radius=radius, fill=255)
    img.paste(gradient, (0, 0), mask)

    # Border stroke
    border_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(border_layer)
    b_draw.rounded_rectangle(
        rect_box,
        radius=radius,
        outline=(55, 65, 85, 255),
        width=int(2.5 * scale),
    )

    top_rim = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    tr_draw = ImageDraw.Draw(top_rim)
    tr_draw.rounded_rectangle(
        rect_box,
        radius=radius,
        outline=(0, 195, 255, 140),
        width=int(2.5 * scale),
    )

    top_mask = Image.new("L", (canvas_size, canvas_size), 0)
    tm_draw = ImageDraw.Draw(top_mask)
    for y in range(margin, margin + int(total_h * 0.4)):
        fade = int(255 * (1 - (y - margin) / (total_h * 0.4)))
        tm_draw.line([(0, y), (canvas_size, y)], fill=fade)

    border_layer.paste(top_rim, (0, 0), top_mask)
    img.alpha_composite(border_layer)

    # Typography
    font_candidates = [
        "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    font_path = next((p for p in font_candidates if os.path.exists(p)), None)

    font_m_size = int(118 * scale)
    font_plus_size = int(84 * scale)

    if font_path:
        font_m = ImageFont.truetype(font_path, font_m_size)
        font_plus = ImageFont.truetype(font_path, font_plus_size)
    else:
        font_m = ImageFont.load_default()
        font_plus = ImageFont.load_default()

    m_bbox = font_m.getbbox("M")
    plus_bbox = font_plus.getbbox("+")

    m_w = m_bbox[2] - m_bbox[0]
    m_h = m_bbox[3] - m_bbox[1]
    plus_w = plus_bbox[2] - plus_bbox[0]
    plus_h = plus_bbox[3] - plus_bbox[1]

    gap = int(7 * scale)
    total_w = m_w + gap + plus_w

    start_x = (canvas_size - total_w) // 2 - int(2 * scale)
    center_y = canvas_size // 2

    m_x = start_x - m_bbox[0]
    m_y = center_y - (m_h // 2) - m_bbox[1]

    txt_draw = ImageDraw.Draw(img)
    txt_draw.text((m_x, m_y + int(2.5 * scale)), "M", font=font_m, fill=(0, 0, 0, 160))
    txt_draw.text((m_x, m_y), "M", font=font_m, fill=(244, 244, 246, 255))

    plus_x = start_x + m_w + gap - plus_bbox[0]
    plus_y = center_y - (plus_h // 2) - plus_bbox[1] - int(6 * scale)

    plus_glow = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    pg_draw = ImageDraw.Draw(plus_glow)
    pg_draw.text((plus_x, plus_y), "+", font=font_plus, fill=(0, 195, 255, 140))
    plus_glow = plus_glow.filter(ImageFilter.GaussianBlur(radius=6 * scale))
    img.alpha_composite(plus_glow)

    final_draw = ImageDraw.Draw(img)
    final_draw.text((plus_x, plus_y), "+", font=font_plus, fill=(0, 205, 255, 255))

    master = img.resize((512, 512), Image.Resampling.LANCZOS)

    out_dir = Path(__file__).resolve().parent.parent / "static"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Multi-resolution icons
    master.save(out_dir / "icon.png", "PNG")
    master.save(
        out_dir / "icon.ico",
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    master.save(
        out_dir / "favicon.ico",
        format="ICO",
        sizes=[(64, 64), (32, 32), (16, 16)],
    )

if __name__ == "__main__":
    generate_icons()
