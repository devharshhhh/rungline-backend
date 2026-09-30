"""
Validates AI-generated problem JSON files against the platform schema
before loading them into the database.

Usage:
    python validate_problems.py path/to/file.json
    python validate_problems.py path/to/folder/          # validates every .json inside

Exit code 0 = all valid. Exit code 1 = at least one error found (see printed report).
"""

import json
import sys
import re
from pathlib import Path

VALID_GRADES = {"A", "B", "C", "D", "E"}
REQUIRED_FIELDS = [
    "topic", "grade", "rank", "title", "statement",
    "starter_code", "test_cases", "tags"
]
# edge_case_notes and common_mistakes are recommended but not hard-required,
# since older batches may not include them yet.
RECOMMENDED_FIELDS = ["edge_case_notes", "common_mistakes"]


class ValidationError:
    def __init__(self, file, index, title, message):
        self.file = file
        self.index = index
        self.title = title
        self.message = message

    def __str__(self):
        loc = f"{self.file} [problem #{self.index}"
        if self.title:
            loc += f' "{self.title}"'
        loc += "]"
        return f"{loc}: {self.message}"


def validate_problem(problem, index, file, seen_titles, errors, warnings):
    # Required fields present
    for field in REQUIRED_FIELDS:
        if field not in problem:
            errors.append(ValidationError(file, index, problem.get("title"), f"missing required field '{field}'"))

    if "title" not in problem or "topic" not in problem:
        # can't do much more meaningful checking without these
        return

    title = problem.get("title", "")

    # Recommended fields present (warning only)
    for field in RECOMMENDED_FIELDS:
        if field not in problem or not str(problem.get(field, "")).strip():
            warnings.append(ValidationError(file, index, title, f"missing recommended field '{field}' (used for AI tutor hints)"))

    # Grade validity
    grade = problem.get("grade")
    if grade is not None and grade not in VALID_GRADES:
        errors.append(ValidationError(file, index, title, f"invalid grade '{grade}', expected one of {sorted(VALID_GRADES)}"))

    # Rank validity
    rank = problem.get("rank")
    if rank is not None:
        if not isinstance(rank, int) or not (1 <= rank <= 10):
            errors.append(ValidationError(file, index, title, f"invalid rank '{rank}', expected an integer 1-10"))

    # Statement non-trivial
    statement = problem.get("statement", "")
    if len(statement.strip()) < 20:
        errors.append(ValidationError(file, index, title, "statement is too short / likely incomplete"))

    # Duplicate title check (within this run)
    key = (problem.get("topic"), title.strip().lower())
    if key in seen_titles:
        errors.append(ValidationError(file, index, title, "duplicate title within the same topic — check for repeated generation"))
    else:
        seen_titles.add(key)

    # starter_code should not already contain a full solution
    starter = problem.get("starter_code", "")
    if _looks_like_full_solution(starter):
        warnings.append(ValidationError(file, index, title, "starter_code looks suspiciously complete — check it isn't leaking the solution"))

    # Test cases
    test_cases = problem.get("test_cases")
    if not isinstance(test_cases, list) or len(test_cases) < 2:
        errors.append(ValidationError(file, index, title, "needs at least 2 test_cases as a list"))
    else:
        for i, tc in enumerate(test_cases):
            if not isinstance(tc, dict):
                errors.append(ValidationError(file, index, title, f"test_cases[{i}] is not an object"))
                continue
            if "input" not in tc or "expected_output" not in tc:
                errors.append(ValidationError(file, index, title, f"test_cases[{i}] missing 'input' or 'expected_output'"))
            elif str(tc.get("expected_output", "")).strip() == "":
                errors.append(ValidationError(file, index, title, f"test_cases[{i}] has empty expected_output"))

    # Tags
    tags = problem.get("tags")
    if not isinstance(tags, list) or len(tags) == 0:
        warnings.append(ValidationError(file, index, title, "no tags provided — search/filtering will be weaker"))


def _looks_like_full_solution(starter_code: str) -> bool:
    """Heuristic: flags starter code that already contains return/print logic
    beyond a bare function signature or 'pass' stub."""
    if not starter_code:
        return False
    stripped = starter_code.strip()
    # allow bare signatures, pass, docstrings, comments, TODOs
    harmless_pattern = re.compile(
        r'^(def\s+\w+\([^)]*\)\s*:\s*|#.*|""".*?"""|pass|\.\.\.|\s)*$',
        re.DOTALL,
    )
    if harmless_pattern.match(stripped):
        return False
    # if it has multiple non-trivial lines with return/print + operators, flag it
    suspicious_lines = [
        l for l in stripped.splitlines()
        if l.strip() and not l.strip().startswith("#") and "def " not in l and "pass" not in l
    ]
    return len(suspicious_lines) >= 3


def validate_file(path: Path):
    errors, warnings = [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(ValidationError(path.name, "-", None, f"invalid JSON: {e}"))
        return errors, warnings

    if not isinstance(data, list):
        errors.append(ValidationError(path.name, "-", None, "top-level JSON must be an array of problem objects"))
        return errors, warnings

    if len(data) == 0:
        warnings.append(ValidationError(path.name, "-", None, "file contains zero problems"))

    seen_titles = set()
    for i, problem in enumerate(data, start=1):
        if not isinstance(problem, dict):
            errors.append(ValidationError(path.name, i, None, "problem entry is not a JSON object"))
            continue
        validate_problem(problem, i, path.name, seen_titles, errors, warnings)

    # Grade distribution sanity check (expect roughly 4 A / 3 B / 3 C per the prompt spec)
    grade_counts = {}
    for problem in data:
        if isinstance(problem, dict) and "grade" in problem:
            grade_counts[problem["grade"]] = grade_counts.get(problem["grade"], 0) + 1
    if grade_counts and grade_counts != {} and len(data) >= 8:
        if grade_counts.get("A", 0) < 2 or grade_counts.get("B", 0) < 1 or grade_counts.get("C", 0) < 1:
            warnings.append(ValidationError(path.name, "-", None, f"unusual grade distribution: {grade_counts} — expected roughly 4A/3B/3C"))

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"Path not found: {target}")
        sys.exit(1)

    files = [target] if target.is_file() else sorted(target.glob("*.json"))
    if not files:
        print(f"No .json files found at {target}")
        sys.exit(1)

    total_errors, total_warnings, total_problems = 0, 0, 0

    for f in files:
        errors, warnings = validate_file(f)
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            count = len(data) if isinstance(data, list) else 0
        except Exception:
            count = 0
        total_problems += count
        total_errors += len(errors)
        total_warnings += len(warnings)

        if errors or warnings:
            print(f"\n=== {f.name} ({count} problems) ===")
            for e in errors:
                print(f"  ERROR   {e}")
            for w in warnings:
                print(f"  WARNING {w}")
        else:
            print(f"{f.name} ({count} problems): OK")

    print(f"\nSummary: {len(files)} file(s), {total_problems} problem(s), "
          f"{total_errors} error(s), {total_warnings} warning(s)")

    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()
