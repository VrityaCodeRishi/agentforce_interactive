from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import subprocess
import os
import sys


class TestExecutorToolInput(BaseModel):
    """Input schema for TestExecutorTool."""
    game_name: str = Field(..., description="The name of the game folder (e.g., 'snake_game') where test_game.py is located.")


class TestExecutorTool(BaseTool):
    name: str = "execute_tests"
    description: str = (
        "Executes the test_game.py file in the specified game folder and returns the complete test output. "
        "This tool runs 'python -m unittest test_game.py -v' in the games/{game_name}/ directory and captures "
        "all output including test results, failures, errors, and tracebacks. Use this to get actual test execution results."
    )
    args_schema: Type[BaseModel] = TestExecutorToolInput

    def _run(self, game_name: str) -> str:
        """
        Execute test_game.py in the specified game directory and return the output.
        
        Args:
            game_name: Name of the game folder (e.g., 'snake_game')
            
        Returns:
            Complete test execution output including all test results, failures, and errors
        """
        try:
            # Construct the path to the test file
            test_dir = os.path.join("games", game_name)
            test_file = os.path.join(test_dir, "test_game.py")
            
            # Check if test file exists
            if not os.path.exists(test_file):
                return f"ERROR: Test file not found at {test_file}. Please verify the game_name is correct."
            
            # Change to the test directory
            original_dir = os.getcwd()
            os.chdir(test_dir)
            
            try:
                # Run the tests with unittest
                result = subprocess.run(
                    [sys.executable, "-m", "unittest", "test_game.py", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60  # 60 second timeout
                )
                
                # Combine stdout and stderr
                output = result.stdout
                if result.stderr:
                    output += "\n" + result.stderr
                
                # Add return code information
                if result.returncode != 0:
                    output += f"\n\n[Test execution exited with code {result.returncode}]"
                else:
                    output += f"\n\n[Test execution completed successfully with code {result.returncode}]"
                
                return output
                
            finally:
                # Always return to original directory
                os.chdir(original_dir)
                
        except subprocess.TimeoutExpired:
            return "ERROR: Test execution timed out after 60 seconds."
        except Exception as e:
            return f"ERROR: Failed to execute tests: {str(e)}\n\nPlease check that:\n- The game_name is correct\n- test_game.py exists in games/{game_name}/\n- Python and unittest are available"

