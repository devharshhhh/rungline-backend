"""
Loads validated problem JSON files (the ones produced via the
Question_Generation_Kit prompt + checked with validate_problems.py) into
the database.

Usage:
    python seed_problems.py path/to/problem_json_folder/ [--language python]

Name your JSON files with a numeric prefix so they load in the order you
want topics to appear, e.g.:
    01_print_output.json
    02_variables_input.json
    03_string_basics.json
    ...
Topics are created the first time they're seen, in file-processing order,
which becomes their order_index (used by the "next problem" endpoint).
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import SessionLocal, init_db  # noqa: E402
from app.db import models  # noqa: E402


def get_or_create_topic(db, name: str, next_order_index: list[int]) -> models.Topic:
    existing = db.query(models.Topic).filter(models.Topic.name == name).first()
    if existing:
        return existing
    topic = models.Topic(name=name, order_index=next_order_index[0])
    next_order_index[0] += 1
    db.add(topic)
    db.flush()
    return topic


def load_folder(folder: Path, language: str):
    init_db()
    db = SessionLocal()
    next_order_index = [0]

    # keep order_index continuing on from whatever's already in the DB
    max_existing = db.query(models.Topic.order_index).order_by(models.Topic.order_index.desc()).first()
    if max_existing:
        next_order_index[0] = max_existing[0] + 1

    total_loaded, total_skipped = 0, 0

    for json_file in sorted(folder.glob("*.json")):
        problems = json.loads(json_file.read_text(encoding="utf-8"))
        if not isinstance(problems, list):
            print(f"Skipping {json_file.name}: not a JSON array")
            continue

        for p in problems:
            topic = get_or_create_topic(db, p["topic"], next_order_index)

            already_exists = (
                db.query(models.Problem)
                .filter(models.Problem.topic_id == topic.id, models.Problem.title == p["title"])
                .first()
            )
            if already_exists:
                total_skipped += 1
                continue

            problem = models.Problem(
                topic_id=topic.id,
                sub_topic=p.get("topic"),
                grade=p["grade"],
                rank=p["rank"],
                language=language,
                title=p["title"],
                statement=p["statement"],
                starter_code=p.get("starter_code", ""),
                test_cases=p["test_cases"],
                time_limit_ms=p.get("time_limit_ms", 2000),
                edge_case_notes=p.get("edge_case_notes", ""),
                common_mistakes=p.get("common_mistakes", ""),
                tags=p.get("tags", []),
            )
            db.add(problem)
            total_loaded += 1

        db.commit()
        print(f"{json_file.name}: processed")

    db.close()
    print(f"\nDone. Loaded {total_loaded} new problem(s), skipped {total_skipped} duplicate(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=str, help="Folder containing validated problem JSON files")
    parser.add_argument("--language", default="python", choices=["python", "cpp"])
    args = parser.parse_args()

    load_folder(Path(args.folder), args.language)
