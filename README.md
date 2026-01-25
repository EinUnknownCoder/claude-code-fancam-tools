# K-Pop Fancam Organizer

Automatische Sortierung von K-Pop Fancam-Videos nach dem Haupttänzer mittels Gesichtserkennung und Clustering.

## Features

- Erkennt automatisch den Haupttänzer in Fancam-Videos (größtes Gesicht = nächste Person zur Kamera)
- Gruppiert Videos derselben Person mit DBSCAN-Clustering
- Unterstützt gängige Videoformate (MP4, AVI, MOV, MKV, WebM, FLV, WMV)
- Überspringt Intros/Outros automatisch (erste/letzte 10% des Videos)
- Dry-Run-Modus zum Testen ohne Dateien zu verschieben

## Installation

```bash
git clone https://github.com/EinUnknownCoder/claude-code-fancam-analyser.git
cd claude-code-fancam-analyser
pip install -r requirements.txt
```

**Hinweis:** Beim ersten Lauf werden die DeepFace-Modelle heruntergeladen (~500MB).

## Verwendung

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
