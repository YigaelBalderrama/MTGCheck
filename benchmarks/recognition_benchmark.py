from __future__ import annotations

import argparse
import os
import statistics
import time
from pathlib import Path
from typing import Any

from app import create_app
from app.utils.text_utils import normalize_card_name

EXPECTED_NAMES = {
    normalize_card_name(name)
    for name in [
        "Massacre Girl",
        "Incinerar",
        "Mutilate",
        "La crueldad de Gix",
        "Empantanar",
        "Difundeplagas",
        "Fleshbag Marauder",
        "Discípulo del demonio",
        "Merodeador maldito",
        "Epic Downfall",
        "Bitter Triumph",
        "Cut Down",
        "Pharika's Libation",
        "Feed the Swarm",
    ]
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark MTG recognition pipeline.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--use-cache", action="store_true")
    args = parser.parse_args()

    if not args.image.exists():
        raise SystemExit(f"Image not found: {args.image}")

    os.environ["ENABLE_DIAGNOSTIC_METRICS"] = "true"
    os.environ["ENABLE_RECOGNITION_CACHE"] = "true" if args.use_cache else "false"
    image_bytes = args.image.read_bytes()
    content_type = _content_type_for(args.image)
    app = create_app(os.getenv("APP_ENV", "development"))
    service = app.extensions["card_recognition_service"]

    for _ in range(args.warmup):
        service.recognize(image_bytes, content_type)

    results: list[dict[str, Any]] = []
    durations: list[int] = []
    for _ in range(args.iterations):
        started_at = time.perf_counter()
        response = service.recognize(image_bytes, content_type)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        payload = response.to_dict()
        payload["wall_time_ms"] = elapsed_ms
        results.append(payload)
        durations.append(elapsed_ms)

    latest = results[-1]
    recognized_names = {
        normalize_card_name(card.get("printed_name") or card.get("name"))
        for card in latest["cards"]
        if card["recognized"]
    }
    expected_hits = len(EXPECTED_NAMES.intersection(recognized_names))
    sorted_durations = sorted(durations)
    p95_index = min(len(sorted_durations) - 1, int(len(sorted_durations) * 0.95))

    print("MTG Multi-Card Recognition Benchmark")
    print(f"image={args.image}")
    print("previous_time_ms=unavailable")
    print(f"iterations={args.iterations}")
    print(f"average_ms={statistics.mean(durations):.2f}")
    print(f"median_ms={statistics.median(durations):.2f}")
    print(f"p95_ms={sorted_durations[p95_index]}")
    print(f"cards_detected={latest['cards_detected']}")
    print(f"cards_recognized={latest['cards_recognized']}")
    print(f"expected_accuracy={expected_hits}/{len(EXPECTED_NAMES)}")
    print(f"stage_metrics={latest.get('metrics', {})}")


def _content_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


if __name__ == "__main__":
    main()
