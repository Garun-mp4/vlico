"""Prepare client videos without recompression: python scripts/prepare-project-videos.py --source-root PATH."""
import argparse
from pathlib import Path
import runpy
import subprocess
import tempfile

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    videos = runpy.run_path(str(root / 'backend/core/project_videos.py'))['PROJECT_VIDEOS']
    filenames = (
        'video_2026-11-11_23-20-10.mp4', 'video_2026-11-11_23-20-28.mp4',
        'video_2026-11-11_23-20-32.mp4', 'video_2026-11-11_23-20-35.mp4',
        'video_2026-11-11_23-20-38.mp4', 'video_2026-11-11_23-21-27.mp4',
        'video_2026-11-11_23-22-46.mp4',
    )
    sources = [args.source_root / name for name in filenames]
    for source in sources:
        if not source.is_file():
            parser.error(f'Missing video: {source}')
    output = root / 'backend/static/project-videos'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vlico-video-') as temporary:
        for video, source, position in zip(videos, sources, (3, 9, 3, 6, 3, 3, 3), strict=True):
            target = output / video['slug']
            subprocess.run([args.ffmpeg, '-v', 'error', '-y', '-i', str(source),
                            '-map', '0:v:0', '-map', '0:a:0?', '-c', 'copy',
                            '-movflags', '+faststart', str(target.with_suffix('.mp4'))], check=True)
            frame = Path(temporary) / 'frame.png'
            subprocess.run([args.ffmpeg, '-v', 'error', '-y', '-ss', str(position),
                            '-i', str(source), '-frames:v', '1', str(frame)], check=True)
            with Image.open(frame) as image:
                image.convert('RGB').save(target.with_suffix('.webp'), quality=85)
            print(target.name)


if __name__ == '__main__':
    main()
