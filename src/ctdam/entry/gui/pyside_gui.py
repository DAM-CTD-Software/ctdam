import sys
import tomlkit
import gsw
import qdarktheme
import inspect
from copy import deepcopy
from pathlib import Path
from typing import Callable
from ctdam.proc.modules.external_functions import ExternalFunctions, ExternalFunctionInfo
from ctdam.proc.module import Module
from ctdam.proc.modules import proc_name_mapper
from PySide6.QtCore import (
    Qt,
    QSize,
    Signal,
)
from PySide6.QtGui import (
    QAction, 
    QFont,
)
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QScrollArea,
    QTableWidget,
    QHeaderView,
    QTableWidgetItem,
    QPlainTextEdit
)
#TODO: Add bl filepath parameter for bottle module
#TODO: small description for each module and return info
#TODO: Optional: Add the option to add parameters to the modules if needed. Use old button logic from previous version.
class ModuleListWidget(QWidget):
    """
    Left panel 
    Widget for displaying available modules and allowing the user to select and add them to the TOML file.
    Search bar for filtering modules and two lists for custom and GSW modules.
    """
    add_requested = Signal(object)
    info_requested = Signal(object, object)

    def __init__(
        self, 
        available_modules, 
        parent=None
    ):
        super().__init__(parent)
        self.available_modules = available_modules
        self.setLayout(self.module_picker_layout())

    def module_picker_layout(self):       
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(20)
        title = QLabel("Available Modules")
        title.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            """
        )
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        self.module_search = QLineEdit()
        self.module_search.setPlaceholderText("Search module")
        self.module_search.setClearButtonEnabled(True)
        layout.addWidget(self.module_search)

        columns = QHBoxLayout()
        columns.setSpacing(10)

        custom_group = QGroupBox("Custom Modules")
        custom_layout = QVBoxLayout(custom_group)
        self.custom_modules = QListWidget()
        self.custom_modules.setObjectName("ModulePicker")
        custom_layout.addWidget(self.custom_modules)
        custom_add_button = QPushButton("Add selected")
        custom_add_button.clicked.connect(
            lambda checked=False: self.add_requested.emit(self.custom_modules)
        )
        self.custom_modules.itemDoubleClicked.connect(
            lambda item: self.add_requested.emit(self.custom_modules)
        )
        custom_layout.addWidget(custom_add_button)

        gsw_group = QGroupBox("Gsw Modules")
        gsw_layout = QVBoxLayout(gsw_group)
        self.gsw_modules = QListWidget()
        self.gsw_modules.setObjectName("ModulePicker")
        gsw_layout.addWidget(self.gsw_modules)
        gsw_add_button = QPushButton("Add selected")
        gsw_add_button.clicked.connect(
            lambda checked=False: self.add_requested.emit(self.gsw_modules)
        )
        self.gsw_modules.itemDoubleClicked.connect(
            lambda item: self.add_requested.emit(self.gsw_modules)
        )
        gsw_layout.addWidget(gsw_add_button)

        columns.addWidget(custom_group, 1)
        columns.addWidget(gsw_group, 1)

        layout.addLayout(columns,1)

        custom_modules = {
            name: module
            for name, module in self.available_modules.get("custom", {}).items()
            if name == module.name
        }

        self.add_modules_to_list(
            self.custom_modules,
            custom_modules,
        )
        self.add_modules_to_list(
            self.gsw_modules,
            self.available_modules.get("gsw", {}),
        )
        self.custom_modules.currentItemChanged.connect(self.info_requested.emit)
        self.gsw_modules.currentItemChanged.connect(self.info_requested.emit)
        self.module_search.textChanged.connect(self.filter_modules)

        return layout


    def filter_modules(self, search_text):
        query = search_text.casefold().strip()

        for module_list in (self.custom_modules, self.gsw_modules):
            for index in range(module_list.count()):
                item = module_list.item(index)
                item.setHidden(query not in item.text().casefold())
    
    def add_modules_to_list(self, list_widget, modules):
        list_widget.ensurePolished()
        for name, module in sorted(modules.items()):
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, module)
            list_widget.addItem(item)


class TomlModuleListWidget(QWidget):
    """
    Middle panel
    Widget for displaying the modules currently in the loaded TOML file and allowing the user to remove or reorder them.
    """
    remove_requested = Signal()
    order_changed = Signal()
    info_requested = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(self.toml_layout())

    def toml_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.toml_title = QLabel("No TOML file loaded")
        self.toml_title.setStyleSheet(
            """
            font-size: 22px;
            font-weight: bold;
            """
        )
        self.toml_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        self.toml_module_list = QListWidget()
        self.toml_module_list.setObjectName("tomlModuleList")
        self.toml_module_list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.toml_module_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.toml_module_list.setDragDropOverwriteMode(False)
        self.toml_module_list.setDropIndicatorShown(True)

        self.toml_module_list.model().rowsMoved.connect(
            lambda *args: self.order_changed.emit()
        )
        layout.addWidget(self.toml_title)
        layout.addWidget(self.toml_module_list, 1)
        
        self.toml_module_list.currentItemChanged.connect(self.info_requested.emit)
        remove_button = QPushButton("Remove selected")
        remove_button.clicked.connect(
            lambda checked=False: self.remove_requested.emit()
        )
        layout.addWidget(remove_button)
        self.toml_module_list.itemDoubleClicked.connect(
            lambda item: self.remove_requested.emit()
        )
        return layout
    
    def show_toml_modules(self, document):
        self.toml_module_list.clear()

        modules = document.get("modules", {})

        if not modules:
            self.toml_module_list.addItem("No modules in the TOML file.")
            return

        for position, (module_name, parameters) in enumerate(
            modules.items(),
            start=1,
        ):
            item = QListWidgetItem(f"{position}. {module_name}")

            item.setData(
                Qt.ItemDataRole.UserRole,
                {
                    "name": module_name,
                    "parameters": dict(parameters),
                },
            )

            self.toml_module_list.addItem(item)


class ModuleSettingsWidget(QWidget):
    """
    Right panel
    Widget for displaying and editing the parameters of the selected module from the TOML file.
    Shows the module info in the right bottom corner and the module settings in the right top corner.
    """
    parameters_changed = Signal(str, object)
    def __init__(
        self, 
        available_modules, 
        parent=None
    ):
        super().__init__(parent)
        self.available_modules = available_modules
        self.setLayout(self.settings_layout())
        self.show_no_module_selected()


    def settings_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(10)


        module_info = QVBoxLayout()
        module_info.setSpacing(4)

        module_title = QLabel("Module Info")
        module_title.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            """
        )

        self.module_info = QTextBrowser()
        self.module_info.setPlaceholderText(
            "Select a module to display its documentation."
        )

        module_info.addWidget(module_title)
        module_info.addWidget(self.module_info, 1)

        
        
        module_settings = QVBoxLayout()
        module_settings.setSpacing(4)

        module_title = QLabel("Module Settings")
        module_title.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            """
        )

        self.module_settings = QScrollArea()
        self.module_settings.setWidgetResizable(True)
        
        module_settings.addWidget(module_title)  
        module_settings.addWidget(self.module_settings, 1)

        layout.addLayout(module_settings, 1)
        layout.addLayout(module_info, 1)
        return layout

    def show_info(
        self, 
        current_item,
    ):
        if current_item is None:
            self.module_info.clear()
            return

        module = current_item.data(Qt.ItemDataRole.UserRole)
        module_name = current_item.text()

        if isinstance(module, dict):
            module_name = module["name"]
            module = self.available_modules.get("custom", {}).get(module_name)
            if module is None:
                module = self.available_modules.get("gsw", {}).get(module_name)
        
        if isinstance(module, Module):
            message = str(module.info)

        elif isinstance(module, ExternalFunctionInfo):
            message = module.raw_docstring

        elif callable(module):
            message = module.__doc__ or "No documentation available."

        else:
            message = (
                f"No information for the module '{module_name}' available."
            )

        self.module_info.setPlainText(
            f"{module_name}\n\n{message}"
        )

    def show_module_parameters(
        self, 
        module_name, 
        module_parameters=None
    ):

        old_editor = self.module_settings.takeWidget()
        if old_editor is not None:
            old_editor.deleteLater()

        if module_name is None:
            self.show_no_module_selected()
            return

        module_parameters = (
            deepcopy(module_parameters)
            if module_parameters is not None
            else tomlkit.table()
        )
        parameters = self.get_available_parameters(module_name)
        if module_name == "bottlefile":
            parameters = {
                "bl": "searching for bl file in the same input directory",
            }
        if not parameters and not module_parameters:
            label = QLabel(
                "No parameter settings available for this module."
            )
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.module_settings.setWidget(label)
            return

        if module_name == "wfilter":
            editor = self.create_wfilter_param_fields(
                module_name, parameters, module_parameters
            )
        else:
            editor = self.create_module_param_fields(
                module_name, parameters, module_parameters
            )

        self.module_settings.setWidget(editor)

    def get_available_parameters(
        self,
        module_name: str,
    ):
        parameters = {}
        parameter = None
        if module_name in self.available_modules.get("custom", {}):
            module_class = proc_name_mapper[module_name]
            parameters = inspect.signature(module_class.__call__).parameters
            parameter = parameters.get("default_values")

        if parameter is not None and parameter.default is not inspect.Parameter.empty:
            parameters_dict = parameter.default
        else: 
            parameters_dict = {}
        return parameters_dict

    def create_module_param_fields(
        self,
        module_name: str,
        parameters:dict,
        module_parameters: dict
    ):
        container = QWidget()
        layout = QVBoxLayout(container)
        names = list(dict.fromkeys([*parameters, *module_parameters]))

        table = QTableWidget(len(names), 2)
        table.setObjectName("ParameterTable")
        table.setHorizontalHeaderLabels(["Parameters", "Value"])
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(table)

        def update_value(key, text):
            if text == "":
                module_parameters.pop(key, None)
            else:
                try:
                    value = tomlkit.parse(f"value = {text}\n")["value"]
                except tomlkit.exceptions.ParseError:
                    value = text

                module_parameters[key] = value
            self.parameters_changed.emit(module_name, module_parameters)

        for row, key in enumerate(names):
            name_item = QTableWidgetItem(key)
            name_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )
            table.setItem(row, 0, name_item)

            field = QLineEdit()

            if key in module_parameters:
                field.setText(str(module_parameters[key]))

            if key in parameters:
                field.setPlaceholderText(f"default: {parameters[key]}")

            field.textEdited.connect(
                lambda text, param = key: update_value(param, text)
            )
            table.setCellWidget(row, 1, field)

        return container

    def create_wfilter_param_fields(
        self, 
        module_name: str, 
        parameters: dict,
        module_parameters: dict
    ):
        fields = {}
        container = QWidget()
        layout = QVBoxLayout(container)
        columns = [
            "window_type",
            "window_width",
            "half_width",
            "offset",
            ]
        table = QTableWidget(len(parameters), len(columns) + 1)
        table.setObjectName("ParameterTable")
        table.setHorizontalHeaderLabels(["Parameters", *columns])
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        for column in range(1, len(columns) + 1):
            table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Stretch
            )
        for row, (name, defaults) in enumerate(parameters.items()):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )
            table.setItem(row, 0, name_item)

            saved = module_parameters.get(name, {})

            for column, parameter in enumerate(columns, start=1):
                field = QLineEdit()
                field.setAlignment(Qt.AlignmentFlag.AlignCenter)
                field.setPlaceholderText(f"{defaults[parameter]}")
                fields[(name, parameter)] = field
                if parameter in saved:
                    field.setText(str(saved[parameter]))

                table.setCellWidget(row, column, field)

        def get_settings():
            settings = {}
            for (name, parameter), field in fields.items():
                text = field.text().strip()
                if not text:
                    continue

                if parameter == "window_width":
                    value = int(text)
                elif parameter in ("half_width", "offset"):
                    value = float(text)
                else:
                    value = text
                settings.setdefault(name, {})[parameter] = value
            return settings        

        def update_value(setting):
            module_table = tomlkit.table()

            for name , settings in setting.items():
                entry = tomlkit.inline_table()
                entry.update(settings)
                module_table[name] = entry
            self.parameters_changed.emit(module_name, module_table)
        
        for field in fields.values():
            field.editingFinished.connect(
                lambda: update_value(get_settings())
            )                    
        layout.addWidget(table)
        return container

    def add_parameter(
        self,
        module_name: str,
    ):
        """
        Add new parameter to the module settings if needed.
        """
        return

    def show_no_module_selected(self):
        label = QLabel(
            "Select a module from the TOML list to edit its parameters."
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.module_settings.setWidget(label)



class MainWindow(QMainWindow):
    """
    Main window for the application.
    Contains the left, middle, and right panels.
    Sets up the menu bar, and handles loading and saving TOML files.
    Add or remove modules per double click or by selecting the module and use the add/remove button on the bottom.
    The module order can be changed by drag and drop in the middle panel.
    Shortcuts:
        - Alt+F: Open File menu
        - Ctrl+L: Load TOML file
        - Ctrl+S: Save TOML file
        - Ctrl+E: Edit TOML settings
        - Ctrl+T: Toggle between light and dark theme
        - Esc: Close application
        - F11: switch between maximized and normal size window
    """

    def __init__(self):
        super().__init__()
        self.current_toml_path: Path | None = None
        self.current_toml_document = None
        self.available_modules = self.get_dict_of_available_processing_modules()
        theme = QApplication.styleHints().colorScheme()
        self.current_theme = "dark" if theme == Qt.ColorScheme.Dark else "light"
        self.apply_theme()
        file_menu = self.menuBar().addMenu("&File")

        load_toml_button = QAction("Load TOML", self)
        load_toml_button.setShortcut("Ctrl+L")
        load_toml_button.setStatusTip("Load a TOML file")
        load_toml_button.triggered.connect(self.load_toml)
        file_menu.addAction(load_toml_button)

        file_menu.addSeparator()

        save_toml_button = QAction("Save TOML", self)
        save_toml_button.setShortcut("Ctrl+S")
        save_toml_button.setStatusTip("Save the current TOML file")
        save_toml_button.triggered.connect(self.save_toml)
        file_menu.addAction(save_toml_button)

        file_menu.addSeparator()

        edit_toml_settings = QAction("Edit TOML Settings", self)
        edit_toml_settings.setShortcut("Ctrl+E")
        edit_toml_settings.setStatusTip("Edit the TOML settings")
        edit_toml_settings.triggered.connect(self.show_toml_settings)
        file_menu.addAction(edit_toml_settings)

        file_menu.addSeparator()

        toggle_theme_button = QAction("Toggle Theme", self)
        toggle_theme_button.setShortcut("Ctrl+T")
        toggle_theme_button.setStatusTip("Toggle between light and dark theme")
        toggle_theme_button.triggered.connect(self.toggle_theme)
        file_menu.addAction(toggle_theme_button)    

        file_menu.addSeparator()

        close_button = QAction("Close", self)
        close_button.setStatusTip("Close the current editor")
        close_button.triggered.connect(self.cancel_program)
        file_menu.addAction(close_button)


        widget = QWidget()
        widget.setLayout(self.main_layout())
        self.setCentralWidget(widget)

        for widget in (
            self.toml_panel.toml_module_list,
        ):
            widget.currentItemChanged.connect(self.show_selected_module_parameters)
        
        for widget in (
            self.module_picker.custom_modules,
            self.module_picker.gsw_modules,
            self.toml_panel.toml_module_list,
        ):  
            widget.itemSelectionChanged.connect(
                lambda source=widget: (
                    self.clear_other_selections(source)
                    if source.selectedItems()
                    else None
                )
            )
        for widget in (
            self.module_picker.gsw_modules,
            self.module_picker.custom_modules,
        ):
            widget.itemSelectionChanged.connect(
                lambda source=widget: (
                    self.settings_panel.show_no_module_selected()
                    if source.selectedItems()
                    else None
                )
            )
        gui_path = Path(__file__).resolve().parent
        project_path = gui_path.parents[3]
        self.load_toml(file_path = project_path/"proc_template.toml")
        
    
    def main_layout(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        self.module_picker = ModuleListWidget(self.available_modules, self)
        self.toml_panel = TomlModuleListWidget(self)
        self.settings_panel = ModuleSettingsWidget(self.available_modules, self)    

        layout.addWidget(self.module_picker)
        layout.addWidget(self.toml_panel)
        layout.addWidget(self.settings_panel)

        self.module_picker.add_requested.connect(self.add_module)
        self.module_picker.info_requested.connect(self.settings_panel.show_info)
        self.toml_panel.remove_requested.connect(self.remove_module)
        self.toml_panel.order_changed.connect(self.update_module_order)
        self.toml_panel.info_requested.connect(self.settings_panel.show_info)
        self.settings_panel.parameters_changed.connect(self.update_module_parameters)
        
        return layout

    def get_dict_of_available_processing_modules(self):
        gsw_functions = ExternalFunctions([gsw])
        return {
            "custom": {
                name: module_class()
                for name, module_class in proc_name_mapper.items()
            },
            **gsw_functions.data,
    }

    def show_selected_module_parameters(
        self, 
        current_item, 
        previous_item=None
    ):
        if current_item is None or self.current_toml_document is None:
            self.settings_panel.show_module_parameters(None)
            return

        data = current_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            self.settings_panel.show_module_parameters(None)
            return

        module_name = data["name"]
        modules = self.current_toml_document.get("modules", {})

        if module_name not in modules:
            self.settings_panel.show_module_parameters(None)
            return

        self.settings_panel.show_module_parameters(
            module_name, modules[module_name]
        )

    def update_module_parameters(
        self, 
        module_name, 
        parameters
    ):
        if self.current_toml_document is None:
            return

        modules = self.current_toml_document.get("modules", {})

        if module_name in modules:
            modules[module_name] = deepcopy(parameters)
            
    def clear_other_selections(self, active_list):
        for widget in (
            self.module_picker.custom_modules,
            self.module_picker.gsw_modules,
            self.toml_panel.toml_module_list,
        ):
            if widget is not active_list:
                widget.blockSignals(True)
                widget.clearSelection()
                widget.setCurrentItem(None)
                widget.blockSignals(False)

    def update_module_order(self):
        if self.current_toml_document is None:
            return

        modules = self.current_toml_document.get("modules", {})
        module_order = []

        for index in range(self.toml_panel.toml_module_list.count()):
            item = self.toml_panel.toml_module_list.item(index)
            data = item.data(Qt.ItemDataRole.UserRole)

            if not isinstance(data, dict):
                return
            
            name = data["name"]
            module_order.append((name, modules[name]))
            item.setText(f"{index + 1}. {name}")

        for name, _ in module_order:
            del modules[name]

        for name, parameters in module_order:
            original_indent = parameters.trivia.indent
            modules[name] = parameters
            parameters.trivia.indent = original_indent

    def serialize_toml(self):
        """
        Serialize the current TOML document into a string, preserving the order of modules.
        """
        document = deepcopy(self.current_toml_document)
        if "modules" not in document:
            return tomlkit.dumps(document)

        modules = document.pop("modules")
        parts = [tomlkit.dumps(document).rstrip()]

        for module_name, settings in modules.items():
            fragment = tomlkit.document()
            fragment.add(
                "modules",
                tomlkit.table(is_super_table=True),    
            )
            fragment["modules"].add(module_name, settings)

            parts.append(tomlkit.dumps(fragment).strip())
        return "\n\n".join(part for part in parts if part) + "\n"

    def add_module(self, source_list):
        selected_item = source_list.currentItem()

        if selected_item is None:
            QMessageBox.information(
                self,
                "No module selected",
                "Please select a module first.",
            )
            return

        if self.current_toml_document is None:
            QMessageBox.information(
                self,
                "No TOML file loaded",
                "Load a TOML file first.",
            )
            return

        module_name = selected_item.text()

        if "modules" not in self.current_toml_document:
            self.current_toml_document["modules"] = tomlkit.table()

        modules = self.current_toml_document["modules"]

        if module_name in modules:
            QMessageBox.information(
                self,
                "Module already exists",
                f"'{module_name}' is already in the TOML file.",
            )
            return
        modules[module_name] = tomlkit.table()

        self.toml_panel.show_toml_modules(self.current_toml_document)

        self.toml_panel.toml_module_list.setCurrentRow(
            self.toml_panel.toml_module_list.count() - 1
        )

    def remove_module(self):
        if self.current_toml_document is None:
            return
        selected_items = self.toml_panel.toml_module_list.selectedItems()
        if not selected_items:
            return
        
        data = selected_items[0].data(Qt.ItemDataRole.UserRole)

        if not isinstance(data, dict):
            return
        module_name = data["name"]
        modules = self.current_toml_document.get("modules", {})

        if module_name in modules:
            del modules[module_name]
        
        self.toml_panel.show_toml_modules(self.current_toml_document)
        self.settings_panel.module_info.clear()
            
    def load_toml(
        self, 
        checked=False, 
        file_path=None
    ):
        if self.current_toml_document is not None:
            if not self.loadEvent():
                return
            
        if file_path is None: 
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load TOML File",
                "",
                "TOML Files (*.toml);;All Files (*)",
            )

        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                document = tomlkit.load(file)

        except (OSError, tomlkit.exceptions.ParseError) as error:
            QMessageBox.critical(
                self,
                "Error loading TOML file",
                str(error),
            )
            return

        self.current_toml_path = Path(file_path)
        self.current_toml_document = document

        self.toml_panel.toml_title.setText(self.current_toml_path.name)
        self.toml_panel.show_toml_modules(document)

    def save_toml(self, checked=False):
        if self.current_toml_document is None:
            QMessageBox.information(
                self,
                "No TOML file loaded",
                "Load a TOML file first.",
            )
            return
        suggested_path = str(self.current_toml_path)

        select_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save TOML File",
            suggested_path,
            "TOML Files (*.toml);;All Files (*)",
        )

        if not select_path:
            return

        file_path = Path(select_path)

        if file_path.suffix.lower() != ".toml":
                file_path = file_path.with_suffix(".toml")

        try:
            text = self.serialize_toml()
            with file_path.open("w", encoding="utf-8") as file:
                file.write(text)

        except OSError as error:
            QMessageBox.critical(
                self,
                "Error saving file",
                str(error),
            )
            return

        self.current_toml_path = file_path
        self.toml_panel.toml_title.setText(file_path.name)

        QMessageBox.information(
            self,
            "Saved",
            f"File saved:\n{file_path}",
        ) 

    def toml_settings(self, document):
        return {
            key: value
            for key, value in document.items()
            if key != "modules"
        }
    
    def show_toml_settings(self):
        if self.current_toml_document is None:
            QMessageBox.information(
                self,
                "No TOML file loaded",
                "Load a TOML file first.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("TOML-Settings")
        dialog.setMinimumSize(QSize(600, 600))
        layout = QVBoxLayout(dialog)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        fields = {}
        settings = self.toml_settings(self.current_toml_document)

        def select_path(name, field):
            if name  == "output_dir":
                path = QFileDialog.getExistingDirectory(
                    dialog, "Select directory", field.text()
                )
            else:
                path, _ = QFileDialog.getOpenFileName(
                    dialog, "Select file", field.text(), "All Files (*)"
                )

            if path:
                field.setText(path)

        for name, value in settings.items():
            if name == "output_columns":
                field = QPlainTextEdit()
                field.setPlainText("\n".join(value))
                fields[name] = field
                form.addRow(name, field)
                continue

            if name in {"input", "xmlcon", "output_dir", "output_name", "output_type"}:
                value_text = str(value)
            else:
                value_text = tomlkit.dumps({"value": value}).partition("=")[2].strip()
            field = QLineEdit(value_text)
            fields[name] = field
            if name in {"input", "xmlcon", "output_dir"}:
                row = QHBoxLayout()
                row.addWidget(field)

                button = QPushButton("Select path…")
                button.clicked.connect(
                    lambda checked=False, name=name, field=field:
                        select_path(name, field)
                )
                row.addWidget(button)

                form.addRow(name, row)
            else:
                form.addRow(name, field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)

        def apply_settings():
            updated = {}

            for name, field in fields.items():
                if name == "output_columns":
                    updated[name] = [
                        line.strip()
                        for line in field.toPlainText().splitlines()
                        if line.strip()
                    ]
                    continue
                if name in {"input", "xmlcon", "output_dir", "output_name", "output_type"}:
                    updated[name] = field.text()
                    continue
                try:
                    parsed = tomlkit.parse(f"value = {field.text()}\n")
                    if set(parsed) != {"value"}:
                        raise ValueError("Setting must be a single value.")
                    updated[name] = parsed["value"]
                except (tomlkit.exceptions.ParseError, ValueError) as error:
                    QMessageBox.warning(
                        dialog,
                        "Invalid Value",
                        f"{name}:\n{error}",
                    )
                    field.setFocus()
                    return
            for name, value in updated.items():
                if name == "output_columns":
                    value = tomlkit.array(value)
                    value.multiline(True)
                self.current_toml_document[name] = value
            dialog.accept()
        buttons.accepted.connect(apply_settings)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme()
    
    def apply_theme(self):
        stylesheet = (
            self.dark_theme()
            if self.current_theme == "dark"
            else self.light_theme()
        )
        qdarktheme.setup_theme(
            self.current_theme,
            additional_qss=stylesheet,
        )
    def dark_theme(self):
        return """
        /* toml_layout */
        QListWidget#tomlModuleList {
            background-color: #202124;
            color: #e8eaed;
            border: none;
        }

        QListWidget#tomlModuleList::item {
            background-color: #34363a;
            border: 1px solid #505258;
            border-radius: 6px;
            padding: 12px;
            margin: 4px;
        }

        QListWidget#tomlModuleList::item:hover {
            background-color: #2b2d31;
        }
        
        QListWidget#tomlModuleList::item:selected {
            background-color: #344b68;
            color: #e8eaed;
            border-color: #8ab4f8;
        }

        /* module_picker_layout */
        QListWidget#ModulePicker {
            background-color: #202124;
            color: #e8eaed;
            border: none;
        }

        QListWidget#ModulePicker::item {
            background-color: #34363a;
            border: 1px solid #505258;
            border-radius: 6px;
            padding: 6px;
            margin: 4px;
        }

        QListWidget#ModulePicker::item:hover {
            background-color: #2b2d31;
        }

        QListWidget#ModulePicker::item:selected {
            background: #375777;
            border: 1px solid #78a9dc;
        }

        /* module_settings */
        QTableWidget#ParameterTable {
            background-color: #202124;
            color: #e8eaed;
            gridline-color: #505258;
            border: 1px solid #505258;
        }

        QTableWidget#ParameterTable QHeaderView {
            background-color: #202124
        }

        QTableWidget#ParameterTable QHeaderView::section {
            background-color: #34363a;
            color: #e8eaed;
        }

        QTableWidget#ParameterTable QLineEdit {
            background-color: #2b2d31;
            color: #e8eaed;
            border: 1px solid #505258;
        }

        QTableWidget#ParameterTable QLineEdit:focus {
            border-color: #8ab4f8;
        }
        """

    def light_theme(self):
        return """
        /* toml_layout */
        QListWidget#tomlModuleList {
            background-color: #e8eaed;
            color: #494d53;
            border: none;
        }

        QListWidget#tomlModuleList::item {
            background-color: #e8eaed;
            border: 1px solid #505258;
            border-radius: 6px;
            padding: 12px;
            margin: 4px;
        }

        QListWidget#tomlModuleList::item:hover {
            background-color: #d2e3fc;
        }

        QListWidget#tomlModuleList::item:selected {
            background-color: #8ab4f8;
            color: #494d53;
            border-color: #4e729e;
        }

        /* module_picker_layout */
        QListWidget#ModulePicker {
            background-color: #e8eaed;
            color: #494d53;
            border: none;
        }

        QListWidget#ModulePicker::item {
            background-color: #e8eaed;
            border: 1px solid #505258;
            border-radius: 6px;
            padding: 6px;
            margin: 4px;
        }

        QListWidget#ModulePicker::item:hover {
            background-color: #d2e3fc;
        }

        QListWidget#ModulePicker::item:selected {
            background: #8ab4f8;
            border: 1px solid #4e729e;
        }
        """

    def cancel_program(self):
        self.close()

    def keyPressEvent(self, e):  
        if e.key() == Qt.Key_Escape:
            self.close()
        if e.key() == Qt.Key_F11:
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()

    def loadEvent(self):
        reply = QMessageBox.question(
            self,
            "Load TOML File",
            "Your current TOML file will be replaced. Are you sure you want to continue?",
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Yes,
        )
        return reply == QMessageBox.StandardButton.Yes
            
    
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Quit",
            "Are you sure you want to quit?",
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
    

def main():
    app = QApplication(sys.argv)
    font = QFont()
    font.setPointSize(11)
    app.setFont(font)
    window = MainWindow()
    window.showMaximized()
    app.exec()


if __name__ == "__main__":
    main()