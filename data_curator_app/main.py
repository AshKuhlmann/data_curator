"""GUI entry point for the Data Curator application."""

from __future__ import annotations

import csv
import io
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from typing import Any

from PIL import Image, ImageTk  # type: ignore[import]
from pygments import highlight  # type: ignore[import]
from pygments.formatters import ImageFormatter  # type: ignore[import]
from pygments.lexers import TextLexer, guess_lexer_for_filename  # type: ignore[import]
import fitz  # type: ignore[import]

from data_curator_app import curator_core as core
from data_curator_app import rules_engine


class DataCuratorApp(tk.Tk):
    """Graphical interface for reviewing and managing files."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Data Curator")
        self.geometry("1000x700")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Accent.TButton", foreground="white", background="#4CAF50")
        style.map("Accent.TButton", background=[("active", "#45A049")])

        self.repository_path = ""
        self.file_list: list[str] = []
        self.current_file_index = -1

        self.status_var = tk.StringVar(value="Ready")
        self._status_after: str | None = None
        self.create_widgets()
        self.bind("<KeyPress>", self.handle_keypress)

    # ------------------------------------------------------------------
    # UI helpers
    def create_widgets(self) -> None:
        """Build all interface widgets."""

        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Select Repository", command=self.select_repository).pack(
            side=tk.LEFT
        )
        self.repo_label = ttk.Label(
            top, text="No repository selected.", foreground="gray"
        )
        self.repo_label.pack(side=tk.LEFT, padx=10)

        # Paned layout for file list and preview
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=1)
        preview_frame = ttk.Frame(paned)
        paned.add(preview_frame, weight=3)

        ttk.Label(
            list_frame, text="Files to Review", font=("Helvetica", 12, "bold")
        ).pack(anchor="w")
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(list_frame, textvariable=self.filter_var)
        entry.pack(fill=tk.X, pady=5)
        entry.bind("<KeyRelease>", lambda _: self.load_files(self.filter_var.get()))

        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.file_listbox.pack(fill=tk.BOTH, expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        ttk.Label(
            preview_frame, text="File Preview", font=("Helvetica", 12, "bold")
        ).pack(anchor="w")
        self.preview_canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        tag_frame = ttk.Frame(preview_frame)
        tag_frame.pack(fill=tk.X, pady=5)
        self.tag_entry = ttk.Entry(tag_frame)
        self.tag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(tag_frame, text="Add Tag", command=self.add_tag).pack(
            side=tk.LEFT, padx=5
        )
        self.tag_label = ttk.Label(preview_frame, text="Tags: ")
        self.tag_label.pack(anchor="w")

        action = ttk.Frame(self, padding=10)
        action.pack(fill=tk.X)
        ttk.Button(
            action,
            text="Keep (K)",
            style="Accent.TButton",
            command=lambda: self.process_file("keep_forever"),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            action,
            text="Temp Keep (T)",
            command=lambda: self.process_file("keep_90_days"),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(action, text="Rename (R)", command=self.rename_current_file).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(action, text="Open (O)", command=self.open_location).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(action, text="Next (→)", command=self.next_file).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(action, text="DELETE (D)", command=self.delete_current_file).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(action, text="Undo (Ctrl+Z)", command=self.undo_last_action).pack(
            side=tk.RIGHT, padx=5
        )

        status = ttk.Label(
            self, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w"
        )
        status.pack(fill=tk.X, side=tk.BOTTOM)

    # ------------------------------------------------------------------
    def set_status(self, msg: str, timeout: int = 3000) -> None:
        """Display a temporary status message."""

        self.status_var.set(msg)
        if self._status_after is not None:
            self.after_cancel(self._status_after)
        self._status_after = self.after(timeout, lambda: self.status_var.set("Ready"))

    # ------------------------------------------------------------------
    # Event handlers and actions
    def handle_keypress(self, event: tk.Event) -> None:
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
        elif key in {"right", "space"}:
            self.next_file()
        elif (int(event.state) & 4) and key == "z":
            self.undo_last_action()

    def run_rules_engine(self) -> None:
        if not self.repository_path:
            return
        rules = rules_engine.load_rules()
        if not rules:
            return
        suggestions: list[tuple[str, str, dict[str, Any]]] = []
        for name in os.listdir(self.repository_path):
            path = os.path.join(self.repository_path, name)
            if not os.path.isfile(path):
                continue
            result = rules_engine.evaluate_file(name, path, rules)
            if result:
                suggestions.append((name, path, result))
        if not suggestions:
            return
        counts: dict[str, int] = {}
        for _, _, res in suggestions:
            rname = res.get("name", res.get("action", ""))
            counts[rname] = counts.get(rname, 0) + 1
        summary = "The rules engine suggests the following actions:\n"
        for rname, cnt in counts.items():
            summary += f"- {rname}: {cnt} file(s)\n"
        summary += "\nDo you want to proceed?"
        if not messagebox.askyesno("Rules Engine", summary):
            return
        for filename, filepath, res in suggestions:
            action = res.get("action")
            if action == "trash":
                core.delete_file(filepath)
            elif action == "add_tag":
                tag = res.get("action_value")
                if tag:
                    core.manage_tags(filename, tags_to_add=[tag])
                core.update_file_status(filename, "auto_tagged")

    def handle_expired_files(self) -> None:
        if not self.repository_path:
            return
        expired = core.check_for_expired_files()
        if not expired:
            return
        messagebox.showinfo(
            "Expired Files Found",
            f"Found {len(expired)} file(s) whose temporary keep period has ended. Please review them.",
        )
        for filename in expired:
            path = os.path.join(self.repository_path, filename)
            if not os.path.exists(path):
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
                core.delete_file(path)
            elif action == messagebox.NO:
                core.update_file_status(filename, "keep_forever")

    def select_repository(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.repository_path = path
            core.TARGET_REPOSITORY = path
            self.repo_label.config(
                text=f"Current: {self.repository_path}", foreground="black"
            )
            self.run_rules_engine()
            self.handle_expired_files()
            self.load_files(self.filter_var.get())

    # ------------------------------------------------------------------
    # File list & preview
    def load_files(self, filter_term: str | None = None) -> None:
        if not self.repository_path:
            return
        self.file_list = core.scan_directory(self.repository_path, filter_term)
        self.file_listbox.delete(0, tk.END)
        for fname in self.file_list:
            self.file_listbox.insert(tk.END, fname)
        if self.file_list:
            self.current_file_index = 0
            self.file_listbox.selection_set(0)
            self.show_preview()
        else:
            messagebox.showinfo("All Done!", "No files to review in this repository.")

    def on_file_select(self, _event: tk.Event) -> None:
        selection = self.file_listbox.curselection()
        self.preview_canvas.delete("all")
        for w in self.preview_canvas.winfo_children():
            w.destroy()
        if not selection:
            return
        if len(selection) == 1:
            self.current_file_index = selection[0]
            self.show_preview()
        else:
            total = 0
            for i in selection:
                try:
                    total += os.path.getsize(
                        os.path.join(self.repository_path, self.file_list[i])
                    )
                except OSError:
                    pass
            info = f"{len(selection)} files selected\n\nTotal size: {total / (1024*1024):.2f} MB"
            self.preview_canvas.create_text(
                20, 20, anchor=tk.NW, text=info, font=("Helvetica", 14)
            )

    def _render_code_image(self, path: str) -> Image.Image:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(5000)
        try:
            lexer = guess_lexer_for_filename(path, content)
        except Exception:
            lexer = TextLexer()
        formatter = ImageFormatter(
            style="solarized-light", font_name="DejaVu Sans Mono"
        )
        buf = io.BytesIO()
        highlight(content, lexer, formatter, outfile=buf)
        buf.seek(0)
        return Image.open(buf)

    def show_preview(self) -> None:
        self.preview_canvas.delete("all")
        for w in self.preview_canvas.winfo_children():
            w.destroy()
        if self.current_file_index < 0 or self.current_file_index >= len(
            self.file_list
        ):
            return
        filename = self.file_list[self.current_file_index]
        path = os.path.join(self.repository_path, filename)
        tags = core.load_state().get(filename, {}).get("tags", [])
        self.tag_label.config(text="Tags: " + ", ".join(tags))
        try:
            img: Image.Image
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                img = Image.open(path)
            elif filename.lower().endswith(".pdf"):
                doc = fitz.open(path)
                page = doc.load_page(0)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                doc.close()
            elif filename.lower().endswith(".csv"):
                frame = ttk.Frame(self.preview_canvas)
                self.preview_canvas.create_window(0, 0, window=frame, anchor="nw")
                tree = ttk.Treeview(frame, show="headings")
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if header:
                        tree["columns"] = header
                        for col in header:
                            tree.heading(col, text=col)
                            tree.column(col, width=100)
                    for i, row in enumerate(reader):
                        if i < 100 and (not header or len(row) == len(header)):
                            tree.insert("", "end", values=row)
                vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
                hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
                tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
                vsb.pack(side="right", fill="y")
                hsb.pack(side="bottom", fill="x")
                tree.pack(side="left", fill="both", expand=True)
                return
            else:
                img = self._render_code_image(path)
            canvas_w = self.preview_canvas.winfo_width()
            canvas_h = self.preview_canvas.winfo_height()
            if canvas_w < 2 or canvas_h < 2:
                self.after(50, self.show_preview)
                return
            img.thumbnail((canvas_w - 20, canvas_h - 20), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(img)
            self.preview_canvas.create_image(
                canvas_w / 2, canvas_h / 2, image=self.photo_image
            )
        except Exception as e:  # pylint: disable=broad-except
            self.preview_canvas.create_text(
                10,
                10,
                anchor=tk.NW,
                text=f"Cannot preview file.\n\nError: {e}",
                font=("Helvetica", 10),
            )

    # ------------------------------------------------------------------
    # File operations
    def process_file(self, status: str) -> None:
        indices = self.file_listbox.curselection()
        if not indices:
            return
        for i in indices:
            core.update_file_status(self.file_list[i], status)
        self.set_status("Status Updated")
        self.load_files(self.filter_var.get())

    def rename_current_file(self) -> None:
        indices = self.file_listbox.curselection()
        if not indices:
            return
        for i in indices:
            old_name = self.file_list[i]
            old_path = os.path.join(self.repository_path, old_name)
            new_name = simpledialog.askstring(
                "Rename File", f"Enter new name for {old_name}:", initialvalue=old_name
            )
            if new_name and new_name != old_name:
                if core.rename_file(old_path, new_name):
                    self.set_status("File Renamed")
                else:
                    messagebox.showerror("Error", f"Could not rename {old_name}.")
        self.load_files(self.filter_var.get())

    def delete_current_file(self) -> None:
        indices = self.file_listbox.curselection()
        if not indices:
            return
        names = [self.file_list[i] for i in indices]
        if messagebox.askyesno(
            "Confirm Action",
            f"Are you sure you want to move {len(names)} files to the trash?",
        ):
            for name in names:
                core.delete_file(os.path.join(self.repository_path, name))
            self.set_status("File Deleted")
            self.load_files(self.filter_var.get())

    def undo_last_action(self) -> None:
        messagebox.showinfo("Undo", "Nothing to undo.")

    def open_location(self) -> None:
        indices = self.file_listbox.curselection()
        if not indices:
            return
        for i in indices:
            path = os.path.join(self.repository_path, self.file_list[i])
            core.open_file_location(path)

    def add_tag(self) -> None:
        tag = self.tag_entry.get().strip()
        if not tag or self.current_file_index < 0 or not self.file_list:
            return
        fname = self.file_list[self.current_file_index]
        tags = core.manage_tags(fname, tags_to_add=[tag])
        self.tag_label.config(text="Tags: " + ", ".join(tags))
        self.tag_entry.delete(0, tk.END)
        self.set_status("Tag Added")

    def next_file(self, reload_list: bool = False) -> None:
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
