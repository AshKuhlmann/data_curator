"""GUI entry point for the Data Curator application."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

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

        self.create_widgets()

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
        list_frame.grid_rowconfigure(1, weight=1)

        tk.Label(
            list_frame, text="Files to Review", font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.file_listbox.grid(row=1, column=0, sticky="nswe")
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        preview_frame = tk.Frame(main_frame)
        preview_frame.grid(row=0, column=1, sticky="nswe")
        preview_frame.grid_rowconfigure(1, weight=1)

        tk.Label(
            preview_frame, text="File Preview", font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.preview_canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=0)
        self.preview_canvas.grid(row=1, column=0, sticky="nswe")

        action_frame = tk.Frame(self, padx=10, pady=10)
        action_frame.pack(fill=tk.X)

        btn_config: dict[str, Any] = {"padx": 10, "pady": 5, "width": 12}

        tk.Button(
            action_frame,
            text="Keep (Forever)",
            **btn_config,
            bg="#4CAF50",
            fg="white",
            command=lambda: self.process_file("keep_forever"),
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="Keep (90 days)",
            **btn_config,
            bg="#8BC34A",
            fg="white",
            command=lambda: self.process_file("keep_90_days"),
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="Rename",
            **btn_config,
            bg="#2196F3",
            fg="white",
            command=self.rename_current_file,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="Open Location",
            **btn_config,
            bg="#FFC107",
            command=self.open_location,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="Decide Later",
            **btn_config,
            bg="#607D8B",
            fg="white",
            command=self.next_file,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            action_frame,
            text="DELETE",
            **btn_config,
            bg="#f44336",
            fg="white",
            command=self.delete_current_file,
        ).pack(side=tk.RIGHT, padx=5)

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
            self.load_files()

    def load_files(self) -> None:
        """Load files from the currently selected repository."""

        if not self.repository_path:
            return

        self.file_list = core.scan_directory(self.repository_path)
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
        """Handle selection of a file from the list."""

        selection_indices = self.file_listbox.curselection()
        if selection_indices:
            self.current_file_index = selection_indices[0]
            self.show_preview()

    def show_preview(self) -> None:
        """Display a preview of the currently selected file."""

        self.preview_canvas.delete("all")
        if self.current_file_index < 0 or self.current_file_index >= len(
            self.file_list
        ):
            return

        filename = self.file_list[self.current_file_index]
        file_path = os.path.join(self.repository_path, filename)

        try:
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
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
            else:
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
        """Record the user's decision for the current file."""

        if self.current_file_index < 0:
            return

        filename = self.file_list[self.current_file_index]
        core.update_file_status(filename, status)
        self.next_file()

    def rename_current_file(self) -> None:
        """Prompt to rename the selected file."""

        if self.current_file_index < 0:
            return

        old_filename = self.file_list[self.current_file_index]
        old_path = os.path.join(self.repository_path, old_filename)
        new_name = simpledialog.askstring(
            "Rename File", "Enter new name:", initialvalue=old_filename
        )
        if new_name and new_name != old_filename:
            if core.rename_file(old_path, new_name):
                self.next_file(reload_list=True)
            else:
                messagebox.showerror("Error", f"Could not rename {old_filename}.")

    def delete_current_file(self) -> None:
        """Delete the selected file after confirmation."""

        if self.current_file_index < 0:
            return

        filename = self.file_list[self.current_file_index]
        file_path = os.path.join(self.repository_path, filename)
        if messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to permanently delete\n{filename}?",
        ):
            if core.delete_file(file_path):
                self.next_file(reload_list=True)
            else:
                messagebox.showerror("Error", f"Could not delete {filename}.")

    def open_location(self) -> None:
        """Open the directory of the currently selected file."""

        if self.current_file_index < 0:
            return

        filename = self.file_list[self.current_file_index]
        file_path = os.path.join(self.repository_path, filename)
        core.open_file_location(file_path)

    def next_file(self, reload_list: bool = False) -> None:
        """Advance to the next file in the list."""

        if reload_list:
            self.load_files()
        else:
            self.file_listbox.delete(self.current_file_index)
            self.file_list.pop(self.current_file_index)

            if not self.file_list:
                self.preview_canvas.delete("all")
                messagebox.showinfo("All Done!", "No more files to review.")
                return

            if self.current_file_index >= len(self.file_list):
                self.current_file_index = 0

            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_file_index)
            self.file_listbox.see(self.current_file_index)
            self.show_preview()


if __name__ == "__main__":
    app = DataCuratorApp()
    app.mainloop()
