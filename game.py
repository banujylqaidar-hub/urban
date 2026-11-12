# game.py
import random
import pygame

from settings import (
    TILE_SIZE, HUD_HEIGHT, WIDTH, HEIGHT, LEVEL_MAP,
    BLACK, BLUE, WALL_BLUE, YELLOW, WHITE, RED, PINK,
    CYAN, ORANGE, GREEN, PLAYER_STEP_MS, GHOST_STEP_MS,
    PLAYER_LIVES, DOT_POINTS
)


class Entity:
    """Базовый класс для игрока и призраков (наследование)."""

    def __init__(self, row, col, color):
        self.start_row = row
        self.start_col = col
        self.row = row
        self.col = col
        self.color = color

    def reset_position(self):
        self.row = self.start_row
        self.col = self.start_col

    def draw(self, screen):
        x = self.col * TILE_SIZE + TILE_SIZE // 2
        y = self.row * TILE_SIZE + TILE_SIZE // 2
        pygame.draw.circle(screen, self.color, (x, y), TILE_SIZE // 2 - 3)


class Player(Entity):
    """Игрок, который двигается по клеткам лабиринта."""

    def __init__(self, row, col):
        super().__init__(row, col, YELLOW)
        self.direction = (0, 0)
        self.next_direction = (0, 0)

    def move(self, game_map):
        # Сначала пробуем выполнить последнее нажатое направление.
        if self.can_move(game_map, self.next_direction):
            self.direction = self.next_direction

        if self.can_move(game_map, self.direction):
            dr, dc = self.direction
            self.row += dr
            self.col += dc

    def can_move(self, game_map, direction):
        dr, dc = direction
        if direction == (0, 0):
            return False
        new_row = self.row + dr
        new_col = self.col + dc
        return (
            0 <= new_row < len(game_map)
            and 0 <= new_col < len(game_map[0])
            and game_map[new_row][new_col] != "#"
        )

    def draw(self, screen):
        x = self.col * TILE_SIZE + TILE_SIZE // 2
        y = self.row * TILE_SIZE + TILE_SIZE // 2
        pygame.draw.circle(screen, self.color, (x, y), TILE_SIZE // 2 - 3)
        # Небольшой треугольный "рот" Пакмана.
        pygame.draw.polygon(
            screen, BLACK,
            [(x, y), (x + 13, y - 8), (x + 13, y + 8)]
        )


class Ghost(Entity):
    """Призрак: иногда выбирает ход ближе к игроку, иногда случайный."""

    def __init__(self, row, col, color):
        super().__init__(row, col, color)

    def move(self, game_map, player):
        options = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = self.row + dr, self.col + dc
            if (0 <= nr < len(game_map) and
                    0 <= nc < len(game_map[0]) and
                    game_map[nr][nc] != "#"):
                options.append((nr, nc))

        if not options:
            return

        # В большинстве случаев призрак выбирает клетку ближе к игроку.
        if random.random() < 0.7:
            options.sort(
                key=lambda pos: abs(pos[0] - player.row) + abs(pos[1] - player.col)
            )
            best_distance = abs(options[0][0] - player.row) + abs(options[0][1] - player.col)
            best_options = [
                pos for pos in options
                if abs(pos[0] - player.row) + abs(pos[1] - player.col) == best_distance
            ]
            target = random.choice(best_options)
        else:
            target = random.choice(options)

        self.row, self.col = target


class Game:
    """Хранит состояние игры и управляет всеми игровыми объектами."""

    def __init__(self):
        self.game_map = [list(row) for row in LEVEL_MAP]
        self.score = 0
        self.lives = PLAYER_LIVES
        self.over = False
        self.won = False
        self.player = None
        self.ghosts = []
        self.dots_left = 0
        self.player_timer = 0
        self.ghost_timer = 0
        self.create_objects()

    def create_objects(self):
        ghost_colors = [RED, PINK, CYAN, ORANGE]
        for row in range(len(self.game_map)):
            for col in range(len(self.game_map[0])):
                cell = self.game_map[row][col]
                if cell == "P":
                    self.player = Player(row, col)
                    self.game_map[row][col] = " "
                elif cell == "G":
                    color = ghost_colors[len(self.ghosts) % len(ghost_colors)]
                    self.ghosts.append(Ghost(row, col, color))
                    self.game_map[row][col] = " "
                elif cell == ".":
                    self.dots_left += 1

    def handle_key(self, key):
        directions = {
            pygame.K_UP: (-1, 0),
            pygame.K_DOWN: (1, 0),
            pygame.K_LEFT: (0, -1),
            pygame.K_RIGHT: (0, 1),
            pygame.K_w: (-1, 0),
            pygame.K_s: (1, 0),
            pygame.K_a: (0, -1),
            pygame.K_d: (0, 1),
        }
        if key in directions and self.player:
            self.player.next_direction = directions[key]

    def update(self, dt):
        if self.over:
            return

        self.player_timer += dt
        self.ghost_timer += dt

        if self.player_timer >= PLAYER_STEP_MS:
            self.player_timer = 0
            self.player.move(self.game_map)
            self.collect_dot()

        if self.ghost_timer >= GHOST_STEP_MS:
            self.ghost_timer = 0
            for ghost in self.ghosts:
                ghost.move(self.game_map, self.player)

        self.check_collisions()

        if self.dots_left == 0:
            self.won = True
            self.over = True

    def collect_dot(self):
        if self.game_map[self.player.row][self.player.col] == ".":
            self.game_map[self.player.row][self.player.col] = " "
            self.score += DOT_POINTS
            self.dots_left -= 1

    def check_collisions(self):
        for ghost in self.ghosts:
            if ghost.row == self.player.row and ghost.col == self.player.col:
                self.lives -= 1
                if self.lives <= 0:
                    self.over = True
                else:
                    self.player.reset_position()
                    for item in self.ghosts:
                        item.reset_position()
                break

    def draw(self, screen, font, big_font):
        screen.fill(BLACK)

        # Лабиринт и точки.
        for row, line in enumerate(self.game_map):
            for col, cell in enumerate(line):
                x = col * TILE_SIZE
                y = row * TILE_SIZE
                if cell == "#":
                    pygame.draw.rect(
                        screen, WALL_BLUE,
                        (x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4),
                        border_radius=6
                    )
                elif cell == ".":
                    pygame.draw.circle(
                        screen, WHITE,
                        (x + TILE_SIZE // 2, y + TILE_SIZE // 2), 3
                    )

        self.player.draw(screen)
        for ghost in self.ghosts:
            ghost.draw(screen)

        # Панель информации.
        pygame.draw.rect(screen, (20, 20, 40), (0, ROWS_PIXELS, WIDTH, HUD_HEIGHT))
        score_text = font.render(f"Очки: {self.score}", True, WHITE)
        lives_text = font.render(f"Жизни: {self.lives}", True, WHITE)
        screen.blit(score_text, (12, ROWS_PIXELS + 18))
        screen.blit(lives_text, (WIDTH - 125, ROWS_PIXELS + 18))

        if self.over:
            message = "ПОБЕДА!" if self.won else "ИГРА ОКОНЧЕНА"
            color = GREEN if self.won else RED
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            screen.blit(overlay, (0, 0))
            title = big_font.render(message, True, color)
            hint = font.render("Нажмите R, чтобы начать заново", True, WHITE)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 25)))


# Высота игрового поля без нижней панели.
ROWS_PIXELS = len(LEVEL_MAP) * TILE_SIZE
