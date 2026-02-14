#!/usr/bin/env python3
"""
Fancam Splitter
===============
Schneidet ein Video anhand einer Timestamp-Datei in einzelne Clips.
Nutzt FFmpeg für volle Audio-Unterstützung und Smartphone-Kompatibilität.
"""

import argparse
import re
import shlex
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

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL)

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


def process_video(
    video_path: Path,
    timestamp_path: Path,
    output_dir: Path,
    codec: str = 'h264',
    crf: int = 18,
    preset: str = 'medium',
    dry_run: bool = False,
    prefix: str = ''
) -> tuple[int, int, int]:
    """
    Verarbeitet ein einzelnes Video anhand einer Timestamp-Datei.

    Returns:
        Tupel (success_count, skipped_count, error_count)
    """
    # Video-Dauer ermitteln
    print(f"\nVideo: {video_path.name}")
    try:
        video_duration = get_video_duration(video_path)
        print(f"Dauer: {format_time(video_duration)}")
    except RuntimeError as e:
        print(f"Fehler: {e}")
        return (0, 0, 1)

    # Timestamps parsen
    print(f"Timestamp-Datei: {timestamp_path.name}")
    try:
        clips = parse_timestamp_file(timestamp_path)
    except Exception as e:
        print(f"Fehler beim Parsen der Timestamps: {e}")
        return (0, 0, 1)

    if not clips:
        print("Keine Timestamps gefunden!")
        return (0, 0, 1)

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

    if dry_run:
        print("\n[DRY-RUN] Keine Clips wurden erstellt.")
        return (0, 0, 0)

    # Ausgabeverzeichnis erstellen
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nAusgabe: {output_dir}\n")

    # Clips extrahieren
    success_count = 0
    error_count = 0
    skipped_count = 0

    for i, clip in enumerate(clips, 1):
        start = clip['start']
        end = clip.get('end', video_duration)
        duration = end - start

        # Dateiname generieren
        title_clean = sanitize_filename(clip['title'])
        pfx = f"{prefix}_" if prefix else ""
        filename = f"{pfx}{i:02d}_{title_clean}.mp4"
        output_path = output_dir / filename

        # Bereits vorhandene Clips überspringen
        if output_path.exists():
            print(f"[{i}/{len(clips)}] {filename} — ÜBERSPRUNGEN (existiert bereits)")
            skipped_count += 1
            continue

        print(f"\n[{i}/{len(clips)}] {filename}", flush=True)

        success = split_video(
            input_path=video_path,
            output_path=output_path,
            start=start,
            duration=duration,
            codec=codec,
            crf=crf,
            preset=preset
        )

        if success:
            print("OK")
            success_count += 1
        else:
            print("FEHLER")
            error_count += 1

    return (success_count, skipped_count, error_count)


def parse_batch_file(filepath: Path) -> list[tuple[Path, Path]]:
    """
    Parst eine Batch-Datei mit Video- und Timestamp-Paaren.

    Format:
        # Kommentar
        video1.mp4 | timestamps1.txt
        video2.mp4 | timestamps2.txt

    Pfade werden relativ zur Batch-Datei aufgelöst.

    Returns:
        Liste von (video_path, timestamp_path) Tupeln
    """
    batch_dir = filepath.parent
    pairs = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Leere Zeilen und Kommentare überspringen
            if not line or line.startswith('#'):
                continue

            if '|' not in line:
                print(f"Warnung: Zeile übersprungen (kein | Trennzeichen): {line}")
                continue

            parts = line.split('|', 1)
            video_str = parts[0].strip()
            timestamp_str = parts[1].strip()

            video_path = Path(video_str)
            timestamp_path = Path(timestamp_str)

            # Relative Pfade zur Batch-Datei auflösen
            if not video_path.is_absolute():
                video_path = (batch_dir / video_path).resolve()
            if not timestamp_path.is_absolute():
                timestamp_path = (batch_dir / timestamp_path).resolve()

            pairs.append((video_path, timestamp_path))

    return pairs


def main():
    parser = argparse.ArgumentParser(
        description="Fancam Splitter - Schneidet Videos anhand einer Timestamp-Datei"
    )
    parser.add_argument(
        "video",
        type=str,
        nargs='?',
        help="Pfad zur Videodatei"
    )
    parser.add_argument(
        "timestamps",
        type=str,
        nargs='?',
        help="Pfad zur Timestamp-Datei"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="Batch-Datei mit Video|Timestamp-Paaren (eine pro Zeile)"
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
    parser.add_argument(
        "--organize",
        action="store_true",
        help="Nach dem Splitten den Fancam Organizer auf dem Clips-Ordner starten"
    )
    parser.add_argument(
        "--organize-args",
        type=str,
        default="",
        help="Zusätzliche Argumente für den Organizer (z.B. \"--eps 0.3 --min-samples 2\")"
    )

    args = parser.parse_args()

    # Entweder --batch oder video + timestamps
    if args.batch:
        batch_path = Path(args.batch).resolve()
        if not batch_path.exists():
            print(f"Fehler: Batch-Datei nicht gefunden: {batch_path}")
            return 1
    elif args.video and args.timestamps:
        pass  # Einzelmodus
    else:
        parser.error("Entweder --batch DATEI oder VIDEO TIMESTAMPS angeben")

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

    output_dir = Path(args.output).resolve()

    # Batch-Modus
    if args.batch:
        pairs = parse_batch_file(batch_path)
        if not pairs:
            print("Keine Video-Timestamp-Paare in der Batch-Datei gefunden!")
            return 1

        print(f"Batch-Modus: {len(pairs)} Videos")
        print("=" * 60)

        total_success = 0
        total_skipped = 0
        total_errors = 0

        for idx, (video_path, timestamp_path) in enumerate(pairs, 1):
            print(f"\n{'#' * 60}")
            print(f"# Video {idx}/{len(pairs)}: {video_path.name}")
            print(f"{'#' * 60}")

            if not video_path.exists():
                print(f"Fehler: Video nicht gefunden: {video_path}")
                total_errors += 1
                continue

            if not timestamp_path.exists():
                print(f"Fehler: Timestamp-Datei nicht gefunden: {timestamp_path}")
                total_errors += 1
                continue

            success, skipped, errors = process_video(
                video_path=video_path,
                timestamp_path=timestamp_path,
                output_dir=output_dir,
                codec=args.codec,
                crf=args.crf,
                preset=args.preset,
                dry_run=args.dry_run,
                prefix=args.prefix
            )

            total_success += success
            total_skipped += skipped
            total_errors += errors

        # Gesamtzusammenfassung
        print(f"\n{'=' * 60}")
        print(f"GESAMT: {len(pairs)} Videos verarbeitet")
        parts = []
        if total_success > 0:
            parts.append(f"{total_success} Clips erstellt")
        if total_skipped > 0:
            parts.append(f"{total_skipped} übersprungen")
        if total_errors > 0:
            parts.append(f"{total_errors} Fehler")
        print(f"Ergebnis: {', '.join(parts)}.")
        print("=" * 60)

        split_ok = total_errors == 0

    else:
        # Einzelmodus
        video_path = Path(args.video).resolve()
        timestamp_path = Path(args.timestamps).resolve()

        if not video_path.exists():
            print(f"Fehler: Video nicht gefunden: {video_path}")
            return 1

        if not timestamp_path.exists():
            print(f"Fehler: Timestamp-Datei nicht gefunden: {timestamp_path}")
            return 1

        success, skipped, errors = process_video(
            video_path=video_path,
            timestamp_path=timestamp_path,
            output_dir=output_dir,
            codec=args.codec,
            crf=args.crf,
            preset=args.preset,
            dry_run=args.dry_run,
            prefix=args.prefix
        )

        # Zusammenfassung
        parts = []
        if success > 0:
            parts.append(f"{success} Clips erstellt")
        if skipped > 0:
            parts.append(f"{skipped} übersprungen")
        if errors > 0:
            parts.append(f"{errors} Fehler")
        print(f"\nFertig! {', '.join(parts)}.")

        split_ok = errors == 0

    # Organizer starten
    if args.organize and not args.dry_run:
        organizer_script = Path(__file__).resolve().parent / 'fancam_organizer.py'

        if not organizer_script.exists():
            print(f"\nFehler: Organizer nicht gefunden: {organizer_script}")
            return 1

        print(f"\n{'#' * 60}")
        print("# Starte Fancam Organizer...")
        print(f"{'#' * 60}")

        cmd = [sys.executable, str(organizer_script), str(output_dir)]
        if args.organize_args:
            cmd.extend(shlex.split(args.organize_args))

        result = subprocess.run(cmd)

        if result.returncode != 0:
            print("\nOrganizer mit Fehlern beendet.")
            return 1

    return 0 if split_ok else 1


if __name__ == "__main__":
    sys.exit(main())
