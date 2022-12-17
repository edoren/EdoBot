from typing import Any, List, Mapping, MutableMapping, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLineEdit, QSpinBox, QWidget


class FormWidget(QWidget):
    valueChanged = Signal(str, object)

    def __init__(self,
                 parent: Optional[QWidget],
                 form: List[Mapping[str, Any]],
                 data: MutableMapping[str, Any] = {}) -> None:
        super().__init__(parent=parent)

        self.main_layout = QFormLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        position = 0
        for input_meta in form:
            qt_widget = None
            title = input_meta["title"]
            input_type = input_meta["type"]
            input_key = input_meta["id"]
            if input_type == "text_box":
                qt_input = QLineEdit(data.setdefault(input_key, input_meta.get("default", "")))
                qt_input.setProperty("key", input_key)
                qt_input.editingFinished.connect(self.__input_receiver)  # type: ignore
                qt_widget = qt_input
            elif input_type == "number_box":
                qt_spin_box = QSpinBox()
                qt_spin_box.setMaximum(1000000)
                qt_spin_box.setValue(data.setdefault(input_key, input_meta.get("default", 0)))
                qt_spin_box.setProperty("key", input_key)
                qt_spin_box.valueChanged.connect(self.__spin_box_receiver)  # type: ignore
                qt_widget = qt_spin_box
            elif input_type == "combo_box":
                qt_combo_box = QComboBox()
                qt_combo_box.setProperty("key", input_key)
                for choice in input_meta["choices"]:
                    qt_combo_box.addItem(choice["name"], choice["value"])
                current_key = data.setdefault(input_key, input_meta.get("default", input_meta["choices"][0]["value"]))
                qt_combo_box.setCurrentIndex(qt_combo_box.findData(current_key))
                qt_combo_box.activated.connect(self.__combo_box_receiver)  # type: ignore
                qt_widget = qt_combo_box
            elif input_type == "check_box":
                qt_check_box = QCheckBox()
                qt_check_box.setProperty("key", input_key)
                qt_check_box.setChecked(data.setdefault(input_key, input_meta.get("default", False)))
                qt_check_box.stateChanged.connect(self.__check_box_receiver)  # type: ignore
                qt_widget = qt_check_box
            if qt_widget:
                self.main_layout.insertRow(position, title, qt_widget)
                position += 1

        self.setLayout(self.main_layout)

    def __input_receiver(self):
        input_box: QLineEdit = self.sender()  # type: ignore
        self.valueChanged.emit(input_box.property("key"), input_box.text().strip())

    def __spin_box_receiver(self, i: int):
        spin_box: QSpinBox = self.sender()  # type: ignore
        self.valueChanged.emit(spin_box.property("key"), i)

    def __combo_box_receiver(self, i: int):
        combo_box: QComboBox = self.sender()  # type: ignore
        self.valueChanged.emit(combo_box.property("key"), combo_box.itemData(i))

    def __check_box_receiver(self, state: int):
        check_box: QCheckBox = self.sender()  # type: ignore
        self.valueChanged.emit(check_box.property("key"), state != 0)

    def set_values(self, data: Mapping[str, Any]) -> None:
        for i in range(self.main_layout.rowCount()):
            layoutItem = self.main_layout.itemAt(i, QFormLayout.ItemRole.FieldRole)
            widget = layoutItem.widget()
            input_key = widget.property("key")
            if input_key in data:
                if isinstance(widget, QLineEdit):
                    widget.setText(data[input_key])
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(widget.findData(data[input_key]))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(data[input_key])
