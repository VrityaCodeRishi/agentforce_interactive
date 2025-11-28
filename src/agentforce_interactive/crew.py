from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
import re
import shutil
from agentforce_interactive.tools.read_game_design_tool import ReadGameDesignTool
from agentforce_interactive.tools.read_game_code_tool import ReadGameCodeTool
from agentforce_interactive.tools.read_evaluation_report_tool import ReadEvaluationReportTool
from agentforce_interactive.tools.read_report_file_tool import ReadReportFileTool
from agentforce_interactive.tools.code_quality_evaluator_tool import CodeQualityEvaluatorTool
from agentforce_interactive.tools.design_quality_evaluator_tool import DesignQualityEvaluatorTool
from agentforce_interactive.tools.design_compliance_evaluator_tool import DesignComplianceEvaluatorTool
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class AgentforceInteractive():
    """Gaming Studio Crew - Creates, tests, and publishes Python games"""

    agents: List[BaseAgent]
    tasks: List[Task]

    def _sanitize_game_name(self, name: str) -> str:
        """Sanitize game name for folder creation"""
        # Remove special chars, keep only alphanumeric, spaces, hyphens, underscores
        sanitized = re.sub(r'[^a-z0-9\s_-]', '', name.lower())
        # Replace spaces with underscores
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Remove multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized if sanitized else 'untitled_game'

    @before_kickoff
    def setup_game_folder(self, inputs: dict):
        """Create game folder before crew starts, removing existing folder if it exists"""
        game_name = inputs.get('game_name', '')
        if not game_name:
            # Derive name from concept if not provided
            concept = inputs.get('game_concept', 'untitled_game')
            game_name = self._sanitize_game_name(concept)
            inputs['game_name'] = game_name
        
        # Ensure game_name is sanitized
        game_name = self._sanitize_game_name(game_name)
        inputs['game_name'] = game_name
        
        # Create games directory if it doesn't exist
        games_dir = 'games'
        if not os.path.exists(games_dir):
            os.makedirs(games_dir)
        
        # Remove existing game folder if it exists to start fresh
        game_folder = os.path.join(games_dir, game_name)
        if os.path.exists(game_folder):
            shutil.rmtree(game_folder)
            print(f"✓ Removed existing folder: {game_folder}")
        
        # Create fresh game-specific folder
        os.makedirs(game_folder)
        print(f"✓ Created fresh folder: {game_folder}")
        
        return inputs

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def game_designer(self) -> Agent:
        return Agent(
            config=self.agents_config['game_designer'], # type: ignore[index]
            verbose=True
        )

    @agent
    def game_developer(self) -> Agent:
        return Agent(
            config=self.agents_config['game_developer'], # type: ignore[index]
            tools=[ReadGameDesignTool(), ReadGameCodeTool(), ReadEvaluationReportTool()],
            verbose=True
        )

    @agent
    def test_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['test_engineer'], # type: ignore[index]
            tools=[
                ReadGameDesignTool(),
                ReadGameCodeTool(),
                CodeQualityEvaluatorTool(),
                DesignQualityEvaluatorTool(),
                DesignComplianceEvaluatorTool(),
                ReadReportFileTool()  # For compile_evaluation_report_task to read intermediate reports
            ],
            verbose=True
        )

    @agent
    def game_publisher(self) -> Agent:
        return Agent(
            config=self.agents_config['game_publisher'], # type: ignore[index]
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def design_game_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_game_task'], # type: ignore[index]
            output_file='games/{game_name}/game_design.md'
        )

    @task
    def analyze_design_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_design_task'], # type: ignore[index]
            # No context - agent will use read_game_design tool to read the design file
            output_file='games/{game_name}/design_analysis.md'  # Optional output
        )

    @task
    def implement_game_task(self) -> Task:
        return Task(
            config=self.tasks_config['implement_game_task'], # type: ignore[index]
            context=[self.analyze_design_task()],  # Use design analysis as context
            output_file='games/{game_name}/game.py'
        )

    @task
    def create_requirements_task(self) -> Task:
        return Task(
            config=self.tasks_config['create_requirements_task'], # type: ignore[index]
            context=[self.implement_game_task()],  # Use game implementation as context
            output_file='games/{game_name}/requirements.txt'
        )

    @task
    def evaluate_game_task(self) -> Task:
        """Legacy task - kept for backward compatibility. Use split tasks instead."""
        return Task(
            config=self.tasks_config['evaluate_game_task'], # type: ignore[index]
            # No context - agent will use read_game_design and read_game_code tools to read files
            output_file='games/{game_name}/evaluation_report.md'
        )

    @task
    def linter_code_task(self) -> Task:
        return Task(
            config=self.tasks_config['linter_code_task'], # type: ignore[index]
            output_file='games/{game_name}/linter_report.md'
        )

    @task
    def evaluate_code_quality_task(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_code_quality_task'], # type: ignore[index]
            output_file='games/{game_name}/code_quality_report.md'
        )

    @task
    def evaluate_design_quality_task(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_design_quality_task'], # type: ignore[index]
            output_file='games/{game_name}/design_quality_report.md'
        )

    @task
    def evaluate_design_compliance_task(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_design_compliance_task'], # type: ignore[index]
            output_file='games/{game_name}/compliance_report.md'
        )

    @task
    def compile_evaluation_report_task(self) -> Task:
        return Task(
            config=self.tasks_config['compile_evaluation_report_task'], # type: ignore[index]
            context=[
                self.linter_code_task(),
                self.evaluate_code_quality_task(),
                self.evaluate_design_quality_task(),
                self.evaluate_design_compliance_task()
            ],
            output_file='games/{game_name}/evaluation_report.md'
        )

    @task
    def fix_game_issues_task(self) -> Task:
        return Task(
            config=self.tasks_config['fix_game_issues_task'], # type: ignore[index]
            # Agent will use read_game_code to read evaluation_report.md and fix issues
            # This task is ONLY invoked when evaluation finds issues
            output_file='games/{game_name}/game.py'  # Fixes game.py (and potentially game_design.md)
        )

    @task
    def publish_game_task(self) -> Task:
        return Task(
            config=self.tasks_config['publish_game_task'], # type: ignore[index]
            context=[
                self.design_game_task(),
                self.analyze_design_task(),
                self.implement_game_task(),  # Use new task name
                self.create_requirements_task(),
                self.compile_evaluation_report_task()  # Use compiled report instead of single evaluate task
            ],
            output_file='games/{game_name}/README.md'
        )

    @crew
    def crew(self) -> Crew:
        """
        Creates the Gaming Studio crew for game design, development, and evaluation.
        """
        # Get the tasks list
        tasks_list = self.tasks
        
        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=tasks_list, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
