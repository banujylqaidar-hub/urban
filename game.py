# pacman.py — Pac-Man в одном файле. Запуск: python pacman.py
import math, os, random, sys
import pygame

# ===================== НАСТРОЙКИ =====================
# Легенда: # стена, . точка, O большая точка, пробел - пусто (P и G ставятся кодом).
# Каждая карта — левая верхняя половина (8 строк × 11 символов); остальное отражается зеркально.
HALVES = [
    ["###########", "#.........#", "#.###.###.#", "#O.........", "#.###.#.###", "#.....#...#", "#####.###.#", "#####.#...."],
    ["###########", "#O...#....#", "#.##.#.##.#", "#..........", "#.##.###.##", "#....#.....", "####.#.#.##", "####......."],
    ["###########", "#....#....#", "#.##.#.##.#", "#O.........", "#.#.##.#.##", "#.#....#...", "#.#.##.##.#", "#...#......"],
]
HOUSE = ".......#   "                                  # средняя строка: туннель и дом призраков


def build_map(half):
    top = [h + h[-2::-1] for h in half]
    grid = [list(r) for r in top + [HOUSE + HOUSE[-2::-1]] + top[::-1]]
    for c in range(8, 12): grid[8][c] = "G"           # призраки в доме
    grid[13][10] = "P"                                # старт игрока
    return ["".join(r) for r in grid]


MAPS = [build_map(h) for h in HALVES]
ROWS, COLS, TILE, HUD_H, FPS = len(MAPS[0]), len(MAPS[0][0]), 30, 60, 60
WIDTH, FIELD_H = COLS * TILE, ROWS * TILE
HEIGHT = FIELD_H + HUD_H
BLACK, WHITE, BLUE, WALL = (0, 0, 0), (255, 255, 255), (33, 33, 222), (30, 60, 200)
YELLOW, RED, PINK, CYAN = (255, 220, 0), (255, 60, 60), (255, 150, 200), (0, 220, 220)
ORANGE, GREEN, ASH = (255, 165, 0), (60, 220, 100), (130, 130, 130)
PLAYER_MS, GHOST_MS = 140, 170                               # время одного шага, мс
# Сложность: название, жизни, призраков, множитель скорости призраков, шанс случайного хода
DIFFS = [("Лёгкий", 5, 3, 1.3, 0.30), ("Нормальный", 3, 4, 1.0, 0.12), ("Сложный", 2, 4, 0.8, 0.04)]
DOT, POWER, POWER_MS, GHOST_PTS = 10, 50, 6000, 200          # очки и время "испуга"
CHERRY_PTS, CHERRY_MS = 100, 8000                            # вишня: очки и время "испуга"
CHERRY_FIRST, CHERRY_PAUSE, CHERRY_LIFE = 6000, 12000, 9000  # когда появляется и живёт вишня
READY_MS, END_MS = 1500, 2200                                # "ГОТОВ!" и эффект конца игры
DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]
SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")


def neighbor(m, r, c, dr, dc):
    """Соседняя клетка с туннелем по горизонтали. None, если там стена."""
    nr, nc = r + dr, (c + dc) % COLS
    return (nr, nc) if 0 <= nr < ROWS and m[nr][nc] != "#" else None


# ===================== ОБЪЕКТЫ =====================
class Entity:
    """Общая основа для игрока и призраков."""
    def __init__(self, row, col, color):
        self.start, self.color = (row, col), color
        self.row, self.col = self.prev_row, self.prev_col = row, col

    def reset_position(self):
        self.row, self.col = self.prev_row, self.prev_col = self.start

    def set_pos(self, pos):
        self.prev_row, self.prev_col, (self.row, self.col) = self.row, self.col, pos

    def center(self, t):
        """Центр в пикселях; t от 0 до 1 — плавный переход между клетками."""
        pr, pc = self.prev_row, self.prev_col
        if abs(self.row - pr) > 1 or abs(self.col - pc) > 1:
            pr, pc = self.row, self.col                      # туннель — без анимации
        t = max(0.0, min(1.0, t))
        return (int((pc + (self.col - pc) * t) * TILE + TILE // 2),
                int((pr + (self.row - pr) * t) * TILE + TILE // 2))


class Player(Entity):
    def __init__(self, row, col):
        super().__init__(row, col, YELLOW)
        self.dir = self.next_dir = (0, 0)
        self.facing = (0, 1)

    def reset_position(self):
        super().reset_position()
        self.dir = self.next_dir = (0, 0)

    def target(self, m, d):
        return neighbor(m, self.row, self.col, *d) if d != (0, 0) else None

    def move(self, m):
        if self.target(m, self.next_dir): self.dir = self.next_dir   # поворот, как только есть проход
        n = self.target(m, self.dir)
        if n: self.facing = self.dir
        self.set_pos(n or (self.row, self.col))

    def draw(self, s, t):
        x, y = self.center(t)
        r, angle = TILE // 2 - 3, math.atan2(-self.facing[0], self.facing[1])
        mouth = math.radians(25 if self.dir == (0, 0) else 4 + 36 * abs(math.sin(pygame.time.get_ticks() / 90)))
        pts = [(x, y)] + [(x + r * math.cos(a), y - r * math.sin(a)) for a in
                          (angle + mouth + (2 * math.pi - 2 * mouth) * i / 22 for i in range(23))]
        pygame.draw.polygon(s, YELLOW, pts)


class Ghost(Entity):
    """0 красный — прямо за игроком; 1 розовый — на 4 клетки вперёд; 2 голубой — заходит за спину;
    3 оранжевый — издалека гонится, вблизи убегает в свой угол."""
    def __init__(self, row, col, color, kind, corner, release, rand):
        super().__init__(row, col, color)
        self.kind, self.corner, self.initial_release, self.rand = kind, corner, release, rand
        self.release, self.dir, self.frightened = release, (0, 0), False

    def reset_position(self, release=None):
        super().reset_position()
        self.dir, self.frightened = (0, 0), False
        self.release = self.initial_release if release is None else release

    def chase_target(self, p):
        (pr, pc), (fr, fc) = (p.row, p.col), p.facing
        if self.kind == 0: return pr, pc
        if self.kind == 1: return pr + 4 * fr, pc + 4 * fc
        if self.kind == 2: return pr - 3 * fr, pc - 3 * fc
        return (pr, pc) if math.hypot(self.row - pr, self.col - pc) > 8 else self.corner

    def move(self, m, player):
        here, back = (self.row, self.col), (-self.dir[0], -self.dir[1])
        if self.release > 0:                                 # ещё сидит дома
            self.release -= 1
            return self.set_pos(here)
        opts = [(d, neighbor(m, *here, *d)) for d in DIRS if self.dir == (0, 0) or d != back]
        opts = [o for o in opts if o[1]] or ([(back, neighbor(m, *here, *back))] if neighbor(m, *here, *back) else [])
        if not opts: return self.set_pos(here)               # без разворота, кроме тупика
        if self.frightened or random.random() < self.rand:
            d, n = random.choice(opts)
        else:
            tr, tc = self.chase_target(player)
            dist = lambda o: (o[1][0] - tr) ** 2 + (o[1][1] - tc) ** 2
            d, n = random.choice([o for o in opts if dist(o) == min(map(dist, opts))])
        self.dir = d
        self.set_pos(n)

    def draw(self, s, t, mode):
        x, y = self.center(t)
        r, color = TILE // 2 - 3, {"frightened": BLUE, "flash": WHITE}.get(mode, self.color)
        pygame.draw.circle(s, color, (x, y - 2), r)
        pygame.draw.rect(s, color, (x - r, y - 2, 2 * r, r + 2))
        for i in range(3):                                   # зубчатый подол
            pygame.draw.polygon(s, BLACK, [(x - r + i * 2 * r / 3, y + r), (x - r + (i + .5) * 2 * r / 3, y + r - 5),
                                           (x - r + (i + 1) * 2 * r / 3, y + r)])
        for sx in (-r // 2, r // 2):                         # глаза смотрят по ходу движения
            if mode == "normal":
                pygame.draw.circle(s, WHITE, (x + sx, y - 4), 4)
                pygame.draw.circle(s, BLUE, (x + sx + self.dir[1] * 2, y - 4 + self.dir[0] * 2), 2)
            else:
                pygame.draw.circle(s, BLUE if mode == "frightened" else RED, (x + sx, y - 4), 2)


# ===================== ИГРА =====================
class Game:
    def __init__(self, diff=1, level=1):
        self.diff, self.start_level, self.level = diff, level, level
        self.score, self.lives, self.in_menu = 0, DIFFS[diff][1], True   # игра начинается со стартового меню
        self.over = self.won = self.paused = self.menu_open = self.should_quit = False
        self.menu_index = self.end_timer = self.shake = self.firework_timer = 0
        self.particles = []                                  # [x, y, vx, vy, жизнь, макс, цвет, размер, g]
        try:
            with open(SAVE, encoding="utf-8") as f: self.high_score = int(f.read().strip())
        except (OSError, ValueError):
            self.high_score = 0
        self.load_level()

    def save_high_score(self):
        try:
            with open(SAVE, "w", encoding="utf-8") as f: f.write(str(self.high_score))
        except OSError:
            pass

    def load_level(self):
        self.map, self.ghosts = [list(r) for r in MAPS[self.level - 1]], []
        colors, corners = [RED, PINK, CYAN, ORANGE], [(0, COLS), (0, 0), (ROWS, COLS), (ROWS, 0)]
        for r, row in enumerate(self.map):
            for c, ch in enumerate(row):
                if ch == "P": self.player = Player(r, c)
                if ch == "G" and len(self.ghosts) < DIFFS[self.diff][2]:
                    i = len(self.ghosts)
                    self.ghosts.append(Ghost(r, c, colors[i], i, corners[i], i * 6, DIFFS[self.diff][4]))
                if ch in "PG": row[c] = " "
        self.dots_left = sum(row.count(".") + row.count("O") for row in self.map)
        self.player_t = self.ghost_t = self.fright_t = self.combo = 0
        self.cherry, self.cherry_wait, self.cherry_life = None, CHERRY_FIRST, 0
        self.ready_t, self.speed = READY_MS, 0.9 ** (self.level - 1)   # на каждом уровне призраки быстрее
        self.ready_text = "ГОТОВ!" if self.level == 1 else f"УРОВЕНЬ {self.level}"

    # ---------- ввод ----------
    def handle_key(self, key):
        if self.over and self.end_timer < END_MS: return     # пока идёт эффект, ввод игнорируем
        if self.in_menu:                                     # выбор сложности и уровня
            if key == pygame.K_ESCAPE: self.should_quit = True
            elif key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s): self.menu_index = 1 - self.menu_index
            elif key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                step = 1 if key in (pygame.K_RIGHT, pygame.K_d) else -1
                if self.menu_index == 0: self.diff = (self.diff + step) % len(DIFFS)
                else: self.start_level = (self.start_level - 1 + step) % len(MAPS) + 1
                self.level, self.lives = self.start_level, DIFFS[self.diff][1]
                self.load_level()                            # карта за меню показывает выбранный уровень
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.in_menu, self.menu_index = False, 0
                self.load_level()
            return
        if key == pygame.K_ESCAPE:
            if self.over: self.should_quit = True
            elif self.menu_open: self.menu_open = self.paused = False
            else: self.menu_open = self.paused = True; self.menu_index = 0
        elif self.menu_open or self.over:
            if key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s): self.menu_index = 1 - self.menu_index
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):    # 0 — продолжить / заново, 1 — выход
                if self.menu_index == 1: self.should_quit = True
                elif self.over: self.__init__(self.diff, self.start_level)
                else: self.menu_open = self.paused = False
            elif key == pygame.K_r and self.over: self.__init__(self.diff, self.start_level)
        elif key in (pygame.K_p, pygame.K_SPACE): self.paused = not self.paused
        else:
            d = {pygame.K_UP: (-1, 0), pygame.K_w: (-1, 0), pygame.K_DOWN: (1, 0), pygame.K_s: (1, 0),
                 pygame.K_LEFT: (0, -1), pygame.K_a: (0, -1), pygame.K_RIGHT: (0, 1), pygame.K_d: (0, 1)}.get(key)
            if d: self.player.next_dir = d

    # ---------- логика ----------
    def ghost_interval(self):
        return GHOST_MS * self.speed * DIFFS[self.diff][3] * (1.4 if any(g.frightened for g in self.ghosts) else 1)

    def update(self, dt):
        if self.paused or self.in_menu: return
        dt = min(dt, 100)
        self.update_effects(dt)
        if self.over: return
        if self.ready_t > 0:
            self.ready_t -= dt
            return
        if self.fright_t > 0:
            self.fright_t -= dt
            if self.fright_t <= 0:
                for g in self.ghosts: g.frightened = False
        self.update_cherry(dt)
        self.player_t += dt
        self.ghost_t += dt
        if self.player_t >= PLAYER_MS:
            self.player_t -= PLAYER_MS
            self.player.move(self.map)
            self.collect()
            self.check_hits()
        if not self.over and self.ghost_t >= self.ghost_interval():
            self.ghost_t -= self.ghost_interval()
            for g in self.ghosts: g.move(self.map, self.player)
            self.check_hits()
        if not self.over and self.dots_left == 0: self.next_level()

    def add_score(self, points):
        self.score += points
        self.high_score = max(self.high_score, self.score)

    def edible(self, ms):
        self.fright_t, self.combo = ms, 0
        for g in self.ghosts: g.frightened = True

    def update_cherry(self, dt):
        if self.cherry:
            self.cherry_life -= dt
            if self.cherry_life <= 0: self.cherry, self.cherry_wait = None, CHERRY_PAUSE
        else:
            self.cherry_wait -= dt
            p = self.player
            cells = [(r, c) for r, row in enumerate(self.map) for c, ch in enumerate(row)
                     if ch in ". " and abs(r - p.row) + abs(c - p.col) >= 6]
            if self.cherry_wait <= 0 and cells: self.cherry, self.cherry_life = random.choice(cells), CHERRY_LIFE

    def collect(self):
        r, c = self.player.row, self.player.col
        if self.cherry == (r, c):                            # вишня: очки и призраков можно есть
            self.add_score(CHERRY_PTS)
            self.edible(CHERRY_MS)
            self.cherry, self.cherry_wait = None, CHERRY_PAUSE
        cell = self.map[r][c]
        if cell in ".O":
            self.add_score(DOT if cell == "." else POWER)
            if cell == "O": self.edible(POWER_MS)
            self.map[r][c] = " "
            self.dots_left -= 1

    def check_hits(self):
        p = self.player
        for g in self.ghosts:
            same = (g.row, g.col) == (p.row, p.col)
            swapped = (g.row, g.col) == (p.prev_row, p.prev_col) and (g.prev_row, g.prev_col) == (p.row, p.col)
            if not (same or swapped): continue
            if g.frightened:
                self.add_score(GHOST_PTS * 2 ** self.combo)
                self.combo = min(self.combo + 1, 3)
                g.reset_position(release=4)
            else:
                return self.lose_life()

    def lose_life(self):
        self.lives -= 1
        x, y = self.player.center(1.0)
        self.burst(x, y, [YELLOW, WHITE], 70 if self.lives <= 0 else 30, 0.28)
        self.shake = 800 if self.lives <= 0 else 300
        if self.lives <= 0:                                  # поражение
            self.over, self.end_timer = True, 0
            return self.save_high_score()
        self.player.reset_position()
        for g in self.ghosts: g.reset_position()
        self.player_t = self.ghost_t = self.fright_t = 0
        self.cherry, self.cherry_wait = None, CHERRY_FIRST
        self.ready_t, self.ready_text = READY_MS, "ГОТОВ!"

    def next_level(self):
        if self.level < len(MAPS):
            self.level += 1
            return self.load_level()
        self.won = self.over = True                          # победа
        self.end_timer = self.firework_timer = 0
        self.save_high_score()

    # ---------- эффекты победы (салют) и поражения (взрыв, тряска, пепел) ----------
    def burst(self, x, y, colors, n, speed):
        for _ in range(n):
            a, life, v = random.uniform(0, 2 * math.pi), random.randint(700, 1400), speed * random.uniform(0.3, 1)
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, life, life,
                                   random.choice(colors), random.randint(2, 4), 0.0004])

    def update_effects(self, dt):
        if self.over:
            self.end_timer += dt
            if self.won:
                self.firework_timer -= dt
                if self.firework_timer <= 0:
                    self.burst(random.randint(60, WIDTH - 60), random.randint(40, FIELD_H - 200),
                               [random.choice([RED, PINK, CYAN, ORANGE, YELLOW, GREEN]), WHITE], 45, 0.22)
                    self.firework_timer = random.randint(250, 500)
            elif self.end_timer < 3000:                      # пепел падает сверху
                for _ in range(2):
                    self.particles.append([random.randint(0, WIDTH), -5, random.uniform(-.01, .01),
                                           random.uniform(.04, .1), 2500, 2500, ASH, random.randint(2, 3), 0])
        self.shake -= dt
        for p in self.particles:
            p[0] += p[2] * dt; p[1] += p[3] * dt; p[3] += p[8] * dt; p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]

    # ---------- отрисовка ----------
    def render(self, screen, font, big):
        """Кадр рисуется на отдельной поверхности и сдвигается при тряске."""
        canvas, mag = pygame.Surface((WIDTH, HEIGHT)), int(min(8, max(self.shake, 0) / 60))
        self.draw(canvas, font, big)
        screen.fill(BLACK)
        screen.blit(canvas, (random.randint(-mag, mag), random.randint(-mag, mag)))

    def draw(self, s, font, big):
        s.fill(BLACK)
        ticks = pygame.time.get_ticks()
        for r, line in enumerate(self.map):
            for c, ch in enumerate(line):
                x, y = c * TILE, r * TILE
                if ch == "#": pygame.draw.rect(s, WALL, (x + 2, y + 2, TILE - 4, TILE - 4), border_radius=6)
                elif ch == ".": pygame.draw.circle(s, WHITE, (x + TILE // 2, y + TILE // 2), 3)
                elif ch == "O": pygame.draw.circle(s, WHITE, (x + TILE // 2, y + TILE // 2), 6 + int(2 * math.sin(ticks / 150)))
        if self.cherry and not (self.cherry_life < 3000 and (ticks // 150) % 2):   # мигает перед исчезновением
            cx, cy = self.cherry[1] * TILE + TILE // 2, self.cherry[0] * TILE + TILE // 2
            pygame.draw.line(s, GREEN, (cx - 5, cy + 2), (cx + 2, cy - 10), 2)
            pygame.draw.line(s, GREEN, (cx + 6, cy + 3), (cx + 2, cy - 10), 2)
            pygame.draw.circle(s, RED, (cx - 5, cy + 5), 6)
            pygame.draw.circle(s, RED, (cx + 6, cy + 6), 6)
        if not (self.over and not self.won):                 # при поражении Pac-Man уже рассыпался
            self.player.draw(s, self.player_t / PLAYER_MS)
        flash = self.fright_t < 2000 and (ticks // 200) % 2 == 0
        for g in self.ghosts:
            g.draw(s, self.ghost_t / self.ghost_interval(), ("flash" if flash else "frightened") if g.frightened else "normal")
        for x, y, _, _, life, mx, col, size, _ in self.particles:
            f = max(0.0, min(1.0, life / mx))
            pygame.draw.circle(s, tuple(int(v * f) for v in col), (int(x), int(y)), size)
        pygame.draw.rect(s, (20, 20, 40), (0, FIELD_H, WIDTH, HUD_H))              # нижняя панель
        my = FIELD_H + HUD_H // 2
        t1, t2 = font.render(f"Очки: {self.score}", True, WHITE), font.render(f"Ур. {self.level}  Рекорд: {self.high_score}", True, WHITE)
        s.blit(t1, t1.get_rect(midleft=(12, my)))
        s.blit(t2, t2.get_rect(center=(WIDTH // 2, my)))
        for i in range(max(self.lives, 0)): pygame.draw.circle(s, YELLOW, (WIDTH - 20 - i * 26, my), 9)
        if self.over and self.end_timer < END_MS:            # эффект: вспышка / красный оттенок + надпись
            t, layer = self.end_timer, pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            k = (math.sin(t / 120) + 1) / 2
            layer.fill((255, 255, 255, max(0, int(120 * (1 - t / 300)))) if self.won else (140, 0, 0, min(120, t // 8)))
            s.blit(layer, (0, 0))
            label = big.render("ПОБЕДА!" if self.won else "ИГРА ОКОНЧЕНА", True,
                               (255, int(180 + 75 * k), int(60 * k)) if self.won else RED)
            s.blit(label, label.get_rect(center=(WIDTH // 2, FIELD_H // 2)))
        elif not self.over and self.ready_t > 0:
            label = font.render(self.ready_text, True, YELLOW)
            box = label.get_rect(center=(WIDTH // 2, FIELD_H // 2)).inflate(24, 12)
            pygame.draw.rect(s, BLACK, box, border_radius=8)
            s.blit(label, label.get_rect(center=box.center))
        if self.in_menu:
            d = DIFFS[self.diff]
            self.menu(s, font, big, "PAC-MAN", YELLOW, [f"Сложность: < {d[0]} >", f"Уровень: < {self.start_level} >"],
                      f"Жизни: {d[1]}, призраков: {d[2]}. Enter — играть, Esc — выход")
        elif self.menu_open: self.menu(s, font, big, "ПАУЗА", YELLOW, ["Продолжить", "Выход"])
        elif self.over and self.end_timer >= END_MS:
            self.menu(s, font, big, "ПОБЕДА!" if self.won else "ИГРА ОКОНЧЕНА", GREEN if self.won else RED,
                      ["Играть снова", "Выход"])
        elif self.paused: self.menu(s, font, big, "ПАУЗА", YELLOW, [])

    def menu(self, s, font, big, title, color, labels, hint="Enter — выбрать, Esc — назад"):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        s.blit(overlay, (0, 0))
        top = HEIGHT // 2 - (90 if labels else 20)
        s.blit(big.render(title, True, color), big.render(title, True, color).get_rect(center=(WIDTH // 2, top)))
        lines = labels or ["P или пробел — продолжить"]
        for i, text in enumerate(lines):
            t = font.render(("> " if labels and i == self.menu_index else "") + text, True, YELLOW if labels and i == self.menu_index else WHITE)
            s.blit(t, t.get_rect(center=(WIDTH // 2, top + 60 + i * 40)))
        t = font.render(hint if labels else "", True, (160, 160, 200))
        s.blit(t, t.get_rect(center=(WIDTH // 2, top + 70 + len(lines) * 40)))


# ===================== ЗАПУСК =====================
def find_font(size, bold=False):
    for name in ("arial", "dejavusans", "liberationsans", "segoeui", "tahoma", "verdana"):
        path = pygame.font.match_font(name, bold=bold)       # шрифт с кириллицей
        if path: return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pac-Man")
    clock, font, big = pygame.time.Clock(), find_font(22), find_font(52, bold=True)
    game = Game()
    while not game.should_quit:
        dt = clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: game.should_quit = True
            elif e.type == pygame.KEYDOWN: game.handle_key(e.key)
        game.update(dt)
        game.render(screen, font, big)
        pygame.display.flip()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
