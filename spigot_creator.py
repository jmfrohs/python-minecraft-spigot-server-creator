# MIT License
#
# Copyright (c) 2025 jmfrohs
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

#!/usr/bin/env python3
"""
Minecraft Spigot Test Server Creator - Optimized Version
Ein Command-Line-Tool zum automatischen Erstellen von Minecraft Spigot Test Servern
"""

import sys
import argparse
import subprocess
import requests
import shutil
import tempfile
import json
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Optional
import time
import os


class SpigotServerCreator:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.servers_dir = self.base_dir / "servers" 
        self.cache_dir = Path.home() / ".minecraft_server_creator" / "cache"
        self.config_file = Path.home() / ".minecraft_server_creator" / "config.json"
        
        # Erstelle notwendige Verzeichnisse
        self.servers_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Lade oder erstelle Konfiguration
        self.config = self.load_config()
        
        # Cache für verfügbare Versionen
        self._versions_cache = None
        self._versions_cache_time = 0
    
    def load_config(self) -> Dict:
        """Lädt die Konfiguration oder erstellt eine Standard-Konfiguration"""
        default_config = {
            "java_path": "java",
            "default_memory": "2G",
            "default_port": 25565,
            "buildtools_update_interval": 86400,  # 24 Stunden in Sekunden
            "use_prebuilt_spigot": True,  # Verwende vorgefertigte Spigot JARs wenn möglich
            "parallel_downloads": True,   # Parallele Downloads aktivieren
            "skip_java_check": False,     # Java-Check überspringen für Geschwindigkeit
            "quick_mode": False           # Schnellmodus für häufige Entwicklung
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge mit default_config für fehlende Werte
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"Warnung: Konnte Konfiguration nicht laden: {e}")
        
        # Erstelle Standard-Konfiguration
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def check_java_version(self) -> bool:
        """Überprüft ob Java verfügbar ist und eine geeignete Version hat"""
        if self.config.get("skip_java_check", False):
            print("Java-Check übersprungen (skip_java_check=true)")
            return True
            
        try:
            result = subprocess.run(
                [self.config["java_path"], "-version"],
                capture_output=True,
                text=True,
                timeout=5  # Timeout hinzugefügt
            )

            output = result.stderr + result.stdout
            if result.returncode != 0 or "version" not in output.lower():
                print(f"Fehler: Java nicht gefunden unter '{self.config['java_path']}'")
                return False

            # Java Version aus stderr extrahieren (Java gibt Version Info dort aus)
            version_line = output.split('\n')[0]
            if not self.config.get("quick_mode", False):
                print(f"Java gefunden: {version_line}")

            # Prüfe auf Java 17+ für neuere Minecraft Versionen
            if any(f"{v}." in version_line for v in range(17, 22)):
                return True
            elif "1.8" in version_line:
                if not self.config.get("quick_mode", False):
                    print("Warnung: Java 8 erkannt. Für Minecraft 1.17+ wird Java 17+ empfohlen.")
                return True
            else:
                if not self.config.get("quick_mode", False):
                    print("Warnung: Unbekannte Java Version. Fortfahren...")
                return True

        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("Fehler: Java nicht gefunden oder Timeout. Bitte installieren Sie Java oder setzen Sie skip_java_check=true.")
            return False
        except Exception as e:
            print(f"Fehler beim Überprüfen der Java Version: {e}")
            return False
    
    def get_available_versions(self) -> List[str]:
        """Holt verfügbare Spigot Versionen mit Caching"""
        # Cache für 1 Stunde
        if (self._versions_cache and 
            time.time() - self._versions_cache_time < 3600):
            return self._versions_cache
        
        try:
            # Erweiterte Versionsliste mit neueren Versionen
            versions = [
                "1.21.4", "1.21.3", "1.21.2", "1.21.1", "1.21",
                "1.20.6", "1.20.5", "1.20.4", "1.20.3", "1.20.2", "1.20.1", "1.20",
                "1.19.4", "1.19.3", "1.19.2", "1.19.1", "1.19",
                "1.18.2", "1.18.1", "1.18",
                "1.17.1", "1.17",
                "1.16.5", "1.16.4", "1.16.3", "1.16.2", "1.16.1",
                "1.15.2", "1.15.1", "1.15",
                "1.14.4", "1.14.3", "1.14.2", "1.14.1", "1.14",
                "1.13.2", "1.13.1", "1.13",
                "1.12.2", "1.12.1", "1.12",
                "1.11.2", "1.11.1", "1.11",
                "1.10.2", "1.10",
                "1.9.4", "1.9.2", "1.9",
                "1.8.8"
            ]
            
            self._versions_cache = versions
            self._versions_cache_time = time.time()
            return versions
        except Exception as e:
            print(f"Warnung: Konnte Versionen nicht abrufen: {e}")
            return ["1.21.4", "1.20.4", "1.19.4", "1.18.2", "1.17.1", "1.16.5"]
    
    def should_update_buildtools(self) -> bool:
        """Prüft ob BuildTools aktualisiert werden sollte"""
        buildtools_path = self.cache_dir / "BuildTools.jar"
        
        if not buildtools_path.exists():
            return True
        
        # Im Quick-Mode weniger häufig aktualisieren
        if self.config.get("quick_mode", False):
            update_interval = self.config["buildtools_update_interval"] * 7  # 7x länger
        else:
            update_interval = self.config["buildtools_update_interval"]
        
        # Prüfe Alter der Datei
        file_age = time.time() - buildtools_path.stat().st_mtime
        return file_age > update_interval
    
    def download_file_parallel(self, url: str, output_path: Path, description: str = "Download") -> None:
        """Optimierter Download mit Progress-Anzeige"""
        try:
            # Verwende Session für bessere Performance
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Größere Chunk-Size für bessere Performance
            chunk_size = 32768  # 32KB statt 8KB
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0 and not self.config.get("quick_mode", False):
                            percent = (downloaded / total_size) * 100
                            print(f"\r{description}: {percent:.1f}%", end='', flush=True)
            
            if not self.config.get("quick_mode", False):
                print()  # Neue Zeile nach Progress
                
        except Exception as e:
            raise Exception(f"Fehler beim Herunterladen: {e}")
    
    def try_download_prebuilt_spigot(self, version: str) -> Optional[Path]:
        """Versucht eine vorgefertigte Spigot JAR herunterzuladen"""
        if not self.config.get("use_prebuilt_spigot", True):
            return None
        
        spigot_jar = self.cache_dir / f"spigot-{version}.jar"
        
        # Bekannte Download-URLs für beliebte Versionen
        prebuilt_urls = {
            "1.21.4": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            "1.21.3": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            "1.20.4": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            "1.19.4": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            "1.18.2": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
        }
        
        # Alternative URLs
        alternative_urls = [
            f"https://download.getbukkit.org/spigot/spigot-{version}.jar",
            f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            f"https://hub.spigotmc.org/stash/projects/SPIGOT/repos/spigot/browse/work/decompile-{version}/spigot-{version}.jar?raw"
        ]
        
        all_urls = [prebuilt_urls.get(version)] + alternative_urls
        all_urls = [url for url in all_urls if url]  # Filter None values
        
        for url in all_urls:
            try:
                print(f"Versuche vorgefertigte Spigot JAR für {version} herunterzuladen...")
                self.download_file_parallel(url, spigot_jar, f"Spigot {version}")
                
                # Verifiziere dass es eine gültige JAR-Datei ist
                if spigot_jar.stat().st_size > 1024 * 1024:  # Mindestens 1MB
                    print(f"Vorgefertigte Spigot JAR für {version} erfolgreich heruntergeladen!")
                    return spigot_jar
                else:
                    spigot_jar.unlink()  # Lösche ungültige Datei
                    
            except Exception as e:  # noqa: F841
                if spigot_jar.exists():
                    spigot_jar.unlink()
                continue
        
        return None
    
    def download_buildtools(self, force_update: bool = False) -> Path:
        """Lädt BuildTools.jar herunter falls nicht vorhanden oder veraltet"""
        buildtools_path = self.cache_dir / "BuildTools.jar"
        
        if buildtools_path.exists() and not force_update and not self.should_update_buildtools():
            if not self.config.get("quick_mode", False):
                print("BuildTools.jar bereits vorhanden und aktuell.")
            return buildtools_path
        
        print("Lade BuildTools.jar herunter...")
        url = "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"
        
        try:
            # Backup der alten Version falls vorhanden
            if buildtools_path.exists():
                backup_path = buildtools_path.with_suffix('.jar.backup')
                shutil.move(buildtools_path, backup_path)
            
            self.download_file_parallel(url, buildtools_path, "BuildTools")
            
            if not self.config.get("quick_mode", False):
                print("BuildTools.jar erfolgreich heruntergeladen.")
            return buildtools_path
            
        except Exception as e:
            # Versuche Backup wiederherzustellen
            backup_path = buildtools_path.with_suffix('.jar.backup')
            if backup_path.exists():
                shutil.move(backup_path, buildtools_path)
                print("Backup von BuildTools.jar wiederhergestellt.")
                return buildtools_path
            
            raise Exception(f"Fehler beim Herunterladen von BuildTools.jar: {e}")
    
    def build_spigot_optimized(self, version: str, force_rebuild: bool = False) -> Path:
        """Optimierte Spigot-Erstellung mit verbesserter Performance"""
        spigot_jar = self.cache_dir / f"spigot-{version}.jar"
        
        if spigot_jar.exists() and not force_rebuild:
            if not self.config.get("quick_mode", False):
                print(f"Spigot {version} bereits erstellt.")
            return spigot_jar
        
        # Versuche zuerst vorgefertigte JAR herunterzuladen
        prebuilt_jar = self.try_download_prebuilt_spigot(version)
        if prebuilt_jar:
            return prebuilt_jar
        
        # Fallback: Erstelle mit BuildTools
        print(f"Erstelle Spigot {version} mit BuildTools...")
        
        if not self.check_java_version():
            raise Exception("Java-Überprüfung fehlgeschlagen")
        
        buildtools_path = self.download_buildtools()
        
        # Temporäres Build-Verzeichnis
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Kopiere BuildTools in temp Verzeichnis
            temp_buildtools = temp_path / "BuildTools.jar"
            shutil.copy2(buildtools_path, temp_buildtools)
            
            # Optimierte BuildTools-Argumente
            cmd = [
                self.config["java_path"], 
                "-Xmx2G",  # Mehr RAM für BuildTools
                "-jar", str(temp_buildtools),
                "--rev", version,
                "--output-dir", str(temp_path),
                "--compile", "spigot",  # Nur Spigot kompilieren
                "--disable-certificate-check"  # Zertifikatsprüfung deaktivieren
            ]
            
            # Zusätzliche Optimierungen für neuere Versionen
            if version.startswith(("1.19", "1.20", "1.21")):
                cmd.extend(["--disable-java-check"])
            
            try:
                if not self.config.get("quick_mode", False):
                    print(f"Führe aus: {' '.join(cmd)}")
                    print("Dies kann einige Minuten dauern...")
                
                # Verwende optimierte Umgebungsvariablen
                env = dict(os.environ)
                env.update({
                    "MAVEN_OPTS": "-Xmx2G -XX:+UseG1GC",
                    "JAVA_TOOL_OPTIONS": "-Xmx2G"
                })
                
                if self.config.get("quick_mode", False):
                    # Im Quick-Mode: Stille Ausführung
                    result = subprocess.run(
                        cmd,
                        cwd=temp_path,
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=1800  # 30 Minuten Timeout
                    )
                    
                    if result.returncode != 0:
                        print("BuildTools Fehler:")
                        print(result.stdout[-1000:])  # Letzten 1000 Zeichen
                        print(result.stderr[-1000:])
                        raise Exception(f"BuildTools fehlgeschlagen mit Exit-Code: {result.returncode}")
                else:
                    # Normaler Modus: Live-Output
                    process = subprocess.Popen(
                        cmd,
                        cwd=temp_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True,
                        env=env
                    )
                    
                    # Zeige Live-Output
                    for line in process.stdout:
                        print(f"BuildTools: {line.strip()}")
                    
                    process.wait()
                    
                    if process.returncode != 0:
                        raise Exception(f"BuildTools fehlgeschlagen mit Exit-Code: {process.returncode}")
                
                # Finde die erstellte Spigot JAR
                built_jar = temp_path / f"spigot-{version}.jar"
                if not built_jar.exists():
                    # Suche nach möglichen JAR-Dateien
                    jar_files = list(temp_path.glob("spigot*.jar"))
                    if jar_files:
                        built_jar = jar_files[0]
                        print(f"Spigot JAR gefunden: {built_jar}")
                    else:
                        raise Exception(f"Spigot JAR nicht gefunden in: {temp_path}")
                
                # Kopiere in Cache
                shutil.copy2(built_jar, spigot_jar)
                print(f"Spigot {version} erfolgreich erstellt und im Cache gespeichert.")
                
                return spigot_jar
                
            except subprocess.TimeoutExpired:
                raise Exception("BuildTools Timeout - Build dauerte zu lange")
            except Exception as e:
                raise Exception(f"Fehler beim Erstellen von Spigot: {e}")
    
    def build_spigot(self, version: str, force_rebuild: bool = False) -> Path:
        """Wrapper für optimierte Spigot-Erstellung"""
        return self.build_spigot_optimized(version, force_rebuild)
    
    def create_files_parallel(self, server_dir: Path, name: str, version: str, port: int, memory: str, **kwargs) -> None:
        """Erstellt alle Server-Dateien parallel"""
        def create_server_properties_task():
            self.create_server_properties(server_dir, port, **kwargs)
        
        def create_eula_task():
            self.create_eula_txt(server_dir)
        
        def create_start_script_task():
            self.create_start_script(server_dir, f"spigot-{version}.jar", memory)
        
        def create_server_info_task():
            self.create_server_info(server_dir, name, version, port, memory)
        
        def create_readme_task():
            self.create_readme(server_dir, name, version, port, memory)
        
        def create_directories_task():
            (server_dir / "plugins").mkdir(exist_ok=True)
            (server_dir / "world").mkdir(exist_ok=True)
            (server_dir / "logs").mkdir(exist_ok=True)
        
        # Führe alle Tasks parallel aus
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(create_server_properties_task),
                executor.submit(create_eula_task),
                executor.submit(create_start_script_task),
                executor.submit(create_server_info_task),
                executor.submit(create_readme_task),
                executor.submit(create_directories_task)
            ]
            
            # Warte auf Completion
            concurrent.futures.wait(futures)
            
            # Prüfe auf Exceptions
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Fehler beim Erstellen der Dateien: {e}")
    
    def create_server_properties(self, server_dir: Path, port: int = 25565, **kwargs) -> None:
        """Erstellt server.properties Datei mit erweiterten Optionen"""
        properties = {
            "server-port": port,
            "gamemode": kwargs.get("gamemode", "creative"),
            "difficulty": kwargs.get("difficulty", "peaceful"),
            "spawn-protection": kwargs.get("spawn_protection", 0),
            "max-players": kwargs.get("max_players", 10),
            "online-mode": kwargs.get("online_mode", False),
            "pvp": kwargs.get("pvp", False),
            "enable-command-block": kwargs.get("enable_command_block", True),
            "motd": kwargs.get("motd", "Spigot Test Server"),
            "white-list": kwargs.get("whitelist", False),
            "enforce-whitelist": kwargs.get("enforce_whitelist", False),
            "spawn-monsters": kwargs.get("spawn_monsters", True),
            "spawn-animals": kwargs.get("spawn_animals", True),
            "spawn-npcs": kwargs.get("spawn_npcs", True),
            "allow-flight": kwargs.get("allow_flight", True),
            "view-distance": kwargs.get("view_distance", 10),
            "simulation-distance": kwargs.get("simulation_distance", 10)
        }

        properties_file = server_dir / "server.properties"
        with open(properties_file, 'w', encoding='utf-8') as f:
            f.write("# Minecraft server properties\n")
            f.write("# Generated by Spigot Server Creator\n")
            f.write(f"# {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            for key, value in properties.items():
                f.write(f"{key}={value}\n")
    
    def create_eula_txt(self, server_dir: Path) -> None:
        """Erstellt eula.txt Datei"""
        eula_file = server_dir / "eula.txt"
        with open(eula_file, 'w', encoding='utf-8') as f:
            f.write("# EULA Agreement\n")
            f.write("# By changing the setting below to TRUE you are indicating your agreement to our EULA\n")
            f.write("# https://account.mojang.com/documents/minecraft_eula\n")
            f.write("eula=true\n")
    
    def create_start_script(self, server_dir: Path, jar_name: str, memory: str = "2G") -> None:
        """Erstellt Start-Skripte für den Server mit optimierten JVM-Argumenten"""
        
        # Optimierte JVM-Argumente für bessere Performance
        jvm_args = [
            f"-Xmx{memory}",
            f"-Xms{memory}",
            "-XX:+UseG1GC",
            "-XX:+ParallelRefProcEnabled",
            "-XX:MaxGCPauseMillis=200",
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+DisableExplicitGC",
            "-XX:+AlwaysPreTouch",
            "-XX:G1NewSizePercent=30",
            "-XX:G1MaxNewSizePercent=40",
            "-XX:G1HeapRegionSize=8M",
            "-XX:G1ReservePercent=20",
            "-XX:G1HeapWastePercent=5",
            "-XX:G1MixedGCCountTarget=4",
            "-XX:InitiatingHeapOccupancyPercent=15",
            "-XX:G1MixedGCLiveThresholdPercent=90",
            "-XX:G1RSetUpdatingPauseTimePercent=5",
            "-XX:SurvivorRatio=32",
            "-XX:+PerfDisableSharedMem",
            "-XX:MaxTenuringThreshold=1",
            "-Dusing.aikars.flags=https://mcflags.emc.gs",
            "-Daikars.new.flags=true"
        ]
        
        java_cmd = f"{self.config['java_path']} {' '.join(jvm_args)} -jar {jar_name} nogui"
        
        # Linux/Mac Start-Skript
        start_sh = server_dir / "start.sh"
        with open(start_sh, 'w', encoding='utf-8') as f:
            f.write("#!/bin/bash\n")
            f.write("# Minecraft Spigot Server Start Script\n")
            f.write("# Generated by Spigot Server Creator\n\n")
            f.write("echo 'Starting Minecraft Spigot Server...'\n")
            f.write("echo 'Memory allocation: " + memory + "'\n")
            f.write("echo 'Java command: " + java_cmd + "'\n")
            f.write("echo ''\n\n")
            f.write(java_cmd + "\n")
            f.write("\necho 'Server stopped.'\n")
            f.write("read -p 'Press enter to continue...'\n")
        start_sh.chmod(0o755)
        
        # Windows Start-Skript
        start_bat = server_dir / "start.bat"
        with open(start_bat, 'w', encoding='utf-8') as f:
            f.write("@echo off\n")
            f.write("REM Minecraft Spigot Server Start Script\n")
            f.write("REM Generated by Spigot Server Creator\n\n")
            f.write("echo Starting Minecraft Spigot Server...\n")
            f.write(f"echo Memory allocation: {memory}\n")
            f.write(f"echo Java command: {java_cmd}\n")
            f.write("echo.\n\n")
            f.write(java_cmd + "\n")
            f.write("\necho Server stopped.\n")
            f.write("pause\n")
    
    def create_server_info(self, server_dir: Path, name: str, version: str, port: int, memory: str) -> None:
        """Erstellt eine Info-Datei für den Server"""
        info = {
            "name": name,
            "version": version,
            "port": port,
            "memory": memory,
            "created": time.strftime('%Y-%m-%d %H:%M:%S'),
            "creator": "Spigot Server Creator (Optimized)"
        }
        
        info_file = server_dir / "server_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2)
    
    def create_readme(self, server_dir: Path, name: str, version: str, port: int, memory: str) -> None:
        """Erstellt README-Datei"""
        readme_file = server_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(f"# Minecraft Spigot Server: {name}\n\n")
            f.write(f"**Version:** {version}\n")
            f.write(f"**Port:** {port}\n")
            f.write(f"**Memory:** {memory}\n")
            f.write(f"**Erstellt:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Starten\n")
            f.write("- **Linux/Mac:** `./start.sh`\n")
            f.write("- **Windows:** `start.bat`\n\n")
            f.write("## Verzeichnisse\n")
            f.write("- `plugins/` - Für Plugins\n")
            f.write("- `world/` - Spielwelt\n")
            f.write("- `logs/` - Server-Logs\n\n")
            f.write("## Konfiguration\n")
            f.write("- `server.properties` - Server-Einstellungen\n")
            f.write("- `server_info.json` - Server-Informationen\n")

    def create_server(self, name: str, version: str, port: int = 25565, memory: str = "2G", **kwargs) -> Path:
        """Erstellt einen neuen Spigot Test Server - OPTIMIERTE VERSION"""
        server_dir = self.servers_dir / name
    
        if server_dir.exists():
            response = input(f"Server '{name}' existiert bereits. Überschreiben? (y/N): ")
            if response.lower() != 'y':
                print("Abgebrochen.")
                return server_dir
            shutil.rmtree(server_dir)
    
        start_time = time.time()
        print(f"Erstelle Server '{name}' mit Version {version}...")
    
        # Erstelle Server-Verzeichnis
        server_dir.mkdir(parents=True)
    
        # Parallel: Spigot JAR erstellen und Dateien vorbereiten
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Task 1: Spigot JAR erstellen/laden
            spigot_future = executor.submit(
                self.build_spigot, version, kwargs.get('force_rebuild', False)
            )
        
            # Task 2: Verzeichnisse erstellen
            dirs_future = executor.submit(
                lambda: [
                    (server_dir / "plugins").mkdir(exist_ok=True),
                    (server_dir / "world").mkdir(exist_ok=True),
                    (server_dir / "logs").mkdir(exist_ok=True)
                ]
            )
        
            # Warte auf Spigot JAR
            spigot_jar = spigot_future.result()
            dirs_future.result()
    
        # Kopiere Spigot JAR in Server-Verzeichnis
        server_jar = server_dir / f"spigot-{version}.jar"
        if not server_jar.exists():
            shutil.copy2(spigot_jar, server_jar)
    
        # Erstelle alle Server-Dateien parallel
        self.create_files_parallel(server_dir, name, version, port, memory, **kwargs)
    
        elapsed_time = time.time() - start_time
        print(f"Server '{name}' erfolgreich erstellt in {elapsed_time:.2f} Sekunden!")
        print(f"Pfad: {server_dir}")
        print(f"Zum Starten: cd {server_dir} && ./start.sh (Linux/Mac) oder start.bat (Windows)")
    
        return server_dir
    
    def create_server_simple(self, name: str, version: str, port: int = 25565, memory: str = "2G") -> Path:
        """Einfache Server-Erstellung ohne erweiterte Optionen - für Kompatibilität"""
        return self.create_server(name, version, port, memory)
    
    def list_servers(self) -> List[Path]:
        """Listet alle vorhandenen Server auf"""
        if not self.servers_dir.exists():
            return []
        
        servers = []
        for item in self.servers_dir.iterdir():
            if item.is_dir():
                info_file = item / "server_info.json"
                if info_file.exists():
                    servers.append(item)
        
        return servers
    
    def remove_server(self, name: str) -> bool:
        """Entfernt einen Server"""
        server_dir = self.servers_dir / name
        
        if not server_dir.exists():
            print(f"Server '{name}' nicht gefunden.")
            return False
        
        response = input(f"Server '{name}' wirklich löschen? (y/N): ")
        if response.lower() != 'y':
            print("Abgebrochen.")
            return False
        
        try:
            shutil.rmtree(server_dir)
            print(f"Server '{name}' erfolgreich gelöscht.")
            return True
        except Exception as e:
            print(f"Fehler beim Löschen: {e}")
            return False
    
    def clean_cache(self) -> None:
        """Bereinigt den Cache"""
        if not self.cache_dir.exists():
            print("Cache-Verzeichnis existiert nicht.")
            return
        
        response = input("Cache wirklich löschen? (y/N): ")
        if response.lower() != 'y':
            print("Abgebrochen.")
            return
        
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True)
            print("Cache erfolgreich bereinigt.")
        except Exception as e:
            print(f"Fehler beim Bereinigen des Caches: {e}")
    
    def show_config(self) -> None:
        """Zeigt die aktuelle Konfiguration an"""
        print("Aktuelle Konfiguration:")
        print(json.dumps(self.config, indent=2))
        print(f"\nKonfigurationsdatei: {self.config_file}")
    
    def update_config(self, key: str, value: str) -> None:
        """Aktualisiert einen Konfigurationswert"""
        # Versuche den Wert als JSON zu parsen
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value
        
        self.config[key] = parsed_value
        
        # Speichere Konfiguration
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        print(f"Konfiguration aktualisiert: {key} = {parsed_value}")


def main():
    """Hauptfunktion mit Command-Line Interface"""
    
    creator = SpigotServerCreator()
    
    parser = argparse.ArgumentParser(
        description="Minecraft Spigot Test Server Creator - Optimized Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s create MyServer 1.21.4                    # Erstelle Server mit Standard-Einstellungen
  %(prog)s create TestServer 1.20.4 -p 25566 -m 4G  # Server mit Port 25566 und 4GB RAM
  %(prog)s create DevServer 1.19.4 --gamemode survival --difficulty normal
  %(prog)s list                                       # Zeige alle Server
  %(prog)s remove MyServer                           # Lösche Server
  %(prog)s versions                                  # Zeige verfügbare Versionen
  %(prog)s config show                               # Zeige Konfiguration
  %(prog)s config set quick_mode true               # Aktiviere Quick-Mode
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Verfügbare Befehle')
    
    # Create Command
    create_parser = subparsers.add_parser('create', help='Erstelle einen neuen Server')
    create_parser.add_argument('name', help='Name des Servers')
    create_parser.add_argument('version', help='Minecraft Version (z.B. 1.21.4)')
    create_parser.add_argument('-p', '--port', type=int, default=25565, help='Server Port (Standard: 25565)')
    create_parser.add_argument('-m', '--memory', default='2G', help='RAM-Allocation (Standard: 2G)')
    create_parser.add_argument('--gamemode', choices=['survival', 'creative', 'adventure', 'spectator'], 
                               default='creative', help='Spielmodus (Standard: creative)')
    create_parser.add_argument('--difficulty', choices=['peaceful', 'easy', 'normal', 'hard'], 
                               default='peaceful', help='Schwierigkeit (Standard: peaceful)')
    create_parser.add_argument('--max-players', type=int, default=10, help='Max. Spieler (Standard: 10)')
    create_parser.add_argument('--online-mode', action='store_true', help='Online-Modus aktivieren')
    create_parser.add_argument('--pvp', action='store_true', help='PvP aktivieren')
    create_parser.add_argument('--whitelist', action='store_true', help='Whitelist aktivieren')
    create_parser.add_argument('--motd', default='Spigot Test Server', help='Server MOTD')
    create_parser.add_argument('--force-rebuild', action='store_true', help='Spigot JAR neu erstellen')
    create_parser.add_argument('--view-distance', type=int, default=10, help='Sichtweite (Standard: 10)')
    
    # List Command
    subparsers.add_parser('list', help='Liste alle Server auf') 
    
    # Remove Command
    remove_parser = subparsers.add_parser('remove', help='Entferne einen Server')
    remove_parser.add_argument('name', help='Name des zu löschenden Servers')
    
    # Versions Command
    subparsers.add_parser('versions', help='Zeige verfügbare Versionen')  
    
    # Cache Command
    cache_parser = subparsers.add_parser('cache', help='Cache-Verwaltung')
    cache_subparsers = cache_parser.add_subparsers(dest='cache_action')
    cache_subparsers.add_parser('clean', help='Cache bereinigen')
    cache_subparsers.add_parser('info', help='Cache-Informationen')
    
    # Config Command
    config_parser = subparsers.add_parser('config', help='Konfiguration verwalten')
    config_subparsers = config_parser.add_subparsers(dest='config_action')
    config_subparsers.add_parser('show', help='Konfiguration anzeigen')
    config_set_parser = config_subparsers.add_parser('set', help='Konfigurationswert setzen')
    config_set_parser.add_argument('key', help='Konfigurationsschlüssel')
    config_set_parser.add_argument('value', help='Neuer Wert')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'create':
            # Java-Check nur wenn nicht übersprungen
            if not creator.check_java_version():
                sys.exit(1)
            
            # Sammle alle Optionen
            options = {
                'gamemode': args.gamemode,
                'difficulty': args.difficulty,
                'max_players': args.max_players,
                'online_mode': args.online_mode,
                'pvp': args.pvp,
                'whitelist': args.whitelist,
                'motd': args.motd,
                'force_rebuild': args.force_rebuild,
                'view_distance': args.view_distance
            }
            
            creator.create_server(args.name, args.version, args.port, args.memory, **options)
        
        elif args.command == 'list':
            servers = creator.list_servers()
            if not servers:
                print("Keine Server gefunden.")
            else:
                print(f"Gefundene Server ({len(servers)}):")
                for server_dir in servers:
                    info_file = server_dir / "server_info.json"
                    if info_file.exists():
                        try:
                            with open(info_file, 'r') as f:
                                info = json.load(f)
                            print(f"  {server_dir.name}: Version {info.get('version', 'unknown')}, "
                                  f"Port {info.get('port', 'unknown')}, "
                                  f"Memory {info.get('memory', 'unknown')}")
                        except:  # noqa: E722
                            print(f"  {server_dir.name}: (Info nicht lesbar)")
                    else:
                        print(f"  {server_dir.name}: (Keine Info verfügbar)")
        
        elif args.command == 'remove':
            creator.remove_server(args.name)
        
        elif args.command == 'versions':
            versions = creator.get_available_versions()
            print("Verfügbare Minecraft Versionen:")
            for i, version in enumerate(versions, 1):
                print(f"  {version}", end="\n" if i % 5 == 0 else " ")
            if len(versions) % 5 != 0:
                print()
        
        elif args.command == 'cache':
            if args.cache_action == 'clean':
                creator.clean_cache()
            elif args.cache_action == 'info':
                cache_size = 0
                file_count = 0
                if creator.cache_dir.exists():
                    for file_path in creator.cache_dir.rglob('*'):
                        if file_path.is_file():
                            cache_size += file_path.stat().st_size
                            file_count += 1
                
                print(f"Cache-Verzeichnis: {creator.cache_dir}")
                print(f"Dateien: {file_count}")
                print(f"Größe: {cache_size / 1024 / 1024:.2f} MB")
            else:
                print("Cache-Aktion erforderlich: clean, info")
        
        elif args.command == 'config':
            if args.config_action == 'show':
                creator.show_config()
            elif args.config_action == 'set':
                creator.update_config(args.key, args.value)
            else:
                print("Config-Aktion erforderlich: show, set")
        
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(1)
    except Exception as e:
        print(f"Fehler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()