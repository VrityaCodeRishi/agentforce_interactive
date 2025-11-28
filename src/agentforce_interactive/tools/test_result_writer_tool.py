from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import subprocess
import os
import sys


class TestResultWriterToolInput(BaseModel):
    """Input schema for TestResultWriterTool."""
    game_name: str = Field(..., description="The name of the game folder (e.g., 'snake_game') where test_game.py is located.")


class TestResultWriterTool(BaseTool):
    name: str = "write_test_results"
    description: str = (
        "Executes test_game.py and writes the complete test output to a file called test_output.txt in the game folder. "
        "This tool runs 'python -m unittest test_game.py -v' in the games/{game_name}/ directory, captures all output "
        "(including passes, failures, errors, and tracebacks), and saves it to games/{game_name}/test_output.txt. "
        "Use this tool first, then read the test_output.txt file to create the test report. This ensures the report "
        "is based on actual test execution results, not fabricated data."
    )
    args_schema: Type[BaseModel] = TestResultWriterToolInput

    def _run(self, game_name: str) -> str:
        """
        Execute test_game.py and write the complete output to test_output.txt.
        
        Args:
            game_name: Name of the game folder (e.g., 'snake_game')
            
        Returns:
            Confirmation message with the path to the output file
        """
        try:
            game_dir = os.path.join("games", game_name)
            test_file = os.path.join(game_dir, "test_game.py")
            output_file = os.path.join(game_dir, "test_output.txt")
            
            # Check if test file exists
            if not os.path.exists(test_file):
                return f"ERROR: Test file not found at {test_file}. Please verify the game_name is correct."
            
            # Change to the test directory
            original_dir = os.getcwd()
            os.chdir(game_dir)
            
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
                output += f"\n\n[Test execution exited with code {result.returncode}]"
                
                # Write the complete output to file
                # Use "test_output.txt" (relative to current directory after chdir)
                # or use absolute path to ensure correct location
                output_file_local = "test_output.txt"
                with open(output_file_local, 'w', encoding='utf-8') as f:
                    f.write(output)
                
                # Verify file was created (use absolute path for verification)
                abs_output_file = os.path.abspath(output_file_local)
                if not os.path.exists(abs_output_file):
                    return f"ERROR: Failed to create test_output.txt at {abs_output_file}"
                
                return (
                    f"SUCCESS: Test results written to {output_file}\n"
                    f"Test execution completed with exit code {result.returncode}\n"
                    f"Output file contains {len(output)} characters\n"
                    f"Please read the file {output_file} to see the complete test results including all passes, failures, and errors."
                )
                
            finally:
                # Always return to original directory
                os.chdir(original_dir)
                    
        except subprocess.TimeoutExpired:
            return f"ERROR: Test execution timed out after 60 seconds. No output file was created."
        except Exception as e:
            return f"ERROR: Failed to execute tests and write output file: {str(e)}\n\nPlease check that:\n- The game_name is correct\n- test_game.py exists in games/{game_name}/\n- Python and unittest are available\n- Write permissions exist for games/{game_name}/ directory"

