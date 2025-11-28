from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os


class ReadEvaluationReportToolInput(BaseModel):
    """Input schema for ReadEvaluationReportTool."""
    game_name: str = Field(..., description="The name of the game folder (e.g., 'snake_game') where the evaluation_report.md file is located.")


class ReadEvaluationReportTool(BaseTool):
    name: str = "read_evaluation_report"
    description: str = (
        "Reads the evaluation report (evaluation_report.md) from the specified game folder. "
        "This report contains detailed information about code quality issues, design document quality issues, "
        "and design compliance issues found by the evaluator. Use this tool to understand what needs to be fixed."
    )
    args_schema: Type[BaseModel] = ReadEvaluationReportToolInput

    def _run(self, game_name: str) -> str:
        """
        Read the evaluation report and return its complete contents.
        
        Args:
            game_name: Name of the game folder (e.g., 'snake_game')
            
        Returns:
            Complete contents of evaluation_report.md, or an error message if file doesn't exist
        """
        try:
            eval_report_path = os.path.join("games", game_name, "evaluation_report.md")
            
            if not os.path.exists(eval_report_path):
                return (
                    f"ERROR: Evaluation report not found at {eval_report_path}\n"
                    f"Please ensure the evaluation task has been run first."
                )
            
            with open(eval_report_path, 'r', encoding='utf-8') as f:
                contents = f.read()
            
            return (
                f"Evaluation Report from games/{game_name}/evaluation_report.md:\n"
                f"{'=' * 80}\n"
                f"{contents}\n"
                f"{'=' * 80}\n"
                f"[Total content: {len(contents)} characters]"
            )
            
        except Exception as e:
            return f"ERROR: Failed to read evaluation report: {str(e)}\n\nPlease check that:\n- The game_name is correct\n- evaluation_report.md exists in games/{game_name}/\n- The file is readable"

