# Codix Retro: Quickstart & Support Guide
 
**Codix** ― a lightweight, console-based text editor inspired by nano.
Key points: minimalism, TUI via urwid, undo/redo history, search/replace, autosave, optional line numbers.
Use for fast editing of simple text files in the terminal.

## Main hotkeys

| Shortcut   | Action              |
|------------|---------------------|
| `Ctrl + O` | Safe file           |
| `Ctrl + X` | Exit editor         |
| `Ctrl + S` | Search              |
| `Ctrl + R` | Replace             |
| `F3`       | Next search result  |
| `F6`       | Toggle line numbers |
| `Ctrl + Z` | Undo                |
| `Ctrl + Y` | Redo                |
| `Ctrl + G` | Help                |

## Startup

### Read file (read-only):
```commandline
python codix.py -r filename.txt
```

### Open/create file for editing:
```commandline
python codix.py myfile.txt
```

### No filename specified:
Creates a file named `new_document(N).txt`

## Quick Logic Reference

* **History**: Undo/redo handled via a history list; large texts use difflib to store diffs.
* **Files**: Saved via temp file and .bak backup before replacing; safe path checking via is_safe_path.
* **Line Numbers**: Toggle with `F6`; for huge files (5k+ lines), suppress actual numbers for speed.
* **Search**: `Ctrl+S/F3` opens search; jumps to next match (cache used for performance).
* **Replace**: `Ctrl+R` for replace, only replaces the current match, not global.
* **Autosave**: Runs every 5 minutes or on demand, shows `[Autosaved]` in status bar.

## Possible troubles

* Won’t open files larger than `MAX_FILE_SIZE` (see ProjectConstraint.py).
* urwid might have rendering/input quirks in some terminals.
* Plain text only (no syntax highlighting, no code hints).
* Undo/Redo can be buggy on ultra-large changes (difflib quirks).
* Temporary `.bak` and `.codix_tmp` files stored alongside your file.
* Some messages/errors are in Russian.

## Support/Debug Checklist
* **Edit logic**: Key routines are `on_text_change` and `apply_history_state` — history bugs usually start here.
* **File issues**: Most file/path errors are due to `is_safe_path` or permissions.
* **UI**: Widget tree built in `build_editor_container` (watch line number logic).
* **Autosave**: See last_autosave_time and `AUTOSAVE_INTERVAL`.

## Quick Hotkey Recap
* `Ctrl+O` — Save
* `Ctrl+X` — Exit
* `Ctrl+Z/Y` — Undo/Redo
* `Ctrl+S` — Search
* `Ctrl+R` — Replace
* `F3` — Next search result

## Where to Configure
* **Size limits**: `modules/ProjectConstraint.py`
* **Color palette/theme**: check `PALETTE` in your codebase
* **Path safety logic**: `modules/utils.py -> is_safe_path`
* **Hotkey handling**: `handle_keys()`

## Remember!
* Do not edit the history directly — that risks undo bugs.
* urwid may crash on bad keypress; debug with prints/logs as needed.
* Always check permissions and symlink tricks if file ops fail.
* This is not an IDE — no autocomplete, no paren matching etc.
* Want to refactor? Start by rewriting the change history subsystem.

#### Happy hacking!

![boy-kisser-shy.gif](resources/boy-kisser-shy.gif)

