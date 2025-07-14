"""GUI entry point for the Data Curator application."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import csv

from typing import Any

from PIL import Image, ImageTk  # type: ignore[import]

# Adjust the import to reflect the project structure
from data_curator_app import curator_core as core


class DataCuratorApp(tk.Tk):
    """Graphical interface for reviewing and managing files."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Data Curator")
        self.geometry("1000x700")

        self.repository_path = ""
        self.file_list: list[str] = []
        self.current_file_index = -1
        self.last_action: dict[str, Any] | None = None

        self.create_widgets()
        self.bind("<KeyPress>", self.handle_keypress)

    def create_widgets(self) -> None:
        """Create all widgets used by the interface."""

        top_frame = tk.Frame(self, padx=10, pady=10)
        top_frame.pack(fill=tk.X)

        self.repo_button = tk.Button(
            top_frame, text="Select Repository", command=self.select_repository
        )
        self.repo_button.pack(side=tk.LEFT)

        self.repo_label = tk.Label(top_frame, text="No repository selected.", fg="gray")
        self.repo_label.pack(side=tk.LEFT, padx=10)

        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_columnconfigure(1, weight=3)
        main_frame.grid_rowconfigure(0, weight=1)

        list_frame = tk.Frame(main_frame)
        list_frame.grid(row=0, column=0, sticky="nswe", padx=(0, 10))
        list_frame.grid_rowconfigure(2, weight=1)

        tk.Label(
            list_frame, text="Files to Review", font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.filter_var = tk.StringVar()
        filter_entry = tk.Entry(list_frame, textvariable=self.filter_var)
        filter_entry.grid(row=1, column=0, sticky="we", pady=(5, 5))
        filter_entry.bind(
            "<KeyRelease>", lambda e: self.load_files(self.filter_var.get())
        )

        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=2, column=0, sticky="nswe")
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        preview_frame = tk.Frame(main_frame)
        preview_frame.grid(row=0, column=1, sticky="nswe")
        preview_frame.grid_rowconfigure(1, weight=1)

        tk.Label(
            preview_frame, text="File Preview", font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.preview_canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=0)
        self.preview_canvas.grid(row=1, column=0, sticky="nswe")

        tag_frame = tk.Frame(preview_frame)
        tag_frame.grid(row=2, column=0, sticky="we", pady=(5, 0))
        tag_frame.grid_columnconfigure(1, weight=1)

        self.tag_entry = tk.Entry(tag_frame)
        self.tag_entry.grid(row=0, column=0, sticky="we")
        tk.Button(tag_frame, text="Add Tag", command=self.add_tag).grid(
            row=0, column=1, padx=5
        )

        self.tag_label = tk.Label(preview_frame, text="Tags: ")
        self.tag_label.grid(row=3, column=0, sticky="w")

        action_frame = tk.Frame(self, padx=10, pady=10)
        action_frame.pack(fill=tk.X)

        btn_config: dict[str, Any] = {"padx": 10, "pady": 5, "width": 12}

        tk.Button(
            action_frame,
            text="Keep (K)",
            **btn_config,
            bg="#4CAF50",
            fg="white",
            command=lambda: self.process_file("keep_forever"),
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="Temp Keep (T)",
            **btn_config,
            bg="#8BC34A",
            fg="white",
            command=lambda: self.process_file("keep_90_days"),
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="Rename (R)",
            **btn_config,
            bg="#2196F3",
            fg="white",
            command=self.rename_current_file,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="Open (O)",
            **btn_config,
            bg="#FFC107",
            command=self.open_location,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="Next (→)",
            **btn_config,
            bg="#607D8B",
            fg="white",
            command=self.next_file,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="DELETE (D)",
            **btn_config,
            bg="#f44336",
            fg="white",
            command=self.delete_current_file,
        ).pack(side=tk.RIGHT, padx=5)

        tk.Button(
            action_frame,
            text="Undo (Ctrl+Z)",
            **btn_config,
            bg="#FF9800",
            fg="white",
            command=self.undo_last_action,
        ).pack(side=tk.RIGHT, padx=5)

    def handle_keypress(self, event: tk.Event) -> None:
        """Handles global key presses to trigger actions."""
        # We don't want shortcuts firing while typing in a dialog box (like Rename)
        if self.focus_get() is not self:
            return

        key = event.keysym.lower()

        if key == "k":
            self.process_file("keep_forever")
        elif key == "t":
            self.process_file("keep_90_days")
        elif key == "r":
            self.rename_current_file()
        elif key == "o":
            self.open_location()
        elif key == "d":
            self.delete_current_file()
        elif key == "right" or key == "space":  # Right arrow or spacebar to skip
            self.next_file()
        elif (int(event.state) & 4) and key == "z":  # Control + Z
            self.undo_last_action()

    def handle_expired_files(self) -> None:
        """Check for files whose temporary keep period has ended."""
        if not self.repository_path:
            return

        expired_files = core.check_for_expired_files()
        if not expired_files:
            return

        messagebox.showinfo(
            "Expired Files Found",
            f"Found {len(expired_files)} file(s) whose temporary keep period has ended. Please review them.",
        )

        for filename in expired_files:
            file_path = os.path.join(self.repository_path, filename)
            if not os.path.exists(file_path):
                core.update_file_status(filename, "missing")
                continue

            action = messagebox.askquestion(
                "Expired File: " + filename,
                (
                    f"The temporary keep period for '{filename}' has expired.\n\n"
                    "Do you want to DELETE it? (Yes=Delete, No=Keep Forever)"
                ),
                icon="warning",
                type=messagebox.YESNOCANCEL,
            )

            if action == messagebox.YES:
                print(f"Deleting expired file: {filename}")
                core.delete_file(file_path)
            elif action == messagebox.NO:
                print(f"Updating expired file to keep forever: {filename}")
                core.update_file_status(filename, "keep_forever")
            else:
                print(f"Ignoring expired file for now: {filename}")

    def select_repository(self) -> None:
        """Prompt the user to choose a repository to scan."""

        path = filedialog.askdirectory()
        if path:
            self.repository_path = path
            core.TARGET_REPOSITORY = path
            self.repo_label.config(text=f"Current: {self.repository_path}", fg="black")
            self.handle_expired_files()
            self.load_files(self.filter_var.get())

    def load_files(self, filter_term: str | None = None) -> None:
        """Load files from the currently selected repository."""

        if not self.repository_path:
            return

        self.file_list = core.scan_directory(self.repository_path, filter_term)
        self.file_listbox.delete(0, tk.END)
        for filename in self.file_list:
            self.file_listbox.insert(tk.END, filename)

        if self.file_list:
            self.current_file_index = 0
            self.file_listbox.selection_set(0)
            self.show_preview()
        else:
            messagebox.showinfo("All Done!", "No files to review in this repository.")

    def on_file_select(self, event: tk.Event) -> None:  # noqa: D401
        """Handle selection of one or more files from the list."""

        selection_indices = self.file_listbox.curselection()

        self.preview_canvas.delete("all")
        for widget in self.preview_canvas.winfo_children():
            widget.destroy()

        if not selection_indices:
            return
        elif len(selection_indices) == 1:
            self.current_file_index = selection_indices[0]
            self.show_preview()
        else:
            total_size = 0
            for i in selection_indices:
                try:
                    total_size += os.path.getsize(
                        os.path.join(self.repository_path, self.file_list[i])
                    )
                except OSError:
                    pass

            info_text = (
                f"{len(selection_indices)} files selected\n\n"
                f"Total size: {total_size / (1024*1024):.2f} MB"
            )
            self.preview_canvas.create_text(
                20, 20, anchor=tk.NW, text=info_text, font=("Helvetica", 14)
            )

    def show_preview(self) -> None:
        """Displays a preview of the currently selected file."""

        self.preview_canvas.delete("all")
        # Destroy any old widgets in the canvas, like the Treeview
        for widget in self.preview_canvas.winfo_children():
            widget.destroy()

        if self.current_file_index < 0 or self.current_file_index >= len(
            self.file_list
        ):
            return

        filename = self.file_list[self.current_file_index]
        file_path = os.path.join(self.repository_path, filename)

        tags = core.load_state().get(filename, {}).get("tags", [])
        self.tag_label.config(text="Tags: " + ", ".join(tags))

        try:
            # --- MODIFY THIS WHOLE LOGIC BLOCK ---

            # Image Preview
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                # This part remains the same...
                img = Image.open(file_path)
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                if canvas_width < 2 or canvas_height < 2:
                    self.after(50, self.show_preview)
                    return
                img.thumbnail(
                    (canvas_width - 20, canvas_height - 20), Image.Resampling.LANCZOS
                )
                self.photo_image = ImageTk.PhotoImage(img)
                self.preview_canvas.create_image(
                    canvas_width / 2,
                    canvas_height / 2,
                    anchor=tk.CENTER,
                    image=self.photo_image,
                )

            # PDF Preview
            elif filename.lower().endswith(".pdf"):
                import fitz  # type: ignore[import]  # PyMuPDF

                doc = fitz.open(file_path)
                page = doc.load_page(0)  # Get the first page
                pix = page.get_pixmap()
                img_pil = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                if canvas_width < 2 or canvas_height < 2:
                    self.after(50, self.show_preview)
                    return
                img_pil.thumbnail(
                    (canvas_width - 20, canvas_height - 20), Image.Resampling.LANCZOS
                )

                self.photo_image = ImageTk.PhotoImage(img_pil)
                self.preview_canvas.create_image(
                    canvas_width / 2,
                    canvas_height / 2,
                    anchor=tk.CENTER,
                    image=self.photo_image,
                )
                doc.close()

            # CSV Preview
            elif filename.lower().endswith(".csv"):
                # Create a frame to hold the Treeview and scrollbars
                csv_frame = tk.Frame(self.preview_canvas)
                self.preview_canvas.create_window(0, 0, window=csv_frame, anchor="nw")

                tree = ttk.Treeview(csv_frame, show="headings")

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if header:
                        tree["columns"] = header
                        for col in header:
                            tree.heading(col, text=col)
                            tree.column(col, width=100)

                    for i, row in enumerate(reader):
                        if i < 100:  # Limit to previewing the first 100 rows
                            if header and len(row) == len(
                                header
                            ):  # Ensure row matches header count
                                tree.insert("", "end", values=row)

                # Add scrollbars
                vsb = ttk.Scrollbar(csv_frame, orient="vertical", command=tree.yview)
                hsb = ttk.Scrollbar(csv_frame, orient="horizontal", command=tree.xview)
                tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

                vsb.pack(side="right", fill="y")
                hsb.pack(side="bottom", fill="x")
                tree.pack(side="left", fill="both", expand=True)

            # Text Preview (the default fallback)
            else:
                # This part remains the same...
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(5000)
                text_widget = tk.Text(
                    self.preview_canvas,
                    wrap=tk.WORD,
                    font=("Courier New", 10),
                    relief="flat",
                    background="white",
                )
                text_widget.insert(tk.END, content)
                text_widget.config(state=tk.DISABLED)
                self.preview_canvas.create_window(
                    0,
                    0,
                    anchor=tk.NW,
                    window=text_widget,
                    width=self.preview_canvas.winfo_width(),
                    height=self.preview_canvas.winfo_height(),
                )

        except Exception as e:  # pylint: disable=broad-except
            self.preview_canvas.create_text(
                10,
                10,
                anchor=tk.NW,
                text=f"Cannot preview file.\n\nError: {e}",
                font=("Helvetica", 10),
            )

    def process_file(self, status: str) -> None:
        """Record the user's decision for all selected files."""

        indices = self.file_listbox.curselection()
        if not indices:
            return

        for i in indices:
            filename = self.file_list[i]
            core.update_file_status(filename, status)

        self.last_action = None
        self.load_files(self.filter_var.get())

    def rename_current_file(self) -> None:
        """Prompt to rename the selected file(s)."""

        indices = self.file_listbox.curselection()
        if not indices:
            return

        for i in indices:
            old_filename = self.file_list[i]
            old_path = os.path.join(self.repository_path, old_filename)
            new_name = simpledialog.askstring(
                "Rename File",
                f"Enter new name for {old_filename}:",
                initialvalue=old_filename,
            )
            if new_name and new_name != old_filename:
                if not core.rename_file(old_path, new_name):
                    messagebox.showerror("Error", f"Could not rename {old_filename}.")

        self.last_action = None
        self.load_files(self.filter_var.get())

    def delete_current_file(self) -> None:
        """Delete the selected file(s) after confirmation."""

        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            return

        filenames = [self.file_list[i] for i in selected_indices]

        if messagebox.askyesno(
            "Confirm Action",
            f"Are you sure you want to move {len(filenames)} files to the trash?",
        ):
            for filename in filenames:
                file_path = os.path.join(self.repository_path, filename)
                core.delete_file(file_path)

            self.last_action = None
            self.load_files(self.filter_var.get())

    def undo_last_action(self) -> None:
        """Reverts the last stored action."""

        if not self.last_action:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return

        action = self.last_action
        try:
            if action["type"] == "status_change":
                filename = action["filename"]
                old_status = action["old_status"]
                if old_status == "new":
                    state = core.load_state()
                    if filename in state:
                        del state[filename]
                    core.save_state(state)
                else:
                    core.update_file_status(filename, old_status)
                print(f"UNDO: Reverted '{filename}' to status '{old_status}'")

            elif action["type"] == "rename":
                old_path = action["old_path"]
                new_name = action["new_name"]
                new_path = os.path.join(self.repository_path, new_name)
                core.rename_file(new_path, os.path.basename(old_path))
                print(
                    f"UNDO: Renamed '{new_name}' back to '{os.path.basename(old_path)}'"
                )

            messagebox.showinfo("Undo", "Last action has been undone.")
        except Exception as e:  # pylint: disable=broad-except
            messagebox.showerror("Undo Error", f"Could not perform undo: {e}")

        self.last_action = None
        self.load_files(self.filter_var.get())

    def open_location(self) -> None:
        """Open the directory of the selected file(s)."""

        indices = self.file_listbox.curselection()
        if not indices:
            return

        for i in indices:
            filename = self.file_list[i]
            file_path = os.path.join(self.repository_path, filename)
            core.open_file_location(file_path)

    def add_tag(self) -> None:
        """Add a tag to the currently selected file."""
        tag = self.tag_entry.get().strip()
        if not tag or self.current_file_index < 0 or not self.file_list:
            return

        filename = self.file_list[self.current_file_index]
        tags = core.manage_tags(filename, tags_to_add=[tag])
        self.tag_label.config(text="Tags: " + ", ".join(tags))
        self.tag_entry.delete(0, tk.END)

    def next_file(self, reload_list: bool = False) -> None:
        """Advance to the next file in the list."""

        if reload_list:
            self.load_files(self.filter_var.get())
        else:
            indices = self.file_listbox.curselection()
            if not indices:
                return

            for i in reversed(indices):
                self.file_listbox.delete(i)
                self.file_list.pop(i)

            if not self.file_list:
                self.preview_canvas.delete("all")
                messagebox.showinfo("All Done!", "No more files to review.")
                return

            self.current_file_index = min(indices[0], len(self.file_list) - 1)

            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_file_index)
            self.file_listbox.see(self.current_file_index)
            self.show_preview()


if __name__ == "__main__":
    app = DataCuratorApp()
    app.mainloop()
