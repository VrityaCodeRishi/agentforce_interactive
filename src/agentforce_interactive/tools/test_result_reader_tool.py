from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os


class TestResultReaderToolInput(BaseModel):
    """Input schema for TestResultReaderTool."""
    game_name: str = Field(..., description="The name of the game folder (e.g., 'snake_game') where test_output.txt is located.")


class TestResultReaderTool(BaseTool):
    name: str = "read_test_results"
    description: str = (
        "Reads the test_output.txt file that was created by the write_test_results tool. "
        "This tool reads the complete test execution output from games/{game_name}/test_output.txt "
        "and returns it exactly as written. Use this tool after write_test_results has created the file "
        "to get the actual test execution results including all passes, failures, errors, and tracebacks."
    )
    args_schema: Type[BaseModel] = TestResultReaderToolInput

    def _run(self, game_name: str) -> str:
        """
        Read the test_output.txt file and return its complete contents.
        
        Args:
            game_name: Name of the game folder (e.g., 'snake_game')
            
        Returns:
            Complete contents of the test_output.txt file, or an error message if file doesn't exist
        """
        try:
            output_file = os.path.join("games", game_name, "test_output.txt")
            
            # Check if file exists
            if not os.path.exists(output_file):
                return (
                    f"ERROR: Test output file not found at {output_file}\n"
                    f"Please run write_test_results tool first to create this file.\n"
                    f"The file should be created by calling write_test_results with game_name='{game_name}'"
                )
            
            # Read the complete file contents
            with open(output_file, 'r', encoding='utf-8') as f:
                contents = f.read()
            
            if not contents:
                return f"WARNING: Test output file {output_file} exists but is empty. Please run write_test_results tool again."
            
            return (
                f"Test output file contents from {output_file}:\n"
                f"{'=' * 80}\n"
                f"{contents}\n"
                f"{'=' * 80}\n"
                f"\n[File contains {len(contents)} characters]"
            )
            
        except PermissionError:
            return f"ERROR: Permission denied when reading {output_file}. Please check file permissions."
        except Exception as e:
            return f"ERROR: Failed to read test output file: {str(e)}\n\nPlease check that:\n- The game_name is correct\n- test_output.txt exists in games/{game_name}/\n- The file is readable"

