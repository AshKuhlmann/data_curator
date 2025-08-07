import os
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

# Third-party libraries for enhanced previews
from PIL import Image, ImageTk  # type: ignore[import]
import fitz  # type: ignore[import]
from pygments import lex  # type: ignore[import]
from pygments.lexers import get_lexer_by_name, TextLexer  # type: ignore[import]
from pygments.styles import get_style_by_name  # type: ignore[import]

# Project-specific imports
from data_curator_app import curator_core as core


class DataCuratorApp(tk.Tk):
    """
    A polished graphical interface for reviewing, tagging, and managing files
    in a repository.
    """

    def __init__(self) -> None:
        """Initializes the main application window and its components."""
        super().__init__()

        # --- Basic Window Setup ---
        self.title("Data Curator")
        self.geometry("1200x800")
        self.minsize(800, 600)  # Set a minimum size for the window

        # --- Style Configuration (for a modern look) ---
        self.style = ttk.Style(self)
        self.style.theme_use("clam")  # A clean, modern theme
        self.configure_styles()

        # --- Application State ---
        self.repository_path = ""
        self.file_list: list[str] = []
        self.current_file_index = -1
        self.last_action: dict[str, Any] | None = None
        self.photo_image: ImageTk.PhotoImage | None = (
            None  # Keep a reference to the image
        )

        # --- UI Construction ---
        self.create_widgets()
        self.bind_keyboard_shortcuts()

    def configure_styles(self) -> None:
        """Configures custom styles for ttk widgets."""
        self.style.configure("TButton", font=("Helvetica", 10), padding=5)
        self.style.configure(
            "Accent.TButton",
            font=("Helvetica", 10, "bold"),
            foreground="white",
            background="#007aff",  # A nice blue for the primary action
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

    def create_widgets(self) -> None:
        """Creates and lays out all the widgets for the application."""
        # Use a main frame for better padding control
        main_frame = ttk.Frame(self, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Section: Repository Selection ---
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.repo_button = ttk.Button(
            top_frame, text="Select Repository", command=self.select_repository
        )
        self.repo_button.pack(side=tk.LEFT, padx=(0, 10))
        self.repo_label = ttk.Label(
            top_frame, text="No repository selected.", style="Status.TLabel"
        )
        self.repo_label.pack(side=tk.LEFT, anchor="w")

        # --- Main Content: Resizable Panes ---
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # --- Left Pane: File List ---
        list_frame = ttk.Frame(paned_window, padding=5)
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
        paned_window.add(list_frame, weight=1)  # Add to pane

        # --- Right Pane: File Preview ---
        preview_frame = ttk.Frame(paned_window, padding=5)
        ttk.Label(preview_frame, text="File Preview", style="Header.TLabel").pack(
            anchor="w", pady=(0, 5)
        )

        self.preview_canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        # Tagging Section
        tag_frame = ttk.Frame(preview_frame)
        tag_frame.pack(fill=tk.X, pady=(10, 0))
        self.tag_entry = ttk.Entry(tag_frame)
        self.tag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(tag_frame, text="Add Tag", command=self.add_tag).pack(side=tk.LEFT)
        self.tag_label = ttk.Label(preview_frame, text="Tags: ", wraplength=400)
        self.tag_label.pack(anchor="w", pady=(5, 0))
        paned_window.add(preview_frame, weight=3)  # Add to pane

        # --- Bottom Section: Action Buttons ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            action_frame,
            text="Keep (K)",
            style="Accent.TButton",
            command=lambda: self.process_file("keep_forever"),
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            action_frame,
            text="Temp Keep (T)",
            command=lambda: self.process_file("keep_90_days"),
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            action_frame, text="Rename (R)", command=self.rename_current_file
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Open (O)", command=self.open_location).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(action_frame, text="Next (→)", command=self.next_file).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Button(
            action_frame, text="DELETE (D)", command=self.delete_current_file
        ).pack(side=tk.RIGHT, padx=2)
        ttk.Button(
            action_frame, text="Undo (Ctrl+Z)", command=self.undo_last_action
        ).pack(side=tk.RIGHT, padx=2)

        # --- Status Bar ---
        self.status_bar = ttk.Label(
            self,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=5,
            style="Status.TLabel",
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def bind_keyboard_shortcuts(self) -> None:
        """Binds keyboard shortcuts to application actions."""
        self.bind("<KeyPress>", self.handle_keypress)
        self.bind("<Control-z>", lambda e: self.undo_last_action())
        self.bind("<Right>", lambda e: self.next_file())
        self.bind("<Left>", lambda e: self.prev_file())

    def update_status(self, message: str, duration: int = 3000) -> None:
        """Updates the status bar with a message for a set duration."""
        self.status_bar.config(text=message)
        if duration > 0:
            self.after(duration, lambda: self.status_bar.config(text="Ready"))

    def select_repository(self) -> None:
        """Opens a dialog to select a repository and loads its files."""
        path = filedialog.askdirectory()
        if path:
            self.repository_path = path
            self.repo_label.config(text=f"Current: {self.repository_path}")
            self.update_status(f"Repository loaded: {os.path.basename(path)}")
            self.load_files()

    def load_files(self, filter_text: str = "") -> None:
        """Loads and filters files from the repository."""
        if not self.repository_path:
            return
        state = core.load_state(self.repository_path)
        all_files = os.listdir(self.repository_path)

        # Filter out files that have already been processed
        self.file_list = [
            f for f in all_files if f not in state and not f.startswith(".")
        ]

        # Apply user's filter text
        if filter_text:
            self.file_list = [
                f for f in self.file_list if filter_text.lower() in f.lower()
            ]

        self.file_listbox.delete(0, tk.END)
        for filename in self.file_list:
            self.file_listbox.insert(tk.END, filename)

        if self.file_list:
            self.file_listbox.selection_set(0)
            self.on_file_select(None)

    def on_file_select(self, event: tk.Event | None) -> None:
        """Handles the event when a file is selected in the listbox."""
        selections = self.file_listbox.curselection()
        if selections:
            self.current_file_index = selections[0]
            self.show_preview()

    def show_preview(self) -> None:
        """Displays a rich preview of the currently selected file."""
        self.preview_canvas.delete("all")
        for widget in self.preview_canvas.winfo_children():
            widget.destroy()

        if not (0 <= self.current_file_index < len(self.file_list)):
            return

        filename = self.file_list[self.current_file_index]
        file_path = os.path.join(self.repository_path, filename)
        tags = core.load_state(self.repository_path).get(filename, {}).get("tags", [])
        self.tag_label.config(text="Tags: " + ", ".join(tags))

        try:
            ext = os.path.splitext(filename)[1].lower()
            canvas_w = self.preview_canvas.winfo_width()
            canvas_h = self.preview_canvas.winfo_height()

            # --- Image Preview ---
            if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
                img = Image.open(file_path)
                img.thumbnail((canvas_w - 20, canvas_h - 20), Image.Resampling.LANCZOS)
                self.photo_image = ImageTk.PhotoImage(img)
                self.preview_canvas.create_image(
                    canvas_w / 2, canvas_h / 2, anchor=tk.CENTER, image=self.photo_image
                )

            # --- PDF Preview ---
            elif ext == ".pdf":
                doc = fitz.open(file_path)
                page = doc.load_page(0)
                pix = page.get_pixmap()
                pdf_img: Image.Image = Image.frombytes(
                    "RGB",
                    (pix.width, pix.height),
                    pix.samples,
                )
                pdf_img.thumbnail(
                    (canvas_w - 20, canvas_h - 20), Image.Resampling.LANCZOS
                )
                self.photo_image = ImageTk.PhotoImage(pdf_img)
                self.preview_canvas.create_image(
                    canvas_w / 2, canvas_h / 2, anchor=tk.CENTER, image=self.photo_image
                )
                doc.close()

            # --- CSV Preview ---
            elif ext == ".csv":
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
                            if i >= 100:
                                break  # Limit rows for performance
                            if len(row) == len(header):
                                tree.insert("", "end", values=row)

                vsb.pack(side="right", fill="y")
                hsb.pack(side="bottom", fill="x")
                tree.pack(side="left", fill="both", expand=True)
                self.preview_canvas.create_window(
                    0, 0, window=csv_frame, anchor="nw", width=canvas_w, height=canvas_h
                )

            # --- Text/Code Preview with Syntax Highlighting ---
            else:
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
                    content = f.read(1024 * 100)  # Read up to 100KB

                try:
                    lexer = get_lexer_by_name(
                        os.path.splitext(filename)[1][1:], stripall=True
                    )
                except Exception:
                    lexer = TextLexer()

                style = get_style_by_name("solarized-light")
                text_widget.config(background=style.background_color)

                for token, text in lex(content, lexer):
                    tag_name = str(token)
                    color = style.style_for_token(token)["color"]
                    if color:
                        text_widget.tag_configure(tag_name, foreground=f"#{color}")
                    text_widget.insert("end", text, (tag_name,))

                text_widget.config(state=tk.DISABLED)

        except Exception as e:
            error_msg = f"Cannot preview file: {filename}\n\nError: {e}"
            self.preview_canvas.create_text(
                10, 10, anchor=tk.NW, text=error_msg, fill="red", font=("Helvetica", 12)
            )

    def process_file(self, status: str) -> None:
        """Records the user's decision for all selected files."""
        indices = self.file_listbox.curselection()
        if not indices:
            return

        for i in indices:
            filename = self.file_list[i]
            core.update_file_status(self.repository_path, filename, status)

        self.update_status(f"{len(indices)} file(s) marked as '{status}'")
        self.last_action = (
            None  # This was a deliberate action, not undoable in the same way
        )
        self.load_files(self.filter_var.get())

    def delete_current_file(self) -> None:
        """Moves the selected file to the trash after confirmation."""
        indices = self.file_listbox.curselection()
        if not indices:
            return
        if len(indices) > 1:
            messagebox.showinfo(
                "Undo Limitation", "Can only delete and undo one file at a time."
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
        """Renames the currently selected file."""
        if not (0 <= self.current_file_index < len(self.file_list)):
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
        """Adds a tag to the selected file(s)."""
        tag = self.tag_entry.get()
        if not tag:
            return

        indices = self.file_listbox.curselection()
        if not indices:
            return

        for i in indices:
            filename = self.file_list[i]
            tags = core.manage_tags(self.repository_path, filename, tags_to_add=[tag])
            if i == self.current_file_index:
                self.tag_label.config(text="Tags: " + ", ".join(tags))

        self.tag_entry.delete(0, tk.END)
        self.update_status(f"Tag '{tag}' added to {len(indices)} file(s).")
        self.show_preview()  # Refresh preview to show new tag

    def open_location(self) -> None:
        """Opens the file's location in the system's file explorer."""
        if not (0 <= self.current_file_index < len(self.file_list)):
            return

        filename = self.file_list[self.current_file_index]
        file_path = os.path.join(self.repository_path, filename)
        core.open_file_location(file_path)
        self.update_status(f"Opened location for {filename}")

    def undo_last_action(self) -> None:
        """Reverts the last file operation (delete or rename)."""
        if not self.last_action:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return

        action = self.last_action.get("action")
        try:
            if action == "rename":
                old_path = self.last_action["new_path"]
                new_name = os.path.basename(self.last_action["old_path"])
                core.rename_file(old_path, new_name)
                self.update_status(f"Undo rename: '{os.path.basename(old_path)}'")

            elif action == "delete":
                if core.undo_delete(self.last_action):
                    filename = os.path.basename(self.last_action["original_path"])
                    self.update_status(f"Undo delete: '{filename}' restored.")
                else:
                    messagebox.showerror("Undo Failed", "Could not restore the file.")
                    return  # Keep last_action for another try

            else:
                messagebox.showerror("Undo", "Unknown action to undo.")
                return

            self.last_action = None  # Clear action after undo
            self.load_files(self.filter_var.get())

        except Exception as e:
            messagebox.showerror(
                "Undo Failed", f"Could not undo the last action.\n\nError: {e}"
            )

    def next_file(self) -> None:
        """Selects the next file in the list."""
        if self.current_file_index < self.file_listbox.size() - 1:
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_file_index + 1)
            self.on_file_select(None)

    def prev_file(self) -> None:
        """Selects the previous file in the list."""
        if self.current_file_index > 0:
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_file_index - 1)
            self.on_file_select(None)

    def handle_keypress(self, event: tk.Event) -> None:
        """Handles global keypress events for quick actions."""
        # Ignore keypresses if an entry widget has focus
        if isinstance(self.focus_get(), (ttk.Entry, tk.Text)):
            return

        key = event.keysym.lower()
        if key == "k":
            self.process_file("keep_forever")
        elif key == "t":
            self.process_file("keep_90_days")
        elif key == "d":
            self.delete_current_file()
        elif key == "r":
            self.rename_current_file()
        elif key == "o":
            self.open_location()


if __name__ == "__main__":
    app = DataCuratorApp()
    app.mainloop()
