import io
import logging
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)
CARD_WIDTH = 900
CARD_HEIGHT = 300
AVATAR_SIZE = 180
FONT_PATH: Optional[str] = None

def _load_font(size: int):
    if FONT_PATH:
        try: return ImageFont.truetype(FONT_PATH, size)
        except Exception: pass
    try: return ImageFont.load_default(size=size)
    except TypeError: return ImageFont.load_default()

def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip('#')
    if len(h) != 6: return (43, 45, 49)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def render_level_card(avatar_bytes: bytes, username: str, new_level: int, current_xp_in_level: int, xp_needed_for_next_level: int, background_color: str = '#2b2d31', accent_color: str = '#57F287') -> bytes:
    bg = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), _hex_to_rgb(background_color))
    draw = ImageDraw.Draw(bg)
    accent = _hex_to_rgb(accent_color)
    draw.rectangle([(0, 0), (14, CARD_HEIGHT)], fill=accent)
    try: avatar = Image.open(io.BytesIO(avatar_bytes)).convert('RGBA').resize((AVATAR_SIZE, AVATAR_SIZE))
    except Exception as exc:
        logger.warning('Could not decode avatar: %s', exc)
        avatar = Image.new('RGBA', (AVATAR_SIZE, AVATAR_SIZE), accent)
    mask = Image.new('L', (AVATAR_SIZE, AVATAR_SIZE), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
    avatar_x, avatar_y, ring_pad = 60, (CARD_HEIGHT - AVATAR_SIZE) // 2, 6
    draw.ellipse((avatar_x-ring_pad, avatar_y-ring_pad, avatar_x+AVATAR_SIZE+ring_pad, avatar_y+AVATAR_SIZE+ring_pad), fill=accent)
    bg.paste(avatar, (avatar_x, avatar_y), mask)
    text_x = avatar_x + AVATAR_SIZE + 50
    draw.text((text_x, 55), 'LEVEL UP!', font=_load_font(26), fill=accent)
    draw.text((text_x, 90), username, font=_load_font(44), fill=(255, 255, 255))
    draw.text((text_x, 148), f'Level {new_level}', font=_load_font(34), fill=(255, 255, 255))
    bar_x, bar_y, bar_w, bar_h = text_x, 205, CARD_WIDTH - text_x - 60, 26
    draw.rounded_rectangle((bar_x, bar_y, bar_x+bar_w, bar_y+bar_h), radius=bar_h//2, fill=(60, 63, 68))
    fraction = max(0.0, min(1.0, current_xp_in_level / xp_needed_for_next_level)) if xp_needed_for_next_level > 0 else 1.0
    fill_w = max(bar_h, int(bar_w*fraction)) if fraction > 0 else 0
    if fill_w: draw.rounded_rectangle((bar_x, bar_y, bar_x+fill_w, bar_y+bar_h), radius=bar_h//2, fill=accent)
    draw.text((bar_x, bar_y+bar_h+8), f'{current_xp_in_level}/{xp_needed_for_next_level} XP', font=_load_font(20), fill=(200, 200, 200))
    out = io.BytesIO(); bg.save(out, format='PNG'); return out.getvalue()
