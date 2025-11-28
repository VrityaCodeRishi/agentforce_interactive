"""Tool to evaluate code quality of game.py files."""

import os
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class CodeQualityEvaluatorInput(BaseModel):
    """Input schema for code quality evaluation."""

    game_name: str = Field(..., description="Name of the game to evaluate")


class CodeQualityEvaluatorTool(BaseTool):
    name: str = "code_quality_evaluator"
    description: str = (
        "Evaluates the code quality of game.py file to ensure it contains only Python code. "
        "Checks for markdown code blocks, JSON metadata, explanatory text, LLM reasoning comments, "
        "and ensures the file has valid Python syntax. Returns a detailed evaluation report."
    )
    args_schema: Type[BaseModel] = CodeQualityEvaluatorInput

    def _run(self, game_name: str) -> str:
        """
        Evaluates the code quality of game.py file to ensure it contains only Python code.
        
        Checks for:
        - No markdown code blocks (```python, ```)
        - No JSON metadata at start/end of file
        - No explanatory text or instructions
        - No LLM reasoning or templating comments
        - File starts with valid Python code (import statement)
        - File ends with valid Python code
        
        Args:
            game_name: Name of the game to evaluate
            
        Returns:
            A detailed evaluation report with findings
        """
        game_dir = os.path.join("games", game_name)
        game_file = os.path.join(game_dir, "game.py")
        
        if not os.path.exists(game_file):
            return f"ERROR: game.py not found at {game_file}"
        
        with open(game_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        issues = []
        warnings = []
        checks_passed = []
        
        # Check 1: File should start with Python code (import statement)
        first_line = lines[0].strip() if lines else ""
        if first_line.startswith("```python") or first_line.startswith("```"):
            issues.append("❌ Line 1 contains markdown code block marker (```python or ```)")
        elif first_line.startswith("import") or first_line.startswith("from"):
            checks_passed.append("✓ Line 1 starts with valid Python import statement")
        elif first_line.startswith("#"):
            warnings.append("⚠️  Line 1 is a comment - should start with import statement")
        elif first_line.startswith('{"') or first_line.startswith("{'") or first_line.strip().startswith("{"):
            issues.append("🚨🚨🚨 CRITICAL: Line 1 contains JSON metadata (e.g., {\"game_name\":\"...\"}) - MUST be removed immediately. File must start with 'import pygame'")
        elif not first_line:
            issues.append("❌ File is empty or starts with blank line")
        else:
            warnings.append(f"⚠️  Line 1 doesn't start with import: '{first_line[:50]}'")
        
        # Check 2: File should end with Python code (not markdown closing)
        last_line = lines[-1].strip() if lines else ""
        if last_line == "```":
            issues.append("❌ Last line contains markdown code block closing (```)")
        elif last_line.startswith('{"') or last_line.startswith("{'") or (last_line.strip().startswith("{") and last_line.strip().endswith("}")):
            issues.append("❌ Last line contains JSON metadata (should not be present)")
        elif last_line:
            checks_passed.append("✓ Last line contains code (no markdown closing marker)")
        else:
            warnings.append("⚠️  File ends with blank line")
        
        # Check 3: No markdown code blocks anywhere
        if "```python" in content or "```" in content:
            issues.append("❌ File contains markdown code block markers (```python or ```)")
        else:
            checks_passed.append("✓ No markdown code block markers found")
        
        # Check 4: No JSON metadata at start
        first_50_chars = content[:50].strip()
        if (first_50_chars.startswith("{") and "game_name" in first_50_chars) or \
           (first_50_chars.startswith("{") and '"game_name"' in first_50_chars):
            issues.append("🚨🚨🚨 CRITICAL: File starts with JSON metadata containing 'game_name' (e.g., {\"game_name\":\"ping_pong\"}) - MUST be removed. File must start with 'import pygame'")
        else:
            checks_passed.append("✓ No JSON metadata at start of file")
        
        # Check 5: No explanatory text patterns (common LLM output patterns)
        explanatory_patterns = [
            "Here's the code:",
            "Here is the code:",
            "Save this as",
            "Create a file",
            "The code is as follows:",
            "Below is the code:",
            "I'll create",
            "Let me create",
        ]
        found_patterns = []
        for pattern in explanatory_patterns:
            if pattern.lower() in content.lower():
                found_patterns.append(pattern)
        
        if found_patterns:
            issues.append(f"❌ File contains explanatory text: {', '.join(found_patterns)}")
        else:
            checks_passed.append("✓ No explanatory text found")
        
        # Check 6: Verify it's valid Python (basic syntax check)
        try:
            compile(content, game_file, 'exec')
            checks_passed.append("✓ File contains valid Python syntax")
        except SyntaxError as e:
            issues.append(f"❌ Python syntax error: {str(e)}")
        
        # Check 7: No instructional comments (like "1. Create...", "2. Import...")
        instructional_patterns = [
            "1. Create",
            "2. Create",
            "Step 1:",
            "Step 2:",
            "First, ",
            "Then, ",
            "Next, ",
        ]
        found_instructions = []
        for pattern in instructional_patterns:
            if pattern.lower() in content.lower():
                # Check if it's in a comment or string (more lenient)
                found_instructions.append(pattern)
        
        if found_instructions:
            warnings.append(f"⚠️  File may contain instructional text: {', '.join(found_instructions[:3])}")
        
        # Generate report
        report_lines = [
            f"# Code Quality Evaluation Report for {game_name}/game.py",
            "",
            f"File: {game_file}",
            f"Total lines: {len(lines)}",
            "",
            "## Summary",
            f"- Issues found: {len(issues)}",
            f"- Warnings: {len(warnings)}",
            f"- Checks passed: {len(checks_passed)}",
            "",
        ]
        
        if checks_passed:
            report_lines.append("## ✅ Checks Passed")
            report_lines.extend(checks_passed)
            report_lines.append("")
        
        if warnings:
            report_lines.append("## ⚠️  Warnings")
            report_lines.extend(warnings)
            report_lines.append("")
        
        if issues:
            report_lines.append("## ❌ Issues Found")
            report_lines.extend(issues)
            report_lines.append("")
            report_lines.append("**RECOMMENDATION**: File contains non-code content. Please ensure:")
            report_lines.append("🚨🚨🚨 CRITICAL: File starts with Python import statement (NO JSON like {\"game_name\":\"...\"}, NO markdown, NO metadata)")
            report_lines.append("- File ends with Python code (no markdown closing ```)")
            report_lines.append("- No explanatory text or instructions")
            report_lines.append("🚨🚨🚨 CRITICAL: NO JSON metadata - if you see {\"game_name\":\"...\"} at the start, DELETE that line immediately")
        else:
            report_lines.append("## ✅ Overall Status")
            report_lines.append("**PASS**: File contains only Python code. No issues detected.")
        
        return "\n".join(report_lines)

