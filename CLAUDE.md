# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

K-Pop Fancam Organizer - A Python tool that automatically sorts fancam videos by identifying the main dancer using facial recognition and clustering.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the organizer
python fancam_organizer.py /path/to/videos

# Run with custom output directory
python fancam_organizer.py /path/to/videos -o /path/to/output

# Dry run (analyze without moving files)
python fancam_organizer.py /path/to/videos --dry-run

# Adjust clustering parameters
python fancam_organizer.py /path/to/videos --eps 0.3 --min-samples 2
```

## Architecture

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

## Key Configuration Constants

Located at top of `fancam_organizer.py`:
- `FRAMES_TO_EXTRACT = 20`
- `SKIP_PERCENT = 0.10`
- `EMBEDDING_MODEL = "ArcFace"`
- `DETECTOR_BACKEND = "retinaface"` (alternatives: yolov8, mtcnn, opencv)

## Notes

- First run downloads DeepFace models (~500MB for ArcFace + RetinaFace)
- Lower `--eps` values create stricter groupings, higher values are more permissive
- `--min-samples 1` allows single-video clusters; increase to require minimum group size
