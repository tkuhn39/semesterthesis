# Project Rules & Context

This file defines the strict rules and architectural guidelines for the `semesterthesis\` project. All IDEs and AI agents MUST follow these rules.

## Directory Structure (under `20_code\`)
- `20_code\00_development_documentation\`: e.g., lessons learned, decisions, development stories, deployment, architecture...
- `20_code\10_verifiers\`: Python files used purely for verification/testing.
- `20_code\20_antigravity_scripts\`: Scripts used for moving files, automation, and command execution.

## Global Rules
1. **File Generation**: New project files should be placed in their respective architected directories under `20_code\`.
2. **Backward Compatibility**: No backward compatibility requirements.
3. **Unused Code**: Code must always be tested against unused interfaces or unused variables.
4. **Exception Handling**: Always use the exception script under `commonLibs` for error handling.
5. **Exception Logs**: Check the logs under the `20_code\90_logs\` folder and handle exceptions.
6. **Timezone**: Always use **CET** (Central European Time) unless specified otherwise.
7. **OOP Paradigm**: Think in classes and utilize the object-oriented nature of Python.
8. **Fault Tolerance**: DO NOT silence faults. Avoid mutable defaults in `.get()` (e.g., `.get(key, [])`, `.get(key, {})`).
9. **Categorized Output**: Results, CSVs, logs, and photos must be placed in categorized subfolders under the `20_code\80_output\` folder.
10. **Prompt Headers**: Add a concise, machine-readable prompt at the beginning of each `.py` file describing its context and functionality.
11. **Minimal Try-Except**: Use as few try-except blocks as possible.
12. **Strict Dict Access**: Always use `dict["key"]` instead of `.get("key")` unless default behavior is explicitly required (and non-mutable).
13. **Type Jumps**: No jumps between types (e.g., list <-> tuple <-> dict) unless explicitly stated and limited to optimization.
14. **Accumulative Documentation**: Markdown files for e.g., lessons learned, decisions, and development stories (files in `20_code\00_development_documentation\`) **MUST NEVER** be replaced or overwritten entirely. New entries must be appended or merged to maintain a continuous, accumulating development story.