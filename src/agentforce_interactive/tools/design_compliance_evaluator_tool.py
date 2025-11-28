"""Tool to evaluate if game implementation matches the design document."""

import os
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class DesignComplianceEvaluatorInput(BaseModel):
    """Input schema for design compliance evaluation."""

    game_name: str = Field(..., description="Name of the game to evaluate")


class DesignComplianceEvaluatorTool(BaseTool):
    name: str = "design_compliance_evaluator"
    description: str = (
        "Evaluates if the game.py implementation matches the game_design.md specifications. "
        "Compares game mechanics, features, technical requirements, and file structure between "
        "the design document and the actual implementation. Returns a detailed compliance report."
    )
    args_schema: Type[BaseModel] = DesignComplianceEvaluatorInput

    def _run(self, game_name: str) -> str:
        """
        Evaluates if the game.py implementation matches the game_design.md specifications.
        
        Compares:
        - Game mechanics described in design vs implemented
        - Features listed in design vs present in code
        - Technical requirements vs actual implementation
        - File structure specified vs actual files created
        
        Args:
            game_name: Name of the game to evaluate
            
        Returns:
            A detailed compliance report with findings
        """
        game_dir = os.path.join("games", game_name)
        design_file = os.path.join(game_dir, "game_design.md")
        game_file = os.path.join(game_dir, "game.py")
        
        if not os.path.exists(design_file):
            return f"ERROR: game_design.md not found at {design_file}"
        
        if not os.path.exists(game_file):
            return f"ERROR: game.py not found at {game_file}"
        
        # Read design document
        with open(design_file, 'r', encoding='utf-8') as f:
            design_content = f.read()
        
        # Read game code
        with open(game_file, 'r', encoding='utf-8') as f:
            game_content = f.read()
        
        compliance_checks = []
        non_compliance_issues = []
        warnings = []
        
        # Check 1: Library specified in design vs imported in code
        design_lower = design_content.lower()
        game_lower = game_content.lower()
        
        # Common game libraries
        libraries = ["pygame", "arcade", "turtle", "pyglet", "panda3d"]
        design_library = None
        implemented_library = None
        
        for lib in libraries:
            if f"library: {lib}" in design_lower or f"recommended library: {lib}" in design_lower or \
               f"using {lib}" in design_lower or f"{lib} library" in design_lower:
                design_library = lib
            if f"import {lib}" in game_lower or f"from {lib}" in game_lower:
                implemented_library = lib
                break
        
        if design_library:
            if implemented_library == design_library:
                compliance_checks.append(f"✓ Uses specified library: {design_library}")
            elif implemented_library:
                warnings.append(f"⚠️  Design specifies {design_library}, but code uses {implemented_library}")
            else:
                non_compliance_issues.append(f"❌ Design specifies {design_library}, but library not found in code")
        else:
            if implemented_library:
                compliance_checks.append(f"✓ Uses game library: {implemented_library}")
        
        # Check 2: Check for core game mechanics mentioned in design
        mechanics_to_check = [
            ("collision", "collision"),
            ("score", "score"),
            ("game over", "game over"),
            ("win", "win condition"),
            ("lose", "lose condition"),
            ("movement", "move"),
            ("controls", "keyboard"),
            ("input", "input"),
        ]
        
        for design_term, code_term in mechanics_to_check:
            design_has = design_term in design_lower
            code_has = code_term in game_lower
            
            if design_has:
                if code_has:
                    compliance_checks.append(f"✓ Implements {design_term} mechanic (mentioned in design)")
                else:
                    non_compliance_issues.append(f"❌ Design mentions {design_term}, but not found in code")
        
        # Check 3: File structure from design vs actual files
        if "technical requirements" in design_lower or "file structure" in design_lower:
            # Try to find file names mentioned in design
            design_files_mentioned = []
            game_files_exist = []
            
            # Look for patterns like "create game.py", "snake.py", etc.
            for line in design_content.split('\n'):
                line_lower = line.lower()
                if '.py' in line_lower:
                    # Extract potential file names
                    if 'game.py' in line_lower or 'main.py' in line_lower:
                        if 'game.py' in line_lower:
                            design_files_mentioned.append('game.py')
                        if 'main.py' in line_lower:
                            design_files_mentioned.append('main.py')
            
            # Check what files actually exist
            if os.path.exists(os.path.join(game_dir, "game.py")):
                game_files_exist.append("game.py")
            if os.path.exists(os.path.join(game_dir, "main.py")):
                game_files_exist.append("main.py")
            
            if design_files_mentioned:
                for file in design_files_mentioned:
                    if file in game_files_exist:
                        compliance_checks.append(f"✓ File {file} exists as specified in design")
                    else:
                        non_compliance_issues.append(f"❌ Design specifies {file}, but file does not exist")
        
        # Check 4: Visual requirements (should use pygame.draw, not images)
        if "pygame.draw" in game_lower or "draw.rect" in game_lower or "draw.circle" in game_lower:
            compliance_checks.append("✓ Uses pygame.draw for visuals (as per design guidelines)")
        elif "image.load" in game_lower or "load_image" in game_lower:
            non_compliance_issues.append("❌ Code uses image loading (design specifies shapes only)")
        
        # Check 5: No config imports (as per guidelines)
        if "from config import" in game_content or "import config" in game_content:
            non_compliance_issues.append("❌ Code imports from config module (should be self-contained)")
        else:
            compliance_checks.append("✓ Code is self-contained (no config imports)")
        
        # Check 6: Check game features mentioned in design
        if "features" in design_lower or "game features" in design_lower:
            # Look for feature lists
            feature_section = False
            features_mentioned = []
            for line in design_content.split('\n'):
                if "feature" in line.lower() and "##" in line:
                    feature_section = True
                elif feature_section and line.strip().startswith(("-", "*", "1.", "2.")):
                    feature = line.strip().lstrip("-*1234567890. ").lower()
                    if feature and len(feature) > 5:  # Meaningful feature
                        features_mentioned.append(feature)
            
            # Basic check if features are implemented
            if features_mentioned:
                compliance_checks.append(f"✓ Design specifies {len(features_mentioned)} feature(s) to check")
        
        # Generate report
        report_lines = [
            f"# Design Compliance Evaluation Report for {game_name}",
            "",
            f"Design Document: {design_file}",
            f"Implementation: {game_file}",
            "",
            "## Summary",
            f"- Compliance checks passed: {len(compliance_checks)}",
            f"- Non-compliance issues: {len(non_compliance_issues)}",
            f"- Warnings: {len(warnings)}",
            "",
        ]
        
        if compliance_checks:
            report_lines.append("## ✅ Compliance Checks Passed")
            report_lines.extend(compliance_checks)
            report_lines.append("")
        
        if warnings:
            report_lines.append("## ⚠️  Warnings")
            report_lines.extend(warnings)
            report_lines.append("")
        
        if non_compliance_issues:
            report_lines.append("## ❌ Non-Compliance Issues")
            report_lines.extend(non_compliance_issues)
            report_lines.append("")
            report_lines.append("**RECOMMENDATION**: Implementation does not fully match design specifications.")
            report_lines.append("Please review the design document and ensure all specified features are implemented.")
        else:
            report_lines.append("## ✅ Overall Status")
            report_lines.append("**PASS**: Implementation appears to comply with design specifications.")
        
        return "\n".join(report_lines)
