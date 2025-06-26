# Minecraft Spigot Test Server Creator

Ein leistungsfähiges Command-Line-Tool zum automatischen Erstellen von Minecraft Spigot Test Servern.  
Es übernimmt das Herunterladen, Bauen und Konfigurieren von Spigot-Servern für verschiedene Minecraft-Versionen.

## Features

- Automatisches Herunterladen und/oder Bauen von Spigot-Server-JARs
- Unterstützung für viele Minecraft-Versionen (inkl. 1.21.x)
- Parallele Downloads und optimierte BuildTools-Nutzung
- Verwaltung mehrerer Server-Instanzen
- Konfigurierbare Optionen (RAM, Port, Gamemode, PvP, Whitelist, MOTD, etc.)
- Automatische Java-Versionserkennung und Warnungen
- Caching für Downloads und BuildTools
- Einfache CLI-Bedienung

## Voraussetzungen

- **Python 3.8+**
- **Java 17+** (für Minecraft 1.17+)
- Internetverbindung (für Downloads)

## Installation

1. Repository klonen:
   ```sh
   git clone <repository-url>
   cd python-server-bau
   ```

2. Abhängigkeiten installieren:
   ```sh
   pip install -r requirements.txt
   ```

## Nutzung

### Server erstellen

```sh
python spigot_creator.py create <Servername> <Version> [Optionen]
```

Beispiel:
```sh
python spigot_creator.py create MyServer 1.21.4 -p 25566 -m 4G --gamemode survival --difficulty normal
```

### Server auflisten

```sh
python spigot_creator.py list
```

### Server entfernen

```sh
python spigot_creator.py remove <Servername>
```

### Verfügbare Versionen anzeigen

```sh
python spigot_creator.py versions
```

### Konfiguration anzeigen oder ändern

```sh
python spigot_creator.py config show
python spigot_creator.py config set <key> <value>
```

### Hilfe anzeigen

```sh
python spigot_creator.py --help
```

## Beispiel-Konfiguration

Die Konfiguration wird automatisch unter `~/.minecraft_server_creator/config.json` angelegt.  
Beispiel-Inhalt:
```json
{
  "java_path": "java",
  "default_memory": "2G",
  "default_port": 25565,
  "buildtools_update_interval": 86400,
  "use_prebuilt_spigot": true,
  "parallel_downloads": true,
  "skip_java_check": false,
  "quick_mode": false
}
```

## Lizenz

MIT License – siehe [LICENSE](LICENSE).