# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

K-Pop Fancam Tools - Python tools for processing K-Pop fancam videos:
- **fancam_organizer.py** - Automatically sorts fancam videos by identifying the main dancer using facial recognition and clustering
- **fancam_splitter.py** - Splits a video into clips based on a timestamp file using FFmpeg
- **srt_generator.py** - Generates .srt subtitle files for Random Dance Game videos from timestamp files

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# --- Fancam Organizer ---

# Run the organizer
python fancam_organizer.py /path/to/videos

# Run with custom output directory
python fancam_organizer.py /path/to/videos -o /path/to/output

# Dry run (analyze without moving files)
python fancam_organizer.py /path/to/videos --dry-run

# Adjust clustering parameters
python fancam_organizer.py /path/to/videos --eps 0.3 --min-samples 2

# --- Fancam Splitter ---

# Split video into clips based on timestamps
python fancam_splitter.py video.mp4 timestamps.txt

# Custom output directory
python fancam_splitter.py video.mp4 timestamps.txt -o /path/to/clips

# Dry run (show clips without creating them)
python fancam_splitter.py video.mp4 timestamps.txt --dry-run

# Use H.265 codec for smaller files
python fancam_splitter.py video.mp4 timestamps.txt --codec h265

# Stream copy (fast, no re-encoding)
python fancam_splitter.py video.mp4 timestamps.txt --codec copy

# Adjust quality (lower = better, default 18)
python fancam_splitter.py video.mp4 timestamps.txt --crf 23 --preset fast

# --- SRT Generator ---

# Generate .srt subtitles (edit config constants in script first)
python srt_generator.py
```

## Architecture

### Fancam Organizer

The tool operates in a two-phase pipeline:

**Phase 1 - Feature Extraction:**
- Extracts ~20 frames from each video (skipping first/last 10% to avoid intros/outros)
- Uses DeepFace with RetinaFace backend for face detection
- Selects the largest face in each frame (assumes main dancer is closest to camera)
- Generates ArcFace embeddings and computes mean vector as video fingerprint

**Phase 2 - Clustering:**
- Uses DBSCAN with cosine metric to group videos by person
- Creates folders: `Dancer_01`, `Dancer_02`, etc. for clusters
- `Unknown/` for noise (cluster -1), `Error/` for videos with no detected faces

### Fancam Splitter

The tool uses FFmpeg for video processing:

**Timestamp Parsing:**
- Parses timestamp file with optional `START:` offset
- Supports `MM:SS` and `HH:MM:SS` formats
- Automatically calculates clip durations based on next timestamp

**Video Splitting:**
- Uses FFmpeg subprocess for full codec support
- H.264 encoding with High profile for smartphone compatibility
- AAC audio at 192kbps
- `faststart` flag for web streaming

### SRT Generator

Generates .srt subtitle files showing "ARTIST - SONG TITLE" for Random Dance Game videos:

- Reads numbered timestamp files (1.txt, 2.txt, ...) from a directory
- Accounts for video intro and playlist transitions (configurable durations)
- Strips metadata (section info, usernames) from titles, preserves song title parentheses
- All configuration via constants at top of script (no CLI arguments)

**Configuration constants** at top of `srt_generator.py`:
- `TIMESTAMPS_DIR` - folder with timestamp files
- `VIDEO_DURATION` - total video duration
- `INTRO_DURATION` - intro before first playlist (default 6s)
- `TRANSITION_DURATION` - gap between playlists (default 6s)
- `PLAYLIST_STARTS` - absolute start times for playlists 2-N

## Key Configuration Constants

Located at top of `fancam_organizer.py`:
- `FRAMES_TO_EXTRACT = 20`
- `SKIP_PERCENT = 0.10`
- `EMBEDDING_MODEL = "ArcFace"`
- `DETECTOR_BACKEND = "retinaface"` (alternatives: yolov8, mtcnn, opencv)

## Timestamp File Format

```
START: 01:30
05:16 NCT DOJAEJUNG - PERFUME (Dancebreak)
09:42 aespa - Supernova
13:15 RIIZE - Boom Boom Bass
```

- `START:` line is optional, used as offset when timestamps are from YouTube description
- Each timestamp line: `MM:SS Title` or `HH:MM:SS Title`
- Empty lines are ignored
- Output filenames: `01_NCT_DOJAEJUNG_-_PERFUME.mp4`

## Notes

- First run downloads DeepFace models (~500MB for ArcFace + RetinaFace)
- Lower `--eps` values create stricter groupings, higher values are more permissive
- `--min-samples 1` allows single-video clusters; increase to require minimum group size
- FFmpeg must be installed for fancam_splitter.py to work
