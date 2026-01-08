from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Scene:
    i: int
    start_sec: float
    end_sec: float

    @property
    def dur(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)

def merge_micro_scenes(
    scenes: List[Scene],
    min_scene_sec: float = 1.5,
    max_merge_chain: int = 8,
) -> List[Scene]:
    if not scenes:
        return []

    merged: List[Scene] = []
    chain = 0

    for sc in scenes:
        if not merged:
            merged.append(sc)
            continue

        if sc.dur < min_scene_sec:
            # Merge into previous scene
            merged[-1].end_sec = max(merged[-1].end_sec, sc.end_sec)
            chain += 1
            if chain >= max_merge_chain:
                # Force break: start a new scene to avoid endless glue
                merged.append(sc)
                chain = 0
        else:
            merged.append(sc)
            chain = 0

    # Re-index
    for idx, sc in enumerate(merged):
        sc.i = idx

    return merged
