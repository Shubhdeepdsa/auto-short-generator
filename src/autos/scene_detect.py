import json
import csv
from pathlib import Path
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from autos.paths import episode_dirs

def run_scene_detect(input_video: Path, series_id: str, episode_id: str):
    """
    Detect scenes using PySceneDetect ContentDetector.
    Writes raw_scenes.csv and raw_scenes.json under
    artifacts/<episode_id>/scenes
    """

    # Get all the dirs for this episode
    dirs = episode_dirs("artifacts", episode_id, series_id)
    scenes_dir = dirs["scenes"]
    scenes_dir.mkdir(parents=True, exist_ok=True)

    video_path = str(input_video)

    # Initialize PySceneDetect’s managers
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())

    # Start detection
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    scene_list = scene_manager.get_scene_list()

    # Write CSV
    csv_file = scenes_dir / "raw_scenes.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["start_sec", "end_sec"])
        for start, end in scene_list:
            writer.writerow([start.get_seconds(), end.get_seconds()])

    # Write JSON
    json_file = scenes_dir / "raw_scenes.json"
    json_data = [
        {"start_sec": start.get_seconds(), "end_sec": end.get_seconds()}
        for start, end in scene_list
    ]
    with open(json_file, "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"Scene detection done. {len(scene_list)} scenes found.")
    print(f"CSV → {csv_file}")
    print(f"JSON → {json_file}")
