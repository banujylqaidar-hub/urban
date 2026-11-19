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

