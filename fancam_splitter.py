#!/usr/bin/env python3
"""
Fancam Splitter
===============
Schneidet ein Video anhand einer Timestamp-Datei in einzelne Clips.
Nutzt FFmpeg für volle Audio-Unterstützung und Smartphone-Kompatibilität.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def parse_time_to_seconds(time_str: str) -> float:
    """
    Konvertiert einen Timestamp-String (MM:SS oder HH:MM:SS) in Sekunden.

    Args:
        time_str: Zeit im Format "MM:SS" oder "HH:MM:SS"

    Returns:
        Zeit in Sekunden als float
    """
    parts = time_str.strip().split(':')

    if len(parts) == 2:
        # MM:SS Format
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    elif len(parts) == 3:
        # HH:MM:SS Format
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    else:
        raise ValueError(f"Ungültiges Zeitformat: {time_str}")


def parse_timestamp_file(filepath: Path) -> list[dict]:
    """
    Parst eine Timestamp-Datei und gibt eine Liste von Clips zurück.

    Format der Datei:
        START: 01:30
        05:16 NCT DOJAEJUNG - PERFUME
        09:42 aespa - Supernova

    Args:
        filepath: Pfad zur Timestamp-Datei

    Returns:
        Liste von Dictionaries mit 'start', 'title' und optional 'end'
    """
    clips = []
    start_offset = 0.0

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

        # Leere Zeilen überspringen
        if not line:
            continue

        # START: Offset parsen
        if line.upper().startswith('START:'):
            time_str = line[6:].strip()
            start_offset = parse_time_to_seconds(time_str)
            continue

        # Timestamp-Zeile parsen: "MM:SS Titel" oder "HH:MM:SS Titel"
        match = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$', line)
        if match:
            time_str, title = match.groups()
            timestamp = parse_time_to_seconds(time_str)
            clips.append({
                'start': timestamp,
                'title': title.strip()
            })

    # Start-Offset anwenden und End-Zeiten berechnen
    for i, clip in enumerate(clips):
        clip['start'] = clip['start'] - start_offset

        # End-Zeit ist der Start des nächsten Clips
        if i < len(clips) - 1:
            clip['end'] = clips[i + 1]['start'] - start_offset

    return clips


def sanitize_filename(title: str) -> str:
    """
    Entfernt ungültige Zeichen aus einem Dateinamen.

    Args:
        title: Der zu bereinigende Titel

    Returns:
        Bereinigter Dateiname
    """
    # Ersetze ungültige Zeichen durch Unterstriche
    invalid_chars = r'<>:"/\|?*'
    result = title
    for char in invalid_chars:
        result = result.replace(char, '_')

    # Mehrfache Unterstriche zu einem reduzieren
    result = re.sub(r'_+', '_', result)

    # Leerzeichen durch Unterstriche ersetzen
    result = result.replace(' ', '_')

    # Führende/trailing Unterstriche entfernen
    result = result.strip('_')

    # Kommas entfernen (häufig in Timestamps)
    result = result.replace(',', '')

    return result


def get_video_duration(video_path: Path) -> float:
    """
    Ermittelt die Dauer eines Videos mittels ffprobe.

    Args:
        video_path: Pfad zur Videodatei

    Returns:
        Dauer in Sekunden
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe Fehler: {result.stderr}")

    return float(result.stdout.strip())


def split_video(
    input_path: Path,
    output_path: Path,
    start: float,
    duration: float,
    codec: str = 'h264',
    crf: int = 18,
    preset: str = 'medium'
) -> bool:
    """
    Extrahiert einen Clip aus einem Video mittels FFmpeg.

    Args:
        input_path: Pfad zum Quellvideo
        output_path: Pfad für den extrahierten Clip
        start: Startzeit in Sekunden
        duration: Dauer in Sekunden
        codec: Video-Codec (h264, h265, copy)
        crf: Qualität (0-51, niedriger = besser)
        preset: Encoding-Geschwindigkeit

    Returns:
        True bei Erfolg, False bei Fehler
    """
    cmd = [
        'ffmpeg',
        '-y',  # Überschreiben ohne Nachfrage
        '-ss', str(start),
        '-i', str(input_path),
        '-t', str(duration),
    ]

    if codec == 'copy':
        # Stream-Copy (schnell, keine Re-Encoding)
        cmd.extend(['-c', 'copy'])
    else:
        # Video-Codec
        if codec == 'h264':
            cmd.extend([
                '-c:v', 'libx264',
                '-profile:v', 'high',
                '-level', '5.1',
            ])
        elif codec == 'h265':
            cmd.extend([
                '-c:v', 'libx265',
                '-tag:v', 'hvc1',  # Für Apple-Kompatibilität
            ])

        cmd.extend([
            '-crf', str(crf),
            '-preset', preset,
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
        ])

    cmd.append(str(output_path))

    result = subprocess.run(cmd, capture_output=True, text=True)

    return result.returncode == 0


def format_time(seconds: float) -> str:
    """Formatiert Sekunden als MM:SS oder HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def main():
    parser = argparse.ArgumentParser(
        description="Fancam Splitter - Schneidet Videos anhand einer Timestamp-Datei"
    )
    parser.add_argument(
        "video",
        type=str,
        help="Pfad zur Videodatei"
    )
    parser.add_argument(
        "timestamps",
        type=str,
        help="Pfad zur Timestamp-Datei"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="./clips",
        help="Ausgabeverzeichnis (Standard: ./clips)"
    )
    parser.add_argument(
        "--codec",
        type=str,
        choices=['h264', 'h265', 'copy'],
        default='h264',
        help="Video-Codec (Standard: h264)"
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=18,
        help="Qualität 0-51, niedriger = besser (Standard: 18)"
    )
    parser.add_argument(
        "--preset",
        type=str,
        default='medium',
        choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast',
                 'medium', 'slow', 'slower', 'veryslow'],
        help="Encoding-Geschwindigkeit (Standard: medium)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur anzeigen, nicht schneiden"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Prefix für Dateinamen"
    )

    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    timestamp_path = Path(args.timestamps).resolve()
    output_dir = Path(args.output).resolve()

    # Eingabedateien prüfen
    if not video_path.exists():
        print(f"Fehler: Video nicht gefunden: {video_path}")
        return 1

    if not timestamp_path.exists():
        print(f"Fehler: Timestamp-Datei nicht gefunden: {timestamp_path}")
        return 1

    # FFmpeg Verfügbarkeit prüfen
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Fehler: FFmpeg nicht gefunden. Bitte installieren:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Windows: https://ffmpeg.org/download.html")
        return 1

    # Video-Dauer ermitteln
    print(f"\nVideo: {video_path.name}")
    try:
        video_duration = get_video_duration(video_path)
        print(f"Dauer: {format_time(video_duration)}")
    except RuntimeError as e:
        print(f"Fehler: {e}")
        return 1

    # Timestamps parsen
    print(f"\nTimestamp-Datei: {timestamp_path.name}")
    try:
        clips = parse_timestamp_file(timestamp_path)
    except Exception as e:
        print(f"Fehler beim Parsen der Timestamps: {e}")
        return 1

    if not clips:
        print("Keine Timestamps gefunden!")
        return 1

    # Letzten Clip mit Video-Ende abschließen
    if 'end' not in clips[-1]:
        clips[-1]['end'] = video_duration - clips[0]['start']

    print(f"Gefunden: {len(clips)} Clips\n")

    # Clips anzeigen
    print("=" * 60)
    print(f"{'Nr':<4} {'Start':<10} {'Ende':<10} {'Dauer':<8} Titel")
    print("=" * 60)

    for i, clip in enumerate(clips, 1):
        start = clip['start']
        end = clip.get('end', video_duration)
        duration = end - start

        print(f"{i:02d}   {format_time(start):<10} {format_time(end):<10} "
              f"{format_time(duration):<8} {clip['title']}")

    print("=" * 60)

    if args.dry_run:
        print("\n[DRY-RUN] Keine Clips wurden erstellt.")
        return 0

    # Ausgabeverzeichnis erstellen
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nAusgabe: {output_dir}\n")

    # Clips extrahieren
    success_count = 0
    error_count = 0

    for i, clip in enumerate(clips, 1):
        start = clip['start']
        end = clip.get('end', video_duration)
        duration = end - start

        # Dateiname generieren
        title_clean = sanitize_filename(clip['title'])
        prefix = f"{args.prefix}_" if args.prefix else ""
        filename = f"{prefix}{i:02d}_{title_clean}.mp4"
        output_path = output_dir / filename

        print(f"[{i}/{len(clips)}] {filename}...", end=" ", flush=True)

        success = split_video(
            input_path=video_path,
            output_path=output_path,
            start=start,
            duration=duration,
            codec=args.codec,
            crf=args.crf,
            preset=args.preset
        )

        if success:
            print("OK")
            success_count += 1
        else:
            print("FEHLER")
            error_count += 1

    # Zusammenfassung
    print(f"\nFertig! {success_count} Clips erstellt", end="")
    if error_count > 0:
        print(f", {error_count} Fehler")
    else:
        print()

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
