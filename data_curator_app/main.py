"""
Main application window for the Data Curator GUI.

This module contains the primary graphical user interface (GUI) for the Data
Curator application, built using tkinter. It provides a visual tool for users
to review, classify, and manage files within a selected directory.

The interface is composed of three main sections:
- A file list on the left, showing all items pending review.
- A large preview pane on the right, which displays the content of the
  selected file (e.g., images, text, PDFs).
- A set of action buttons at the bottom for making decisions on each file.

The application state, including which files have been reviewed, is handled by
the `curator_core` module, ensuring a clean separation between the UI and
the underlying business logic.
"""

import os
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Optional

# Third-party libraries for enhanced previews
from PIL import Image, ImageTk
import fitz  # type: ignore[import]
from pygments import lex  # type: ignore[import]
from pygments.lexers import get_lexer_by_name, TextLexer  # type: ignore[import]
from pygments.styles import get_style_by_name  # type: ignore[import]

# Project-specific imports
from data_curator_app import curator_core as core


class DataCuratorApp(tk.Tk):
    """
    The main window of the Data Curator application, providing a graphical
    interface for reviewing, tagging, and managing files in a repository.

    This class encapsulates all the widgets, application state, and event
    handling logic for the GUI.
    """

    def __init__(self) -> None:
        """Initializes the main application window and its components."""
        super().__init__()

        # --- Basic Window Setup ---
        self.title("Data Curator")
        self.geometry("1200x800")
        self.minsize(800, 600)

        # --- Style Configuration (for a modern look) ---
        self.style = ttk.Style(self)
        self.style.theme_use("clam")  # A clean, modern theme
        self._configure_styles()

        # --- Application State ---
        self.repository_path: str = ""
        self.file_list: list[str] = []
        self.current_file_index: int = -1
        self.last_action: Optional[dict[str, Any]] = None
        self.photo_image: Optional[ImageTk.PhotoImage] = None

        # --- UI Construction ---
        self._create_widgets()
        self._bind_keyboard_shortcuts()

    def _configure_styles(self) -> None:
        """Configures custom styles for ttk widgets to create a polished look."""
        self.style.configure("TButton", font=("Helvetica", 10), padding=5)
        self.style.configure(
            "Accent.TButton",
            font=("Helvetica", 10, "bold"),
            foreground="white",
            background="#007aff",  # A vibrant blue for the primary action
        )
        self.style.map(
            "Accent.TButton",
            background=[("active", "#005fcc")],  # Darker blue on click
        )
        self.style.configure("TLabel", font=("Helvetica", 11))
        self.style.configure("Header.TLabel", font=("Helvetica", 14, "bold"))
        self.style.configure("Status.TLabel", font=("Helvetica", 10))
        self.style.configure("Treeview", rowheight=25, font=("Helvetica", 11))
        self.style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"))

    def _create_widgets(self) -> None:
        """Creates and lays out all the widgets for the application."""
        main_frame = ttk.Frame(self, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Section: Repository Selection ---
        top_frame = self._create_top_frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # --- Main Content: Resizable Panes ---
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # --- Left and Right Panes ---
        left_pane = self._create_left_pane(paned_window)
        right_pane = self._create_right_pane(paned_window)
        paned_window.add(left_pane, weight=1)
        paned_window.add(right_pane, weight=3)

        # --- Bottom Section: Action Buttons ---
        action_frame = self._create_action_frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        # --- Status Bar ---
        self.status_bar = ttk.Label(
            self, text="Ready", relief=tk.SUNKEN, anchor=tk.W, padding=5
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_top_frame(self, parent: ttk.Frame) -> ttk.Frame:
        """Creates the frame for repository selection."""
        frame = ttk.Frame(parent)
        self.repo_button = ttk.Button(
            frame, text="Select Repository", command=self.select_repository
        )
        self.repo_button.pack(side=tk.LEFT, padx=(0, 10))
        self.repo_label = ttk.Label(
            frame, text="No repository selected.", style="Status.TLabel"
        )
        self.repo_label.pack(side=tk.LEFT, anchor="w")
        return frame

    def _create_left_pane(self, parent: ttk.PanedWindow) -> ttk.Frame:
        """Creates the left pane containing the file list and filter."""
        list_frame = ttk.Frame(parent, padding=5)
        ttk.Label(list_frame, text="Files to Review", style="Header.TLabel").pack(
            anchor="w", pady=(0, 5)
        )

        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(list_frame, textvariable=self.filter_var)
        filter_entry.pack(fill=tk.X, pady=(0, 5))
        filter_entry.bind(
            "<KeyRelease>", lambda e: self.load_files(self.filter_var.get())
        )

        self.file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            font=("Helvetica", 12),
            bd=0,
            highlightthickness=0,
        )
        self.file_listbox.pack(fill=tk.BOTH, expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        return list_frame

    def _create_right_pane(self, parent: ttk.PanedWindow) -> ttk.Frame:
        """Creates the right pane for the file preview and tagging."""
        preview_frame = ttk.Frame(parent, padding=5)
        ttk.Label(preview_frame, text="File Preview", style="Header.TLabel").pack(
            anchor="w", pady=(0, 5)
        )

        self.preview_canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        tag_frame = ttk.Frame(preview_frame)
        tag_frame.pack(fill=tk.X, pady=(10, 0))
        self.tag_entry = ttk.Entry(tag_frame)
        self.tag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(tag_frame, text="Add Tag", command=self.add_tag).pack(side=tk.LEFT)

        self.tag_label = ttk.Label(preview_frame, text="Tags: ", wraplength=400)
        self.tag_label.pack(anchor="w", pady=(5, 0))
        return preview_frame

    def _create_action_frame(self, parent: ttk.Frame) -> ttk.Frame:
        """Creates the frame with all the main action buttons."""
        frame = ttk.Frame(parent)
        buttons = [
            (
                "Keep (K)",
                "Accent.TButton",
                lambda: self.process_file("keep_forever"),
                tk.LEFT,
            ),
            (
                "Temp Keep (T)",
                "TButton",
                lambda: self.process_file("keep_90_days"),
                tk.LEFT,
            ),
            ("Rename (R)", "TButton", self.rename_current_file, tk.LEFT),
            ("Open (O)", "TButton", self.open_location, tk.LEFT),
            ("Next (→)", "TButton", self.next_file, tk.LEFT),
            ("DELETE (D)", "TButton", self.delete_current_file, tk.RIGHT),
            ("Undo (Ctrl+Z)", "TButton", self.undo_last_action, tk.RIGHT),
        ]
        for text, style, command, side in buttons:
            ttk.Button(frame, text=text, style=style, command=command).pack(
                side=side, padx=2  # type: ignore[arg-type]
            )
        return frame

    def _bind_keyboard_shortcuts(self) -> None:
        """Binds keyboard shortcuts to application actions for efficiency."""
        self.bind("<KeyPress>", self.handle_keypress)
        self.bind("<Control-z>", lambda e: self.undo_last_action())
        self.bind("<Right>", lambda e: self.next_file())
        self.bind("<Left>", lambda e: self.prev_file())

    def update_status(self, message: str, duration: int = 4000) -> None:
        """
        Updates the status bar with a message, which disappears after a delay.

        Args:
            message: The text to display in the status bar.
            duration: The time in milliseconds before the message clears.
                      If 0, the message is permanent.
        """
        self.status_bar.config(text=message)
        if duration > 0:
            self.after(duration, lambda: self.status_bar.config(text="Ready"))

    def select_repository(self) -> None:
        """Opens a dialog to select a repository and loads its files."""
        path = filedialog.askdirectory(title="Select a Folder to Curate")
        if path:
            self.repository_path = path
            self.repo_label.config(text=f"Current: {self.repository_path}")
            self.update_status(f"Repository loaded: {os.path.basename(path)}")
            self.load_files()

    def load_files(self, filter_text: str = "") -> None:
        """
        Loads files from the selected repository that are pending review.

        It calls the core `scan_directory` function and populates the file listbox.
        An optional filter can be applied to narrow down the results.

        Args:
            filter_text: A string used to filter files by name or tag.
        """
        if not self.repository_path:
            return

        self.file_list = core.scan_directory(self.repository_path, filter_text)
        self.file_listbox.delete(0, tk.END)
        for filename in self.file_list:
            self.file_listbox.insert(tk.END, filename)

        if self.file_list:
            self.file_listbox.selection_set(0)
            self.on_file_select(None)
        else:
            self.show_preview()  # Clear preview if no files are left

    def on_file_select(self, event: Optional[tk.Event]) -> None:
        """
        Triggered when a file is selected in the listbox. It updates the
        current file index and triggers a preview update.
        """
        selections = self.file_listbox.curselection()
        if selections:
            self.current_file_index = selections[0]
            self.show_preview()

    def show_preview(self) -> None:
        """
        Displays a rich preview of the currently selected file. It delegates
        to specific preview handlers based on the file extension.
        """
        self._clear_preview_canvas()

        if not (0 <= self.current_file_index < len(self.file_list)):
            return

        filename = self.file_list[self.current_file_index]
        file_path = os.path.join(self.repository_path, filename)

        # Update the tags display for the selected file.
        tags = core.load_state(self.repository_path).get(filename, {}).get("tags", [])
        self.tag_label.config(text="Tags: " + ", ".join(tags))

        try:
            ext = os.path.splitext(filename)[1].lower()
            preview_handlers = {
                ".png": self._preview_image,
                ".jpg": self._preview_image,
                ".jpeg": self._preview_image,
                ".gif": self._preview_image,
                ".bmp": self._preview_image,
                ".pdf": self._preview_pdf,
                ".csv": self._preview_csv,
            }
            # Use the appropriate handler, or default to text preview.
            handler = preview_handlers.get(ext, self._preview_text)
            handler(file_path, filename)
        except Exception as e:
            self._display_preview_error(filename, e)

    def _clear_preview_canvas(self) -> None:
        """Clears all widgets and drawings from the preview canvas."""
        self.preview_canvas.delete("all")
        for widget in self.preview_canvas.winfo_children():
            widget.destroy()

    def _get_canvas_dimensions(self) -> tuple[int, int]:
        """Returns the current width and height of the preview canvas."""
        # Ensure tkinter has processed pending geometry changes.
        self.preview_canvas.update_idletasks()
        return self.preview_canvas.winfo_width(), self.preview_canvas.winfo_height()

    def _preview_image(self, file_path: str, filename: str) -> None:
        """Displays a preview for an image file."""
        canvas_w, canvas_h = self._get_canvas_dimensions()
        img = Image.open(file_path)
        img.thumbnail((canvas_w - 20, canvas_h - 20), Image.Resampling.LANCZOS)
        self.photo_image = ImageTk.PhotoImage(img)
        self.preview_canvas.create_image(
            canvas_w / 2, canvas_h / 2, anchor=tk.CENTER, image=self.photo_image
        )

    def _preview_pdf(self, file_path: str, filename: str) -> None:
        """Displays a preview of the first page of a PDF file."""
        canvas_w, canvas_h = self._get_canvas_dimensions()
        doc = fitz.open(file_path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        pdf_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        pdf_img.thumbnail((canvas_w - 20, canvas_h - 20), Image.Resampling.LANCZOS)
        self.photo_image = ImageTk.PhotoImage(pdf_img)
        self.preview_canvas.create_image(
            canvas_w / 2, canvas_h / 2, anchor=tk.CENTER, image=self.photo_image
        )
        doc.close()

    def _preview_csv(self, file_path: str, filename: str) -> None:
        """Displays a preview of a CSV file in a scrollable table."""
        canvas_w, canvas_h = self._get_canvas_dimensions()
        csv_frame = ttk.Frame(self.preview_canvas)
        tree = ttk.Treeview(csv_frame, show="headings")
        vsb = ttk.Scrollbar(csv_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(csv_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                tree["columns"] = header
                for col in header:
                    tree.heading(col, text=col)
                    tree.column(col, width=120, anchor="w")
                for i, row in enumerate(reader):
                    if i >= 100:  # Limit rows for performance
                        break
                    if len(row) == len(header):
                        tree.insert("", "end", values=row)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)
        self.preview_canvas.create_window(
            0, 0, window=csv_frame, anchor="nw", width=canvas_w, height=canvas_h
        )

    def _preview_text(self, file_path: str, filename: str) -> None:
        """Displays a preview for a text file with syntax highlighting."""
        text_widget = tk.Text(
            self.preview_canvas,
            wrap=tk.WORD,
            font=("Courier New", 11),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        text_widget.pack(fill="both", expand=True)

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(1024 * 100)  # Read up to 100KB for performance

        try:
            lexer = get_lexer_by_name(os.path.splitext(filename)[1][1:], stripall=True)
        except Exception:
            lexer = TextLexer()  # Default to a plain text lexer

        style = get_style_by_name("solarized-light")
        text_widget.config(background=style.background_color)

        for token, text in lex(content, lexer):
            tag_name = str(token)
            token_style = style.style_for_token(token)
            # Apply styles for color, bold, and italic
            if token_style["color"]:
                text_widget.tag_configure(
                    tag_name, foreground=f"#{token_style['color']}"
                )
            if token_style["bold"]:
                text_widget.tag_configure(tag_name, font=("Courier New", 11, "bold"))
            if token_style["italic"]:
                text_widget.tag_configure(tag_name, font=("Courier New", 11, "italic"))
            text_widget.insert("end", text, (tag_name,))

        text_widget.config(state=tk.DISABLED)

    def _display_preview_error(self, filename: str, error: Exception) -> None:
        """Displays an error message in the preview canvas."""
        error_msg = f"Cannot preview file: {filename}\n\nError: {error}"
        self.preview_canvas.create_text(
            10, 10, anchor=tk.NW, text=error_msg, fill="red", font=("Helvetica", 12)
        )

    def process_file(self, status: str) -> None:
        """
        Records the user's decision (e.g., 'keep_forever') for all selected files.
        """
        indices = self.file_listbox.curselection()
        if not indices:
            self.update_status("No file selected to process.", 2000)
            return

        for i in indices:
            filename = self.file_list[i]
            core.update_file_status(self.repository_path, filename, status)

        self.update_status(f"{len(indices)} file(s) marked as '{status}'")
        self.last_action = None  # Clear undo buffer for this type of action
        self.load_files(self.filter_var.get())

    def delete_current_file(self) -> None:
        """Moves the selected file to the trash after user confirmation."""
        indices = self.file_listbox.curselection()
        if not indices:
            self.update_status("No file selected to delete.", 2000)
            return
        if len(indices) > 1:
            messagebox.showinfo(
                "Undo Limitation", "Deletion and undo only work for one file at a time."
            )
            return

        filename = self.file_list[indices[0]]
        if messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to move '{filename}' to the trash?",
        ):
            file_path = os.path.join(self.repository_path, filename)
            result = core.delete_file(file_path)
            if result:
                self.last_action = result
                self.update_status(f"Moved '{filename}' to trash.")
            else:
                self.last_action = None
                messagebox.showerror("Error", f"Could not delete '{filename}'.")
            self.load_files(self.filter_var.get())

    def rename_current_file(self) -> None:
        """Opens a dialog to rename the currently selected file."""
        if not (0 <= self.current_file_index < len(self.file_list)):
            self.update_status("No file selected to rename.", 2000)
            return

        old_filename = self.file_list[self.current_file_index]
        new_filename = simpledialog.askstring(
            "Rename File", "Enter new name:", initialvalue=old_filename
        )

        if new_filename and new_filename != old_filename:
            old_path = os.path.join(self.repository_path, old_filename)
            result = core.rename_file(old_path, new_filename)
            if result:
                self.last_action = result
                self.update_status(f"Renamed '{old_filename}' to '{new_filename}'")
            else:
                self.last_action = None
                messagebox.showerror(
                    "Error", f"Could not rename to '{new_filename}'. File may exist."
                )
            self.load_files(self.filter_var.get())

    def add_tag(self) -> None:
        """Adds a tag from the entry box to the selected file(s)."""
        tag_to_add = self.tag_entry.get().strip()
        if not tag_to_add:
            return

        indices = self.file_listbox.curselection()
        if not indices:
            self.update_status("No file selected to add a tag.", 2000)
            return

        for i in indices:
            filename = self.file_list[i]
            updated_tags = core.manage_tags(
                self.repository_path, filename, tags_to_add=[tag_to_add]
            )
            # If the currently viewed file is updated, refresh its tag label
            if i == self.current_file_index:
                self.tag_label.config(text="Tags: " + ", ".join(updated_tags))

        self.tag_entry.delete(0, tk.END)
        self.update_status(f"Tag '{tag_to_add}' added to {len(indices)} file(s).")

    def open_location(self) -> None:
        """Opens the file's location in the system's file explorer."""
        if not (0 <= self.current_file_index < len(self.file_list)):
            self.update_status("No file selected to open.", 2000)
            return

        filename = self.file_list[self.current_file_index]
        file_path = os.path.join(self.repository_path, filename)
        core.open_file_location(file_path)
        self.update_status(f"Opened location for '{filename}'")

    def undo_last_action(self) -> None:
        """Reverts the last single file operation (delete or rename)."""
        if not self.last_action:
            messagebox.showinfo("Undo", "There is nothing to undo.")
            return

        action = self.last_action.get("action")
        try:
            if action == "rename":
                old_path = self.last_action["new_path"]
                new_name = os.path.basename(self.last_action["old_path"])
                core.rename_file(old_path, new_name)
                self.update_status(f"Undo rename: Restored '{new_name}'")

            elif action == "delete":
                if core.undo_delete(self.last_action):
                    filename = os.path.basename(self.last_action["original_path"])
                    self.update_status(f"Undo delete: '{filename}' restored.")
                else:
                    messagebox.showerror("Undo Failed", "Could not restore the file.")
                    return  # Keep last_action for another try if it fails.

            else:
                messagebox.showerror(
                    "Undo Error", f"Unknown action '{action}' to undo."
                )
                return

            self.last_action = None  # Clear action after a successful undo.
            self.load_files(self.filter_var.get())

        except Exception as e:
            messagebox.showerror(
                "Undo Failed", f"Could not complete the undo operation.\n\nError: {e}"
            )

    def next_file(self) -> None:
        """Selects the next file in the list, wrapping if necessary."""
        if not self.file_list:
            return
        next_index = (self.current_file_index + 1) % self.file_listbox.size()
        self.file_listbox.selection_clear(0, tk.END)
        self.file_listbox.selection_set(next_index)
        self.on_file_select(None)
        self.file_listbox.see(next_index)  # Ensure the item is visible

    def prev_file(self) -> None:
        """Selects the previous file in the list, wrapping if necessary."""
        if not self.file_list:
            return
        prev_index = (self.current_file_index - 1) % self.file_listbox.size()
        self.file_listbox.selection_clear(0, tk.END)
        self.file_listbox.selection_set(prev_index)
        self.on_file_select(None)
        self.file_listbox.see(prev_index)  # Ensure the item is visible

    def handle_keypress(self, event: tk.Event) -> None:
        """
        Handles global keypress events for quick actions, ignoring them if an
        input field has focus.
        """
        # Ignore keypresses if the user is typing in an entry widget.
        if isinstance(self.focus_get(), (ttk.Entry, tk.Text)):
            return

        key_map = {
            "k": lambda: self.process_file("keep_forever"),
            "t": lambda: self.process_file("keep_90_days"),
            "d": self.delete_current_file,
            "r": self.rename_current_file,
            "o": self.open_location,
        }
        action = key_map.get(event.keysym.lower())
        if action:
            action()


if __name__ == "__main__":
    app = DataCuratorApp()
    app.mainloop()
