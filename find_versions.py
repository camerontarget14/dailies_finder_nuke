"""
Find versions - Nuke Script Editor script
Select Read nodes, then run this entire script.
Finds version zeros and latest versions, creates Read nodes
organized under labeled Backdrop nodes.

Config lives at: ~/.nuke/dailies_viewer/config.yaml

This script is READ-ONLY on the filesystem. It never writes,
moves, or deletes any files.
"""

import os
import re
from pathlib import Path

import nuke
import yaml

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".nuke", "dailies_viewer", "config.yaml")


def _load_config():
    if not os.path.exists(CONFIG_PATH):
        nuke.message("Config not found:\n{}".format(CONFIG_PATH))
        return None
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def _extract_shot_name(filename, shot_regex):
    """Extract full shot name (e.g. SEQ_1140a) from filename stem."""
    stem = os.path.splitext(filename)[0]
    m = re.match(shot_regex, stem)
    return m.group(1) if m else None


def _extract_version_label(filename):
    """Extract a short version label from filename, e.g. w0045 from
    SEQ_0240_comp_w0045_vfx.mov -> w0045"""
    stem = os.path.splitext(filename)[0]
    m = re.search(r"_([a-z]\d+)_vfx$", stem)
    if m:
        return m.group(1)
    # Fallback: try _v#### pattern
    m = re.search(r"_(v\d+)", stem)
    return m.group(1) if m else ""


def _shot_base(shot_name):
    """Strip optional trailing letter: SEQ_1140a -> SEQ_1140."""
    return re.sub(r"[a-z]$", "", shot_name)


def _build_vfx_path(shot_name, shot_tree_root, version_subfolder):
    """Build the _vfx folder path from a shot name.
    e.g. SEQ_1140a -> {shot_tree_root}/SEQ/SEQ_1140/_vfx/
    """
    base = _shot_base(shot_name)
    seq = base.split("_")[0]       # SEQ
    shot_dir = base                 # SEQ_1140
    return Path(shot_tree_root) / seq / shot_dir / version_subfolder


def _find_version_zero(shot_name, vfx_dir, file_ext):
    """Find the version zero file (any vendor letter + 0000).
    Searches using the base shot name (no trailing a/b) since
    v-zeros won't have the letter suffix.
    """
    if not vfx_dir.exists():
        return None
    base = _shot_base(shot_name)
    # Match any vendor prefix letter + 0000, e.g. SEQ_1140_comp_u0000_vfx.mov
    patterns = [
        "{}_*_?0000_vfx{}".format(base, file_ext),
        "{}_?0000_vfx{}".format(base, file_ext),
    ]
    for pat in patterns:
        matches = [f for f in vfx_dir.glob(pat) if f.suffix == file_ext]
        if matches:
            return str(matches[0])
    return None


def _find_latest_version(shot_name, vfx_dir, file_ext, exclude_filename=None):
    """Find the highest version for this exact shot name (including a/b suffix).
    Matches any single vendor-letter prefix + digits.
    Skips any file whose name matches exclude_filename.
    """
    if not vfx_dir.exists():
        return None
    patterns = [
        "{}_*_?*_vfx{}".format(shot_name, file_ext),
    ]
    matching_files = []
    for pat in patterns:
        matching_files.extend(f for f in vfx_dir.glob(pat) if f.suffix == file_ext)
    if not matching_files:
        return None

    # Extract version number: single letter + digits, e.g. u0012, i0006, w0009
    version_re = re.compile(r"_([a-z])(\d+)_vfx$")
    versions = []
    for f in matching_files:
        if exclude_filename and f.name == exclude_filename:
            continue
        m = version_re.search(f.stem)
        if m:
            versions.append((int(m.group(2)), str(f)))
    if not versions:
        return None
    versions.sort(key=lambda x: x[0], reverse=True)
    return versions[0][1]


def _create_read(filepath, xpos, ypos):
    read = nuke.createNode("Read", inpanel=False)
    read["file"].fromUserText(filepath)
    read["raw"].setValue(True)
    read.setXpos(xpos)
    read.setYpos(ypos)
    return read


def _create_backdrop(label, xpos, ypos, width, height, color):
    return nuke.nodes.BackdropNode(
        xpos=xpos, ypos=ypos,
        bdwidth=width, bdheight=height,
        tile_color=color,
        label="<center><b>{}</b></center>".format(label),
        note_font_size=30,
    )


# ---- main ----

config = _load_config()
if config is not None:
    shot_regex = config["shot_regex"]
    shot_tree_root = config["shot_tree_root"]
    version_subfolder = config.get("version_subfolder", "_vfx")
    file_ext = config.get("file_extension", ".mov")
    layout = config.get("layout", {})
    bd_w = layout.get("backdrop_width", 300)
    bd_h = layout.get("backdrop_height", 200)
    col_spacing = layout.get("column_spacing", 350)
    row_spacing = layout.get("row_spacing", 300)

    selected = nuke.selectedNodes("Read")
    if not selected:
        nuke.message("Select one or more Read nodes first.")
    else:
        # Parse shot names and version labels for each selected node
        entries = []  # list of (shot_name, version_label, node)
        for node in selected:
            filepath = node["file"].value()
            filename = os.path.basename(filepath)
            shot_name = _extract_shot_name(filename, shot_regex)
            ver_label = _extract_version_label(filename)
            if shot_name:
                entries.append((shot_name, ver_label, node))

        if not entries:
            nuke.message("Could not parse shot names from selected Read nodes.\nCheck shot_regex in config.")
        else:
            # Find versions with progress bar
            total_steps = len(entries) * 2
            task = nuke.ProgressTask("Find versions")
            v0_results = []
            latest_results = []
            cancelled = False
            step = 0

            for shot_name, ver_label, node in entries:
                if task.isCancelled():
                    cancelled = True
                    break

                vfx_dir = _build_vfx_path(shot_name, shot_tree_root, version_subfolder)
                selected_filename = os.path.basename(node["file"].value())

                task.setMessage("Finding v000 for {} {}".format(shot_name, ver_label))
                task.setProgress(int(step / total_steps * 100))
                v0_results.append(_find_version_zero(shot_name, vfx_dir, file_ext))
                step += 1

                task.setMessage("Finding latest for {} {}".format(shot_name, ver_label))
                task.setProgress(int(step / total_steps * 100))
                latest_results.append(_find_latest_version(shot_name, vfx_dir, file_ext, exclude_filename=selected_filename))
                step += 1

            task.setProgress(100)
            del task

            if cancelled:
                nuke.message("Cancelled.")
            else:
                # Layout: to the right of selected nodes
                max_x = max(n.xpos() for _, _, n in entries)
                start_x = max_x + col_spacing + 200
                min_y = min(n.ypos() for _, _, n in entries)
                start_y = min_y

                def _parse_color(val):
                    val = str(val).strip().lstrip("#").replace("0x", "")
                    if len(val) == 6:
                        val += "FF"
                    return int(val, 16)

                colors = config.get("colors", {})
                rows = [
                    ("Selected Versions", _parse_color(colors.get("selected_versions", "4A6FA5FF"))),
                    ("Latest Versions",   _parse_color(colors.get("latest_versions", "7B9F35FF"))),
                    ("Version Zeros",     _parse_color(colors.get("version_zeros", "8C5E3CFF"))),
                ]
                pad_x = 30
                pad_y = 60

                nuke.Undo().begin("Find versions")
                try:
                    for col_idx, (shot_name, ver_label, orig_node) in enumerate(entries):
                        x = start_x + col_idx * col_spacing
                        col_label = "{} {}".format(shot_name, ver_label)

                        for row_idx, (row_label, row_color) in enumerate(rows):
                            y = start_y + row_idx * row_spacing

                            if row_idx == 0:
                                fpath = orig_node["file"].value()
                            elif row_idx == 1:
                                fpath = latest_results[col_idx]
                            else:
                                fpath = v0_results[col_idx]

                            cell_label = col_label
                            if col_idx == 0:
                                cell_label = "{}\n{}".format(row_label, col_label)

                            _create_backdrop(
                                cell_label,
                                x - pad_x, y - pad_y,
                                bd_w, bd_h, row_color,
                            )

                            node_x = x + (bd_w // 2) - pad_x - 40
                            node_y = y + 20

                            if fpath:
                                _create_read(fpath, node_x, node_y)
                            else:
                                ph = nuke.createNode("NoOp", inpanel=False)
                                ph.setName("{}_MISSING".format(shot_name))
                                ph["label"].setValue("NOT FOUND")
                                ph.setXpos(node_x)
                                ph.setYpos(node_y)
                finally:
                    nuke.Undo().end()

                # Build summary
                missing_v0 = ["{} {}".format(e[0], e[1]) for i, e in enumerate(entries) if not v0_results[i]]
                missing_latest = ["{} {}".format(e[0], e[1]) for i, e in enumerate(entries) if not latest_results[i]]
                found_count = len(entries) - len(missing_v0) + len(entries) - len(missing_latest)
                total_count = len(entries) * 2

                summary = "Done! Created nodes for {} versions.\n".format(len(entries))
                summary += "Found {} of {} lookups.\n".format(found_count, total_count)

                if missing_v0:
                    summary += "\nMissing version zeros:\n"
                    for s in missing_v0:
                        summary += "  - {}\n".format(s)

                if missing_latest:
                    summary += "\nMissing latest versions:\n"
                    for s in missing_latest:
                        summary += "  - {}\n".format(s)

                nuke.message(summary)
