"""Bounded, honest estimates from measured work; never invent whole-job progress."""

import math
import re
import statistics


def duration(seconds):
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{seconds // 60} min {seconds % 60:02d} s"
    return f"{seconds // 3600} h {(seconds % 3600) // 60:02d} min"


def clock_seconds(value):
    parts = value.split(":")
    if len(parts) not in (2, 3) or any(not p.isdigit() or len(p)>4 for p in parts):
        return None
    if any(int(p) >= 60 for p in parts[1:]):
        return None
    total = 0
    for part in parts:
        total = total * 60 + int(part)
    return total if total <= 7 * 86400 else None


def prediction_progress(text):
    """Read only the prediction bar, excluding subsequent export/collection bars."""
    text = text[-65536:]
    markers = list(re.finditer(r"^Predicting [^\r\n]+:", text, re.MULTILINE))
    if not markers:
        return None
    lines = text[markers[-1].end():]
    if any(marker in lines for marker in ("sending off prediction", "done with ", "Collecting results:")):
        return {"stage": "saving", "done": None, "total": None, "remaining": None}
    matches = list(re.finditer(r"\d{1,3}%\|[^|\r\n]*\|\s*(\d{1,7})/(\d{1,7})\s+\[([\d:]+)<([\d:?]+)", lines))
    if not matches:
        return None
    done, total, elapsed, remaining = matches[-1].groups()
    done, total = int(done), int(total)
    if not 0 <= done <= total <= 1_000_000 or total == 0:
        return None
    if done == total:
        return {"stage": "saving", "done": done, "total": total, "remaining": None}
    elapsed = clock_seconds(elapsed)
    estimate = clock_seconds(remaining) if done else None
    if not estimate and done and elapsed:
        estimate = elapsed * (total - done) / done
    return {"stage": "predicting", "done": done, "total": total,
            "remaining": estimate, "elapsed": elapsed}


def queued_batch_estimate(cases):
    """Extrapolate only queued cases using completed cases in this same batch."""
    minutes = []
    for case in cases:
        value = case.get("record", {}).get("minutes")
        if case.get("state") == "completed" and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0:
            minutes.append(value)
    pending = sum(case.get("state") == "pending" for case in cases)
    if not pending or len(minutes) < 2:
        return None
    return {"seconds": statistics.median(minutes) * 60 * pending,
            "samples": len(minutes), "pending": pending}
