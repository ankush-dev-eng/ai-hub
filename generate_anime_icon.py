from PIL import Image, ImageDraw, ImageFilter

size = 512
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Deep dark cyber shield background with rounded hexagon
poly = [
    (256, 16),
    (480, 120),
    (480, 392),
    (256, 496),
    (32, 392),
    (32, 120)
]
draw.polygon(poly, fill=(11, 13, 22, 255), outline=(99, 102, 241, 220), width=6)

# Outer cyber circuit glow
glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow)
glow_draw.polygon(poly, outline=(34, 211, 238, 180), width=12)
glow = glow.filter(ImageFilter.GaussianBlur(8))
img = Image.alpha_composite(img, glow)
draw = ImageDraw.Draw(img)

# Inner Mecha Helmet / Anime Cyber Mask Silhouettes
# Crest / Crown Horns (Gundam / Evangelion style angular V-fin)
v_fin_left = [(256, 110), (160, 40), (140, 60), (240, 130)]
v_fin_right = [(256, 110), (352, 40), (372, 60), (272, 130)]
draw.polygon(v_fin_left, fill=(244, 63, 94, 255), outline=(255, 255, 255, 200), width=2)
draw.polygon(v_fin_right, fill=(244, 63, 94, 255), outline=(255, 255, 255, 200), width=2)

# Central forehead gem / power core (Hexagon cyan)
gem = [
    (256, 95), (280, 110), (280, 140), (256, 155), (232, 140), (232, 110)
]
draw.polygon(gem, fill=(34, 211, 238, 255), outline=(255, 255, 255, 255), width=3)

# Face mask upper plate (Dark obsidian armor)
mask_upper = [
    (150, 160), (256, 180), (362, 160),
    (390, 260), (330, 340), (256, 370), (182, 340), (122, 260)
]
draw.polygon(mask_upper, fill=(20, 24, 38, 255), outline=(129, 140, 248, 200), width=4)

# Glowing Anime Slanted Visor Eyes (Cyberpunk Neon Cyan & Electric Violet)
# Left eye
eye_l = [(175, 240), (240, 248), (235, 270), (185, 258)]
draw.polygon(eye_l, fill=(34, 211, 238, 255), outline=(255, 255, 255, 255), width=2)
# Right eye
eye_r = [(337, 240), (272, 248), (277, 270), (327, 258)]
draw.polygon(eye_r, fill=(34, 211, 238, 255), outline=(255, 255, 255, 255), width=2)

# Eye Glow Layer
eye_glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
eg_draw = ImageDraw.Draw(eye_glow)
eg_draw.polygon(eye_l, fill=(34, 211, 238, 240))
eg_draw.polygon(eye_r, fill=(34, 211, 238, 240))
eg_draw.ellipse([240, 100, 272, 135], fill=(34, 211, 238, 240))
eye_glow = eye_glow.filter(ImageFilter.GaussianBlur(12))
img = Image.alpha_composite(img, eye_glow)
draw = ImageDraw.Draw(img)

# Lower Face Mask Ventilation & Cyber Slits (Mecha Mouth Guard)
slits_y = [295, 312, 329]
for sy in slits_y:
    w = 35 - (sy - 295) * 0.6
    draw.line([(256 - w, sy), (256 + w, sy)], fill=(99, 102, 241, 220), width=3)

# Chin Guard point
chin = [(236, 360), (276, 360), (256, 420)]
draw.polygon(chin, fill=(244, 63, 94, 255), outline=(255, 255, 255, 180), width=2)

# Side ear antennas / cyber audio sensors
draw.polygon([(100, 210), (130, 190), (130, 280), (100, 260)], fill=(30, 36, 56, 255), outline=(34, 211, 238, 200), width=3)
draw.polygon([(412, 210), (382, 190), (382, 280), (412, 260)], fill=(30, 36, 56, 255), outline=(34, 211, 238, 200), width=3)

# Save multi-size ICO
icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save("app_icon.ico", format="ICO", sizes=icon_sizes)
img.save("app_icon_anime.png", format="PNG")
print("SUCCESS: app_icon.ico saved with anime cyberpunk mecha AI styling!")
