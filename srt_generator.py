#!/usr/bin/env python3
"""
SRT Subtitle Generator für Random Dance Game Videos
====================================================
Generiert eine .srt-Untertiteldatei aus Timestamp-Dateien,
die den aktuellen Song-Titel und Artist anzeigt.
"""

import re
import sys
from pathlib import Path

# ===== KONFIGURATION =====

# Ordner mit den Timestamp-Dateien (1.txt, 2.txt, ...)
TIMESTAMPS_DIR = "srt_timestamps"

# Ausgabepfad für die .srt-Datei
OUTPUT_FILE = "output.srt"

# Gesamtdauer des Videos (HH:MM:SS oder MM:SS)
VIDEO_DURATION = "2:34:51"

# Vorlauf vor der ersten Playlist in Sekunden
INTRO_DURATION = 6

# Übergang zwischen Playlists in Sekunden
TRANSITION_DURATION = 6

# Absolute Startzeiten der Playlists im Video (ab Playlist 2)
# Playlist 1 startet automatisch nach dem Intro
PLAYLIST_STARTS = [
    "29:37",    # Playlist 2
    "59:04",    # Playlist 3
    "1:29:56",  # Playlist 4
    "1:59:23",  # Playlist 5
]

# ===== ENDE KONFIGURATION =====


def parse_time_to_seconds(time_str: str) -> float:
    """Konvertiert MM:SS oder HH:MM:SS in Sekunden."""
    parts = time_str.strip().split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    else:
        raise ValueError(f"Ungültiges Zeitformat: {time_str}")


def seconds_to_srt_time(seconds: float) -> str:
    """Konvertiert Sekunden in SRT-Zeitformat HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def clean_title(title: str) -> str:
    """Entfernt die letzte Klammer-Gruppe (Section-Info und Usernames)."""
    return re.sub(r'\s*\([^)]*\)\s*$', '', title).strip()


def parse_timestamp_file(filepath: Path) -> list[dict]:
    """
    Parst eine Timestamp-Datei und gibt Song-Einträge zurück.

    Returns:
        Liste von {'start': float, 'title': str}
    """
    entries = []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.upper().startswith('START:'):
            continue

        match = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$', line)
        if match:
            time_str, title = match.groups()
            entries.append({
                'start': parse_time_to_seconds(time_str),
                'title': clean_title(title),
            })

    return entries


def generate_subtitles() -> list[dict]:
    """
    Generiert alle Untertitel-Einträge aus den Timestamp-Dateien.

    Returns:
        Liste von {'index': int, 'start': float, 'end': float, 'text': str}
    """
    timestamps_dir = Path(TIMESTAMPS_DIR)
    if not timestamps_dir.is_dir():
        print(f"Fehler: Ordner nicht gefunden: {timestamps_dir}")
        sys.exit(1)

    # Timestamp-Dateien numerisch sortiert finden
    txt_files = sorted(timestamps_dir.glob("*.txt"), key=lambda p: int(p.stem))
    if not txt_files:
        print(f"Fehler: Keine .txt-Dateien in {timestamps_dir} gefunden")
        sys.exit(1)

    print(f"Gefunden: {len(txt_files)} Timestamp-Dateien")

    # Validierung
    expected_starts = len(txt_files) - 1
    if len(PLAYLIST_STARTS) != expected_starts:
        print(f"Fehler: {len(txt_files)} Dateien gefunden, aber {len(PLAYLIST_STARTS)} "
              f"Playlist-Startzeiten angegeben (erwartet: {expected_starts})")
        sys.exit(1)

    # Absolute Startzeiten berechnen
    playlist_abs_starts = [float(INTRO_DURATION)]
    for time_str in PLAYLIST_STARTS:
        playlist_abs_starts.append(parse_time_to_seconds(time_str))

    # Endzeiten berechnen
    video_duration = parse_time_to_seconds(VIDEO_DURATION)
    playlist_ends = []
    for i in range(len(txt_files)):
        if i < len(txt_files) - 1:
            playlist_ends.append(playlist_abs_starts[i + 1] - TRANSITION_DURATION)
        else:
            playlist_ends.append(video_duration)

    # Untertitel generieren
    subtitles = []
    index = 1

    for file_idx, txt_file in enumerate(txt_files):
        entries = parse_timestamp_file(txt_file)
        if not entries:
            print(f"Warnung: Keine Einträge in {txt_file.name}")
            continue

        abs_start = playlist_abs_starts[file_idx]
        playlist_end = playlist_ends[file_idx]

        print(f"\nPlaylist {file_idx + 1} ({txt_file.name}): "
              f"{len(entries)} Songs, "
              f"Start {seconds_to_srt_time(abs_start)}, "
              f"Ende {seconds_to_srt_time(playlist_end)}")

        for i, entry in enumerate(entries):
            sub_start = abs_start + entry['start']

            if i < len(entries) - 1:
                sub_end = abs_start + entries[i + 1]['start']
            else:
                sub_end = playlist_end

            subtitles.append({
                'index': index,
                'start': sub_start,
                'end': sub_end,
                'text': entry['title'],
            })
            index += 1

    return subtitles


def write_srt(subtitles: list[dict], output_path: str):
    """Schreibt die Untertitel in eine .srt-Datei."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for sub in subtitles:
            f.write(f"{sub['index']}\n")
            f.write(f"{seconds_to_srt_time(sub['start'])} --> {seconds_to_srt_time(sub['end'])}\n")
            f.write(f"{sub['text']}\n")
            f.write("\n")


def main():
    print("SRT Subtitle Generator für Random Dance Game Videos")
    print("=" * 55)

    subtitles = generate_subtitles()

    print(f"\n{'=' * 55}")
    print(f"Gesamt: {len(subtitles)} Untertitel generiert")

    write_srt(subtitles, OUTPUT_FILE)
    print(f"Gespeichert: {OUTPUT_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
