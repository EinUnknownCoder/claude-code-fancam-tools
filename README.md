# K-Pop Fancam Tools

Tools zur Verarbeitung von K-Pop Fancam-Videos.

## Features

### Fancam Organizer
- Erkennt automatisch den Haupttänzer in Fancam-Videos (größtes Gesicht = nächste Person zur Kamera)
- Gruppiert Videos derselben Person mit DBSCAN-Clustering
- Unterstützt gängige Videoformate (MP4, AVI, MOV, MKV, WebM, FLV, WMV)
- Überspringt Intros/Outros automatisch (erste/letzte 10% des Videos)
- Dry-Run-Modus zum Testen ohne Dateien zu verschieben

### Fancam Splitter
- Schneidet Videos anhand einer Timestamp-Datei in einzelne Clips
- Volle Audio-Unterstützung durch FFmpeg
- H.264/H.265 Encoding für Smartphone-Kompatibilität
- Unterstützt 4K/60fps mit einstellbarer Qualität

## Installation

```bash
git clone https://github.com/EinUnknownCoder/claude-code-fancam-tools.git
cd claude-code-fancam-tools

# Virtual Environment erstellen
python -m venv .venv

# Aktivieren (Linux/macOS)
source .venv/bin/activate

# Aktivieren (Windows)
.venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

Das Virtual Environment muss vor jeder Nutzung aktiviert werden. Zum Deaktivieren: `deactivate`

**Hinweis:** Beim ersten Lauf werden die DeepFace-Modelle heruntergeladen (~500MB).

### FFmpeg Installation (für Fancam Splitter)

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**macOS (mit Homebrew):**
```bash
brew install ffmpeg
```

**Windows:**
1. Download von https://ffmpeg.org/download.html
2. Entpacken und zum PATH hinzufügen

## Verwendung

### Fancam Organizer

```bash
# Standard: Videos analysieren und in Unterordner sortieren
python fancam_organizer.py /pfad/zu/fancams

# Mit benutzerdefiniertem Ausgabeordner
python fancam_organizer.py /pfad/zu/fancams -o /pfad/zu/sortiert

# Nur analysieren ohne Verschieben (Dry-Run)
python fancam_organizer.py /pfad/zu/fancams --dry-run

# Clustering-Parameter anpassen
python fancam_organizer.py /pfad/zu/fancams --eps 0.3 --min-samples 2
```

### Fancam Splitter

```bash
# Standard: Video in Clips schneiden
python fancam_splitter.py video.mp4 timestamps.txt

# Mit benutzerdefiniertem Ausgabeordner
python fancam_splitter.py video.mp4 timestamps.txt -o /pfad/zu/clips

# Nur Timestamps anzeigen (Dry-Run)
python fancam_splitter.py video.mp4 timestamps.txt --dry-run

# H.265 für kleinere Dateien
python fancam_splitter.py video.mp4 timestamps.txt --codec h265

# Schnelleres Encoding (niedrigere Qualität)
python fancam_splitter.py video.mp4 timestamps.txt --preset fast --crf 23

# Stream-Copy (sehr schnell, keine Neucodierung)
python fancam_splitter.py video.mp4 timestamps.txt --codec copy

# Mit Prefix für Dateinamen
python fancam_splitter.py video.mp4 timestamps.txt --prefix "2024_Concert"
```

#### Timestamp-Datei Format

```
START: 01:30
05:16 NCT DOJAEJUNG - PERFUME (Dancebreak)
09:42 aespa - Supernova
13:15 RIIZE - Boom Boom Bass (Full Cam)
```

- `START: MM:SS` - Optionaler Offset (falls Timestamps aus YouTube-Beschreibung)
- Jede Zeile: `MM:SS Titel` oder `HH:MM:SS Titel`
- Leere Zeilen werden ignoriert

#### Splitter Parameter

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `--codec` | h264 | Video-Codec (h264, h265, copy) |
| `--crf` | 18 | Qualität 0-51, niedriger = besser |
| `--preset` | medium | Encoding-Geschwindigkeit |
| `--dry-run` | - | Nur anzeigen, nicht schneiden |
| `--prefix` | - | Prefix für Dateinamen |
| `-o, --output` | ./clips | Ausgabeverzeichnis |

## Ausgabestruktur

```
organized/
├── Dancer_01/    # Videos von Person 1
├── Dancer_02/    # Videos von Person 2
├── Dancer_03/    # Videos von Person 3
├── Unknown/      # Konnte keiner Gruppe zugeordnet werden
└── Error/        # Keine Gesichter erkannt
```

## Funktionsweise

### Schritt 1: Feature Extraction
1. Extrahiert ~20 Frames pro Video (gleichmäßig verteilt, ohne Intro/Outro)
2. Erkennt Gesichter mit RetinaFace
3. Wählt das größte Gesicht pro Frame (Haupttänzer = nächste Person)
4. Erstellt ArcFace-Embeddings und berechnet den Durchschnittsvektor

### Schritt 2: Clustering
1. Gruppiert alle Video-Vektoren mit DBSCAN (Cosine-Distanz)
2. Erstellt Ordner basierend auf Cluster-IDs
3. Verschiebt Videos in die entsprechenden Ordner

## Parameter

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `--eps` | 0.4 | DBSCAN-Empfindlichkeit. Kleiner = strengere Gruppierung |
| `--min-samples` | 1 | Minimale Videos pro Gruppe. 1 = einzelne Videos erlaubt |
| `--dry-run` | - | Nur analysieren, nichts verschieben |
| `-o, --output` | `source/organized` | Zielordner für sortierte Videos |

## Abhängigkeiten

- Python 3.10+
- DeepFace (Gesichtserkennung & Embeddings)
- OpenCV (Videoverarbeitung)
- scikit-learn (DBSCAN-Clustering)
- NumPy
- tqdm (Fortschrittsanzeige)

## Lizenz

MIT
