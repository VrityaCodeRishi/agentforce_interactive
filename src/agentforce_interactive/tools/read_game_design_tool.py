from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os


class ReadGameDesignToolInput(BaseModel):
    """Input schema for ReadGameDesignTool."""
    game_name: str = Field(..., description="The name of the game folder (e.g., 'snake_game') where game_design.md is located.")


class ReadGameDesignTool(BaseTool):
    name: str = "read_game_design"
    description: str = (
        "Reads the game design document (game_design.md) from the specified game folder. "
        "This tool reads the complete contents of games/{game_name}/game_design.md and returns it. "
        "Use this tool to read the game design specifications, mechanics, and technical requirements "
        "that were created by the game designer agent."
    )
    args_schema: Type[BaseModel] = ReadGameDesignToolInput

    def _run(self, game_name: str) -> str:
        """
        Read the game_design.md file and return its complete contents.
        
        Args:
            game_name: Name of the game folder (e.g., 'snake_game')
            
        Returns:
            Complete contents of the game_design.md file, or an error message if file doesn't exist
        """
        try:
            design_file = os.path.join("games", game_name, "game_design.md")
            
            # Check if file exists
            if not os.path.exists(design_file):
                return (
                    f"ERROR: Game design file not found at {design_file}\n"
                    f"Please ensure the game designer has created the design document first.\n"
                    f"The file should be at games/{game_name}/game_design.md"
                )
            
            # Read the complete file contents
            with open(design_file, 'r', encoding='utf-8') as f:
                contents = f.read()
            
            if not contents:
                return f"WARNING: Game design file {design_file} exists but is empty."
            
            return (
                f"Game design document contents from {design_file}:\n"
                f"{'=' * 80}\n"
                f"{contents}\n"
                f"{'=' * 80}\n"
                f"\n[File contains {len(contents)} characters]"
            )
            
        except PermissionError:
            return f"ERROR: Permission denied when reading {design_file}. Please check file permissions."
        except Exception as e:
            return f"ERROR: Failed to read game design file: {str(e)}\n\nPlease check that:\n- The game_name is correct\n- game_design.md exists in games/{game_name}/\n- The file is readable"

