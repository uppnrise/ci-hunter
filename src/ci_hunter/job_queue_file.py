from __future__ import annotations

import json
from pathlib import Path

from ci_hunter.file_lock import locked_file
from ci_hunter.queue import AnalysisJob


def append_job(path: str, job: AnalysisJob) -> None:
    payload = {
        "repo": job.repo,
        "pr_number": job.pr_number,
        "commit": job.commit,
        "branch": job.branch,
    }
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with locked_file(path_obj, "a") as handle:
        handle.write(json.dumps(payload) + "\n")
