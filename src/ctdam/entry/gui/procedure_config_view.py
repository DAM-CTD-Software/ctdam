import tkinter as tk
import tkinter.font as tkFont
from inspect import isfunction
from pathlib import Path
from tkinter import ttk
from typing import Callable

try:
    import customtkinter as ctk
    from CTkMessagebox import CTkMessagebox
except ImportError:
    raise ImportError(
        "The 'gui' extra is required to use this feature. Install with: pip install ctd-ctdam.proc[gui]"
    )

from ctdam.entry.gui.toml_editor import TomlEditor
from ctdam.proc import Module
from ctdam.proc.modules.available_modules import (
    get_dict_of_available_processing_modules,
)
from ctdam.proc.modules.external_functions import ExternalFunctionInfo


class ModuleSelector(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.padx = 5
        self.pady = 5
        self.title("Select a processing module from the list")
        self.heading = ctk.CTkLabel(
            self,
            text="Available Modules",
            font=(tkFont.nametofont("TkDefaultFont"), 35),
        )
        self.heading.grid(row=0, column=0, padx=15, pady=15, sticky="N")
        self.content_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent"
        )
        self.content_frame.grid(row=2, column=0, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.populate()

    def populate(self):
        for index, (category, modules) in enumerate(
            get_dict_of_available_processing_modules().items()
        ):
            category_frame = ctk.CTkFrame(
                self.content_frame, fg_color="transparent"
            )
            category_frame.grid(row=index, column=0)
            category_title = ctk.CTkLabel(
                category_frame,
                text=category,
                font=(tkFont.nametofont("TkDefaultFont"), 20),
            )
            category_title.grid(row=0, column=0)
            ttk.Separator(category_frame, orient="horizontal").grid(
                row=1, column=0, columnspan=3, sticky="ew"
            )
            if isinstance(modules, dict):
                for module_index, (module, module_info) in enumerate(
                    modules.items()
                ):
                    self.create_module_field(
                        category_frame, module, module_index + 2, module_info
                    )
            else:
                for module_index, module in enumerate(modules):
                    self.create_module_field(
                        category_frame, module, module_index + 2
                    )

    def create_module_field(
        self,
        frame,
        module,
        row,
        ex_fun_info: ExternalFunctionInfo | None = None,
    ):
        if isfunction(module):
            ex_fun_info = module
            module = module.__name__
        module_name = ctk.CTkLabel(
            frame,
            text=str(module),
        )
        module_name.grid(
            row=row,
            column=0,
            padx=self.padx,
            pady=self.pady,
        )
        if ex_fun_info:
            info = ex_fun_info
        else:
            info = module
        module_info = ctk.CTkButton(
            frame,
            text="Info",
            command=lambda: show_info(info),
        )
        module_info.grid(
            row=row,
            column=1,
            padx=self.padx,
            pady=self.pady,
        )
        module_select = ctk.CTkButton(
            frame,
            text="Select",
            command=lambda: select(str(module)),
        )
        module_select.grid(
            row=row,
            column=2,
            padx=self.padx,
            pady=self.pady,
        )

        def show_info(module: str | Module | ExternalFunctionInfo | Callable):
            if isinstance(module, Module):
                message = str(module.info).replace("\n", " ")
            elif isinstance(module, ExternalFunctionInfo):
                message = module.general_info
            elif isinstance(module, Callable):
                message = module.__doc__
                module = module.__name__
            else:
                message = (
                    f"No information for the module '{module}' available."
                )
            CTkMessagebox(
                title=f"Module: {str(module)}",
                message=message,
                option_1="Ok",
            )

        def select(module: str):
            self.master.add_module(module)
            for frame in self.winfo_children():
                frame.destroy()
            self.destroy()


class ProcedureConfigView(TomlEditor):
    """
    A frame that contains the configuration for a procedure.
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        title: str = "Processing Procedure Config Editor",
        possible_parameters: list[str] = [
            "psa_directory",
            "output_dir",
            "output_name",
        ],
        config_file: Path | str = "",
        title_size: int = 20,
        default_dir_to_save_in: Path | str = "",
    ):
        super().__init__(
            master,
            title,
            possible_parameters,
            config_file,
            title_size,
            default_dir_to_save_in=default_dir_to_save_in,
        )
        self.module_frames = {}
        self.new_module_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.new_module_frame.grid(row=3, column=0)
        self.add_module_button = ctk.CTkButton(
            self.new_module_frame, text="Add Module", command=self.new_module
        )
        self.add_module_button.grid(row=0, column=1, padx=5, pady=10)

    def new_module(self):
        selector = ModuleSelector(master=self)
        selector.geometry("700x850")
        selector.grab_set()

    def remove_module(self, module_name, frame):
        frame.destroy()
        self.config_data["modules"].pop(module_name, None)
        self.module_frames.pop(module_name, None)

    def remove_module_param(
        self, module_name, frame, key_entry, value_entry, param_entries
    ):
        self.update_module_params(module_name, param_entries)
        parent_frame = frame.master
        key_entry.destroy()
        value_entry.destroy()
        frame.grid_forget()
        frame.destroy()
        parent_frame.grid()
        param_entries.pop(key_entry, None)

    def load_config_specific_data(self, row=0):
        if "modules" in self.config_data:
            for module_name, params in self.config_data["modules"].items():
                self.add_module(module_name, params, row=row)
                row += 1

    def add_module(self, module_name=None, params=None, row=None):
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        ttk.Separator(frame, orient="horizontal").grid(
            row=0, column=0, columnspan=3, sticky="ew"
        )
        header = ctk.CTkLabel(
            frame,
            text=f"Module: {module_name or 'New Module'}",
            font=("Arial", 14, "bold"),
        )
        header.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        if module_name is None:
            module_name = f"module_{len(self.module_frames) + 1}"

        self.module_frames[module_name] = frame

        param_entries = {}
        if params:
            for index, (key, value) in enumerate(params.items()):
                self.create_module_param_field(
                    module_name, frame, key, value, param_entries, index
                )
        add_param_button = ctk.CTkButton(
            frame,
            text="+",
            command=lambda: self.create_module_param_field(
                module_name, frame, "", "", param_entries
            ),
        )
        add_param_button.grid(row=1, column=2, sticky="e", padx=5, pady=5)

        remove_module_button = ctk.CTkButton(
            frame,
            text="Remove Module",
            command=lambda: self.remove_module(module_name, frame),
        )
        remove_module_button.grid(row=1, column=1, sticky="e", padx=5, pady=5)
        self.config_data.setdefault("modules", {})[module_name] = {}
        self.update_module_params(module_name, param_entries)
        frame.bind(
            "<FocusOut>",
            lambda e: self.update_module_params(module_name, param_entries),
        )

    def update_module_params(self, module_name, param_entries):
        self.config_data["modules"][module_name] = {
            k.get(): v.get() for k, v in param_entries.items()
        }

    def create_module_param_field(
        self,
        module_name: str,
        parent_frame: ctk.CTkFrame,
        key: str,
        value: str,
        param_entries: dict,
        index=None,
    ):
        if not index:
            index = len(parent_frame.winfo_children())
        frame = ctk.CTkFrame(parent_frame, fg_color="transparent")

        def reload_frame(e):
            frame.destroy()
            try:
                param_entries.pop(key_entry)
            except KeyError:
                pass
            self.create_module_param_field(
                module_name, parent_frame, e, value, param_entries, index
            )

        key_entry = ctk.CTkComboBox(
            frame,
            values=["psa", "file_suffix", "bl", "Oxygen"],
            command=reload_frame,
        )

        key_entry.grid(row=0, column=0, padx=20, pady=5)
        key_entry.set(key)

        value_entry = ctk.CTkEntry(frame)

        def update_param(event=None):
            param_entries[key_entry] = value_entry
            self.update_module_params(module_name, param_entries)

        if key in ["psa", "bl"]:
            file_picker = self.create_picker_element(
                frame=frame,
                entry=value_entry,
                directory=False,
                callback=update_param,
            )
            file_picker.grid(row=0, column=1)
            width = 340
        else:
            width = 400

        value_entry.grid(row=0, column=2, padx=5, pady=5)
        value_entry.configure(require_redraw=True, width=width)
        value_entry.insert(0, value)
        value_entry.xview(tk.END)

        remove_button = ctk.CTkButton(
            frame,
            text="-",
            command=lambda: self.remove_module_param(
                module_name, frame, key_entry, value_entry, param_entries
            ),
        )
        remove_button.grid(row=0, column=3, padx=5, pady=5)
        param_entries[key_entry] = value_entry

        key_entry.bind("<FocusOut>", update_param)
        value_entry.bind("<FocusOut>", update_param)
        frame.grid(row=index + 1, column=0, columnspan=3, sticky="ew")

    def check_input(self) -> bool:
        # TODO: think about sophisticated check here
        return True


def run_gui(file_to_open: str = "proc_test.toml"):
    # Example usage
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.geometry("800x600")

    editor = ProcedureConfigView(
        app,
        config_file=file_to_open,
        title_size=35,
    )

    editor.grid(row=0, column=0, sticky="nsew")

    # Configure the grid to make the editor expand with the window
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)
    app.mainloop()


if __name__ == "__main__":
    run_gui()
