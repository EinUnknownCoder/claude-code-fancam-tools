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

# Pfad zur Timestamp-Datei mit Playlist-Sektionen
TIMESTAMPS_FILE = "srt_timestamps/chapters.txt"

# Ausgabepfad für die .srt-Datei
OUTPUT_FILE = "output.srt"

# Ausgabepfad für die YouTube-Timestamp-Datei
TIMESTAMPS_OUTPUT_FILE = "timestamps.txt"

# Gesamtdauer des Videos (HH:MM:SS oder MM:SS)
VIDEO_DURATION = "2:30:07"

# Vorlauf vor der ersten Playlist in Sekunden
INTRO_DURATION = 6

# Übergang zwischen Playlists in Sekunden
TRANSITION_DURATION = 6

# Absolute Startzeiten der Playlists im Video (ab Playlist 2)
# Playlist 1 startet automatisch nach dem Intro
PLAYLIST_STARTS = [
    "29:27",    # Playlist 2
    "58:36",    # Playlist 3
    "1:29:02",  # Playlist 4
    "1:58:18",  # Playlist 5
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


def parse_chapters_file(filepath: Path) -> list[list[dict]]:
    """
    Parst eine Timestamp-Datei mit Playlist-Sektionen.

    Sektionen werden durch '=== PLAYLIST N ===' Header getrennt.

    Returns:
        Liste von Playlists, jede Playlist ist eine Liste von {'start': float, 'title': str}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    playlists = []
    current_entries = None
    playlist_header = re.compile(r'^=+\s*PLAYLIST\s+\d+\s*=+$', re.IGNORECASE)

    for line in lines:
        line = line.strip()

        if playlist_header.match(line):
            current_entries = []
            playlists.append(current_entries)
            continue

        if current_entries is None or not line or line.upper().startswith('START:'):
            continue

        match = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$', line)
        if match:
            time_str, title = match.groups()
            current_entries.append({
                'start': parse_time_to_seconds(time_str),
                'title': clean_title(title),
            })

    return playlists


def generate_subtitles() -> list[dict]:
    """
    Generiert alle Untertitel-Einträge aus den Timestamp-Dateien.

    Returns:
        Liste von {'index': int, 'start': float, 'end': float, 'text': str}
    """
    timestamps_file = Path(TIMESTAMPS_FILE)
    if not timestamps_file.is_file():
        print(f"Fehler: Datei nicht gefunden: {timestamps_file}")
        sys.exit(1)

    playlists = parse_chapters_file(timestamps_file)
    if not playlists:
        print(f"Fehler: Keine Playlists in {timestamps_file} gefunden")
        sys.exit(1)

    print(f"Gefunden: {len(playlists)} Playlists")

    # Validierung
    expected_starts = len(playlists) - 1
    if len(PLAYLIST_STARTS) != expected_starts:
        print(f"Fehler: {len(playlists)} Playlists gefunden, aber {len(PLAYLIST_STARTS)} "
              f"Playlist-Startzeiten angegeben (erwartet: {expected_starts})")
        sys.exit(1)

    # Absolute Startzeiten berechnen
    playlist_abs_starts = [float(INTRO_DURATION)]
    for time_str in PLAYLIST_STARTS:
        playlist_abs_starts.append(parse_time_to_seconds(time_str))

    # Endzeiten berechnen
    video_duration = parse_time_to_seconds(VIDEO_DURATION)
    playlist_ends = []
    for i in range(len(playlists)):
        if i < len(playlists) - 1:
            playlist_ends.append(playlist_abs_starts[i + 1] - TRANSITION_DURATION)
        else:
            playlist_ends.append(video_duration)

    # Untertitel generieren
    subtitles = []
    index = 1

    for pl_idx, entries in enumerate(playlists):
        if not entries:
            print(f"Warnung: Keine Einträge in Playlist {pl_idx + 1}")
            continue

        abs_start = playlist_abs_starts[pl_idx]
        playlist_end = playlist_ends[pl_idx]

        print(f"\nPlaylist {pl_idx + 1}: "
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
                'playlist': pl_idx + 1,
            })
            index += 1

    return subtitles


def seconds_to_hhmmss(seconds: float) -> str:
    """Konvertiert Sekunden in HH:MM:SS Format (ohne Millisekunden)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def write_youtube_timestamps(subtitles: list[dict], output_path: str):
    """Schreibt YouTube-Kommentar-Timestamps (HH:MM:SS TITLE), nach Playlists unterteilt."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("Song Timestamps\n\n")
        current_playlist = None
        for sub in subtitles:
            if sub['playlist'] != current_playlist:
                if current_playlist is not None:
                    f.write("\n")
                f.write(f"Playlist {sub['playlist']}\n")
                current_playlist = sub['playlist']
            f.write(f"{seconds_to_hhmmss(sub['start'])} {sub['text']}\n")


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

    write_youtube_timestamps(subtitles, TIMESTAMPS_OUTPUT_FILE)
    print(f"Gespeichert: {TIMESTAMPS_OUTPUT_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
