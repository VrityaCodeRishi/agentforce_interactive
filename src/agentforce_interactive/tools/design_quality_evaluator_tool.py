"""Tool to evaluate design document quality of game_design.md files."""

import os
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class DesignQualityEvaluatorInput(BaseModel):
    """Input schema for design document quality evaluation."""

    game_name: str = Field(..., description="Name of the game to evaluate")


class DesignQualityEvaluatorTool(BaseTool):
    name: str = "design_quality_evaluator"
    description: str = (
        "Evaluates the quality of game_design.md to ensure it contains only markdown content. "
        "Checks for JSON metadata, templating variables, LLM reasoning patterns, and ensures "
        "proper markdown structure. Returns a detailed evaluation report."
    )
    args_schema: Type[BaseModel] = DesignQualityEvaluatorInput

    def _run(self, game_name: str) -> str:
        """
        Evaluates the quality of game_design.md to ensure it contains only markdown content.
        
        Checks for:
        - No Python code blocks (unless they're examples)
        - No JSON metadata or templating
        - No LLM reasoning or explanatory text outside markdown
        - Proper markdown structure
        - No templating variables or placeholders
        
        Args:
            game_name: Name of the game to evaluate
            
        Returns:
            A detailed evaluation report with findings
        """
        game_dir = os.path.join("games", game_name)
        design_file = os.path.join(game_dir, "game_design.md")
        
        if not os.path.exists(design_file):
            return f"ERROR: game_design.md not found at {design_file}"
        
        with open(design_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        issues = []
        warnings = []
        checks_passed = []
        
        # Check 1: Should start with markdown (heading, text, etc.)
        first_line = lines[0].strip() if lines else ""
        if first_line.startswith("```python") or first_line.startswith("```markdown"):
            issues.append("❌ File starts with code block marker (```python or ```markdown) - should start with markdown heading directly")
        elif first_line.startswith("```"):
            issues.append("❌ File starts with code block marker (```) - should start with markdown heading directly, not wrapped in code block")
        elif first_line.startswith("#"):
            checks_passed.append("✓ File starts with markdown heading")
        elif first_line.startswith('{"') or first_line.startswith("{'") or (first_line.strip().startswith("{") and "game_name" in first_line):
            issues.append("❌ File starts with JSON metadata (should not be present)")
        elif not first_line:
            issues.append("❌ File is empty or starts with blank line")
        else:
            checks_passed.append("✓ File starts with content")
        
        # Check 2: No JSON metadata at start or end
        first_100_chars = content[:100].strip()
        last_100_chars = content[-100:].strip()
        
        if (first_100_chars.startswith("{") and "game_name" in first_100_chars) or \
           ('{"game_name"' in first_100_chars or "'game_name'" in first_100_chars):
            issues.append("❌ File contains JSON metadata at the beginning")
        else:
            checks_passed.append("✓ No JSON metadata at start of file")
        
        if (last_100_chars.strip().startswith("{") and "game_name" in last_100_chars) or \
           ('{"game_name"' in last_100_chars or "'game_name'" in last_100_chars):
            issues.append("❌ File contains JSON metadata at the end")
        else:
            checks_passed.append("✓ No JSON metadata at end of file")
        
        # Check 3: No templating variables
        templating_patterns = [
            "{{game_name}}",
            "{game_name}",
            "${game_name}",
            "<game_name>",
            "%game_name%",
            "{{ ",
            "{% ",
        ]
        found_templates = []
        for pattern in templating_patterns:
            if pattern in content:
                found_templates.append(pattern)
        
        if found_templates:
            issues.append(f"❌ File contains templating variables: {', '.join(found_templates)}")
        else:
            checks_passed.append("✓ No templating variables found")
        
        # Check 4: No LLM reasoning patterns (outside of natural design discussion)
        reasoning_patterns = [
            "I think",
            "I believe",
            "In my opinion",
            "Let me explain",
            "To summarize",
            "Let me create",
            "I'll design",
            "Here's my reasoning",
        ]
        found_reasoning = []
        # Only flag if it appears in non-natural contexts (like at the start)
        first_500_chars = content[:500].lower()
        for pattern in reasoning_patterns:
            if pattern.lower() in first_500_chars:
                found_reasoning.append(pattern)
        
        if found_reasoning:
            warnings.append(f"⚠️  File may contain LLM reasoning phrases at start: {', '.join(found_reasoning[:2])}")
        else:
            checks_passed.append("✓ No obvious LLM reasoning patterns detected")
        
        # Check 5: Should have proper markdown structure
        has_heading = any(line.strip().startswith("#") for line in lines[:10])
        if has_heading:
            checks_passed.append("✓ File contains markdown headings")
        else:
            warnings.append("⚠️  File may not have proper markdown structure (no headings in first 10 lines)")
        
        # Check 6: No executable Python code outside code blocks (unless it's a small example)
        # This is tricky - we allow code examples in markdown, but not full scripts
        # Check for patterns like "import pygame" outside code blocks
        in_code_block = False
        code_block_content = []
        lines_with_imports_outside_blocks = []
        
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("```"):
                if in_code_block:
                    in_code_block = False
                    code_block_content = []
                else:
                    in_code_block = True
            elif in_code_block:
                code_block_content.append(line)
            else:
                # Check for import statements outside code blocks (likely issue)
                if line.strip().startswith("import ") or line.strip().startswith("from "):
                    # Allow if it's in a list or explanation
                    if not any(line.strip().startswith(marker) for marker in ["-", "*", "1.", "2.", "#"]):
                        lines_with_imports_outside_blocks.append(i)
        
        if lines_with_imports_outside_blocks:
            warnings.append(f"⚠️  Import statements found outside code blocks on lines: {', '.join(map(str, lines_with_imports_outside_blocks[:5]))}")
        else:
            checks_passed.append("✓ No Python code outside of markdown code blocks")
        
        # Check 7: File should NOT end with code block closing marker
        last_line = lines[-1].strip() if lines else ""
        if last_line == "```" or last_line.startswith("```"):
            issues.append("❌ File ends with code block closing marker (```) - file should end with markdown content, not wrapped in code block")
        else:
            checks_passed.append("✓ File ends with markdown content (no code block closing marker)")
        
        # Check 8: No explanatory text that sounds like LLM output instructions
        explanatory_patterns = [
            "Here's the design:",
            "Here is the design:",
            "Save this as",
            "Create a file",
            "The design is as follows:",
            "Below is the design:",
            "I'll create the design",
        ]
        found_patterns = []
        for pattern in explanatory_patterns:
            if pattern.lower() in content.lower():
                found_patterns.append(pattern)
        
        if found_patterns:
            issues.append(f"❌ File contains explanatory text patterns: {', '.join(found_patterns)}")
        else:
            checks_passed.append("✓ No explanatory text patterns found")
        
        # Generate report
        report_lines = [
            f"# Design Document Quality Evaluation Report for {game_name}/game_design.md",
            "",
            f"File: {design_file}",
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
            report_lines.append("**RECOMMENDATION**: File contains non-markdown content. Please ensure:")
            report_lines.append("- File starts directly with markdown heading (# Title), NOT wrapped in ```markdown code block")
            report_lines.append("- File ends with markdown content, NOT with ``` closing marker")
            report_lines.append("- File is pure markdown (headings, lists, text, code examples in blocks)")
            report_lines.append("- No JSON metadata")
            report_lines.append("- No templating variables")
            report_lines.append("- No LLM reasoning or explanatory text outside of design content")
        else:
            report_lines.append("## ✅ Overall Status")
            report_lines.append("**PASS**: File contains only markdown content. No issues detected.")
        
        return "\n".join(report_lines)
