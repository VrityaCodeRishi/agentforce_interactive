#!/usr/bin/env python
import sys
import warnings
import os
import re

from datetime import datetime

from agentforce_interactive.crew import AgentforceInteractive

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def _sanitize_game_name(name: str) -> str:
    """Sanitize game name for folder creation"""
    sanitized = re.sub(r'[^a-z0-9\s_-]', '', name.lower())
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    return sanitized if sanitized else 'untitled_game'

def _ensure_game_folder(game_name: str):
    """Create game folder if it doesn't exist"""
    games_dir = 'games'
    if not os.path.exists(games_dir):
        os.makedirs(games_dir)
    
    game_folder = os.path.join(games_dir, game_name)
    if not os.path.exists(game_folder):
        os.makedirs(game_folder)
    return game_folder

def _check_evaluation_for_issues(game_name: str):
    """
    Check evaluation report for issues.
    Returns: (has_issues: bool, total_issues: int)
    """
    base_dir = os.path.join('games', game_name)
    eval_report_path = os.path.join(base_dir, 'evaluation_report.md')
    linter_report_path = os.path.join(base_dir, 'linter_report.md')
    code_quality_report_path = os.path.join(base_dir, 'code_quality_report.md')
    game_file_path = os.path.join(base_dir, 'game.py')

    has_issues = False
    total_issues = 0

    # 1) Parse the high-level evaluation report if it exists,
    #    but do NOT rely on it as the only source of truth.
    if os.path.exists(eval_report_path):
        try:
            with open(eval_report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for "Issues found:" pattern in the report
            # Pattern: "**Issues found:** X" or "- **Issues found:** X"
            issues_pattern = r'[*-]\s*\*\*Issues found:\*\*\s*(\d+)'
            matches = re.findall(issues_pattern, content)
            
            eval_issues = 0
            for match in matches:
                try:
                    eval_issues += int(match)
                except ValueError:
                    pass
            

            if '❌ Issues Found' in content or '### ❌ Issues Found' in content:
                issue_markers = content.count('❌')
                if issue_markers > 0:
                    eval_issues = max(eval_issues, issue_markers)
            
            issue_keywords = [
                'RECOMMENDATION',
                'Please ensure',
                'Please fix',
                'needs to be fixed',
                'should be corrected'
            ]
            has_recommendations = any(keyword in content for keyword in issue_keywords)
            
            if eval_issues > 0 or has_recommendations:
                has_issues = True
                total_issues = max(total_issues, eval_issues if eval_issues > 0 else 1)
        except Exception as e:
            print(f"  Warning: Could not parse evaluation report: {e}")


    for report_path in (linter_report_path, code_quality_report_path):
        if os.path.exists(report_path):
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    content = f.read()
  
                if 'FAIL' in content or '❌' in content:
                    has_issues = True

                    marker_count = content.count('❌')
                    if marker_count <= 0:
                        marker_count = 1
                    total_issues = max(total_issues, marker_count)
            except Exception as e:
                print(f"  Warning: Could not parse report {report_path}: {e}")


    if os.path.exists(game_file_path):
        try:
            with open(game_file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
            if first_line.startswith('{"game_name"') or first_line.startswith("{'game_name'"):
                has_issues = True
                total_issues = max(total_issues, 1)
        except Exception as e:
            print(f"  Warning: Could not inspect {game_file_path} for JSON metadata: {e}")

    # 4) If we have no signals at all (no reports, no game file),
    #    assume issues exist so that the loop can trigger evaluation.
    if not os.path.exists(eval_report_path) and \
       not os.path.exists(linter_report_path) and \
       not os.path.exists(code_quality_report_path) and \
       not os.path.exists(game_file_path):
        return True, 999

    return has_issues, total_issues

def _run_with_feedback_loop(crew_instance, inputs: dict, max_attempts: int = 3):
    """
    Run the crew with a feedback loop:
    1. Design → Develop → Evaluate
    2. If issues found: Fix → Evaluate (loop)
    3. Once passed: Publish
    
    Args:
        crew_instance: AgentforceInteractive instance
        inputs: Crew inputs dict
        max_attempts: Maximum number of fix attempts
    
    Returns:
        Final crew result
    """
    game_name = inputs.get('game_name', '')

    def _sanitize_game_file_metadata() -> None:
        """Remove known bad metadata patterns (like leading JSON) from game.py proactively."""
        if not game_name:
            return
        game_file = os.path.join('games', game_name, 'game.py')
        if not os.path.exists(game_file):
            return
        try:
            with open(game_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if not lines:
                return
            first_line = lines[0].strip()
            # If the first line is a standalone JSON object containing game_name,
            # strip it out so the file starts with real Python code.
            if first_line.startswith('{') and first_line.endswith('}') and 'game_name' in first_line:
                # If removing this line would leave the file empty, do not modify it here.
                # In that case, let the normal fix flow handle the problem instead of
                # accidentally wiping out all game code.
                if len(lines) <= 1:
                    print(f"  Warning: Detected leading JSON metadata in {game_file} but file has no other lines; skipping automatic removal.")
                    return
                with open(game_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines[1:])
                print(f"  ✓ Removed leading JSON metadata line from {game_file}")
        except Exception as e:
            print(f"  Warning: Could not sanitize {game_file}: {e}")
    
    # Step 1: Run initial tasks (Design → Develop → Requirements → Evaluate)
    print(f"\n{'='*70}")
    print(f"  PHASE 1: Initial Development")
    print(f"{'='*70}\n")
    
    # Create a crew with initial tasks only
    from crewai import Crew, Process
    
    # Get agents
    agents = [
        crew_instance.game_designer(),
        crew_instance.game_developer(),
        crew_instance.test_engineer()
    ]
    
    # Get tasks
    design_task = crew_instance.design_game_task()
    analyze_task = crew_instance.analyze_design_task()  # Understand design first
    implement_task = crew_instance.implement_game_task()  # Build complete game
    requirements_task = crew_instance.create_requirements_task()
    

    linter_task = crew_instance.linter_code_task()
    code_quality_task = crew_instance.evaluate_code_quality_task()
    design_quality_task = crew_instance.evaluate_design_quality_task()
    compliance_task = crew_instance.evaluate_design_compliance_task()
    compile_report_task = crew_instance.compile_evaluation_report_task()
    
    # Run initial development phase
    initial_crew = Crew(
        agents=agents,
        tasks=[
            design_task,
            analyze_task,  # Understand design
            implement_task,  # Build complete game
            requirements_task,
            linter_task,
            code_quality_task,
            design_quality_task,
            compliance_task,
            compile_report_task
        ],
        process=Process.sequential,
        verbose=True
    )
    
    try:
        result = initial_crew.kickoff(inputs=inputs)
    except Exception as e:
        print(f"\n  Warning: Initial crew execution had errors: {str(e)}")
        print(f"  Continuing to check for issues and attempt fixes...\n")

    _sanitize_game_file_metadata()
    
    fix_attempts = 0
    
    while fix_attempts < max_attempts:
        has_issues, issue_count = _check_evaluation_for_issues(game_name)
        
        if not has_issues:
            import sys
            sys.stdout.write(f"\n{'='*70}\n")
            sys.stdout.write(f"  ✓ Evaluation PASSED - No issues found!\n")
            sys.stdout.write(f"{'='*70}\n\n")
            break
        
        import sys
        sys.stdout.write(f"\n{'='*70}\n")
        sys.stdout.write(f"  ⚠️  Evaluation found {issue_count} issue(s)\n")
        sys.stdout.write(f"  Attempting to fix (Attempt {fix_attempts + 1}/{max_attempts})...\n")
        sys.stdout.write(f"{'='*70}\n\n")
        
        fix_task = crew_instance.fix_game_issues_task()
        fix_crew = Crew(
            agents=[crew_instance.game_developer()],
            tasks=[fix_task],
            process=Process.sequential,
            verbose=True
        )
        
        fix_result = fix_crew.kickoff(inputs=inputs)
        
        re_eval_crew = Crew(
            agents=[crew_instance.test_engineer()],
            tasks=[
                linter_task,
                code_quality_task,
                design_quality_task,
                compliance_task,
                compile_report_task
            ],
            process=Process.sequential,
            verbose=True
        )
        
        eval_result = re_eval_crew.kickoff(inputs=inputs)
        fix_attempts += 1
    

    has_issues, issue_count = _check_evaluation_for_issues(game_name)
    if has_issues:
        print(f"\n{'='*70}")
        print(f"  ⚠️  WARNING: Still {issue_count} issue(s) after {max_attempts} fix attempts")
        print(f"  Proceeding to publication anyway...")
        print(f"{'='*70}\n")
    
    print(f"\n{'='*70}")
    print(f"  PHASE 2: Publication")
    print(f"{'='*70}\n")
    
    publish_task = crew_instance.publish_game_task()
    publish_crew = Crew(
        agents=[crew_instance.game_publisher()],
        tasks=[publish_task],
        process=Process.sequential,
        verbose=True
    )
    
    publish_result = publish_crew.kickoff(inputs=inputs)
    
    return publish_result

def run():
    """
    Run the crew to create a game.
    
    Usage:
        # Using crewai run (with environment variables):
        GAME_CONCEPT="A Pong game" GAME_NAME="pong" crewai run
        
        # Using crewai run (interactive):
        crewai run
        
        # Direct Python execution:
        python -m agentforce_interactive.main "A Pong game"
        python -m agentforce_interactive.main "A Pong game" "pong_game"
    """
    # Priority 1: Check environment variables (works with crewai run)
    game_concept = os.getenv('GAME_CONCEPT', '')
    game_name = os.getenv('GAME_NAME', '')
    
    # Priority 2: Check command line arguments (for direct Python execution)
    if not game_concept and len(sys.argv) > 1:
        game_concept = sys.argv[1]
    
    if not game_name and len(sys.argv) > 2:
        game_name = _sanitize_game_name(sys.argv[2])
    
    # Priority 3: Prompt for input if not provided
    if not game_concept:
        game_concept = input("Enter your game concept (e.g., 'A simple Pong game with two paddles'): ").strip()
        if not game_concept:
            game_concept = 'A simple Snake game where the player controls a snake to eat food and grow longer'
            print(f"Using default game concept: {game_concept}")
    
    # Prompt for game name if not provided (always ask when running interactively)
    if not game_name:
        suggested_name = _sanitize_game_name(game_concept)
        game_name_input = input(f"Enter a name for your game (suggested: '{suggested_name}', or press Enter to use it): ").strip()
        if game_name_input:
            game_name = _sanitize_game_name(game_name_input)
        else:
            game_name = suggested_name
            print(f"Using suggested game name: {game_name}")
    else:
        game_name = _sanitize_game_name(game_name)
    
    # Create game folder
    _ensure_game_folder(game_name)
    
    inputs = {
        'game_concept': game_concept,
        'game_name': game_name
    }

    print(f"\nStarting game creation...")
    print(f"Game Concept: {game_concept}")
    print(f"Game Name: {game_name}\n")

    # Check if game already exists (for reference)
    game_dir = os.path.join('games', game_name)
    game_file = os.path.join(game_dir, 'game.py')
    
    result = None
    error_occurred = False
    error_message = None
    
    try:
        crew_instance = AgentforceInteractive()
        
        # Execute the crew with feedback loop
        # This will: Design → Develop → Evaluate → [Fix → Evaluate]* → Publish
        result = _run_with_feedback_loop(crew_instance, inputs, max_attempts=3)
        
    except AttributeError as e:
        # Catch Rich FileProxy errors that may occur with output_file handling
        if "'cell' object has no attribute '_FileProxy__buffer'" in str(e) or "FileProxy__buffer" in str(e):
            error_occurred = True
            error_message = (
                f"Rich FileProxy error during file output (this may be a CrewAI bug): {str(e)}\n"
                f"This error can sometimes occur with output_file handling. "
                f"Check if files were created despite the error."
            )
            print(f"\n  WARNING: {error_message}")
        else:
            # Re-raise other AttributeErrors
            raise
    except Exception as e:
        error_occurred = True
        error_message = str(e)
        # Don't raise yet - check if game was created first
    
    # Always check if game was successfully created
    if os.path.exists(game_file):
        if error_occurred:
            # Use sys.stdout.write to avoid Rich FileProxy recursion issues
            import sys
            sys.stdout.write(f"\n  Warning: An error occurred during crew execution, but game was successfully created.\n")
            sys.stdout.write(f" Game file exists at: {game_file}\n")
            sys.stdout.write(f" Game directory: {game_dir}\n")
            sys.stdout.write(f" Error details: {error_message}\n")
            sys.stdout.write(f" The game should be playable despite this warning.\n\n")
        else:
            print(f"\nGame successfully created at: {game_file}")
            print(f"Game directory: {game_dir}\n")
        
        # Always return 0 (success) if game file exists
        return 0
    else:
        # Game wasn't created - this is a real failure
        if error_occurred:
            print(f"\n  Error: Game was not created. Details: {error_message}")
            raise Exception(f"An error occurred while running the crew: {error_message}")
        else:
            # No error but game doesn't exist - this shouldn't happen but handle it
            print(f"\n  Warning: Crew execution completed but game.py was not found.")
            print(f" Expected location: {game_file}")
            return 1


def train():
    """
    Train the crew for a given number of iterations.
    """
    game_concept = "A simple Snake game where the player controls a snake to eat food and grow longer"
    game_name = _sanitize_game_name('snake_game')
    _ensure_game_folder(game_name)
    
    inputs = {
        "game_concept": game_concept,
        "game_name": game_name
    }
    try:
        AgentforceInteractive().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        AgentforceInteractive().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    game_concept = "A simple Snake game where the player controls a snake to eat food and grow longer"
    game_name = _sanitize_game_name('snake_game')
    _ensure_game_folder(game_name)
    
    inputs = {
        "game_concept": game_concept,
        "game_name": game_name
    }

    try:
        AgentforceInteractive().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "game_concept": "",
        "game_name": "untitled_game"
    }

    try:
        result = AgentforceInteractive().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
