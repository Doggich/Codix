import urwid
import os
import sys
import re
import difflib
import shutil
import datetime
import time
from modules.ProjectConstraint import *
from modules.utils import is_safe_path


class NanoEditor:
    def __init__(self, filename):
        self.filename = os.path.abspath(filename)
        self.text = ""
        self.modified = False
        self.history = [""]
        self.history_index = 0
        self.mode = "edit"
        self.search_query = ""
        self.search_direction = 1
        self.search_cache = {}
        self.cached_positions = []
        self.current_find_pos = -1
        self.replace_query = ""
        self.last_autosave_time = time.time()
        self.stats_update_time = 0
        self.line_count = 0
        self.word_count = 0
        self.char_count = 0
        self.show_line_numbers = True

        # Widgets
        self.top_bar = urwid.Text("", align='center')
        self.status_bar = urwid.Text("", align='center')
        self.edit_widget = urwid.Edit(multiline=True, wrap='space')
        self.bottom_bar = urwid.Text("^G Help   ^O Save   ^X Exit   ^S Search   ^R Replace   F6 Line Numbers",
                                     align='left')
        self.message_widget = urwid.Text("")
        self.search_widget = urwid.Edit(caption="Search: ")
        self.replace_widget = urwid.Edit(caption="Replace with: ")
        self.stats_widget = urwid.Text("", align='right')
        self.line_numbers_widget = urwid.Text("", align='right')
        self.editor_container = self.build_editor_container()

        # Create status bar container
        status_container = urwid.Columns([
            ('weight', 3, urwid.AttrMap(self.status_bar, 'status')),
            ('weight', 1, urwid.AttrMap(self.stats_widget, 'status'))
        ])

        # Frame
        self.frame = urwid.Frame(
            body=urwid.Filler(self.editor_container, valign='top'),
            header=urwid.AttrMap(
                urwid.Pile([urwid.AttrMap(self.top_bar, 'header'),
                            status_container
                            ]), 'header'
            ),
            footer=urwid.AttrMap(self.bottom_bar, 'footer'),
        )

        urwid.connect_signal(self.edit_widget, 'change', self.on_text_change)
        self.update_title()
        self.update_status()
        self.update_stats()
        self.update_line_numbers()

    def build_editor_container(self):
        """Build editor container with current line numbers state"""
        widgets = []
        if self.show_line_numbers:
            widgets.append(('fixed', 6, urwid.AttrMap(self.line_numbers_widget, 'line_numbers')))
        widgets.append(self.edit_widget)
        return urwid.Columns(widgets, dividechars=1)

    def update_line_numbers(self):
        """Update line numbers"""
        if not self.show_line_numbers:
            self.line_numbers_widget.set_text("")
            return

        text = self.edit_widget.get_edit_text()
        if text:
            line_count = text.count('\n') + 1
        else:
            line_count = 1

        if line_count > 5000:
            numbers = "\n".join([" " * 5] * line_count)
        else:
            max_width = len(str(line_count))
            numbers = [str(i).rjust(max_width) for i in range(1, line_count + 1)]
            numbers = "\n".join(numbers)
        self.line_numbers_widget.set_text(numbers)

    def toggle_line_numbers(self):
        """Toggle line numbers visibility"""
        self.show_line_numbers = not self.show_line_numbers
        self.editor_container = self.build_editor_container()
        self.frame.body = urwid.Filler(self.editor_container, valign='top')
        self.update_line_numbers()
        action = "ON" if self.show_line_numbers else "OFF"
        self.show_message(f"Line numbers: {action}")
        if hasattr(self, 'loop'):
            self.loop.draw_screen()

    def update_status(self):
        """Update status bar"""
        pos = self.edit_widget.edit_pos
        text = self.edit_widget.get_edit_text()
        if text:
            line = text.count('\n', 0, pos) + 1
            last_nl = text.rfind('\n', 0, pos)
            col = pos - last_nl if last_nl != -1 else pos + 1
        else:
            line, col = 1, 1
        mod_status = "*" if self.modified else ""
        autosave_status = ""
        if time.time() - self.last_autosave_time < 5:
            autosave_status = " [Autosaved]"
        self.status_bar.set_text(f"Line {line}, Col {col} {mod_status}{autosave_status}")

    def update_stats(self):
        """Update document statistics"""
        text = self.edit_widget.get_edit_text()
        current_time = time.time()
        if current_time - self.stats_update_time > 1.0 or not text:
            self.char_count = len(text)
            self.line_count = text.count('\n') + 1 if text else 0
            self.word_count = len(re.findall(r'\S+', text)) if text else 0
            self.stats_update_time = current_time
        self.stats_widget.set_text(f"Lines: {self.line_count}  Words: {self.word_count}  Chars: {self.char_count}")

    def update_title(self):
        """Update title"""
        status = " [Modified]" if self.modified else ""
        filename_display = os.path.basename(self.filename)
        if len(filename_display) > 35:
            filename_display = "..." + filename_display[-32:]
        title = f"  Codix 0.3         {filename_display}{status}"
        self.top_bar.set_text(title)

    def on_text_change(self, widget, new_text):
        """Handle text changes"""
        if new_text == self.text:
            return

        old_text = self.text
        self.text = new_text
        self.modified = True
        self.update_title()
        self.update_status()
        self.update_stats()
        self.update_line_numbers()

        if self.history_index == len(self.history) - 1:
            if len(self.history) >= MAX_HISTORY_SIZE:
                self.history.pop(0)
                self.history_index = len(self.history) - 1

            if len(old_text) > HISTORY_DIFF_THRESHOLD or len(new_text) > HISTORY_DIFF_THRESHOLD:
                diff = list(difflib.ndiff(
                    old_text.splitlines(True),
                    new_text.splitlines(True)
                ))
                history_entry = ('diff', diff, datetime.datetime.now())
            else:
                history_entry = ('full', new_text, datetime.datetime.now())

            self.history.append(history_entry)
            self.history_index += 1

    def save_file(self, autosave=False):
        """Save file"""
        if not is_safe_path(self.filename):
            if not autosave:
                self.show_message(f"ERROR: Unsafe path '{self.filename}'", style='warning')
            return False

        try:
            temp_name = self.filename + ".codix_tmp"
            with open(temp_name, "w", encoding="utf-8", errors="replace") as f:
                f.write(self.text)

            if os.path.exists(self.filename):
                backup_name = self.filename + ".codix_bak"
                shutil.copy2(self.filename, backup_name)

            os.replace(temp_name, self.filename)
            self.modified = False
            self.update_title()
            if not autosave:
                self.show_message(f"Saved: {os.path.basename(self.filename)}")
            return True
        except Exception as e:
            if not autosave:
                self.show_message(f"ERROR saving: {str(e)}", style='warning')
            return False

    def show_message(self, msg, timeout=2.0, style='message'):
        """Show temporary message"""
        self.message_widget.set_text(str(msg)[:200])
        if style == 'warning':
            widget = urwid.AttrMap(self.message_widget, 'warning')
        else:
            widget = urwid.AttrMap(self.message_widget, 'message')
        self.frame.footer = urwid.AttrMap(
            urwid.Pile([
                widget,
                urwid.Divider(" "),
                self.bottom_bar
            ]), 'footer'
        )
        self.loop.set_alarm_in(timeout, self.hide_message)

    def hide_message(self, loop=None, user_data=None):
        """Hide message"""
        self.frame.footer = urwid.AttrMap(self.bottom_bar, 'footer')
        self.mode = "edit"

    def show_help(self):
        """Show help"""
        help_text = [
            "Codix Help",
            "",
            "Basic commands:",
            "Ctrl+O - Save file",
            "Ctrl+X - Exit",
            "Ctrl+Z - Undo",
            "Ctrl+Y - Redo",
            "Ctrl+S - Search",
            "Ctrl+R - Replace",
            "F3     - Next search result",
            "F6     - Toggle line numbers",  # Updated
            "",
            "Autosave: every 5 minutes"
        ]
        self.show_message("\n".join(help_text), timeout=6.0)

    def start_search(self):
        """Start search"""
        self.mode = "search"
        self.search_query = ""
        self.search_widget.set_edit_text("")
        self.cached_positions = []
        self.search_cache.clear()
        self.frame.footer = urwid.AttrMap(
            urwid.Pile([
                urwid.AttrMap(self.search_widget, 'search_bar'),
                urwid.Text("Enter: Search  Esc: Cancel  F3: Next"),
                self.bottom_bar
            ]), 'footer'
        )
        self.loop.widget = self.frame

    def start_replace(self):
        """Start replace"""
        self.mode = "replace"
        self.search_query = ""
        self.replace_query = ""
        self.search_widget.set_edit_text("")
        self.replace_widget.set_edit_text("")
        self.cached_positions = []
        self.search_cache.clear()
        self.current_find_pos = -1
        self.frame.footer = urwid.AttrMap(
            urwid.Pile([urwid.AttrMap(self.search_widget, 'search_bar'),
                        urwid.AttrMap(self.replace_widget, 'replace_bar'),
                        urwid.Text("Enter: Find/Replace  F3: Next  Esc: Cancel"),
                        self.bottom_bar
                        ]), 'footer'
        )
        self.loop.widget = self.frame

    def build_search_cache(self):
        """Build positions cache"""
        if not self.search_query:
            return

        if self.search_query in self.search_cache:
            self.cached_positions = self.search_cache[self.search_query]
            return

        self.cached_positions = []
        pattern = re.escape(self.search_query)
        for match in re.finditer(pattern, self.text, re.IGNORECASE):
            self.cached_positions.append(match.start())

        self.search_cache[self.search_query] = self.cached_positions
        if len(self.search_cache) > 20:
            oldest_key = next(iter(self.search_cache))
            del self.search_cache[oldest_key]

    def perform_search(self, forward=True):
        """Perform search"""
        if not self.search_query:
            self.show_message("Enter search text")
            return False

        self.build_search_cache()
        if not self.cached_positions:
            self.show_message("Nothing found")
            return False

        current_pos = self.edit_widget.edit_pos
        if forward:
            next_positions = [p for p in self.cached_positions if p > current_pos]
            if next_positions:
                target_pos = min(next_positions)
            else:
                target_pos = min(self.cached_positions, default=current_pos)
        else:
            prev_positions = [p for p in self.cached_positions if p < current_pos]
            if prev_positions:
                target_pos = max(prev_positions)
            else:
                target_pos = max(self.cached_positions, default=current_pos)

        self.current_find_pos = target_pos
        self.edit_widget.set_edit_pos(target_pos)
        self.update_status()
        self.update_line_numbers()
        return True

    def replace_current(self):
        """Replace found text"""
        if self.current_find_pos == -1 or not self.search_query:
            return False

        text = self.edit_widget.get_edit_text()
        search_len = len(self.search_query)
        if text[self.current_find_pos:self.current_find_pos + search_len] != self.search_query:
            return False

        new_text = (text[:self.current_find_pos] +
                    self.replace_query +
                    text[self.current_find_pos + search_len:])
        self.edit_widget.set_edit_text(new_text)
        self.edit_widget.set_edit_pos(self.current_find_pos + len(self.replace_query))
        self.modified = True
        self.update_line_numbers()
        return True

    def handle_search(self, key):
        """Handle search"""
        if key == 'enter':
            self.search_query = self.search_widget.get_edit_text()
            if self.search_query and self.perform_search():
                self.show_message(f"Found: '{self.search_query}'")
            else:
                self.show_message(f"Not found: '{self.search_query}'")
        elif key == 'esc':
            self.hide_message()
        else:
            return self.search_widget.keypress((), key)

    def handle_replace(self, key):
        """Handle replace"""
        if key == 'enter':
            self.search_query = self.search_widget.get_edit_text()
            self.replace_query = self.replace_widget.get_edit_text()
            if self.current_find_pos != -1 and self.replace_current():
                self.show_message(f"Replaced: '{self.search_query}' -> '{self.replace_query}'")
            if self.perform_search():
                self.show_message(f"Found: '{self.search_query}'")
            else:
                self.show_message(f"No more found: '{self.search_query}'")
        elif key == 'f3':
            self.perform_search()
        elif key == 'esc':
            self.hide_message()
        else:
            if self.search_widget._edit_pos is not None:
                return self.search_widget.keypress((), key)
            else:
                return self.replace_widget.keypress((), key)

    def handle_keys(self, key):
        """Main key handler"""
        self.update_status()
        self.update_stats()

        if self.mode == "search":
            result = self.handle_search(key)
            if key == 'enter':
                self.update_line_numbers()
            return result
        elif self.mode == "replace":
            result = self.handle_replace(key)
            if key in ('enter', 'f3'):
                self.update_line_numbers()
            return result

        # Edit mode
        if key == 'ctrl x':
            raise urwid.ExitMainLoop()
        elif key == 'ctrl o':
            self.save_file()
        elif key == 'ctrl g' or key == 'f1':
            self.show_help()
        elif key == 'f3':
            if self.search_query:
                if not self.perform_search():
                    self.show_message("No more matches")
            else:
                self.start_search()
        elif key == 'ctrl s':
            self.start_search()
        elif key == 'ctrl r':
            self.start_replace()
        elif key == 'ctrl z':
            if self.history_index > 0:
                self.history_index -= 1
                self.apply_history_state()
        elif key == 'ctrl y':
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.apply_history_state()
        elif key == 'f6':  # Changed to F6
            self.toggle_line_numbers()
        else:
            return key

        # Autosave
        if time.time() - self.last_autosave_time > AUTOSAVE_INTERVAL:
            if self.save_file(autosave=True):
                self.last_autosave_time = time.time()
                self.update_status()
        return True

    def apply_history_state(self):
        """Restore state from history"""
        if self.history_index < 0 or self.history_index >= len(self.history):
            return
        entry = self.history[self.history_index]
        if isinstance(entry, tuple) and entry[0] == 'diff':
            self.edit_widget.set_edit_text("")
        else:
            text = entry[1] if isinstance(entry, tuple) else entry
            self.edit_widget.set_edit_text(text)
        self.text = self.edit_widget.get_edit_text()
        self.modified = (self.history_index != len(self.history) - 1)
        self.update_title()
        self.update_status()
        self.update_stats()
        self.update_line_numbers()

    def set_initial_text(self, content):
        """Initialize text"""
        if len(content) > MAX_FILE_SIZE:
            content = "FILE TOO LARGE FOR EDITING\nSize: {} > {}".format(
                len(content), MAX_FILE_SIZE)
        self.edit_widget.set_edit_text(content)
        self.text = content
        self.history = [content]
        self.history_index = 0
        self.modified = False
        self.update_title()
        self.update_status()
        self.update_stats()
        self.update_line_numbers()

    def run(self):
        """Run editor"""
        self.loop = urwid.MainLoop(
            self.frame,
            palette=PALETTE,
            unhandled_input=self.handle_keys,
            handle_mouse=False
        )
        try:
            self.loop.screen.set_terminal_properties(colors=256)
        except Exception:
            pass
        self.loop.run()


def main():
    """Entry point"""
    if "-r" in sys.argv and len(sys.argv) >= 3:
        # We find the index -r and take the next argument as the file name
        r_index = sys.argv.index("-r")
        if r_index + 1 < len(sys.argv):
            filename_to_read = sys.argv[r_index + 1]
            try:
                with open(filename_to_read, "r", encoding="utf-8", errors="ignore") as file:
                    print(file.read())
            except Exception as e:
                print(f"Ошибка: {str(e)}")
            sys.exit()

        # Normal logic for the editor
    if len(sys.argv) > 1 and not "-r" in sys.argv:
        filename = sys.argv[1]
    else:
        base = "new_document"
        counter = 1
        while os.path.exists(f"{base}{counter}.txt"):
            counter += 1
        filename = f"{base}{counter}.txt"

    editor = NanoEditor(filename)

    if os.path.exists(filename):
        try:
            file_size = os.path.getsize(filename)
            if file_size > MAX_FILE_SIZE:
                content = "FILE TOO LARGE FOR EDITING\nSize: {} > {}".format(
                    file_size, MAX_FILE_SIZE)
            else:
                with open(filename, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            editor.set_initial_text(content)
        except Exception as e:
            editor.set_initial_text("")
            editor.show_message(f"ERROR reading: {str(e)}", style='warning')
    else:
        editor.set_initial_text("")
        editor.modified = True
        editor.update_title()

    try:
        editor.run()
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
