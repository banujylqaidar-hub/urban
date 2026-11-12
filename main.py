# main.py
import pygame

from settings import WIDTH, HEIGHT, FPS, BLACK
from game import Game


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pac-Man на Python")
    clock = pygame.time.Clock()

    font = pygame.font.Font(None, 30)
    big_font = pygame.font.Font(None, 54)

    game = Game()
    running = True

    while running:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r and game.over:
                    game = Game()
                else:
                    game.handle_key(event.key)

        game.update(dt)
        game.draw(screen, font, big_font)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
