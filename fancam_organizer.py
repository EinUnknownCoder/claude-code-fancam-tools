#!/usr/bin/env python3
"""
K-Pop Fancam Organizer
======================
Automatische Sortierung von Fancam-Videos nach dem Haupttänzer
mittels Gesichtserkennung und Clustering.
"""

import os
import shutil
import argparse
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from deepface import DeepFace
from sklearn.cluster import DBSCAN
from tqdm import tqdm


# Konfiguration
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
FRAMES_TO_EXTRACT = 20
SKIP_PERCENT = 0.10  # Erste und letzte 10% überspringen (Intros/Outros)
EMBEDDING_MODEL = "ArcFace"
DETECTOR_BACKEND = "retinaface"  # Alternativen: "yolov8", "mtcnn", "opencv"


def get_video_files(source_dir: Path) -> list[Path]:
    """Findet alle Videodateien im Quellordner."""
    video_files = []
    for file in source_dir.iterdir():
        if file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS:
            video_files.append(file)
    return sorted(video_files)


def extract_frames(video_path: Path, num_frames: int = FRAMES_TO_EXTRACT) -> list[np.ndarray]:
    """
    Extrahiert Frames aus einem Video in regelmäßigen Abständen.
    Überspringt die ersten und letzten 10% des Videos.
    """
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise ValueError(f"Video konnte nicht geöffnet werden: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames < 10:
        cap.release()
        raise ValueError(f"Video hat zu wenige Frames: {video_path}")

    # Bereich berechnen (10% bis 90%)
    start_frame = int(total_frames * SKIP_PERCENT)
    end_frame = int(total_frames * (1 - SKIP_PERCENT))
    usable_frames = end_frame - start_frame

    # Frame-Indizes für gleichmäßige Verteilung
    if usable_frames < num_frames:
        frame_indices = list(range(start_frame, end_frame))
    else:
        step = usable_frames / num_frames
        frame_indices = [int(start_frame + i * step) for i in range(num_frames)]

    frames = []
    for frame_idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            # BGR zu RGB konvertieren (DeepFace erwartet RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)

    cap.release()
    return frames


def get_largest_face_embedding(frame: np.ndarray) -> Optional[np.ndarray]:
    """
    Findet das größte Gesicht im Frame und gibt dessen Embedding zurück.
    Gibt None zurück, wenn kein Gesicht gefunden wird.
    """
    try:
        # Gesichtserkennung mit Embeddings
        results = DeepFace.represent(
            img_path=frame,
            model_name=EMBEDDING_MODEL,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
            align=True
        )

        if not results:
            return None

        # Bei mehreren Gesichtern: das größte auswählen (größte Bounding Box)
        if len(results) > 1:
            largest_face = max(
                results,
                key=lambda x: x['facial_area']['w'] * x['facial_area']['h']
            )
        else:
            largest_face = results[0]

        return np.array(largest_face['embedding'])

    except Exception:
        # Kein Gesicht gefunden oder anderer Fehler
        return None


def compute_video_fingerprint(video_path: Path) -> Optional[np.ndarray]:
    """
    Erstellt einen Video-Fingerabdruck als Durchschnittsvektor aller Gesichts-Embeddings.
    Gibt None zurück, wenn keine Gesichter gefunden wurden.
    """
    try:
        frames = extract_frames(video_path)
    except ValueError:
        return None

    embeddings = []

    for frame in frames:
        embedding = get_largest_face_embedding(frame)
        if embedding is not None:
            embeddings.append(embedding)

    if not embeddings:
        return None

    # Durchschnittsvektor berechnen
    mean_embedding = np.mean(embeddings, axis=0)

    # Normalisieren für Cosine-Distanz
    norm = np.linalg.norm(mean_embedding)
    if norm > 0:
        mean_embedding = mean_embedding / norm

    return mean_embedding


def cluster_videos(
    video_embeddings: dict[str, np.ndarray],
    eps: float = 0.4,
    min_samples: int = 1
) -> dict[str, int]:
    """
    Gruppiert Videos basierend auf ihren Embeddings mit DBSCAN.
    Gibt ein Dictionary mit Dateiname -> Cluster-ID zurück.
    """
    filenames = list(video_embeddings.keys())
    embeddings = np.array([video_embeddings[f] for f in filenames])

    # DBSCAN mit Cosine-Distanz
    clustering = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric='cosine'
    ).fit(embeddings)

    return {filename: label for filename, label in zip(filenames, clustering.labels_)}


def organize_videos(
    source_dir: Path,
    output_dir: Path,
    cluster_assignments: dict[str, int],
    error_files: list[str]
) -> dict[str, Path]:
    """
    Verschiebt Videos in die entsprechenden Ordner basierend auf Cluster-Zuordnung.
    """
    # Ordner erstellen
    output_dir.mkdir(parents=True, exist_ok=True)

    # Error-Ordner
    error_dir = output_dir / "Error"
    error_dir.mkdir(exist_ok=True)

    # Unknown-Ordner (für Noise-Cluster -1)
    unknown_dir = output_dir / "Unknown"
    unknown_dir.mkdir(exist_ok=True)

    # Dancer-Ordner erstellen
    unique_clusters = set(cluster_assignments.values())
    cluster_dirs = {}

    for cluster_id in unique_clusters:
        if cluster_id == -1:
            cluster_dirs[cluster_id] = unknown_dir
        else:
            dancer_dir = output_dir / f"Dancer_{cluster_id + 1:02d}"
            dancer_dir.mkdir(exist_ok=True)
            cluster_dirs[cluster_id] = dancer_dir

    moved_files = {}

    # Error-Dateien verschieben
    for filename in error_files:
        src = source_dir / filename
        dst = error_dir / filename
        if src.exists():
            shutil.move(str(src), str(dst))
            moved_files[filename] = dst

    # Geclusterte Dateien verschieben
    for filename, cluster_id in cluster_assignments.items():
        src = source_dir / filename
        dst = cluster_dirs[cluster_id] / filename
        if src.exists():
            shutil.move(str(src), str(dst))
            moved_files[filename] = dst

    return moved_files


def main():
    parser = argparse.ArgumentParser(
        description="K-Pop Fancam Organizer - Sortiert Videos nach Haupttänzer"
    )
    parser.add_argument(
        "source",
        type=str,
        help="Quellordner mit den Fancam-Videos"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Zielordner für sortierte Videos (Standard: source/organized)"
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=0.4,
        help="DBSCAN eps-Parameter (Standard: 0.4)"
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=1,
        help="DBSCAN min_samples-Parameter (Standard: 1)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur analysieren, keine Dateien verschieben"
    )

    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    output_dir = Path(args.output).resolve() if args.output else source_dir / "organized"

    if not source_dir.exists():
        print(f"Fehler: Quellordner existiert nicht: {source_dir}")
        return 1

    # Schritt 0: Videos finden
    print(f"\nSuche Videos in: {source_dir}")
    video_files = get_video_files(source_dir)

    if not video_files:
        print("Keine Videodateien gefunden!")
        return 1

    print(f"Gefunden: {len(video_files)} Videos\n")

    # Schritt 1: Feature Extraction
    print("=" * 50)
    print("SCHRITT 1: Video-Fingerabdrücke erstellen")
    print("=" * 50)

    video_embeddings = {}
    error_files = []

    for video_path in tqdm(video_files, desc="Analysiere Videos", unit="video"):
        embedding = compute_video_fingerprint(video_path)

        if embedding is not None:
            video_embeddings[video_path.name] = embedding
        else:
            error_files.append(video_path.name)

    print(f"\nErfolgreich analysiert: {len(video_embeddings)} Videos")
    print(f"Fehlgeschlagen (keine Gesichter): {len(error_files)} Videos")

    if not video_embeddings:
        print("\nKeine Videos konnten analysiert werden!")
        # Nur Error-Dateien verschieben
        if not args.dry_run and error_files:
            organize_videos(source_dir, output_dir, {}, error_files)
        return 1

    # Schritt 2: Clustering
    print("\n" + "=" * 50)
    print("SCHRITT 2: Gruppierung mit DBSCAN")
    print("=" * 50)

    cluster_assignments = cluster_videos(
        video_embeddings,
        eps=args.eps,
        min_samples=args.min_samples
    )

    # Statistiken
    cluster_counts = {}
    for cluster_id in cluster_assignments.values():
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1

    num_dancers = len([c for c in cluster_counts.keys() if c != -1])
    num_unknown = cluster_counts.get(-1, 0)

    print(f"\nGefundene Tänzer (Cluster): {num_dancers}")
    print(f"Unbekannt (Noise): {num_unknown}")
    print(f"Fehler (keine Gesichter): {len(error_files)}")

    print("\nVerteilung:")
    for cluster_id in sorted(cluster_counts.keys()):
        if cluster_id == -1:
            print(f"  Unknown: {cluster_counts[cluster_id]} Videos")
        else:
            print(f"  Dancer_{cluster_id + 1:02d}: {cluster_counts[cluster_id]} Videos")

    if error_files:
        print(f"  Error: {len(error_files)} Videos")

    # Schritt 3: Dateien verschieben
    if args.dry_run:
        print("\n[DRY-RUN] Keine Dateien wurden verschoben.")
    else:
        print("\n" + "=" * 50)
        print("SCHRITT 3: Videos in Ordner verschieben")
        print("=" * 50)

        moved = organize_videos(source_dir, output_dir, cluster_assignments, error_files)
        print(f"\n{len(moved)} Videos wurden nach {output_dir} verschoben.")

    print("\nFertig!")
    return 0


if __name__ == "__main__":
    exit(main())
