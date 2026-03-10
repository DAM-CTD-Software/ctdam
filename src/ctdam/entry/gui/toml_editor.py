import tkinter as tk
import tkinter.font as tkFont
from abc import abstractmethod
from pathlib import Path
from tkinter import filedialog
from typing import Callable

try:
    import customtkinter as ctk
    from CTkMessagebox import CTkMessagebox
except ImportError:
    raise ImportError(
        "The 'gui' extra is required to use this feature. Install with: pip install ctdam[gui]"
    )
import tomlkit
from tomlkit.toml_file import TOMLFile


class TomlEditor(ctk.CTkFrame):
    """General editor to configure toml files."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        title: str,
        possible_parameters: list[str],
        config_file: Path | str = "",
        title_size: int = 20,
        fg_color: str = "transparent",
        default_dir_to_save_in: Path | str = "",
    ):
        super().__init__(master)
        self.master = master
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.configure(fg_color=fg_color)

        self.module_frames = {}
        self.possible_parameters = possible_parameters
        self.default_dir_to_save_in = default_dir_to_save_in

        self.title = ctk.CTkLabel(
            self,
            text=title,
            font=(tkFont.nametofont("TkDefaultFont"), title_size),
        )
        self.title.grid(row=0, column=0, padx=15, pady=15)
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.configure(fg_color="transparent")
        self.header_frame.grid(row=1, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=1)
        self.header_frame.grid_columnconfigure(2, weight=1)

        self.load_button = ctk.CTkButton(
            self.header_frame, text="Load TOML", command=self.load_toml
        )
        self.load_button.grid(row=0, column=0, padx=5, pady=5)

        self.save_button = ctk.CTkButton(
            self.header_frame, text="Save TOML", command=self.save_toml
        )
        self.save_button.grid(row=0, column=1, padx=5, pady=5)

        self.cancel_button = ctk.CTkButton(
            self.header_frame, text="Cancel", command=self.cancel
        )
        self.cancel_button.grid(row=0, column=2, padx=5, pady=5)

        self.content_frame = ctk.CTkScrollableFrame(self)
        self.content_frame.configure(fg_color="transparent")
        self.content_frame.grid(row=2, column=0, sticky="nsew")
        self.content_frame.bind_all(
            "<MouseWheel>",
            lambda e: self.content_frame._parent_canvas.yview(
                "scroll", -1, "units"
            ),
        )
        self.content_frame.bind_all(
            "<Button-4>",
            lambda e: self.content_frame._parent_canvas.yview(
                "scroll", -1, "units"
            ),
        )
        self.content_frame.bind_all(
            "<Button-5>",
            lambda e: self.content_frame._parent_canvas.yview(
                "scroll", 1, "units"
            ),
        )
        if config_file:
            self.load_config(config_file)

    def cancel(self):
        for frame in self.winfo_children():
            frame.destroy()
        self.destroy()
        self.master.destroy()

    def load_toml(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("TOML Files", "*.toml")]
        )
        if file_path:
            self.file_path = Path(file_path).absolute()
            self.load_config(file_path)

    def save_toml(self):
        if not self.check_input():
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".toml",
            filetypes=[("TOML Files", "*.toml")],
            initialfile=self.file_path.name,
            initialdir=(
                self.file_path.parent
                if not self.default_dir_to_save_in
                else self.default_dir_to_save_in
            ),
        )
        if file_path:
            try:
                with open(file_path, "w") as file:
                    file.write(tomlkit.dumps(self.config_data))
                CTkMessagebox(
                    title="Success",
                    message="Configuration saved successfully!",
                    icon="check",
                    option_1="Ok",
                )
                self.cancel()

            except Exception as e:
                print(e)
                CTkMessagebox(
                    title="Error",
                    message=f"Failed to save file: {e}",
                    icon="cancel",
                    option_1="Ok",
                )

    @abstractmethod
    def check_input(self) -> bool:
        pass

    def bad_input_warning(self, message: str):
        CTkMessagebox(
            title="Error",
            message=message,
            icon="cancel",
            option_1="Ok",
        )

    def load_config(self, file_path: Path | str):
        try:
            self.config_data = TOMLFile(file_path).read()
            self.file_path = Path(file_path).absolute()
            self.populate_fields()
        except Exception as e:
            CTkMessagebox(
                title="Error",
                message=f"Failed to load file: {e}",
                icon="cancel",
                option_1="Ok",
            )

    def populate_fields(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.module_frames.clear()
        row_index = 0
        for key in self.possible_parameters:
            if key in self.config_data:
                value = self.config_data[key]
            else:
                value = ""
            self.create_key_value_field(
                self.content_frame, key, value, row=row_index
            )
            row_index += 1

        self.load_config_specific_data(row_index)

    @abstractmethod
    def load_config_specific_data(self, row):
        pass

    def create_picker_element(
        self,
        frame: ctk.CTkFrame,
        entry: ctk.CTkEntry,
        directory: bool = True,
        callback: Callable | None = None,
        initial_dir: Path | str | None = None,
    ) -> ctk.CTkButton:
        if directory:
            command = filedialog.askdirectory
            text = "Pick directory"
            width = 80
        else:
            command = filedialog.askopenfilename
            text = "Pick file"
            width = 60

        def open_file_picker():
            entry.delete(0, tk.END)
            entry.insert(0, command(initialdir=initial_dir))
            entry.xview(tk.END)
            if isinstance(callback, Callable):
                callback()

        return ctk.CTkButton(
            frame, command=open_file_picker, text=text, width=width
        )

    def create_key_value_field(self, parent, key, value, row):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        frame.grid_columnconfigure(0, weight=1)

        key_label = ctk.CTkLabel(frame, text=key, anchor="w")
        key_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        entry = ctk.CTkEntry(frame, width=300)
        entry.grid(row=0, column=2)
        entry.insert(0, value)
        entry.xview(tk.END)

        def update_value(event=None):
            self.config_data[key] = entry.get()
            if not event:
                self.populate_fields()

        if "dir" in key:
            file_picker = self.create_picker_element(
                frame=frame,
                entry=entry,
                callback=update_value,
            )
            file_picker.grid(row=0, column=1, padx=5, pady=5)

        entry.bind("<FocusOut>", update_value)
        entry.bind("<Leave>", update_value)
