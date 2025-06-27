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
Command line tool for the automatic creation of Minecraft spigot test servers
"""

import sys
import argparse
import subprocess
import platform
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
    def __init__(self, servers_dir: Optional[Path] = None):
        self.base_dir = Path.cwd()
        self.servers_dir = Path(servers_dir) if servers_dir else self.base_dir / "servers"
        self.cache_dir = Path.home() / ".minecraft_server_creator" / "cache"
        self.config_file = Path.home() / ".minecraft_server_creator" / "config.json"
        
        self.servers_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = self.load_config()
        
        self._versions_cache = None
        self._versions_cache_time = 0
    
    def load_config(self) -> Dict:
        """Loads the configuration or creates a standard configuration"""
        default_config = {
            "java_path": "java",
            "default_memory": "2G",
            "default_port": 25565,
            "buildtools_update_interval": 86400,  
            "use_prebuilt_spigot": True, 
            "parallel_downloads": True,  
            "skip_java_check": False,   
            "quick_mode": False          
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"Warning: Could not load configuration: {e}")
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def check_java_version(self) -> bool:
        """Checks whether Java is available and has a suitable version"""
        if self.config.get("skip_java_check", False):
            print("Java-Check skiped (skip_java_check=true)")
            return True
            
        try:
            result = subprocess.run(
                [self.config["java_path"], "-version"],
                capture_output=True,
                text=True,
                timeout=5 
            )

            output = result.stderr + result.stdout
            if result.returncode != 0 or "version" not in output.lower():
                print(f"Error: Java not found under'{self.config['java_path']}'")
                return False

            version_line = output.split('\n')[0]
            if not self.config.get("quick_mode", False):
                print(f"Java found: {version_line}")

            if any(f"{v}." in version_line for v in range(17, 22)):
                return True
            elif "1.8" in version_line:
                if not self.config.get("quick_mode", False):
                    print("Warning: Java 8 detected. Java 17+ is recommended for Minecraft 1.17+.")
                return True
            else:
                if not self.config.get("quick_mode", False):
                    print("Warning: Unknown Java version. Continue...")
                return True

        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("Error: Java not found or timeout. Please install Java or set skip_java_check=true.")
            return False
        except Exception as e:
            print(f"Error when checking the Java version: {e}")
            return False
    
    def get_available_versions(self) -> List[str]:
        """Fetches available spigot versions with caching"""
        if (self._versions_cache and 
            time.time() - self._versions_cache_time < 3600):
            return self._versions_cache
        
        try:
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
            print(f"Warning: Could not retrieve versions: {e}")
            return ["1.21.4", "1.20.4", "1.19.4", "1.18.2", "1.17.1", "1.16.5"]
    
    def should_update_buildtools(self) -> bool:
        """Checks whether BuildTools should be updated"""
        buildtools_path = self.cache_dir / "BuildTools.jar"
        
        if not buildtools_path.exists():
            return True

        if self.config.get("quick_mode", False):
            update_interval = self.config["buildtools_update_interval"] * 7
        else:
            update_interval = self.config["buildtools_update_interval"]
        
        file_age = time.time() - buildtools_path.stat().st_mtime
        return file_age > update_interval
    
    def fast_rmtree(self, path: Path, show_progress: bool = False):
        """Fast removal of a directory, especially on Windows - IMPROVED VERSION"""
        if show_progress and not self.config.get("quick_mode", False):
            print(f"Removing directory: {path}")

        if not path.exists():
            if show_progress and not self.config.get("quick_mode", False):
                print("Directory does not exist, nothing to remove")
            return

        if platform.system() == "Windows":
            try:
                # Erst Dateien entsperren (falls möglich)
                subprocess.run(['attrib', '-R', str(path / "*"), '/S'], 
                            capture_output=True, timeout=10)
            except:  # noqa: E722
                pass
                
            try:
                # Windows-spezifische schnelle Entfernung
                result = subprocess.run(['cmd', '/c', 'rmdir', '/S', '/Q', str(path)], 
                                    capture_output=True, timeout=30)
                if result.returncode == 0:
                    if show_progress and not self.config.get("quick_mode", False):
                        print("Directory successfully removed (Windows fast removal)")
                    return
                else:
                    print(f"[DEBUG] Windows rmdir failed with code {result.returncode}")
                    
            except subprocess.TimeoutExpired:
                print("[DEBUG] Windows rmdir timeout, trying fallback...")
            except Exception as e:
                print(f"[DEBUG] Windows rmdir failed: {e}")
        
        # Fallback zu shutil.rmtree für alle Systeme
        try:
            shutil.rmtree(path, ignore_errors=False)
            if show_progress and not self.config.get("quick_mode", False):
                print("Directory successfully removed (shutil.rmtree)")
        except Exception as e:
            print(f"[ERROR] shutil.rmtree also failed: {e}")
            # Letzter Versuch mit ignore_errors=True
            try:
                shutil.rmtree(path, ignore_errors=True)
                if not path.exists():
                    if show_progress and not self.config.get("quick_mode", False):
                        print("Directory successfully removed (shutil.rmtree with ignore_errors)")
                else:
                    raise Exception("All removal methods failed")
            except Exception as final_e:
                raise Exception(f"Complete removal failure: {final_e}")

    
    def download_file_parallel(self, url: str, output_path: Path, description: str = "Download") -> None:
        """Optimized download with progress indicator"""
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Größere Chunk-Size für bessere Performance
            chunk_size = 32768
        
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0 and not self.config.get("quick_mode", False):
                            percent = (downloaded / total_size) * 100
                            print(f"\r{description}: {percent:.1f}%", end='', flush=True)
            
            if not self.config.get("quick_mode", False):
                print() 
                
        except Exception as e:
            raise Exception(f"Error during download: {e}")
    
    def try_download_prebuilt_spigot(self, version: str) -> Optional[Path]:
        """Try to download a ready-made Spigot JAR"""
        if not self.config.get("use_prebuilt_spigot", True):
            return None
        
        spigot_jar = self.cache_dir / f"spigot-{version}.jar"

        prebuilt_urls = {
            "1.21.4": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            "1.21.3": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            "1.20.4": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            "1.19.4": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            "1.18.2": f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
        }
        
        alternative_urls = [
            f"https://download.getbukkit.org/spigot/spigot-{version}.jar",
            f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar",
            f"https://hub.spigotmc.org/stash/projects/SPIGOT/repos/spigot/browse/work/decompile-{version}/spigot-{version}.jar?raw"
        ]
        
        all_urls = [prebuilt_urls.get(version)] + alternative_urls
        all_urls = [url for url in all_urls if url] 
        
        for url in all_urls:
            try:
                print(f"Try to download ready-made Spigot JAR for {version}...")
                self.download_file_parallel(url, spigot_jar, f"Spigot {version}")

                if spigot_jar.stat().st_size > 1024 * 1024: 
                    print(f"Pre-built Spigot JAR for {version} successfully downloaded!")
                    return spigot_jar
                else:
                    spigot_jar.unlink()  
                    
            except Exception: 
                if spigot_jar.exists():
                    spigot_jar.unlink()
                continue
        
        return None
    
    def download_buildtools(self, force_update: bool = False) -> Path:
        """Downloads BuildTools.jar if not available or outdated"""
        buildtools_path = self.cache_dir / "BuildTools.jar"
        
        if buildtools_path.exists() and not force_update and not self.should_update_buildtools():
            if not self.config.get("quick_mode", False):
                print("BuildTools.jar already available and up-to-date.")
            return buildtools_path
        
        print("Download BuildTools.jar...")
        url = "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"
        
        try:
            if buildtools_path.exists():
                backup_path = buildtools_path.with_suffix('.jar.backup')
                shutil.move(buildtools_path, backup_path)
            
            self.download_file_parallel(url, buildtools_path, "BuildTools")
            
            if not self.config.get("quick_mode", False):
                print("BuildTools.jar successfully downloaded.")
            return buildtools_path
            
        except Exception as e:
            backup_path = buildtools_path.with_suffix('.jar.backup')
            if backup_path.exists():
                shutil.move(backup_path, buildtools_path)
                print("Backup of BuildTools.jar restored.")
                return buildtools_path
            
            raise Exception(f"Error downloading BuildTools.jar: {e}")
        
    SUPPORTED_BUKKIT_VERSIONS = [
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

    def download_bukkit(self, version: str) -> Path:
        """Download Bukkit JAR"""
        if version not in self.SUPPORTED_BUKKIT_VERSIONS:
            raise Exception(
                f"Bukkit/CraftBukkit ist für Version {version} nicht verfügbar.\n"
                "Siehe https://getbukkit.org/download/craftbukkit für unterstützte Versionen."
            )
        bukkit_jar = self.cache_dir / f"bukkit-{version}.jar"
        url = f"https://cdn.getbukkit.org/craftbukkit/craftbukkit-{version}.jar"
        response = requests.head(url)
        if response.status_code != 200:
            raise Exception(
                f"Bukkit/CraftBukkit JAR for version {version} not found at {url}.\n"
                "Hinweis: Bukkit/CraftBukkit ist nicht für alle Minecraft-Versionen verfügbar. "
                "Siehe https://getbukkit.org/download/craftbukkit für verfügbare Versionen."
            )  
        if not bukkit_jar.exists():
            print(f"Downloading Bukkit {version} ...")
            self.download_file_parallel(url, bukkit_jar, f"Bukkit {version}")
        return bukkit_jar

    def download_vanilla(self, version: str) -> Path:
        """Download Vanilla Minecraft Server JAR"""
        vanilla_jar = self.cache_dir / f"minecraft_server.{version}.jar"
        url = self.get_vanilla_server_url(version)
        if not url:
            raise Exception(f"Could not find download URL for vanilla version {version}")
        if not vanilla_jar.exists():
            print(f"Downloading Vanilla Minecraft {version} ...")
            self.download_file_parallel(url, vanilla_jar, f"Vanilla {version}")
        return vanilla_jar

    def get_vanilla_hash(self, version: str) -> str:
        """Fetches the Mojang hash for a given version from the official manifest."""
        try:
            manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
            manifest = requests.get(manifest_url, timeout=10).json()
            version_info = next((v for v in manifest["versions"] if v["id"] == version), None)
            if not version_info:
                raise Exception(f"Version {version} not found in Mojang manifest.")
            version_json = requests.get(version_info["url"], timeout=10).json()
            return version_json["downloads"]["server"]["sha1"]
        except Exception as e:
            print(f"Could not fetch vanilla hash for {version}: {e}")
            return ""
        
    def get_vanilla_server_url(self, version: str) -> str:
        """Fetches the Mojang server JAR URL for a given version."""
        try:
            manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
            manifest = requests.get(manifest_url, timeout=10).json()
            version_info = next((v for v in manifest["versions"] if v["id"] == version), None)
            if not version_info:
                raise Exception(f"Version {version} not found in Mojang manifest.")
            version_json = requests.get(version_info["url"], timeout=10).json()
            return version_json["downloads"]["server"]["url"]
        except Exception as e:
            print(f"Could not fetch vanilla server URL for {version}: {e}")
            return ""
    
    def build_spigot_optimized(self, version: str, force_rebuild: bool = False) -> Path:
        """Optimized spigot creation with improved performance"""
        spigot_jar = self.cache_dir / f"spigot-{version}.jar"

        if spigot_jar.exists() and not force_rebuild:
            if not self.config.get("quick_mode", False):
                print(f"Spigot {version} already created.")
            return spigot_jar

        prebuilt_jar = self.try_download_prebuilt_spigot(version)
        if prebuilt_jar:
            return prebuilt_jar

        print(f"Create spigot {version} with BuildTools...")

        if not self.check_java_version():
            raise Exception("Java check failed")

        buildtools_path = self.download_buildtools()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                temp_buildtools = temp_path / "BuildTools.jar"
                shutil.copy2(buildtools_path, temp_buildtools)

                cmd = [
                    self.config["java_path"],
                    "-Xmx2G",
                    "-jar", str(temp_buildtools),
                    "--rev", version,
                    "--output-dir", str(temp_path),
                    "--compile", "spigot",
                    "--disable-certificate-check"
                ]

                if version.startswith(("1.19", "1.20", "1.21")):
                    cmd.append("--disable-java-check")

                if not self.config.get("quick_mode", False):
                    print(f"Execute: {' '.join(cmd)}")
                    print("This may take a few minutes...")

                env = dict(os.environ)
                env.update({
                    "MAVEN_OPTS": "-Xmx2G -XX:+UseG1GC",
                    "JAVA_TOOL_OPTIONS": "-Xmx2G"
                })

                if self.config.get("quick_mode", False):
                    result = subprocess.run(
                        cmd,
                        cwd=temp_path,
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=1800
                    )
                    if result.returncode != 0:
                        print("BuildTools error:")
                        print(result.stdout[-1000:])
                        print(result.stderr[-1000:])
                        raise Exception(f"BuildTools failed with exit code: {result.returncode}")
                else:
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
                    for line in process.stdout:
                        print(f"BuildTools: {line.strip()}")
                    process.wait()
                    if process.returncode != 0:
                        raise Exception(f"BuildTools failed with exit code:{process.returncode}")

                built_jar = temp_path / f"spigot-{version}.jar"
                if not built_jar.exists():
                    jar_files = list(temp_path.glob("spigot*.jar"))
                    if jar_files:
                        built_jar = jar_files[0]
                        print(f"Spigot JAR found: {built_jar}")
                    else:
                        raise Exception(f"Spigot JAR not found in: {temp_path}")

                shutil.copy2(built_jar, spigot_jar)
                print(f"Spigot {version} successfully created and saved in the cache.")

                return spigot_jar

        except subprocess.TimeoutExpired:
            raise Exception("BuildTools timeout - build took too long")
        except Exception as e:
            raise Exception(f"Error when creating spigot: {e}")
    
    def build_spigot(self, version: str, force_rebuild: bool = False) -> Path:
        """Wrapper for optimized spigot creation"""
        return self.build_spigot_optimized(version, force_rebuild)
    
    def create_files_parallel(self, server_dir: Path, name: str, version: str, port: int, memory: str, **kwargs) -> None:
        """Creates all server files in parallel"""
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

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(create_server_properties_task),
                executor.submit(create_eula_task),
                executor.submit(create_start_script_task),
                executor.submit(create_server_info_task),
                executor.submit(create_readme_task),
                executor.submit(create_directories_task)
            ]

            concurrent.futures.wait(futures)

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Error when creating the files: {e}")
    
    def create_server_properties(self, server_dir: Path, port: int = 25565, **kwargs) -> None:
        """Creates server.properties file with advanced options"""
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
        """Creates eula.txt file"""
        eula_file = server_dir / "eula.txt"
        with open(eula_file, 'w', encoding='utf-8') as f:
            f.write("# EULA Agreement\n")
            f.write("# By changing the setting below to TRUE you are indicating your agreement to our EULA\n")
            f.write("# https://account.mojang.com/documents/minecraft_eula\n")
            f.write("eula=true\n")
    
    def create_start_script(self, server_dir: Path, jar_name: str, memory: str = "2G") -> None:
        """Creates start scripts for the server with optimized JVM arguments"""

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
        """Creates README-Datei"""
        readme_file = server_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(f"# Minecraft Spigot Server: {name}\n\n")
            f.write(f"**Version:** {version}\n")
            f.write(f"**Port:** {port}\n")
            f.write(f"**Memory:** {memory}\n")
            f.write(f"**Erstellt:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Starts\n")
            f.write("- **Linux/Mac:** `./start.sh`\n")
            f.write("- **Windows:** `start.bat`\n\n")
            f.write("## Directorys\n")
            f.write("- `plugins/` - Für Plugins\n")
            f.write("- `world/` - Spielwelt\n")
            f.write("- `logs/` - Server-Logs\n\n")
            f.write("## Configuration\n")
            f.write("- `server.properties` - Server-Einstellungen\n")
            f.write("- `server_info.json` - Server-Informationen\n")

    def create_server(self, name: str, version: str, port: int = 25565, memory: str = "2G", **kwargs) -> Path:
        """Creates a new Minecraft Server (Spigot/Bukkit/Vanilla) - OPTIMIZED VERSION WITH BUGFIX"""
        server_type = kwargs.get('type', 'spigot')
        server_dir = self.servers_dir / name
        
        print(f"[DEBUG] Server directory: {server_dir}")
        print(f"[DEBUG] Directory exists: {server_dir.exists()}")
        
        # Handle existing server with optimized removal
        if server_dir.exists():
            if kwargs.get('force_overwrite', False):
                print(f"Force overwriting existing server '{name}'...")
                try:
                    self.fast_rmtree(server_dir, show_progress=True)
                    print("[DEBUG] Force removal completed")
                except Exception as e:
                    print(f"[ERROR] Force removal failed: {e}")
                    raise
                    
                print("[DEBUG] Starting removal process...")
                try:
                    # Check if directory is accessible
                    contents = list(server_dir.iterdir())
                    print(f"[DEBUG] Directory contains {len(contents)} items")
                    
                    # BUGFIX: Immer fast_rmtree verwenden, unabhängig von der Anzahl der Dateien
                    print("Removing existing server directory...")
                    self.fast_rmtree(server_dir, show_progress=True)
                    
                    print("[DEBUG] Removal completed successfully")
                    
                    # Verify removal
                    if server_dir.exists():
                        print("[ERROR] Directory still exists after removal!")
                        # BUGFIX: Zweiter Versuch mit shutil.rmtree wenn fast_rmtree fehlschlägt
                        print("[DEBUG] Trying fallback removal method...")
                        shutil.rmtree(server_dir, ignore_errors=True)
                        
                        # Nochmal prüfen
                        if server_dir.exists():
                            raise Exception("Directory removal failed - directory still exists after fallback")
                        else:
                            print("[DEBUG] Fallback removal successful")
                    else:
                        print("[DEBUG] Directory successfully removed")
                        
                except PermissionError as e:  # <-- Korrekt eingerückt!
                    print(f"[ERROR] Permission denied: {e}")
                    print("Make sure no files are open and you have write permissions.")
                    print("Try running the command as administrator or closing any open files.")
                    raise
                except Exception as e:       
                    print(f"[ERROR] Removal failed: {e}")
                    print(f"[DEBUG] Directory still exists: {server_dir.exists()}")
                    if server_dir.exists():
                        try:
                            contents = list(server_dir.iterdir())
                            print(f"[DEBUG] Directory still contains: {[f.name for f in contents[:5]]}")
                        except:  # noqa: E722
                            print("[DEBUG] Cannot list directory contents")
                    raise
        
        print("[DEBUG] Starting server creation...")
        start_time = time.time()
        print(f"Creating server '{name}' with version {version}...")
        
        # Create server directory
        try:
            server_dir.mkdir(parents=True, exist_ok=True)
            print(f"[DEBUG] Created server directory: {server_dir}")
        except Exception as e:
            print(f"[ERROR] Failed to create server directory: {e}")
            raise
        
        # Get appropriate JAR based on server type
        try:
            print(f"[DEBUG] Getting {server_type} JAR for version {version}")
            if server_type == 'spigot':
                jar_path = self.build_spigot(version, kwargs.get('force_rebuild', False))
                jar_name = f"spigot-{version}.jar"
            elif server_type == 'bukkit':
                jar_path = self.download_bukkit(version)
                jar_name = f"bukkit-{version}.jar"
            elif server_type == 'vanilla':
                jar_path = self.download_vanilla(version)
                jar_name = f"minecraft_server.{version}.jar"
            else:
                raise Exception(f"Unknown server type: {server_type}")
            
            print(f"[DEBUG] JAR obtained: {jar_path}")
        except Exception as e:
            print(f"[ERROR] Failed to get {server_type} JAR: {e}")
            raise
        
        # Copy JAR file efficiently
        try:
            server_jar = server_dir / jar_name
            if not server_jar.exists():
                if not self.config.get("quick_mode", False):
                    print(f"Copying {server_type} JAR...")
                shutil.copy2(jar_path, server_jar)
                print(f"[DEBUG] JAR copied to: {server_jar}")
        except Exception as e:
            print(f"[ERROR] Failed to copy JAR: {e}")
            raise
        
        # Create all server files in parallel
        try:
            print("[DEBUG] Creating server files...")
            self.create_files_parallel(server_dir, name, version, port, memory, **kwargs)
            print("[DEBUG] Server files created")
        except Exception as e:
            print(f"[ERROR] Failed to create server files: {e}")
            raise
        
        elapsed_time = time.time() - start_time
        print(f"Server '{name}' successfully created in {elapsed_time:.2f} seconds!")
        print(f"Path: {server_dir}")
        print(f"To start: cd {server_dir} && ./start.sh (Linux/Mac) or start.bat (Windows)")
        
        return server_dir
    
    def create_server_simple(self, name: str, version: str, port: int = 25565, memory: str = "2G") -> Path:
        """Simple server creation without advanced options - for compatibility"""
        return self.create_server(name, version, port, memory)
    
    def list_servers(self) -> List[Path]:
        """Lists all available servers"""
        if not self.servers_dir.exists():
            return []
        
        servers = []
        for item in self.servers_dir.iterdir():
            if item.is_dir():
                info_file = item / "server_info.json"
                if info_file.exists():
                    servers.append(item)
        
        return servers
    
    def remove_server(self, name: str, force: bool = False) -> bool:
        """Removes a server with optimized deletion"""
        server_dir = self.servers_dir / name
        
        if not server_dir.exists():
            print(f"Server '{name}' not found.")
            return False
        
        if not force:
            response = input(f"Really delete server '{name}'? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return False
        
        try:
            self.fast_rmtree(server_dir, show_progress=True)
            print(f"Server '{name}' successfully deleted.")
            return True
        except Exception as e:
            print(f"Error during deletion: {e}")
            return False

    def clean_cache(self) -> None:
        """Cleans the cache with optimized removal"""
        if not self.cache_dir.exists():
            print("Cache directory does not exist.")
            return
        
        response = input("Really delete cache? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        
        try:
            self.fast_rmtree(self.cache_dir, show_progress=True)
            self.cache_dir.mkdir(parents=True)
            print("Cache successfully cleaned.")
        except Exception as e:
            print(f"Error when clearing the cache: {e}")
    
    def show_config(self) -> None:
        """Displays the current configuration"""
        print("Current configuration:")
        print(json.dumps(self.config, indent=2))
        print(f"\nConfiguration file: {self.config_file}")
    
    def update_config(self, key: str, value: str) -> None:
        """Updates a configuration value"""
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value
        
        self.config[key] = parsed_value
        
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        print(f"Configuration updated: {key} = {parsed_value}")

def main():
    """Main function with command line interface"""
    
    creator = SpigotServerCreator()
    
    parser = argparse.ArgumentParser(
        description="Minecraft Spigot Test Server Creator - Optimized Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
 %(prog)s create MyServer 1.21.4 # Create server with default settings
 %(prog)s create TestServer 1.20.4 -p 25566 -m 4G # Server with port 25566 and 4GB RAM
 %(prog)s create DevServer 1.19.4 --gamemode survival --difficulty normal
 %(prog)s list # Show all servers
 %(prog)s remove MyServer # Delete server
 %(prog)s versions # Show available versions
 %(prog)s config show # Show configuration
 %(prog)s config set quick_mode true # Activate Quick-Mode
 """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    create_parser = subparsers.add_parser('create', help='Creates a new server')
    create_parser.add_argument('name', help='Name of the server')
    create_parser.add_argument('version', help='Minecraft version (e.g. 1.21.4)')
    create_parser.add_argument('--type', choices=['spigot', 'bukkit', 'vanilla'], default='spigot', help='Server type (default: spigot)')
    create_parser.add_argument('-p', '--port', type=int, default=25565, help='Server port (default: 25565)')
    create_parser.add_argument('-m', '--memory', default='2G', help='RAM allocation (default: 2G)')
    create_parser.add_argument('--dir', '--directory', dest='directory', default=None, help='Directory to save the server')
    create_parser.add_argument('--gamemode', choices=['survival', 'creative', 'adventure', 'spectator'], 
        default='creative', help='Gamemode (default: creative)')
    create_parser.add_argument('--difficulty', choices=['peaceful', 'easy', 'normal', 'hard'], 
        default='peaceful', help='Difficulty (default: peaceful)')
    create_parser.add_argument('--max-players', type=int, default=10, help='Max players (default: 10)')
    create_parser.add_argument('--online-mode', action='store_true', help='Activate online mode')
    create_parser.add_argument('--pvp', action='store_true', help='Activate PvP')
    create_parser.add_argument('--whitelist', action='store_true', help='Activate whitelist')
    create_parser.add_argument('--motd', default='Spigot Test Server', help='Server MOTD')
    create_parser.add_argument('--force-rebuild', action='store_true', help='Create new Spigot JAR')
    create_parser.add_argument('--view-distance', type=int, default=10, help='View distance (default: 10)')
    
    subparsers.add_parser('list', help='List all servers')

    # Remove Command
    remove_parser = subparsers.add_parser('remove', help='Remove a server')
    remove_parser.add_argument('name', help='Name of the server to delete')

    # Versions Command
    subparsers.add_parser('versions', help='Show available versions')

    # Cache Command
    cache_parser = subparsers.add_parser('cache', help='Cache management')
    cache_subparsers = cache_parser.add_subparsers(dest='cache_action')
    cache_subparsers.add_parser('clean', help='Clean cache')
    cache_subparsers.add_parser('info', help='Cache information')

    # Config Command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_subparsers = config_parser.add_subparsers(dest='config_action')
    config_set_parser = config_subparsers.add_parser('set', help='Set configuration value')
    config_set_parser.add_argument('key', help='Configuration key')
    config_set_parser.add_argument('value', help='New value')
    
    args = parser.parse_args()

    servers_dir = Path(args.directory) if getattr(args, 'directory', None) else None
    creator = SpigotServerCreator(servers_dir=servers_dir)
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'create':
            # Java check only if not skipped
            if not creator.check_java_version():
                sys.exit(1)
            
            # Collect all options
            options = {
                'gamemode': args.gamemode,
                'difficulty': args.difficulty,
                'max_players': args.max_players,
                'online_mode': args.online_mode,
                'pvp': args.pvp,
                'whitelist': args.whitelist,
                'motd': args.motd,
                'force_rebuild': args.force_rebuild,
                'view_distance': args.view_distance,
                'type': args.type
            }
            
            creator.create_server(args.name, args.version, args.port, args.memory, **options)
        
        elif args.command == 'list':
            servers = creator.list_servers()
            if not servers:
                print("No servers found.")
            else:
                print(f"Found servers ({len(servers)}):")
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
                            print(f"  {server_dir.name}: (Info not readable)")
                    else:
                        print(f"  {server_dir.name}: (No info available)")
        
        elif args.command == 'remove':
            creator.remove_server(args.name)
        
        elif args.command == 'versions':
            versions = creator.get_available_versions()
            print("Available Minecraft versions:")
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
                
                print(f"Cache directory: {creator.cache_dir}")
                print(f"Files: {file_count}")
                print(f"Size: {cache_size / 1024 / 1024:.2f} MB")
            else:
                print("Cache action required: clean, info")
        
        elif args.command == 'config':
            if args.config_action == 'show':
                creator.show_config()
            elif args.config_action == 'set':
                creator.update_config(args.key, args.value)
            else:
                print("Config action required: show, set")
        
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()