# Minecraft Spigot Test Server Creator

A powerful command-line tool for automatically creating Minecraft Spigot test servers.  
It handles downloading, building, and configuring Spigot servers for various Minecraft versions.

## Features

- Automatic downloading and/or building of Spigot server JARs
- Supports many Minecraft versions (including 1.21.x)
- Parallel downloads and optimized BuildTools usage
- Manage multiple server instances
- Configurable options (RAM, port, gamemode, PvP, whitelist, MOTD, etc.)
- Automatic Java version detection and warnings
- Caching for downloads and BuildTools
- Simple CLI usage

## Requirements

- **Python 3.8+**
- **Java 17+** (for Minecraft 1.17+)
- Internet connection (for downloads)

## Installation

1. Clone the repository:
   ```sh
   git clone <repository-url>
   cd python-server-bau
   ```

2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

## Usage

### Create a server

```sh
python spigot_creator.py create <ServerName> <Version> [options]
```

Example:
```sh
python spigot_creator.py create MyServer 1.21.4 -p 25566 -m 4G --gamemode survival --difficulty normal
```

### List servers

```sh
python spigot_creator.py list
```

### Remove a server

```sh
python spigot_creator.py remove <ServerName>
```

### Show available versions

```sh
python spigot_creator.py versions
```

### Show or change configuration

```sh
python spigot_creator.py config show
python spigot_creator.py config set <key> <value>
```

### Show help

```sh
python spigot_creator.py --help
```

## Example configuration

The configuration is automatically created at `~/.minecraft_server_creator/config.json`.  
Example content:
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

## License

MIT License – see [LICENSE](LICENSE).