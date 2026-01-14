"""
Utilities for analyzing existing codebase structure and generating test files.
"""
import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import importlib.util


class CodebaseAnalyzer:
    """Analyzes existing codebase to understand structure and generate appropriate tests."""
    
    def __init__(self, base_path: str = "."):
        """
        Initialize codebase analyzer.
        
        Args:
            base_path: Base directory to analyze
        """
        self.base_path = Path(base_path).resolve()
        self.ignore_patterns = [
            '__pycache__', '.git', '.venv', 'venv', 'node_modules',
            '.pytest_cache', '.coverage', '*.pyc', '*.pyo', '*.egg-info',
            'generated_project', 'metrics.db', '.env'
        ]
    
    def should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return True
        return False
    
    def find_code_files(self, extensions: List[str] = None) -> List[Path]:
        """
        Find all code files in the codebase.
        
        Args:
            extensions: List of file extensions to include (e.g., ['.py', '.js'])
        
        Returns:
            List of file paths
        """
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs']
        
        code_files = []
        
        # Check if base_path exists
        if not self.base_path.exists():
            return code_files
        
        try:
            for root, dirs, files in os.walk(self.base_path):
                # Filter out ignored directories
                dirs[:] = [d for d in dirs if not self.should_ignore(Path(root) / d)]
                
                for file in files:
                    file_path = Path(root) / file
                    if self.should_ignore(file_path):
                        continue
                    
                    if any(file.endswith(ext) for ext in extensions):
                        code_files.append(file_path)
        except Exception as e:
            # If walking fails, return empty list
            print(f"Warning: Error walking directory {self.base_path}: {e}")
            return code_files
        
        return code_files
    
    def analyze_python_file(self, file_path: Path) -> Dict:
        """
        Analyze a Python file to extract functions, classes, and structure.
        
        Args:
            file_path: Path to Python file
        
        Returns:
            Dictionary with analysis results
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            functions = []
            classes = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Extract decorator names (compatible with Python < 3.9)
                    decorators = []
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            decorators.append(decorator.id)
                        elif hasattr(ast, 'unparse'):
                            decorators.append(ast.unparse(decorator))
                        else:
                            decorators.append(ast.dump(decorator))
                    
                    functions.append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'decorators': decorators
                    })
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append({
                                'name': item.name,
                                'line': item.lineno,
                                'args': [arg.arg for arg in item.args.args]
                            })
                    # Extract base class names (compatible with Python < 3.9)
                    bases = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            bases.append(base.id)
                        elif hasattr(ast, 'unparse'):
                            bases.append(ast.unparse(base))
                        else:
                            bases.append(ast.dump(base))
                    
                    classes.append({
                        'name': node.name,
                        'line': node.lineno,
                        'methods': methods,
                        'bases': bases
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.extend([alias.name for alias in node.names])
                    else:
                        imports.append(node.module or '')
            
            return {
                'file_path': str(file_path.relative_to(self.base_path)),
                'functions': functions,
                'classes': classes,
                'imports': imports,
                'line_count': len(content.split('\n')),
                'has_tests': self._check_existing_tests(file_path)
            }
        except SyntaxError:
            # If file has syntax errors, do basic analysis
            return {
                'file_path': str(file_path.relative_to(self.base_path)),
                'functions': [],
                'classes': [],
                'imports': [],
                'line_count': 0,
                'has_tests': False,
                'error': 'Syntax error in file'
            }
        except Exception as e:
            return {
                'file_path': str(file_path.relative_to(self.base_path)),
                'error': str(e)
            }
    
    def _check_existing_tests(self, file_path: Path) -> bool:
        """Check if test files already exist for this file."""
        # Look for test files in common locations
        test_patterns = [
            f"test_{file_path.stem}.py",
            f"{file_path.stem}_test.py",
            f"tests/test_{file_path.stem}.py",
            f"tests/{file_path.stem}_test.py"
        ]
        
        for pattern in test_patterns:
            test_path = file_path.parent / pattern
            if test_path.exists():
                return True
            
            # Check in tests/ directory
            tests_dir = file_path.parent / 'tests'
            if tests_dir.exists():
                test_path = tests_dir / pattern.split('/')[-1]
                if test_path.exists():
                    return True
        
        return False
    
    def analyze_codebase(self) -> Dict:
        """
        Analyze the entire codebase.
        
        Returns:
            Dictionary with codebase structure and analysis
        """
        code_files = self.find_code_files()
        
        analysis = {
            'base_path': str(self.base_path),
            'total_files': len(code_files),
            'files': [],
            'structure': {},
            'test_coverage': {
                'files_with_tests': 0,
                'files_without_tests': 0
            }
        }
        
        # Group files by directory
        structure = {}
        for file_path in code_files:
            rel_path = file_path.relative_to(self.base_path)
            dir_path = str(rel_path.parent)
            
            if dir_path not in structure:
                structure[dir_path] = []
            structure[dir_path].append(str(rel_path))
        
        analysis['structure'] = structure
        
        # Analyze Python files in detail
        python_files = [f for f in code_files if f.suffix == '.py']
        for file_path in python_files:
            file_analysis = self.analyze_python_file(file_path)
            analysis['files'].append(file_analysis)
            
            if file_analysis.get('has_tests'):
                analysis['test_coverage']['files_with_tests'] += 1
            else:
                analysis['test_coverage']['files_without_tests'] += 1
        
        return analysis
    
    def generate_test_structure_summary(self, analysis: Dict) -> str:
        """
        Generate a human-readable summary of what tests need to be created.
        
        Args:
            analysis: Codebase analysis result
        
        Returns:
            Summary string
        """
        summary_lines = [
            f"Codebase Analysis Summary:",
            f"Total files: {analysis['total_files']}",
            f"Files with tests: {analysis['test_coverage']['files_with_tests']}",
            f"Files without tests: {analysis['test_coverage']['files_without_tests']}",
            "",
            "Files needing tests:"
        ]
        
        for file_info in analysis['files']:
            if not file_info.get('has_tests') and not file_info.get('error'):
                rel_path = file_info['file_path']
                func_count = len(file_info.get('functions', []))
                class_count = len(file_info.get('classes', []))
                
                summary_lines.append(f"  - {rel_path}")
                summary_lines.append(f"    Functions: {func_count}, Classes: {class_count}")
                
                if file_info.get('functions'):
                    summary_lines.append(f"    Functions to test: {', '.join([f['name'] for f in file_info['functions']])}")
                if file_info.get('classes'):
                    summary_lines.append(f"    Classes to test: {', '.join([c['name'] for c in file_info['classes']])}")
                summary_lines.append("")
        
        return "\n".join(summary_lines)
    
    def analyze_existing_test_patterns(self) -> str:
        """
        Analyze existing test files to extract patterns and conventions.
        
        Returns:
            String describing test patterns found in existing tests
        """
        test_files = []
        tests_dir = self.base_path / 'tests'
        
        if tests_dir.exists():
            for test_file in tests_dir.glob('test_*.py'):
                if not self.should_ignore(test_file):
                    test_files.append(test_file)
        
        if not test_files:
            return ""
        
        patterns = {
            'import_setup': False,
            'pytest_import': False,
            'test_function_pattern': False,
            'docstrings': False,
            'cleanup_patterns': False,
            'skipif_patterns': False
        }
        
        example_imports = []
        example_test = ""
        
        for test_file in test_files[:3]:  # Analyze first 3 test files
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for sys.path setup pattern
                if 'sys.path.insert' in content and 'os.path.abspath' in content:
                    patterns['import_setup'] = True
                    # Extract the import setup lines
                    lines = content.split('\n')
                    for i, line in enumerate(lines[:10]):
                        if 'sys.path.insert' in line:
                            import_setup = '\n'.join(lines[max(0, i-2):i+3])
                            if import_setup not in example_imports:
                                example_imports.append(import_setup)
                            break
                
                # Check for pytest import
                if 'import pytest' in content:
                    patterns['pytest_import'] = True
                
                # Check for test function pattern
                if 'def test_' in content:
                    patterns['test_function_pattern'] = True
                    # Extract a sample test function
                    if not example_test:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip().startswith('def test_'):
                                # Get the test function (next 10-15 lines)
                                test_func = '\n'.join(lines[i:min(i+15, len(lines))])
                                example_test = test_func
                                break
                
                # Check for docstrings
                if '"""' in content or "'''" in content:
                    patterns['docstrings'] = True
                
                # Check for cleanup patterns (try/finally)
                if 'try:' in content and 'finally:' in content:
                    patterns['cleanup_patterns'] = True
                
                # Check for skipif patterns
                if '@pytest.mark.skipif' in content:
                    patterns['skipif_patterns'] = True
                    
            except Exception:
                continue
        
        # Build pattern description
        pattern_lines = []
        if patterns['import_setup'] and example_imports:
            pattern_lines.append("**REQUIRED TEST FILE FORMAT - COPY THIS EXACT PATTERN:**")
            pattern_lines.append("")
            pattern_lines.append("Every test file MUST start with this import setup:")
            pattern_lines.append("```python")
            pattern_lines.append(example_imports[0].strip())
            pattern_lines.append("```")
            pattern_lines.append("")
        
        if patterns['pytest_import']:
            pattern_lines.append("Then import pytest and the modules being tested:")
            pattern_lines.append("```python")
            pattern_lines.append("import pytest")
            pattern_lines.append("from module_name import function_name, ClassName")
            pattern_lines.append("```")
            pattern_lines.append("")
        
        if patterns['test_function_pattern'] and example_test:
            pattern_lines.append("Test functions follow this pattern:")
            pattern_lines.append("```python")
            # Truncate example if too long
            example_lines = example_test.split('\n')[:12]
            pattern_lines.append('\n'.join(example_lines))
            if len(example_test.split('\n')) > 12:
                pattern_lines.append("    # ... more test code ...")
            pattern_lines.append("```")
            pattern_lines.append("")
        
        if patterns['docstrings']:
            pattern_lines.append("- Each test function MUST have a docstring: \"\"\"Test that...\"\"\"")
        
        if patterns['cleanup_patterns']:
            pattern_lines.append("- Tests that create resources (files, databases, etc.) MUST use try/finally for cleanup")
        
        if patterns['skipif_patterns']:
            pattern_lines.append("- For optional dependencies, use @pytest.mark.skipif to skip tests gracefully")
        
        return "\n".join(pattern_lines)
    
    def get_codebase_summary(self, max_files: int = 50) -> str:
        """
        Get a concise summary of the codebase for the LLM.
        
        Args:
            max_files: Maximum number of files to include in summary
        
        Returns:
            Summary string
        """
        analysis = self.analyze_codebase()
        summary_lines = [
            f"Codebase located at: {analysis['base_path']}",
            f"Total code files: {analysis['total_files']}",
            f"Files with existing tests: {analysis['test_coverage']['files_with_tests']}",
            f"Files needing tests: {analysis['test_coverage']['files_without_tests']}",
            "",
            "Directory structure:"
        ]
        
        for dir_path, files in list(analysis['structure'].items())[:20]:
            summary_lines.append(f"  {dir_path}/")
            for file in files[:5]:  # Show first 5 files per directory
                summary_lines.append(f"    - {file}")
            if len(files) > 5:
                summary_lines.append(f"    ... and {len(files) - 5} more files")
        
        # Add existing test patterns
        test_patterns = self.analyze_existing_test_patterns()
        if test_patterns:
            summary_lines.append("")
            summary_lines.append("=" * 80)
            summary_lines.append("EXISTING TEST PATTERNS - YOU MUST FOLLOW THESE EXACTLY:")
            summary_lines.append("=" * 80)
            summary_lines.append(test_patterns)
            summary_lines.append("")
        
        # Add detailed info for files needing tests
        files_needing_tests = [
            f for f in analysis['files'][:max_files]
            if not f.get('has_tests') and not f.get('error')
        ]
        
        if files_needing_tests:
            summary_lines.append("=" * 80)
            summary_lines.append("Files needing unit tests:")
            summary_lines.append("=" * 80)
            for file_info in files_needing_tests:
                summary_lines.append(f"  {file_info['file_path']}:")
                if file_info.get('functions'):
                    func_names = [f['name'] for f in file_info['functions']]
                    summary_lines.append(f"    Functions: {', '.join(func_names[:10])}")
                if file_info.get('classes'):
                    class_names = [c['name'] for c in file_info['classes']]
                    summary_lines.append(f"    Classes: {', '.join(class_names[:10])}")
        
        return "\n".join(summary_lines)
