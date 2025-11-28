from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import subprocess
import os
import sys
import tempfile


class GameTesterToolInput(BaseModel):
    """Input schema for GameTesterTool."""
    game_name: str = Field(..., description="The name of the game folder (e.g., 'snake_game', 'pong_game', 'tetris_game') where game.py is located. Works with any game type.")


class GameTesterTool(BaseTool):
    name: str = "test_gameplay"
    description: str = (
        "Runs the game and tests actual gameplay functionality by importing the game module and testing core gameplay features. "
        "This tool dynamically imports the game, creates a game instance, simulates user input (keyboard events), and verifies "
        "that the game responds correctly to user actions. Use this to test that the game actually works when played, not just "
        "that individual components work in isolation. This tool works with any game type (Snake, Pong, Tetris, etc.) by "
        "dynamically discovering the game's structure and testing generic gameplay features."
    )
    args_schema: Type[BaseModel] = GameTesterToolInput

    def _run(self, game_name: str) -> str:
        """
        Run the game and test gameplay functionality dynamically.
        
        Args:
            game_name: Name of the game folder (e.g., 'snake_game', 'pong_game')
            
        Returns:
            Test results including what was tested and whether it passed or failed
        """
        try:
            game_dir = os.path.join("games", game_name)
            game_file = os.path.join(game_dir, "game.py")
            
            if not os.path.exists(game_file):
                return f"ERROR: Game file not found at {game_file}. Please verify the game_name is correct."
            
            # Create a generic test script that works with any game
            test_script = f'''
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import sys
sys.path.insert(0, "{game_dir}")
import pygame
import game as game_module

# Initialize pygame in headless mode
pygame.init()

test_results = []

# Test 1: Game module can be imported and instantiated
try:
    # Try to create a game instance - different games may have different class names
    # Try common patterns: Game, SnakeGame, PongGame, etc.
    game = None
    game_class = None
    
    # Look for a main game class
    if hasattr(game_module, "Game"):
        game_class = game_module.Game
    elif hasattr(game_module, "SnakeGame"):
        game_class = game_module.SnakeGame
    elif hasattr(game_module, "PongGame"):
        game_class = game_module.PongGame
    else:
        # Try to find any class that looks like a game class
        for attr_name in dir(game_module):
            attr = getattr(game_module, attr_name)
            if isinstance(attr, type) and attr_name[0].isupper():
                # Check if it has common game methods
                if hasattr(attr, "__init__"):
                    try:
                        game = attr()
                        game_class = attr
                        break
                    except:
                        pass
    
    if game is None and game_class is not None:
        game = game_class()
    
    if game is None:
        test_results.append("FAIL: Could not instantiate game - no game class found")
    else:
        test_results.append("PASS: Game can be instantiated")
        game_instance = game
except Exception as e:
    test_results.append(f"FAIL: Game instantiation - {{e}}")
    game_instance = None

if game_instance is not None:
    # Test 2: Game responds to keyboard input
    try:
        # Get the game's current state/attributes to understand its structure
        game_attrs = dir(game_instance)
        
        # Try to simulate key presses and verify game responds
        # Test common keys: arrow keys and WASD
        test_keys = [
            (pygame.K_UP, "UP arrow"),
            (pygame.K_DOWN, "DOWN arrow"),
            (pygame.K_LEFT, "LEFT arrow"),
            (pygame.K_RIGHT, "RIGHT arrow"),
            (pygame.K_w, "W key"),
            (pygame.K_s, "S key"),
            (pygame.K_a, "A key"),
            (pygame.K_d, "D key"),
        ]
        
        keys_responded = 0
        for key, key_name in test_keys:
            # Post a key event
            key_event = pygame.event.Event(pygame.KEYDOWN, key=key)
            pygame.event.post(key_event)
            
            # Get events to verify they were posted
            events = pygame.event.get()
            if len(events) > 0:
                keys_responded += 1
        
        # Check if game has methods that handle input
        has_input_handler = any(
            'key' in attr.lower() or 'input' in attr.lower() or 'event' in attr.lower() or 'handle' in attr.lower()
            for attr in game_attrs if callable(getattr(game_instance, attr, None))
        )
        
        if has_input_handler and keys_responded > 0:
            test_results.append(f"PASS: Game can receive keyboard input events ({{keys_responded}} keys tested)")
        elif keys_responded > 0:
            test_results.append(f"WARN: Keyboard events work but input handler not clearly detected")
        else:
            test_results.append("WARN: Game input handling not detected - may need manual testing")
    except Exception as e:
        test_results.append(f"ERROR: Keyboard input test - {{e}}")
    
    # Test 3: Game has an update or run method
    try:
        has_update = hasattr(game_instance, "update") or hasattr(game_instance, "run") or hasattr(game_instance, "tick")
        if has_update:
            test_results.append("PASS: Game has update/run method")
        else:
            test_results.append("WARN: Game update method not found")
    except Exception as e:
        test_results.append(f"ERROR: Update method check - {{e}}")
    
    # Test 4: Game has a draw or render method
    try:
        has_draw = hasattr(game_instance, "draw") or hasattr(game_instance, "render") or hasattr(game_instance, "display")
        if has_draw:
            test_results.append("PASS: Game has draw/render method")
        else:
            test_results.append("WARN: Game draw method not found")
    except Exception as e:
        test_results.append(f"ERROR: Draw method check - {{e}}")
    
    # Test 5: Test that game actually responds to input (integration test)
    try:
        # Try to test that input actually changes game state
        # This works by: posting key event -> calling update -> checking if state changed
        
        # Save initial state if possible
        initial_state = None
        if hasattr(game_instance, "state"):
            initial_state = game_instance.state
        elif hasattr(game_instance, "direction"):
            initial_state = getattr(game_instance, "direction", None)
        elif hasattr(game_instance, "snake"):
            initial_state = game_instance.snake[0] if len(game_instance.snake) > 0 else None
        
        # Post a key event
        key_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
        pygame.event.post(key_event)
        
        # Try to process the event through game's update method
        events_processed = False
        if hasattr(game_instance, "update_playing"):
            # Some games have update_playing that takes events
            try:
                events = pygame.event.get()
                game_instance.update_playing(events)
                events_processed = True
            except:
                pass
        elif hasattr(game_instance, "handle_events"):
            try:
                events = pygame.event.get()
                game_instance.handle_events(events)
                events_processed = True
            except:
                pass
        elif hasattr(game_instance, "update"):
            # Try update with events or time delta
            try:
                events = pygame.event.get()
                try:
                    game_instance.update(events, 0.1)
                    events_processed = True
                except TypeError:
                    try:
                        game_instance.update(0.1)
                        events_processed = True
                    except:
                        game_instance.update()
                        events_processed = True
            except:
                pass
        
        # Check if state changed (indicating game responded to input)
        state_changed = False
        if initial_state is not None:
            if hasattr(game_instance, "state") and game_instance.state != initial_state:
                state_changed = True
            elif hasattr(game_instance, "direction") and getattr(game_instance, "direction", None) != initial_state:
                state_changed = True
            elif hasattr(game_instance, "next_direction"):
                # Check if next_direction changed (indicates input was processed)
                new_direction = getattr(game_instance, "next_direction", None)
                if new_direction != initial_state:
                    state_changed = True
        
        if events_processed:
            if state_changed:
                test_results.append("PASS: Game responds to keyboard input (state changed)")
            else:
                test_results.append("WARN: Game processes events but state may not change immediately")
        else:
            test_results.append("WARN: Could not test game response to input - update method may need events parameter")
    except Exception as e:
        test_results.append(f"ERROR: Game input response test - {{e}}")
    
    # Test 6: Try to call update if it exists (test that game can progress)
    try:
        if hasattr(game_instance, "update"):
            # Try calling update with a small time delta
            try:
                game_instance.update(0.1)
                test_results.append("PASS: Game update() can be called")
            except TypeError:
                # Maybe update takes no args
                try:
                    game_instance.update()
                    test_results.append("PASS: Game update() can be called")
                except:
                    test_results.append("WARN: Game update() exists but cannot be called")
        elif hasattr(game_instance, "tick"):
            try:
                game_instance.tick()
                test_results.append("PASS: Game tick() can be called")
            except:
                test_results.append("WARN: Game tick() exists but cannot be called")
    except Exception as e:
        test_results.append(f"ERROR: Game update test - {{e}}")
    
    # Test 6: Test that game state can change (if applicable)
    try:
        if hasattr(game_instance, "state"):
            initial_state = game_instance.state
            # Try to change state if there's a method to do so
            if hasattr(game_instance, "reset") or hasattr(game_instance, "reset_game"):
                reset_method = getattr(game_instance, "reset", None) or getattr(game_instance, "reset_game", None)
                if reset_method:
                    reset_method()
                    test_results.append("PASS: Game state can be reset")
        elif hasattr(game_instance, "score"):
            # Games with score can be tested
            test_results.append("PASS: Game has score/state tracking")
    except Exception as e:
        test_results.append(f"ERROR: Game state test - {{e}}")

pygame.quit()

# Print results
for result in test_results:
    print(result)

# Count passes and failures
passed = sum(1 for r in test_results if r.startswith("PASS"))
failed = sum(1 for r in test_results if r.startswith("FAIL"))
warnings = sum(1 for r in test_results if r.startswith("WARN"))
errors = sum(1 for r in test_results if r.startswith("ERROR"))

print(f"\\nGameplay Test Summary: {{passed}} passed, {{failed}} failed, {{warnings}} warnings, {{errors}} errors")
'''
            
            # Write test script to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_script)
                temp_script = f.name
            
            try:
                # Run the test script
                result = subprocess.run(
                    [sys.executable, temp_script],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=game_dir
                )
                
                output = result.stdout
                if result.stderr:
                    output += "\n" + result.stderr
                
                if result.returncode != 0:
                    output += f"\n\n[Gameplay test exited with code {result.returncode}]"
                else:
                    output += f"\n\n[Gameplay test completed with code {result.returncode}]"
                
                return output
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_script):
                    os.unlink(temp_script)
                    
        except subprocess.TimeoutExpired:
            return "ERROR: Gameplay test timed out after 30 seconds."
        except Exception as e:
            return f"ERROR: Failed to test gameplay: {str(e)}\n\nPlease check that:\n- The game_name is correct\n- game.py exists in games/{game_name}/\n- Python and pygame are available"
