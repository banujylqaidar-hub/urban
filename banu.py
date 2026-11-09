import tkinter as tk
import random

CELL = 32      # бір тор көзінің өлшемі
TICK = 130     # ойын жылдамдығы (миллисекунд)

# =====================================================
# 2-ҚАТЫСУШЫ (Бану): Лабиринт картасы, Wall, Exit, Maze
# =====================================================
# #  - қабырға,  .  - нүкте,  P - ойыншы,  G - елес,  E - шығу
MAZE_MAP = [
    "###################",
    "#........#........#",
    "#.##.###.#.###.##.#",
    "#.................E",
    "#.##.#.##.##.#.##.#",
    "#....#..GGG..#....#",
    "####.#.#####.#.####",
    "#.................#",
    "#.##.###.#.###.##.#",
    "#........P........#",
    "###################",
]

DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]


class Wall:
    """Қабырға: орны (x, y) сақталады."""
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Exit:
    """Шығу: орны сақталады. Нүктелер жиналғанша жабық тұрады."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.open = False


class Maze:
    """Лабиринт: қабырғалар, нүктелер, шығу, бастапқы орындар."""
    def __init__(self, layout):
        self.walls = []
        self.wall_cells = set()
        self.dots = set()
        self.exit = None
        self.player_start = (1, 1)
        self.ghost_starts = []
        self.rows = len(layout)
        self.cols = len(layout[0])
        for y, row in enumerate(layout):
            for x, ch in enumerate(row):
                if ch == "#":
                    self.walls.append(Wall(x, y))
                    self.wall_cells.add((x, y))
                elif ch == ".":
                    self.dots.add((x, y))
                elif ch == "P":
                    self.player_start = (x, y)
                elif ch == "G":
                    self.ghost_starts.append((x, y))
                elif ch == "E":
                    self.exit = Exit(x, y)

    def is_wall(self, x, y):
        """Осы көзде қабырға бар ма? Жабық шығу да қабырға сияқты."""
        if (x, y) in self.wall_cells:
            return True
        if not self.exit.open and (x, y) == (self.exit.x, self.exit.y):
            return True
        return False

    def is_exit(self, x, y):
        return (x, y) == (self.exit.x, self.exit.y)

    def eat_dot(self, x, y):
        """Нүктені жейді. Соңғы нүкте жиналса, шығу ашылады."""
        if (x, y) in self.dots:
            self.dots.remove((x, y))
            if not self.dots:
                self.exit.open = True
            return True
        return False

    def draw(self, canvas):
        for w in self.walls:
            canvas.create_rectangle(w.x * CELL + 1, w.y * CELL + 1,
                                    (w.x + 1) * CELL - 1, (w.y + 1) * CELL - 1,
                                    fill="#1a1aa6", outline="#4d4dff")
        for (x, y) in self.dots:
            cx = x * CELL + CELL // 2
            cy = y * CELL + CELL // 2
            canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                               fill="#ffd9a0", outline="")
        # Шығу: жабық - қызыл, ашық - жасыл
        e = self.exit
        color = "#2ecc71" if e.open else "#8b1a1a"
        text = "EXIT" if e.open else "LOCK"
        canvas.create_rectangle(e.x * CELL + 2, e.y * CELL + 2,
                                (e.x + 1) * CELL - 2, (e.y + 1) * CELL - 2,
                                fill=color, outline="white", width=2)
        canvas.create_text(e.x * CELL + CELL // 2, e.y * CELL + CELL // 2,
                           text=text, fill="white", font=("Arial", 8, "bold"))


# =====================================================
# 3-ҚАТЫСУШЫ (Даниал): Қозғалыс (Player, Ghost), соқтығысу тексеруі
# =====================================================
class Character:
    """Ортақ класс: ойыншы мен елес екеуі де осыдан мұрагерлік алады."""
    def __init__(self, x, y):
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.px = x      # алдыңғы қадамдағы орны
        self.py = y
        self.dx = 0
        self.dy = 0

    def can_move(self, dx, dy, maze):
        return not maze.is_wall(self.x + dx, self.y + dy)

    def remember(self):
        self.px = self.x
        self.py = self.y

    def reset(self):
        self.x = self.start_x
        self.y = self.start_y
        self.px = self.x
        self.py = self.y
        self.dx = 0
        self.dy = 0


class Player(Character):
    """Pacman: пернетақтамен бағытталады, нүктелерді жейді, шығуға қашады."""
    ANGLES = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}

    def __init__(self, x, y):
        super().__init__(x, y)
        self.want_dx = 0
        self.want_dy = 0
        self.face = 0
        self.mouth = True

    def set_direction(self, dx, dy):
        self.want_dx = dx
        self.want_dy = dy

    def reset(self):
        super().reset()
        self.want_dx = 0
        self.want_dy = 0

    def update(self, maze):
        # Қалаған бағытқа бұрыла алса, бұрылады
        if (self.want_dx, self.want_dy) != (0, 0) and \
                self.can_move(self.want_dx, self.want_dy, maze):
            self.dx = self.want_dx
            self.dy = self.want_dy
        # Қабырға болмаса, алға жүреді
        if (self.dx, self.dy) != (0, 0) and self.can_move(self.dx, self.dy, maze):
            self.x += self.dx
            self.y += self.dy
            self.face = self.ANGLES[(self.dx, self.dy)]
            self.mouth = not self.mouth

    def reached_exit(self, maze):
        """Жеңіс шарты: шығу ашық және ойыншы сонда тұр."""
        return maze.exit.open and maze.is_exit(self.x, self.y)

    def draw(self, canvas):
        half = 45 if self.mouth else 12
        canvas.create_arc(self.x * CELL + 3, self.y * CELL + 3,
                          (self.x + 1) * CELL - 3, (self.y + 1) * CELL - 3,
                          start=self.face + half, extent=360 - 2 * half,
                          fill="#ffe600", outline="#ffe600")


class Ghost(Character):
    """Елес: ойыншыны қуады, кейде кездейсоқ бұрылады. Шығуға кірмейді."""
    def __init__(self, x, y, color):
        super().__init__(x, y)
        self.color = color

    def can_move(self, dx, dy, maze):
        nx, ny = self.x + dx, self.y + dy
        return not maze.is_wall(nx, ny) and not maze.is_exit(nx, ny)

    def update(self, maze, player):
        options = [d for d in DIRS if self.can_move(d[0], d[1], maze)]
        if len(options) > 1:
            back = (-self.dx, -self.dy)          # кері бұрылмайды
            options = [d for d in options if d != back] or options
        if random.random() < 0.6:                # 60% ойыншыға қарай жүреді
            best = min(options, key=lambda d: abs(self.x + d[0] - player.x)
                                              + abs(self.y + d[1] - player.y))
        else:                                    # 40% кездейсоқ
            best = random.choice(options)
        self.dx, self.dy = best
        self.x += self.dx
        self.y += self.dy

    def draw(self, canvas):
        x0 = self.x * CELL + 3
        y0 = self.y * CELL + 3
        x1 = (self.x + 1) * CELL - 3
        y1 = (self.y + 1) * CELL - 3
        mid = (y0 + y1) / 2
        canvas.create_oval(x0, y0, x1, y1, fill=self.color, outline="")
        canvas.create_rectangle(x0, mid, x1, y1, fill=self.color, outline="")
        w = x1 - x0
        for ex in (x0 + w * 0.3, x0 + w * 0.7):
            canvas.create_oval(ex - 4, y0 + 7, ex + 4, y0 + 17,
                               fill="white", outline="")
            canvas.create_oval(ex - 2 + self.dx * 2, y0 + 10 + self.dy * 2,
                               ex + 2 + self.dx * 2, y0 + 14 + self.dy * 2,
                               fill="#1a1aa6", outline="")


# =====================================================
# 1-ҚАТЫСУШЫ (Дильназ): Ойынның негізгі коды (Game)
# =====================================================
class Game:
    """Ойын: ұпай, жан, ойын күйі, экранды салу, іске қосу."""
    COLORS = ["#ff2a2a", "#ff8ad8", "#2affff"]

    def __init__(self, root):
        self.root = root
        root.title("Pacman - URBAN")
        root.resizable(False, False)

        self.info = tk.Label(root, font=("Arial", 14, "bold"),
                             bg="black", fg="white", anchor="w", padx=10)
        self.info.pack(fill="x")

        maze = Maze(MAZE_MAP)
        self.canvas = tk.Canvas(root, width=maze.cols * CELL,
                                height=maze.rows * CELL,
                                bg="black", highlightthickness=0)
        self.canvas.pack()

        root.bind("<Key>", self.on_key)
        self.new_game()
        self.tick()

    def new_game(self):
        self.maze = Maze(MAZE_MAP)
        self.player = Player(*self.maze.player_start)
        self.ghosts = [Ghost(x, y, self.COLORS[i % len(self.COLORS)])
                       for i, (x, y) in enumerate(self.maze.ghost_starts)]
        self.score = 0
        self.lives = 3
        self.ticks = 0
        self.state = "play"      # play / won / lost

    def on_key(self, event):
        keys = {"Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0)}
        if event.keysym in keys:
            self.player.set_direction(*keys[event.keysym])
        elif event.keysym in ("r", "R"):
            self.new_game()

    def check_collision(self):
        """Елес ойыншыға тиді ме? (орын ауыстырып өтіп кетуді де тексереді)"""
        p = self.player
        for g in self.ghosts:
            if (g.x, g.y) == (p.x, p.y):
                return True
            if (g.x, g.y) == (p.px, p.py) and (p.x, p.y) == (g.px, g.py):
                return True
        return False

    def lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            self.state = "lost"
        else:
            self.player.reset()
            for g in self.ghosts:
                g.reset()

    def tick(self):
        if self.state == "play":
            self.ticks += 1
            self.player.remember()
            for g in self.ghosts:
                g.remember()

            self.player.update(self.maze)
            if self.maze.eat_dot(self.player.x, self.player.y):
                self.score += 10
            if self.player.reached_exit(self.maze):
                self.state = "won"
            elif self.check_collision():
                self.lose_life()

            if self.state == "play":
                if self.ticks % 3 != 0:          # елестер сәл баяу жүреді
                    for g in self.ghosts:
                        g.update(self.maze, self.player)
                if self.check_collision():
                    self.lose_life()
        self.draw()
        self.root.after(TICK, self.tick)

    def draw(self):
        self.canvas.delete("all")
        self.maze.draw(self.canvas)
        for g in self.ghosts:
            g.draw(self.canvas)
        self.player.draw(self.canvas)

        if self.maze.exit.open:
            hint = "ШЫҒУ АШЫЛДЫ! Қаш!"
        else:
            hint = f"Қалған нүкте: {len(self.maze.dots)}"
        self.info.config(text=f"Ұпай: {self.score}   Жан: {'♥ ' * self.lives}   {hint}")

        if self.state in ("won", "lost"):
            w = self.maze.cols * CELL
            h = self.maze.rows * CELL
            if self.state == "won":
                title, color = "Жеңіс! Сіз қашып шықтыңыз!", "#27ae60"
            else:
                title, color = "Ойын аяқталды!", "#c0392b"
            self.canvas.create_rectangle(w // 2 - 200, h // 2 - 50,
                                         w // 2 + 200, h // 2 + 50,
                                         fill="white", outline=color, width=3)
            self.canvas.create_text(w // 2, h // 2 - 12, text=title,
                                    font=("Arial", 16, "bold"), fill=color)
            self.canvas.create_text(w // 2, h // 2 + 20,
                                    text="Қайта ойнау үшін R басыңыз",
                                    font=("Arial", 11), fill="#555")


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()