import pygame
import sys
import ui
from game import Game

if __name__ == "__main__":
    pygame.init()
    
    # Load the config FIRST before setting the display
    ui.initialize_game()
    
    # Now ui.SCREEN_WIDTH and ui.SCREEN_HEIGHT have the correct values
    main_screen_surface = pygame.display.set_mode((ui.SCREEN_WIDTH, ui.SCREEN_HEIGHT))
    pygame.display.set_caption("Chess AI")
    
    # Load images and sounds
    ui.load_assets()
    
    # Start the game loop
    game = Game(main_screen_surface)
    game.run()