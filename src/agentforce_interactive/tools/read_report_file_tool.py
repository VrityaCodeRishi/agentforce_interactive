from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os


class ReadReportFileToolInput(BaseModel):
    """Input schema for ReadReportFileTool."""
    game_name: str = Field(..., description="The name of the game folder (e.g., 'snake_game')")
    filename: str = Field(..., description="The name of the report file to read (e.g., 'linter_report.md', 'code_quality_report.md')")


class ReadReportFileTool(BaseTool):
    name: str = "read_report_file"
    description: str = (
        "Reads a report file from the specified game folder. "
        "Use this tool to read intermediate evaluation reports like linter_report.md, "
        "code_quality_report.md, design_quality_report.md, or compliance_report.md. "
        "This is useful for compiling all reports into a final evaluation_report.md."
    )
    args_schema: Type[BaseModel] = ReadReportFileToolInput

    def _run(self, game_name: str, filename: str) -> str:
        """
        Read a report file and return its complete contents.
        
        Args:
            game_name: Name of the game folder (e.g., 'snake_game')
            filename: Name of the report file (e.g., 'linter_report.md')
            
        Returns:
            Complete contents of the report file, or an error message if file doesn't exist
        """
        try:
            report_path = os.path.join("games", game_name, filename)
            
            if not os.path.exists(report_path):
                return (
                    f"ERROR: Report file not found at {report_path}\n"
                    f"Please ensure the report has been generated first."
                )
            
            with open(report_path, 'r', encoding='utf-8') as f:
                contents = f.read()
            
            return (
                f"Report from games/{game_name}/{filename}:\n"
                f"{'=' * 80}\n"
                f"{contents}\n"
                f"{'=' * 80}\n"
                f"[Total content: {len(contents)} characters]"
            )
            
        except Exception as e:
            return f"ERROR: Failed to read report file: {str(e)}\n\nPlease check that:\n- The game_name is correct\n- {filename} exists in games/{game_name}/\n- The file is readable"

