from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
import glob


class ReadGameCodeToolInput(BaseModel):
    """Input schema for ReadGameCodeTool."""
    game_name: str = Field(..., description="The name of the game folder (e.g., 'snake_game') where game code files are located.")


class ReadGameCodeTool(BaseTool):
    name: str = "read_game_code"
    description: str = (
        "Reads all game code files from the specified game folder. This tool reads game.py and any other "
        "Python game files (like snake.py, food.py, constants.py, etc.) that were created by the game developer. "
        "It returns the complete contents of all game code files. Use this tool to understand the actual "
        "game implementation structure, classes, functions, and how the game is organized."
    )
    args_schema: Type[BaseModel] = ReadGameCodeToolInput

    def _run(self, game_name: str) -> str:
        """
        Read all game code files and return their complete contents.
        
        Args:
            game_name: Name of the game folder (e.g., 'snake_game')
            
        Returns:
            Complete contents of all game code files, or an error message if files don't exist
        """
        try:
            game_dir = os.path.join("games", game_name)
            
            # Check if directory exists
            if not os.path.exists(game_dir):
                return (
                    f"ERROR: Game directory not found at {game_dir}\n"
                    f"Please ensure the game developer has created the game files first."
                )
            
            # Find all Python files in the game directory (excluding test files)
            python_files = []
            for file_path in glob.glob(os.path.join(game_dir, "*.py")):
                filename = os.path.basename(file_path)
                # Exclude test files
                if not filename.startswith("test_") and filename != "__init__.py":
                    python_files.append(file_path)
            
            if not python_files:
                return (
                    f"ERROR: No game code files found in {game_dir}\n"
                    f"Expected to find game.py or other Python game files.\n"
                    f"Please ensure the game developer has created the game files first."
                )
            
            # Sort files to ensure consistent order (game.py first if it exists)
            python_files.sort(key=lambda x: (os.path.basename(x) != "game.py", os.path.basename(x)))
            
            # Read all files
            all_contents = []
            for file_path in python_files:
                filename = os.path.basename(file_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        contents = f.read()
                    all_contents.append(
                        f"\n{'=' * 80}\n"
                        f"File: {filename}\n"
                        f"Path: {file_path}\n"
                        f"{'=' * 80}\n"
                        f"{contents}\n"
                    )
                except Exception as e:
                    all_contents.append(
                        f"\n{'=' * 80}\n"
                        f"File: {filename}\n"
                        f"Path: {file_path}\n"
                        f"ERROR: Failed to read file - {str(e)}\n"
                        f"{'=' * 80}\n"
                    )
            
            combined = "".join(all_contents)
            
            return (
                f"Game code files from {game_dir}:\n"
                f"Found {len(python_files)} file(s): {', '.join(os.path.basename(f) for f in python_files)}\n"
                f"{combined}\n"
                f"[Total content: {len(combined)} characters]"
            )
            
        except Exception as e:
            return f"ERROR: Failed to read game code files: {str(e)}\n\nPlease check that:\n- The game_name is correct\n- Game files exist in games/{game_name}/\n- The files are readable"

