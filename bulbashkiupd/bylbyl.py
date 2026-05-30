import os
import json
import sounddevice as sd
import pygame
import numpy as np
import random
import math
import textwrap

pygame.mixer.init()

# ─── НАСТРОЙКИ ─────────────────────────────
WIDTH, HEIGHT = 1000, 650
FPS = 90
CHUNK = 1024
FS = 44100
MAX_BUBBLES = 500


pygame.init()
pygame.mixer.music.load("bgmus1.mp3")
pygame.mixer.music.set_volume(0.4)
pygame.mixer.music.play(-1)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Симулятор бульбашек")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Comic Sans MS", 28, bold=True)
small_font = pygame.font.SysFont("Comic Sans MS", 20, bold=True)

# ─── УТВЕРЖДЁННАЯ ПАЛИТРА (сине‑голубая тема) ──
# Аквамарин, циан, голубой, синий — в формате (R,G,B)
SEA_PALETTE = [
    (127, 255, 212),  # аквамарин
    (0, 255, 255),    # циан
    (100, 200, 255),  # небесно‑голубой
    (65, 105, 225),   # королевский синий
    (0, 191, 255),    # глубокий небесный
    (72, 209, 204),   # средний бирюзовый
    (0, 150, 255),    # ярко‑голубой
    (0, 100, 200),    # синий
]
# Тёмный фон (почти чёрный с синевой)
BG_COLOR = (5, 10, 25)
MENU_HEIGHT = 130
MENU_COLOR_TOP = (45, 45, 45)
MENU_COLOR_BOTTOM = (80, 80, 80)
MENU_WIDTH = 220
MENU_PANEL_PADDING = 20
MENU_BUTTON_WIDTH = 180
MENU_BUTTON_HEIGHT = 40
MENU_BUTTON_PADDING = 20
#--------СОХРАНЕНИЕ--------------------------------------------------------------------------
MENU_SECTION_HEIGHT = 120
SAVE_ENABLED = True
SAVE_FILE = "save_data.json"
MENU_SECTION_SPACING = 20
BUTTON_TEXT_COLOR = (240, 240, 240)
BUTTON_ON_COLOR = (26, 150, 220)
BUTTON_OFF_COLOR = (120, 120, 120)

# ─── УТИЛИТЫ ─────────────────────────────────
def create_vertical_gradient_surface(width, height, top_color, bottom_color, border_radius=0):
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = [
            int(top_color[i] + (bottom_color[i] - top_color[i]) * ratio)
            for i in range(3)
        ]
        pygame.draw.line(surface, (*color, 220), (0, y), (width, y))
    if border_radius > 0:
        mask = pygame.Surface((width, height), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=border_radius)
        surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.rect(surface, (255, 255, 255, 35), surface.get_rect(), 1, border_radius=border_radius)
    return surface

# ─── ФУНКЦИИ МАГАЗИНА ──────────────────────
def draw_shop(surf, shop_type=1):
    global shop_scroll_offset, current_shop
    # Полупрозрачный фон
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surf.blit(overlay, (0, 0))
    
    # Окно магазина
    shop_width, shop_height = 500, 400
    shop_x = (WIDTH - shop_width) // 2
    shop_y = (HEIGHT - shop_height) // 2
    
    # Фон окна
    pygame.draw.rect(surf, (20, 40, 60), (shop_x, shop_y, shop_width, shop_height))
    pygame.draw.rect(surf, (0, 200, 255), (shop_x, shop_y, shop_width, shop_height), 3)
    
    # Заголовок
    title = font.render(f"МАГАЗИН {shop_type}", True, (0, 230, 255))
    surf.blit(title, (shop_x + (shop_width - title.get_width()) // 2, shop_y + 15))
    
    # Кнопка переключения магазина
    switch_text = f"Магазин {3 - shop_type}"
    switch_button = pygame.Rect(shop_x + shop_width - 150, shop_y + 10, 140, 30)
    pygame.draw.rect(surf, (100, 150, 200), switch_button, border_radius=10)
    switch_surf = small_font.render(switch_text, True, (255, 255, 255))
    surf.blit(switch_surf, (switch_button.x + (switch_button.width - switch_surf.get_width()) // 2, switch_button.y + 2))
    
    # Товары
    if shop_type == 1:
        items = [
            {
                "name": "Больше пузырьков",
                "price": shop_prices["more_bubbles"],
                "desc": "Увеличивает максимальное количество пузырьков",
                "unlock": 1,
                "color": (50, 100, 150),
            },
            {
                "name": "Удавиватель денег",
                "price": shop_prices["money_doubler"],
                "desc": "Удваивает количество лопаний за каждый пузырек",
                "unlock": 1,
                "color": (50, 100, 150),
            },
            {
                "name": "Увеличение макс. размера",
                "price": shop_prices["max_size_upgrade"],
                "desc": "Увеличивает лимит роста размера на 0.5",
                "unlock": 3,
                "color": (80, 150, 220),
            },
            {
                "name": "Размер побольше",
                "price": shop_prices["size_boost"],
                "desc": "Увеличивает пузырек на 1.2×, 30% шанс удвоения",
                "unlock": 5,
                "color": (80, 150, 220),
            },
            {
                "name": "Автопоявление",
                "price": shop_prices["auto_spawn"],
                "desc": "Автоматически добавляет пузырьки без звука",
                "unlock": 10,
                "color": (50, 100, 150),
            },
            {
                "name": "Автолопанье",
                "price": shop_prices["auto_pop"],
                "desc": "Лопает пузырьки при наведении курсора без клика",
                "unlock": 20,
                "color": (255, 215, 0) if auto_pop_enabled else (205, 145, 0),
            },
            {
                "name": "Удвоение опыта",
                "price": shop_prices["experience_doubler"],
                "desc": "Удваивает получаемый опыт за лопанье пузырьков",
                "unlock": 5,
                "color": (80, 150, 220),
            },
        ]
    elif shop_type == 2:
        items = [
            {
                "name": "Расширение экрана",
                "price": shop_prices["screen_width_upgrade"],
                "desc": "Увеличивает экран на 50 пикселей в ширину",
                "unlock": 10,
                "color": (50, 100, 150),
            },
            {
                "name": "Увеличение громкости",
                "price": shop_prices["volume_boost"],
                "desc": "Увеличивает чувствительность микрофона",
                "unlock": 5,
                "color": (50, 100, 150),
            },
            {
                "name": "Разнообразие цветов",
                "price": shop_prices["color_variety"],
                "desc": "Добавляет новые цвета для пузырьков",
                "unlock": 3,
                "color": (80, 150, 220),
            },
        ]
    items.sort(key=lambda item: (item["unlock"], item["price"]))
    
    content_rect = pygame.Rect(shop_x + 20, shop_y + 70, shop_width - 40, shop_height - 100)
    pygame.draw.rect(surf, (15, 30, 45), content_rect, border_radius=12)
    
    item_buttons = []
    item_height = 130
    item_spacing = 30
    total_height = len(items) * item_height + (len(items) - 1) * item_spacing
    min_offset = min(0, content_rect.height - total_height)
    shop_scroll_offset = max(min(shop_scroll_offset, 0), min_offset)
    
    old_clip = surf.get_clip()
    surf.set_clip(content_rect)
    for i, item in enumerate(items):
        y_pos = content_rect.y + i * (item_height + item_spacing) + shop_scroll_offset
        item_name = item["name"] if level >= item["unlock"] else "???"
        item_text = small_font.render(item_name, True, (240, 240, 240))
        price_text = small_font.render(f"{item['price']} баллов", True, (255, 200, 100))
        desc_text = item["desc"] if level >= item["unlock"] else f"Доступно с {item['unlock']} уровня"
        desc_lines = textwrap.wrap(desc_text, width=32)
        desc_lines = desc_lines[:2]
        desc_font = pygame.font.SysFont("Comic Sans MS", 16, bold=False)
        
        button_rect = pygame.Rect(shop_x + 30, y_pos, shop_width - 60, item_height)
        pygame.draw.rect(surf, item["color"], button_rect, border_radius=12)
        pygame.draw.rect(surf, (255, 255, 255), button_rect, 2, border_radius=12)
        
        surf.blit(item_text, (button_rect.x + 10, button_rect.y + 8))
        if shop_type == 1 and item["name"] == "Автолопанье" and auto_pop_enabled:
            max_text = small_font.render("Макс.", True, (255, 200, 100))
            surf.blit(max_text, (button_rect.x + 10, button_rect.y + 36))
        else:
            surf.blit(price_text, (button_rect.x + 10, button_rect.y + 36))
        for j, line in enumerate(desc_lines):
            desc_text = desc_font.render(line, True, (180, 220, 255))
            surf.blit(desc_text, (button_rect.x + 10, button_rect.y + 60 + j * 20))
        
        item_buttons.append(button_rect)
    surf.set_clip(old_clip)
    
    if total_height > content_rect.height:
        scrollbar_height = max(40, int(content_rect.height * content_rect.height / total_height))
        scroll_progress = -shop_scroll_offset / (total_height - content_rect.height)
        scrollbar_y = content_rect.y + int(scroll_progress * (content_rect.height - scrollbar_height))
        pygame.draw.rect(surf, (70, 70, 90), (shop_x + shop_width - 18, content_rect.y + 5, 10, content_rect.height - 10), border_radius=5)
        pygame.draw.rect(surf, (180, 220, 255), (shop_x + shop_width - 16, scrollbar_y, 6, scrollbar_height), border_radius=3)
    
    # Кнопка закрытия
    close_button = pygame.Rect(shop_x + shop_width - 40, shop_y + 10, 30, 30)
    pygame.draw.rect(surf, (200, 50, 50), close_button)
    close_text = small_font.render("X", True, (255, 255, 255))
    surf.blit(close_text, (close_button.x + 8, close_button.y + 2))
    
    return close_button, switch_button, item_buttons

# ─── ЗВУК ЛОПАНЬЯ ──────────────────────────
# def make_pop_sound(freq=800, length=0.06):
#     t = np.linspace(0, length, int(FS * length), endpoint=False)
#     wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 40)
#     wave = (wave * 32767).astype(np.int16)
#     stereo = np.column_stack((wave, wave))
#     return pygame.sndarray.make_sound(stereo)

# pop_sound = make_pop_sound()


pop_sound = pygame.mixer.Sound("pop.mp3")

# ─── ДАННЫЕ ────────────────────────────────
audio_data = np.zeros(CHUNK)
smooth_vol = 0.0
gain = 2.0
score = 0
level = 1
next_level_score = 50
level_progress_score = 0
music_enabled = True
shop_open = False
shop_close_button = None
shop_item_buttons = []
shop_switch_button = None
shop_scroll_offset = 0
shop_scroll_speed = 40
current_shop = 1

score_multiplier = 1
experience_multiplier = 1
auto_spawn_amount = 0
auto_spawn_timer = 0.0
auto_pop_enabled = False
size_boost_multiplier = 1.0
size_boost_limit = 3.0
max_size_bonus = 0
screen_width_bonus = 0
volume_multiplier = 1.0
color_variety_enabled = False
shop_prices = {
    "more_bubbles": 150,
    "money_doubler": 500,
    "size_boost": 1000,
    "max_size_upgrade": 500,
    "auto_spawn": 1000,
    "auto_pop": 50000,
    "experience_doubler": 5000,
    "screen_width_upgrade": 5000,
    "volume_boost": 2000,
    "color_variety": 3000,
}

SAVE_PATH = os.path.join(os.path.dirname(__file__), SAVE_FILE)

def load_save():
    global score, level, next_level_score, level_progress_score
    global MAX_BUBBLES, score_multiplier, experience_multiplier, auto_spawn_amount
    global auto_pop_enabled, size_boost_multiplier, size_boost_limit, max_size_bonus
    global screen_width_bonus, volume_multiplier, color_variety_enabled
    global shop_prices, music_enabled

    if not SAVE_ENABLED:
        return

    if not os.path.exists(SAVE_PATH):
        return

    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return

    score = data.get("score", score)
    level = data.get("level", level)
    next_level_score = data.get("next_level_score", next_level_score)
    level_progress_score = data.get("level_progress_score", level_progress_score)
    MAX_BUBBLES = data.get("MAX_BUBBLES", MAX_BUBBLES)
    score_multiplier = data.get("score_multiplier", score_multiplier)
    experience_multiplier = data.get("experience_multiplier", experience_multiplier)
    auto_spawn_amount = data.get("auto_spawn_amount", auto_spawn_amount)
    auto_pop_enabled = data.get("auto_pop_enabled", auto_pop_enabled)
    size_boost_multiplier = data.get("size_boost_multiplier", size_boost_multiplier)
    size_boost_limit = data.get("size_boost_limit", size_boost_limit)
    max_size_bonus = data.get("max_size_bonus", max_size_bonus)
    screen_width_bonus = data.get("screen_width_bonus", screen_width_bonus)
    volume_multiplier = data.get("volume_multiplier", volume_multiplier)
    color_variety_enabled = data.get("color_variety_enabled", color_variety_enabled)
    shop_prices.update(data.get("shop_prices", shop_prices))
    music_enabled = data.get("music_enabled", music_enabled)
    if screen_width_bonus > 0:
        global WIDTH, screen, trail
        WIDTH += screen_width_bonus
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        trail = pygame.Surface((WIDTH, HEIGHT))
        trail.set_alpha(25)
        trail.fill(BG_COLOR)
    if not music_enabled:
        pygame.mixer.music.pause()


def save_game():
    if not SAVE_ENABLED:
        return

    data = {
        "score": score,
        "level": level,
        "next_level_score": next_level_score,
        "level_progress_score": level_progress_score,
        "MAX_BUBBLES": MAX_BUBBLES,
        "score_multiplier": score_multiplier,
        "experience_multiplier": experience_multiplier,
        "auto_spawn_amount": auto_spawn_amount,
        "auto_pop_enabled": auto_pop_enabled,
        "size_boost_multiplier": size_boost_multiplier,
        "size_boost_limit": size_boost_limit,
        "max_size_bonus": max_size_bonus,
        "screen_width_bonus": screen_width_bonus,
        "volume_multiplier": volume_multiplier,
        "color_variety_enabled": color_variety_enabled,
        "shop_prices": shop_prices,
        "music_enabled": music_enabled,
    }

    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

# Весёлые надписи (тоже в цветах темы)
POP_WORDS = ["ПУК!", "ХЛОП!", "БАХ!", "POP!", "БУЛЬК!", "ПШИК!", "ЧПОК!"]

class TextEffect:
    def __init__(self, x, y, text, color):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 90

    def update(self):
        self.y -= 1.5
        self.life -= 4

    def draw(self, surf):
        if self.life > 0:
            text_surf = small_font.render(self.text, True, self.color)
            text_surf.set_alpha(max(0, self.life))
            surf.blit(text_surf, (self.x - text_surf.get_width() // 2, int(self.y)))

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-4, 4)
        self.life = 255

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 12

    def draw(self, surf):
        if self.life > 0:
            pygame.draw.circle(surf, (*self.color, int(self.life)),
                               (int(self.x), int(self.y)), 3)

class Bubble:
    def __init__(self, volume):
        # Размер всё ещё зависит от громкости
        max_radius = 50 + max_size_bonus
        self.radius = random.randint(8, int(min(max_radius, 12 + volume * 2.5)))
        if size_boost_multiplier > 1.0:
            applied_boost = min(size_boost_multiplier, size_boost_limit)
            self.radius = int(self.radius * applied_boost)
            if random.random() < 0.3:
                self.radius *= 2
            self.radius = min(self.radius, (WIDTH - MENU_WIDTH) // 2)
        self.x = random.randint(self.radius, WIDTH - MENU_WIDTH - self.radius + screen_width_bonus)
        self.y = HEIGHT + self.radius
        self.speed = random.uniform(1.5, 3.5)
        self.angle = random.uniform(0, 2 * math.pi)
        self.swing_speed = random.uniform(0.03, 0.08)

        # Цвет СТРОГО из сине‑голубой палитры (случайный выбор)
        palette = SEA_PALETTE
        if color_variety_enabled:
            palette += [
                (255, 0, 0),    # красный
                (0, 255, 0),    # зелёный
                (255, 255, 0),  # жёлтый
                (255, 0, 255),  # magenta
                (128, 0, 128),  # purple
            ]
        self.rgb = random.choice(palette)
        self.color = pygame.Color(*self.rgb)

        # Кэшируем картинку
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        # Полупрозрачное тело
        pygame.draw.circle(self.image, (*self.rgb, 70),
                           (self.radius, self.radius), self.radius)
        # Обводка поярче
        pygame.draw.circle(self.image, (*self.rgb, 220),
                           (self.radius, self.radius), self.radius, 2)
        # Белый блик для объёма
        blink_x = int(self.radius * 0.65)
        blink_y = int(self.radius * 0.65)
        blink_r = int(self.radius * 0.22)
        pygame.draw.circle(self.image, (255, 255, 255, 150), (blink_x, blink_y), blink_r)

    def update(self):
        self.y -= self.speed
        self.angle += self.swing_speed
        self.x += math.sin(self.angle) * 1.5

    def draw(self, surf):
        surf.blit(self.image, (int(self.x - self.radius), int(self.y - self.radius)))

    def contains_point(self, pos):
        return math.hypot(pos[0] - self.x, pos[1] - self.y) <= self.radius

# ─── АУДИО ПОТОК ───────────────────────────
def audio_callback(indata, frames, time, status):
    global audio_data
    audio_data = indata[:, 0]

stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=FS, blocksize=CHUNK)
stream.start()

load_save()

bubbles = []
particles = []
text_effects = []

# Фон с эффектом шлейфа (тоже тёмный)
trail = pygame.Surface((WIDTH, HEIGHT))
trail.set_alpha(25)
trail.fill(BG_COLOR)

running = True
while running:
    screen.blit(trail, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_game()
            running = False
        if event.type == pygame.MOUSEWHEEL and shop_open:
            shop_scroll_offset += event.y * shop_scroll_speed
            continue
        if event.type == pygame.KEYDOWN and shop_open:
            if event.key == pygame.K_UP:
                shop_scroll_offset += shop_scroll_speed
            elif event.key == pygame.K_DOWN:
                shop_scroll_offset -= shop_scroll_speed
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if shop_open:
                shop_width, shop_height = 500, 400
                shop_x = (WIDTH - shop_width) // 2
                shop_y = (HEIGHT - shop_height) // 2
                shop_window_rect = pygame.Rect(shop_x, shop_y, shop_width, shop_height)
                content_rect = pygame.Rect(shop_x + 20, shop_y + 70, shop_width - 40, shop_height - 100)
                
                # Проверяем, что клик произошел внутри окна магазина
                if not shop_window_rect.collidepoint(event.pos):
                    shop_open = False
                elif shop_close_button and shop_close_button.collidepoint(event.pos):
                    shop_open = False
                elif shop_switch_button and shop_switch_button.collidepoint(event.pos):
                    current_shop = 3 - current_shop
                    shop_scroll_offset = 0
                else:
                    for idx, item_button in enumerate(shop_item_buttons):
                        if item_button.collidepoint(event.pos):
                            if not item_button.colliderect(content_rect):
                                continue
                            if current_shop == 1:
                                keys = ["more_bubbles", "money_doubler", "size_boost", "max_size_upgrade", "auto_spawn", "auto_pop", "experience_doubler"]
                                prices = [shop_prices[k] for k in keys]
                                unlock_levels = [1, 1, 5, 3, 10, 20, 5]
                                if idx == 5 and auto_pop_enabled:
                                    text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Уже куплено", (255, 215, 0)))
                                    break
                                if level < unlock_levels[idx]:
                                    text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, f"Откроется с {unlock_levels[idx]} уровня", (255, 100, 100)))
                                    break
                                if score >= prices[idx]:
                                    if idx == 2 and size_boost_multiplier >= size_boost_limit:
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✖ Лимит размера достигнут", (255, 100, 100)))
                                        break
                                    score -= prices[idx]
                                    if idx == 0:
                                        MAX_BUBBLES += 50
                                        shop_prices["more_bubbles"] *= 2
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ +50 к MAX_BUBBLES", (0, 255, 0)))
                                        save_game()
                                    elif idx == 1:
                                        score_multiplier *= 2
                                        shop_prices["money_doubler"] *= 2
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Удвоено", (0, 255, 0)))
                                        save_game()
                                    elif idx == 2:
                                        old_multiplier = size_boost_multiplier
                                        size_boost_multiplier = min(size_boost_multiplier * 1.2, size_boost_limit)
                                        shop_prices["size_boost"] *= 4
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Размер побольше", (0, 255, 0)))
                                        save_game()
                                    elif idx == 3:
                                        size_boost_limit += 0.5
                                        shop_prices["max_size_upgrade"] *= 2
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ +0.5 к лимиту размера", (0, 255, 0)))
                                        save_game()
                                    elif idx == 4:
                                        auto_spawn_amount += 10
                                        shop_prices["auto_spawn"] *= 2
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Автопоявление +10", (0, 255, 0)))
                                        save_game()
                                    elif idx == 5:
                                        auto_pop_enabled = True
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Автолопанье включено", (255, 215, 0)))
                                        save_game()
                                    elif idx == 6:
                                        experience_multiplier *= 2
                                        shop_prices["experience_doubler"] *= 2
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Удвоение опыта", (0, 255, 0)))
                                        save_game()
                                else:
                                    text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✖ Недостаточно", (255, 100, 100)))
                            elif current_shop == 2:
                                keys = ["screen_width_upgrade", "volume_boost", "color_variety"]
                                prices = [shop_prices[k] for k in keys]
                                unlock_levels = [10, 5, 3]
                                if idx == 2 and color_variety_enabled:
                                    text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Уже куплено", (255, 215, 0)))
                                    break
                                if level < unlock_levels[idx]:
                                    text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, f"Откроется с {unlock_levels[idx]} уровня", (255, 100, 100)))
                                    break
                                if score >= prices[idx]:
                                    score -= prices[idx]
                                    if idx == 0:
                                        screen_width_bonus += 50
                                        WIDTH += 50
                                        screen = pygame.display.set_mode((WIDTH, HEIGHT))
                                        trail = pygame.Surface((WIDTH, HEIGHT))
                                        trail.set_alpha(25)
                                        trail.fill(BG_COLOR)
                                        shop_prices["screen_width_upgrade"] *= 2
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Расширение экрана +50", (0, 255, 0)))
                                        save_game()
                                    elif idx == 1:
                                        volume_multiplier *= 1.5
                                        shop_prices["volume_boost"] *= 2
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Увеличение громкости", (0, 255, 0)))
                                        save_game()
                                    elif idx == 2:
                                        color_variety_enabled = True
                                        text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✔ Разнообразие цветов", (255, 215, 0)))
                                        save_game()
                                else:
                                    text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, "✖ Недостаточно", (255, 100, 100)))
                            break
            else:
                button_rect = pygame.Rect(
                    WIDTH - MENU_WIDTH + MENU_PANEL_PADDING,
                    MENU_PANEL_PADDING,
                    MENU_BUTTON_WIDTH,
                    MENU_BUTTON_HEIGHT,
                )
                section_rect = pygame.Rect(
                    WIDTH - MENU_WIDTH + MENU_PANEL_PADDING,
                    button_rect.bottom + MENU_SECTION_SPACING,
                    MENU_WIDTH - MENU_PANEL_PADDING * 2,
                    MENU_SECTION_HEIGHT,
                )
                shop_button_rect = pygame.Rect(
                    section_rect.x + 5,
                    section_rect.y + 40,
                    section_rect.width - 10,
                    35,
                )
                
                if button_rect.collidepoint(event.pos):
                    music_enabled = not music_enabled
                    if music_enabled:
                        pygame.mixer.music.unpause()
                    else:
                        pygame.mixer.music.pause()
                    save_game()
                elif shop_button_rect.collidepoint(event.pos):
                    shop_open = True
                else:
                    for b in bubbles[:]:
                        if b.contains_point(event.pos):
                            pop_sound.play()
                            # Осколки того же цвета
                            for _ in range(12):
                                particles.append(Particle(b.x, b.y, b.rgb))
                            critical = random.random() < 0.3
                            if critical:
                                points = score_multiplier * 2
                                text_effects.append(TextEffect(b.x, b.y, "КРИТ", (255, 215, 0)))
                                for _ in range(4):
                                    text_effects.append(TextEffect(
                                        b.x + random.randint(-15, 15),
                                        b.y - 10, "✨", (255, 255, 150)))
                            else:
                                points = score_multiplier
                                word = random.choice(POP_WORDS)
                                text_effects.append(TextEffect(b.x, b.y, word, b.rgb))
                                if random.random() < 0.4:
                                    text_effects.append(TextEffect(
                                        b.x + random.randint(-15, 15),
                                        b.y - 10, "✨", (255, 255, 200)))
                            bubbles.remove(b)
                            score += points
                            level_progress_score += points * experience_multiplier
                            if level_progress_score >= next_level_score:
                                level += 1
                                next_level_score *= 2
                                level_progress_score = 0
                                text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, f"Уровень {level}!", (255, 215, 0)))
                                save_game()

    # Громкость
    raw_vol = np.linalg.norm(audio_data) * 10
    if raw_vol > 0.1:
        target_gain = 22.0 / (raw_vol + 1.0)
        gain += (target_gain - gain) * 0.08
    current_vol = raw_vol * gain * volume_multiplier
    smooth_vol += (current_vol - smooth_vol) * 0.15

    # Спавн морских пузырей
    if smooth_vol > 1.2 and len(bubbles) < MAX_BUBBLES:
        spawn_count = int(min(3, smooth_vol // 4))
        for _ in range(max(1, spawn_count)):
            bubbles.append(Bubble(smooth_vol))

    # Автопоявление
    if auto_spawn_amount > 0:
        auto_spawn_timer += 1 / FPS
        if auto_spawn_timer >= 1.0:
            auto_spawn_timer = 0.0
            for _ in range(min(auto_spawn_amount, MAX_BUBBLES - len(bubbles))):
                bubbles.append(Bubble(0))

    # Автолопанье
    if auto_pop_enabled:
        mouse_pos = pygame.mouse.get_pos()
        for b in bubbles[:]:
            if b.contains_point(mouse_pos):
                pop_sound.play()
                for _ in range(12):
                    particles.append(Particle(b.x, b.y, b.rgb))
                critical = random.random() < 0.3
                if critical:
                    points = score_multiplier * 2
                    text_effects.append(TextEffect(b.x, b.y, "КРИТ", (255, 215, 0)))
                    for _ in range(4):
                        text_effects.append(TextEffect(
                            b.x + random.randint(-15, 15),
                            b.y - 10, "✨", (255, 255, 150)))
                else:
                    points = score_multiplier
                    word = random.choice(POP_WORDS)
                    text_effects.append(TextEffect(b.x, b.y, word, b.rgb))
                    if random.random() < 0.4:
                        text_effects.append(TextEffect(
                            b.x + random.randint(-15, 15),
                            b.y - 10, "✨", (255, 255, 200)))
                bubbles.remove(b)
                score += points
                level_progress_score += points * experience_multiplier
                if level_progress_score >= next_level_score:
                    level += 1
                    next_level_score *= 2
                    level_progress_score = 0
                    text_effects.append(TextEffect(WIDTH // 2, HEIGHT // 2, f"Уровень {level}!", (255, 215, 0)))

    # Пузырьки
    for b in bubbles[:]:
        b.update()
        b.draw(screen)
        if b.y < -20:
            for _ in range(6):
                particles.append(Particle(b.x, b.y, b.rgb))
            bubbles.remove(b)

    # Частицы
    for p in particles[:]:
        p.update()
        p.draw(screen)
        if p.life <= 0:
            particles.remove(p)

    # Тексты
    for te in text_effects[:]:
        te.update()
        te.draw(screen)
        if te.life <= 0:
            text_effects.remove(te)

    # Счёт и индикатор громкости (тоже в стиле океана)
    score_surf = font.render(f"Лопнуто: {score} | Уровень: {level}", True, (255, 255, 255))
    screen.blit(score_surf, (20, 20))

    # Правая вертикальная панель меню
    menu_panel = create_vertical_gradient_surface(MENU_WIDTH, HEIGHT, MENU_COLOR_TOP, MENU_COLOR_BOTTOM, border_radius=16)
    screen.blit(menu_panel, (WIDTH - MENU_WIDTH, 0))

    button_rect = pygame.Rect(
        WIDTH - MENU_WIDTH + MENU_PANEL_PADDING,
        MENU_PANEL_PADDING,
        MENU_BUTTON_WIDTH,
        MENU_BUTTON_HEIGHT,
    )
    button_color = BUTTON_ON_COLOR if music_enabled else BUTTON_OFF_COLOR
    pygame.draw.rect(screen, button_color, button_rect, border_radius=12)
    button_text = "МУЗЫКА ВКЛ" if music_enabled else "МУЗЫКА ВЫКЛ"
    button_surf = small_font.render(button_text, True, BUTTON_TEXT_COLOR)
    screen.blit(
        button_surf,
        (
            button_rect.x + (button_rect.width - button_surf.get_width()) // 2,
            button_rect.y + (button_rect.height - button_surf.get_height()) // 2,
        ),
    )

    section_rect = pygame.Rect(
        WIDTH - MENU_WIDTH + MENU_PANEL_PADDING,
        button_rect.bottom + MENU_SECTION_SPACING,
        MENU_WIDTH - MENU_PANEL_PADDING * 2,
        MENU_SECTION_HEIGHT,
    )
    pygame.draw.rect(screen, (70, 70, 85), section_rect, border_radius=14)
    section_label = small_font.render("Меню", True, (200, 200, 220))
    screen.blit(
        section_label,
        (
            section_rect.x + (section_rect.width - section_label.get_width()) // 2,
            section_rect.y + 10,
        ),
    )

    # Кнопка магазина внутри раздела меню
    shop_button_rect = pygame.Rect(
        section_rect.x + 5,
        section_rect.y + 40,
        section_rect.width - 10,
        35,
    )
    pygame.draw.rect(screen, (200, 150, 50), shop_button_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 200, 100), shop_button_rect, 2, border_radius=10)
    shop_text = small_font.render("МАГАЗИН", True, BUTTON_TEXT_COLOR)
    screen.blit(
        shop_text,
        (
            shop_button_rect.x + (shop_button_rect.width - shop_text.get_width()) // 2,
            shop_button_rect.y + (shop_button_rect.height - shop_text.get_height()) // 2,
        ),
    )

    # Нижнее меню с градиентом (слева от правой панели)
    menu_surface = create_vertical_gradient_surface(WIDTH - MENU_WIDTH, MENU_HEIGHT, MENU_COLOR_TOP, MENU_COLOR_BOTTOM, border_radius=16)
    screen.blit(menu_surface, (0, HEIGHT - MENU_HEIGHT))

    bar_width = int(min(WIDTH - MENU_WIDTH - 40, smooth_vol * 12))
    bar_rect = pygame.Rect(20, HEIGHT - MENU_HEIGHT + 24, bar_width, 10)
    pygame.draw.rect(screen, (0, 180, 255), bar_rect, border_radius=4)

    xp_label = small_font.render("XP", True, (255, 215, 0))
    screen.blit(xp_label, (20, HEIGHT - MENU_HEIGHT + 38))

    # Бар прогресса уровня
    level_progress = level_progress_score / next_level_score
    level_bar_width = int(level_progress * (WIDTH - MENU_WIDTH - 40 - (xp_label.get_width() + 8)))
    level_bar_rect = pygame.Rect(20 + xp_label.get_width() + 8, HEIGHT - MENU_HEIGHT + 40, level_bar_width, 10)
    pygame.draw.rect(screen, (255, 215, 0), level_bar_rect, border_radius=4)

    # Окно магазина
    if shop_open:
        shop_close_button, shop_switch_button, shop_item_buttons = draw_shop(screen, current_shop)

    pygame.display.flip()
    clock.tick(FPS)

stream.stop()
pygame.quit()
