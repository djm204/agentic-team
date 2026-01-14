"""
Utilities for writing project files from implementation output.
"""
import os
import re
from pathlib import Path


def _is_valid_file_path(file_path: str) -> bool:
    """
    Validate that a file path is actually a file path, not descriptive text.
    
    Args:
        file_path: Potential file path to validate
    
    Returns:
        True if it looks like a valid file path
    """
    # Remove quotes and backticks
    file_path = file_path.strip('`"\'').strip()
    
    # Must end with a valid file extension
    valid_extensions = ('.py', '.js', '.ts', '.json', '.md', '.txt', '.yml', '.yaml', 
                       '.toml', '.ini', '.cfg', '.conf', '.sh', '.bash', '.html', '.css',
                       '.xml', '.sql', '.go', '.rs', '.java', '.cpp', '.c', '.h', '.hpp')
    
    if not file_path.endswith(valid_extensions):
        return False
    
    # Must not contain spaces (except in valid directory names, but be strict)
    if '  ' in file_path:  # Double spaces are suspicious
        return False
    
    # Must not be a sentence (contains common sentence words)
    sentence_indicators = [' could ', ' should ', ' would ', ' might ', ' we ', ' you ', 
                          ' have a ', ' have an ', ' for the ', ' of the ', ' in the ']
    file_path_lower = file_path.lower()
    if any(indicator in file_path_lower for indicator in sentence_indicators):
        return False
    
    # Must not be too long (likely descriptive text)
    if len(file_path) > 200:
        return False
    
    # Must contain at least one slash or be a simple filename
    if '/' not in file_path and '\\' not in file_path:
        # Simple filename is OK if it's short and has extension
        if len(file_path) > 50:
            return False
    
    return True


def _clean_file_path(file_path: str) -> str:
    """
    Clean a file path by removing quotes, backticks, and descriptive text.
    
    Args:
        file_path: Raw file path string
    
    Returns:
        Cleaned file path
    """
    # Remove quotes and backticks
    file_path = file_path.strip('`"\'').strip()
    
    # Remove common prefixes that are descriptive text
    prefixes_to_remove = [
        r'^for the .+? we could have a\s+',
        r'^we could have a\s+',
        r'^for the\s+',
        r'^the\s+',
        r'^a\s+',
        r'^an\s+',
    ]
    
    for prefix in prefixes_to_remove:
        file_path = re.sub(prefix, '', file_path, flags=re.IGNORECASE)
    
    # Extract just the file path if it's embedded in text
    # Look for patterns like: "text `.github/workflows/file.yml` more text"
    match = re.search(r'`([^`]+)`', file_path)
    if match:
        file_path = match.group(1)
    
    # Remove trailing descriptive words like " file" or " directory"
    file_path = re.sub(r'\s+(file|directory|folder|path)$', '', file_path, flags=re.IGNORECASE)
    
    # Remove leading ./ if present
    if file_path.startswith('./'):
        file_path = file_path[2:]
    
    return file_path.strip()


def parse_implementation_to_files(implementation: str, base_path: str = "."):
    """
    Parse implementation output and extract file contents.
    
    This function attempts to extract file paths and contents from the
    implementation text, which may be in various formats.
    
    Args:
        implementation: The implementation text from the developer agent
        base_path: Base directory to write files to
    
    Returns:
        Dictionary mapping file paths to file contents
    """
    files = {}
    
    # Pattern 1: Markdown code blocks with file paths (most common)
    # ```python:path/to/file.py
    # code here
    # ```
    # Also handles: ```python:tests/test_file.py
    pattern1 = r'```(?:\w+)?:([^\n]+)\n(.*?)```'
    matches = re.finditer(pattern1, implementation, re.DOTALL)
    for match in matches:
        file_path = match.group(1).strip()
        content = match.group(2).strip()
        
        # Clean and validate file path
        file_path = _clean_file_path(file_path)
        if not _is_valid_file_path(file_path):
            continue
        
        # Validate content is actual code, not just description
        if not _is_valid_code_content(content):
            continue
        
        files[file_path] = content
    
    # Pattern 2: File path headers followed by code blocks
    # File: path/to/file.py
    # ```python
    # code here
    # ```
    pattern2 = r'File:\s*([^\n]+)\n.*?```(?:\w+)?\n(.*?)```'
    matches = re.finditer(pattern2, implementation, re.DOTALL)
    for match in matches:
        file_path = match.group(1).strip()
        content = match.group(2).strip()
        
        # Clean and validate file path
        file_path = _clean_file_path(file_path)
        if not _is_valid_file_path(file_path):
            continue
        
        # Validate content is actual code, not just description
        if not _is_valid_code_content(content):
            continue
        
        files[file_path] = content
    
    # Pattern 3: Test file patterns (tests/test_*.py, test_*.py, etc.)
    # Look for test file mentions followed by code blocks
    test_pattern = r'(?:test|tests)[/\\]?([^\s:]+\.(?:py|js|ts|java))\s*[:]?\s*\n.*?```(?:\w+)?\n(.*?)```'
    matches = re.finditer(test_pattern, implementation, re.DOTALL | re.IGNORECASE)
    for match in matches:
        test_file = match.group(1).strip()
        content = match.group(2).strip()
        
        # Clean and validate
        test_file = _clean_file_path(test_file)
        if not _is_valid_file_path(test_file):
            continue
        
        # Validate content is actual code
        if not _is_valid_code_content(content):
            continue
        
        # Ensure it's in tests/ directory
        if not test_file.startswith('tests/'):
            test_file = f'tests/{test_file}'
        files[test_file] = content
    
    # Pattern 4: Directory structure with file contents (be very strict)
    # path/to/
    #   file.py:
    #     code here
    lines = implementation.split('\n')
    current_path = None
    current_content = []
    
    for line in lines:
        # Check if line indicates a file path
        if ':' in line and not line.strip().startswith('#') and not line.strip().startswith('//'):
            potential_path = line.split(':')[0].strip()
            potential_path = _clean_file_path(potential_path)
            
            # Must be a valid file path
            if _is_valid_file_path(potential_path):
                # Save previous file if it had valid content
                if current_path and current_content:
                    content = '\n'.join(current_content).strip()
                    if _is_valid_code_content(content):
                        files[current_path] = content
                current_path = potential_path
                current_content = []
                continue
        
        if current_path:
            current_content.append(line)
    
    # Save last file
    if current_path and current_content:
        content = '\n'.join(current_content).strip()
        if _is_valid_code_content(content):
            files[current_path] = content
    
    return files


def _is_valid_code_content(content: str) -> bool:
    """
    Validate that content is actual code, not just descriptive text.
    
    Args:
        content: Content to validate
    
    Returns:
        True if it looks like actual code
    """
    if not content or len(content.strip()) < 10:
        return False
    
    content_lower = content.lower().strip()
    first_line = content.split('\n')[0].strip() if content else ""
    first_line_lower = first_line.lower()
    
    # Reject if first line starts with a sentence (capital letter, ends with period)
    # This catches things like "And, this pattern will be followed..."
    if first_line and first_line[0].isupper() and (first_line.endswith('.') or first_line.endswith(',')):
        # But allow if it's a comment or docstring
        if not (first_line.startswith('#') or first_line.startswith('"""') or first_line.startswith("'''")):
            # Check if it looks like a sentence (has common sentence words)
            sentence_starters = ['and', 'once', 'here', 'this', 'that', 'the', 'for', 'when', 'where', 'how', 'why']
            first_words = first_line_lower.split()[:3]
            if any(word in sentence_starters for word in first_words):
                return False
    
    # Reject if it's just descriptive text
    descriptive_phrases = [
        'could look like',
        'might look like',
        'should look like',
        'would look like',
        'the content of',
        'an example',
        'for example',
        'here is an example',
        'given the abstract',
        'without access to',
        'i cannot',
        'i don\'t have',
        'i need',
        'please provide',
        'this pattern will be followed',
        'once all the test files',
        'here is an example command',
    ]
    
    # Check first few lines for descriptive text
    first_lines = '\n'.join(content.split('\n')[:3]).lower()
    if any(phrase in first_lines for phrase in descriptive_phrases):
        return False
    
    # Must contain actual code patterns
    code_indicators = [
        'import ', 'from ', 'def ', 'class ', 'return ', 'if ', 'for ', 'while ',
        'function ', 'const ', 'let ', 'var ', 'public ', 'private ', 'protected ',
        '<?php', '<!DOCTYPE', 'package ', 'namespace ', 'use ', 'require ',
        'test_', 'def test_', 'it(', 'describe(', 'expect(', 'assert',
    ]
    
    # Check if content has code-like patterns
    has_code = any(indicator in content for indicator in code_indicators)
    
    # If it's very short and has no code indicators, it's probably not code
    if len(content) < 50 and not has_code:
        return False
    
    return has_code or len(content) > 100  # Allow longer content even without obvious code patterns


def write_files_from_implementation(implementation: str, base_path: str = "."):
    """
    Parse implementation and write files to disk.
    
    Args:
        implementation: The implementation text from the developer agent
        base_path: Base directory to write files to
    
    Returns:
        List of created file paths
    """
    files = parse_implementation_to_files(implementation, base_path)
    created_files = []
    seen_paths = set()  # Track paths to avoid duplicates
    
    base = Path(base_path)
    base.mkdir(parents=True, exist_ok=True)
    
    for file_path, content in files.items():
        # Clean up file path
        file_path = file_path.strip()
        if file_path.startswith('./'):
            file_path = file_path[2:]
        
        # Normalize path to avoid duplicates (e.g., tests/file.py vs tests//file.py)
        normalized_path = str(Path(file_path)).replace('\\', '/')
        
        # Skip if we've already seen this path
        if normalized_path in seen_paths:
            print(f"Skipping duplicate: {normalized_path}")
            continue
        
        seen_paths.add(normalized_path)
        
        full_path = base / normalized_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Skip weird paths like "s/" or single letter directories that aren't valid
        path_parts = normalized_path.split('/')
        if any(len(part) == 1 and part.isalpha() and part != 's' for part in path_parts):
            # Single letter directories are suspicious unless they're common (like 's' for src)
            # But "s/" by itself is weird, reject it
            if normalized_path.startswith('s/') and len(path_parts) == 2:
                print(f"Skipping suspicious path: {normalized_path}")
                continue
        
        # Write file
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            created_files.append(str(full_path))
            print(f"Created: {full_path}")
        except Exception as e:
            print(f"Error writing {full_path}: {e}")
    
    return created_files


def extract_file_structure(implementation: str):
    """
    Extract just the file structure from implementation.
    
    Args:
        implementation: The implementation text
    
    Returns:
        List of file paths mentioned in the implementation
    """
    files = parse_implementation_to_files(implementation)
    return list(files.keys())
