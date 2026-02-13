# Dailies Finder for Nuke

A Nuke script that finds and lays out version comparisons for selected shots. Select your Read nodes, run the script, and it creates an organized grid of **version zero**, **latest version**, and **selected version** Read nodes — each under a color-coded Backdrop.

This script is **read-only** on the filesystem. It never writes, moves, or deletes any files.

## How It Works

1. You select one or more Read nodes in your Nuke script.
2. The script parses each filename to extract the shot name (e.g. `SEQ_1140a`).
3. For each shot it looks up:
   - **Version zero** — the initial delivery (vendor letter + `0000`)
   - **Latest version** — the highest-numbered file on disk
4. New Read nodes are created to the right of your selection, organized in a labeled grid of Backdrops.

## Requirements

- [Nuke](https://www.foundry.com/products/nuke) (any version with Python 3 support)
- Python `pyyaml` package (ships with most Nuke installations)

## Installation

### 1. Copy the config file

Copy `nuke_config.yaml` to `~/.nuke/dailies_viewer/config.yaml`:

```bash
mkdir -p ~/.nuke/dailies_viewer
cp nuke_config.yaml ~/.nuke/dailies_viewer/config.yaml
```

### 2. Edit the config

Open `~/.nuke/dailies_viewer/config.yaml` and set `shot_tree_root` to your facility's shot tree path:

```yaml
shot_tree_root: "/mnt/projects/MY_SHOW/SHOT_TREE/vfx"
```

Adjust `shot_regex` if your filename convention differs from the default (see the comments in the config file for details).

### 3. Run in Nuke

Open `find_versions.py` in Nuke's Script Editor, select one or more Read nodes in the node graph, then execute the script.

**Tip:** You can add it to a menu or toolbar for quick access by adding this to your `menu.py`:

```python
toolbar = nuke.toolbar("Nodes")
toolbar.addCommand("Dailies Finder", lambda: execfile("/path/to/find_versions.py"))
```

## Configuration Reference

| Key | Description | Default |
|---|---|---|
| `shot_tree_root` | Root directory of your shot tree | *(required)* |
| `version_subfolder` | Folder inside each shot dir containing versions | `_vfx` |
| `shot_regex` | Regex to extract shot name from filename (group 1) | See config |
| `file_extension` | File extension to search for | `.mov` |
| `layout.*` | Backdrop sizing and spacing in the node graph | See config |
| `colors.*` | Hex colors for each Backdrop row | See config |

### Shot Tree Structure

The script expects a directory layout like:

```
{shot_tree_root}/
  SEQ/
    SEQ_1140/
      _vfx/
        SEQ_1140_comp_u0000_vfx.mov    <- version zero
        SEQ_1140a_comp_u0012_vfx.mov   <- latest for "a" variant
        ...
```

### Filename Convention

The default `shot_regex` matches filenames structured as:

```
{SHOT}_{task}_{vendorLetter}{version}_vfx.{ext}
```

For example: `SEQ_1140a_comp_u0012_vfx.mov`

- `SEQ_1140a` — shot name (sequence + shot number + optional letter variant)
- `comp` — task/department
- `u0012` — single vendor letter + four-digit version number
- `vfx` — delivery tag

## License

[MIT](LICENSE)
