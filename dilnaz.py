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
