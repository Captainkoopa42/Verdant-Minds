#!/usr/bin/env python3
"""Build a structured JSON summary of repository contents."""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


EXCLUDED_DIRS = {".git", "__pycache__", ".ipynb_checkpoints"}
EXCLUDED_PATTERNS = {"*.pyc"}
EXCLUDED_BINARY_EXTENSIONS = {
    ".pdf",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wav",
    ".gz",
    ".tar",
    ".7z",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
}

MARKDOWN_EXTENSIONS = {".md"}
CONFIG_EXTENSIONS = {".toml", ".json"}
DOC_EXTENSIONS = {".tex", ".bib", ".txt"}
DOC_FILENAMES = {"LICENSE", "README"}


def read_text(path: Path) -> str:
    """Read text safely with fallback decoding."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def should_skip(path: Path) -> bool:
    """Return True if this path should be excluded."""
    if path.name in EXCLUDED_DIRS:
        return True

    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(path.name, pattern):
            return True

    if path.suffix.lower() in EXCLUDED_BINARY_EXTENSIONS:
        return True

    return False


def format_arguments(args: ast.arguments) -> str:
    """Return a readable function signature from AST arguments."""
    pieces: list[str] = []

    positional = [*args.posonlyargs, *args.args]
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    posonly_count = len(args.posonlyargs)

    for idx, (arg, default) in enumerate(zip(positional, defaults)):
        token = arg.arg
        if arg.annotation is not None:
            token += f": {ast.unparse(arg.annotation)}"
        if default is not None:
            token += f"={ast.unparse(default)}"
        pieces.append(token)
        if posonly_count and idx + 1 == posonly_count:
            pieces.append("/")

    if args.vararg is not None:
        token = f"*{args.vararg.arg}"
        if args.vararg.annotation is not None:
            token += f": {ast.unparse(args.vararg.annotation)}"
        pieces.append(token)
    elif args.kwonlyargs:
        pieces.append("*")

    for kwarg, default in zip(args.kwonlyargs, args.kw_defaults):
        token = kwarg.arg
        if kwarg.annotation is not None:
            token += f": {ast.unparse(kwarg.annotation)}"
        if default is not None:
            token += f"={ast.unparse(default)}"
        pieces.append(token)

    if args.kwarg is not None:
        token = f"**{args.kwarg.arg}"
        if args.kwarg.annotation is not None:
            token += f": {ast.unparse(args.kwarg.annotation)}"
        pieces.append(token)

    return f"({', '.join(pieces)})"


def extract_import(node: ast.AST) -> str | None:
    """Render import statements in string form."""
    if isinstance(node, ast.Import):
        parts = []
        for alias in node.names:
            if alias.asname:
                parts.append(f"{alias.name} as {alias.asname}")
            else:
                parts.append(alias.name)
        return f"import {', '.join(parts)}"

    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        level_prefix = "." * node.level
        module_part = f"{level_prefix}{module}"
        names = []
        for alias in node.names:
            if alias.asname:
                names.append(f"{alias.name} as {alias.asname}")
            else:
                names.append(alias.name)
        return f"from {module_part} import {', '.join(names)}"

    return None


def summarize_python(path: Path, relative_path: str, content: str) -> dict[str, Any]:
    """Extract Python-specific metadata from source code."""
    result: dict[str, Any] = {
        "path": relative_path,
        "file_path": relative_path,
        "full_content": content,
        "imports": [],
        "classes": [],
        "functions": [],
    }

    try:
        tree = ast.parse(content)
    except SyntaxError as error:
        result["parse_error"] = f"{error.__class__.__name__}: {error}"
        return result

    for node in tree.body:
        import_stmt = extract_import(node)
        if import_stmt is not None:
            result["imports"].append(import_stmt)
            continue

        if isinstance(node, ast.ClassDef):
            methods = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(
                        {
                            "name": child.name,
                            "method_name": child.name,
                            "signature": format_arguments(child.args),
                        }
                    )

            result["classes"].append(
                {
                    "name": node.name,
                    "class_name": node.name,
                    "docstring": ast.get_docstring(node),
                    "methods": methods,
                    "method_names": [method["name"] for method in methods],
                }
            )
            continue

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"].append(
                {
                    "name": node.name,
                    "function_name": node.name,
                    "docstring": ast.get_docstring(node),
                    "signature": format_arguments(node.args),
                }
            )

    return result


def summarize_config(path: Path, relative_path: str, content: str) -> dict[str, Any]:
    """Extract configuration file content and parsed data."""
    entry: dict[str, Any] = {
        "path": relative_path,
        "file_path": relative_path,
        "full_content": content,
    }

    try:
        if path.suffix.lower() == ".json":
            entry["parsed_data"] = json.loads(content)
        elif path.suffix.lower() == ".toml":
            if tomllib is None:
                entry["parse_error"] = "tomllib is unavailable in this Python version"
            else:
                entry["parsed_data"] = tomllib.loads(content)
    except Exception as error:  # deliberate broad catch for robust reporting
        entry["parse_error"] = f"{error.__class__.__name__}: {error}"

    return entry


def classify_file(path: Path) -> str | None:
    """Classify a file into one of the output categories."""
    suffix = path.suffix.lower()
    if suffix == ".py":
        return "python_files"
    if suffix in MARKDOWN_EXTENSIONS:
        return "markdown_files"
    if suffix in CONFIG_EXTENSIONS:
        return "config_files"
    if suffix in DOC_EXTENSIONS:
        return "doc_files"

    upper_name = path.name.upper()
    if upper_name in DOC_FILENAMES or upper_name.startswith("README"):
        return "doc_files"

    return None


def build_summary(root: Path) -> dict[str, Any]:
    """Traverse repository and build structured summary object."""
    output: dict[str, Any] = {
        "repository_root": str(root),
        "python_files": [],
        "markdown_files": [],
        "config_files": [],
        "doc_files": [],
    }

    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if not should_skip(Path(name))]

        current_root_path = Path(current_root)
        for filename in filenames:
            file_path = current_root_path / filename
            if should_skip(file_path):
                continue

            category = classify_file(file_path)
            if category is None:
                continue

            relative_path = str(file_path.relative_to(root))
            try:
                content = read_text(file_path)
            except OSError as error:
                output[category].append(
                    {
                        "path": relative_path,
                        "file_path": relative_path,
                        "error": f"{error.__class__.__name__}: {error}",
                    }
                )
                continue

            if category == "python_files":
                output[category].append(summarize_python(file_path, relative_path, content))
            elif category == "config_files":
                output[category].append(summarize_config(file_path, relative_path, content))
            else:
                output[category].append(
                    {
                        "path": relative_path,
                        "file_path": relative_path,
                        "full_content": content,
                    }
                )

    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recursively summarize repository files into structured JSON"
    )
    parser.add_argument(
        "root",
        nargs="?",
        default="/content/verdant",
        help="Root directory to scan (default: /content/verdant)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output with indentation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()

    if not root.exists():
        raise SystemExit(f"Root path does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"Root path is not a directory: {root}")

    summary = build_summary(root)
    if args.pretty:
        print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=False))
    else:
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
