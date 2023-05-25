from typing import Union, Any, Tuple, Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QDialogButtonBox,
    QComboBox,
    QLineEdit,
    QLabel,
    QWidget,
    QTabWidget,
    QListWidget,
    QPushButton,
    QTableView,
    QCheckBox,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSlot, QEvent
from PyQt6.QtGui import QIntValidator, QDoubleValidator
from .ygModel import (
    unicode_cat_names,
    reverse_unicode_cat_names,
    ygMasters,
    random_id,
    ygFont,
    ygGlyph,
    ygPoint,
    ygcvt
)
from .ygPreferences import ygPreferences

NEW_CV_NAME = "New_Control_Value"
NEW_CV_CONTENT = {"val": 0, "axis": "y", "type": "pos"}

#
# A dialog (makeCVDialog) for creating a CV based on one or two selected points.
#
# A "Font Info" window (fontInfoWindow) for creating/editing/deleting CVs and
# their various properties; editing variation masters; and managing the defaults
# for the current font.
#
# Here is the structure of the Font Info window:
#
# fontInfoWindow ---|
#                   |---- cvEditPane -----|
#                   |                     | --- QListWidget
#                   |                     | --- cvWidget ---|
#                   |                                       |--- general_tab
#                   |                                       |--- same-as tab
#                   |                                       |--- deltas tab
#                   |                                       |--- variants tab
#                   |
#                   |--- mastersWidget ---|
#                   |                     |--- QListWidget
#                   |                     |--- masterWidget
#                   |                     |--- generate variant CVs button
#                   |
#                   |--- font defaults ---|
#                                         |--- Rounding
#                                         |--- Miscellaneous defaults


class cvSource:
    """Mixin superclass for objects that serve CV data."""

    def send_error_message(self, d: dict):
        ...

    def cvt(self):
        ...

    def current_cv(self):
        ...

    def current_cv_name(self):
        ...

    def set_cv_name(self, s: str):
        ...

    def from_current_cv(self, s: str):
        ...

    def set_in_current_cv(self, k: str, s, fallback: Any):
        ...

    def has_key(self, k: str):
        ...

    def del_key(self, k: str):
        ...


class cvEditPane(QWidget, cvSource):
    """A widget with a list of CVs and a cvWidget. Click in the
    list to display and edit that CV.

    params:

    owner: The owner of this widget.

    yg_font (ygFont): The font being edited.

    preferences (ygPreferences): The preferences for this app.

    """

    def __init__(self, owner, yg_font: ygFont, preferences: ygPreferences) -> None:
        super().__init__()
        self.owner = owner
        self.yg_font = yg_font
        self._cvt = self.yg_font.cvt
        self.preferences = preferences
        self.layout_obj = QHBoxLayout()

        # Set up CV list.

        self.cv_list_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.cv_list = QListWidget()
        self.cv_list.addItems(self._cvt.keys)
        self.current_list_item = self.cv_list.item(0)
        self.cv_list.setCurrentItem(self.current_list_item)
        self._current_cv_name = self.current_list_item.text()
        self.cv_list.itemActivated.connect(self.new_item)

        # And the edit pane.

        self._current_cv = self._cvt.get_cv(self._current_cv_name)
        self.edit_pane = cvWidget(self, self.yg_font, self)

        # Put them together

        self.cv_list_layout.addWidget(self.cv_list)
        add_button = QPushButton("Add")
        del_button = QPushButton("Delete")
        self.button_layout.addWidget(add_button)
        self.button_layout.addWidget(del_button)
        add_button.clicked.connect(self.add_cv)
        del_button.clicked.connect(self.del_cv)
        self.cv_list_layout.addLayout(self.button_layout)
        self.layout_obj.addLayout(self.cv_list_layout)
        self.layout_obj.addWidget(self.edit_pane)
        self.setLayout(self.layout_obj)

    def send_error_message(self, d: dict) -> None:
        self.yg_font.send_error_message(d)

    def add_cv(self) -> None:
        self._current_cv_name = NEW_CV_NAME
        self._cvt.add_cv(self._current_cv_name, NEW_CV_CONTENT)
        self.cv_list.addItem(self._current_cv_name)
        matches = self.cv_list.findItems(
            self._current_cv_name, Qt.MatchFlag.MatchExactly
        )
        if len(matches) > 0:
            self.current_list_item = matches[0]
            self.cv_list.setCurrentItem(self.current_list_item)
            self.new_item(self.current_list_item, forced=True)

    def change_name_in_list(self, n) -> None:
        self.current_list_item.setText(n)

    def del_cv(self) -> None:
        self._cvt.del_cv(self._current_cv_name)
        self.cv_list.clear()
        try:
            self._current_cv_name = list(self._cvt.keys)[0]
        except IndexError:
            return
        self.refresh()

    def refresh(self) -> None:
        """This is the place to figure out whether the source
        or masters have been changed: if not, we don't have to
        go through all this.
        """
        if not len(self._cvt):
            self.add_cv()
        self._current_cv = self._cvt.get_cv(self._current_cv_name)
        self.cv_list.clear()
        self.cv_list.addItems(self._cvt.keys)
        matches = self.cv_list.findItems(
            self._current_cv_name, Qt.MatchFlag.MatchExactly
        )
        if len(matches) > 0:
            self.cv_list.setCurrentItem(matches[0])
        else:
            try:
                current_item = self.cv_list.item(0)
                self.cv_list.setCurrentItem(current_item)
                self._current_cv_name = current_item.text()
                self._current_cv = self._cvt.get_cv(self._current_cv_name)
            except Exception:
                pass
        self.edit_pane.refresh(self)

    def fixup(self) -> None:
        self.edit_pane.fixup()

    def new_item(self, list_item, forced: bool = False) -> None:
        """Switch the view to another cv. Simply delete the
        old cv editing pane and create a new one to put
        in its place.
        """
        new_cv_name = list_item.text()
        if forced or new_cv_name != self._current_cv_name:
            old_pane = self.layout_obj.itemAt(1)
            self.layout_obj.removeItem(old_pane)
            old_pane.widget().deleteLater()
            self._current_cv_name = new_cv_name
            self._current_cv = self._cvt.get_cv(self._current_cv_name)
            self.edit_pane = cvWidget(self, self.yg_font, self)
            self.layout_obj.addWidget(self.edit_pane)

    def cvt(self) -> ygcvt:
        return self._cvt

    def current_cv(self) -> Union[int, dict]:
        return self._current_cv

    def current_cv_name(self) -> str:
        return self._current_cv_name

    def set_cv_name(self, s: str) -> None:
        self._current_cv_name = s

    def from_current_cv(self, s: str):
        try:
            return self._current_cv[s] # type: ignore
        except KeyError:
            return None

    def set_in_current_cv(self, k: str, s: Any, fallback = Optional[str]) -> None:
        if s == "None" or s == "" or s == None:
            if fallback != None:
                self._cvt.set_cv_property(self.current_cv_name(), k, fallback)
            else:
                if k in self._current_cv: # type: ignore
                    self._cvt.del_cv(k)
        else:
            self._cvt.set_cv_property(self.current_cv_name(), k, s)

    def has_key(self, k: str) -> bool:
        return k in self._current_cv # type: ignore

    def del_key(self, k: str) -> None:
        self._cvt.del_cv_property(self.current_cv_name(), k)

    def rename_cv(self, old_name: str, new_name: str) -> None:
        self._cvt.rename(old_name, new_name)

    def showEvent(self, event) -> None:
        self.refresh()

    def hideEvent(self, event) -> None:
        self.fixup()


class fontInfoWindow(QWidget):
    """A one-stop shop for font-level settings: CVs, masters, font-wide
    defaults.

    params:

    yg_font (ygFont): The font being edited.

    preferences (ygPreferences): The preferences for this app.

    """

    def __init__(self, yg_font: ygFont, preferences: ygPreferences) -> None:
        super().__init__()
        self.yg_font = yg_font
        self.cvt = self.yg_font.cvt
        self.preferences = preferences
        self.layout_obj = QVBoxLayout()

        # Set up tabs

        self.tabs = QTabWidget()
        self.cv_tab = cvEditPane(self, self.yg_font, self.preferences)
        self._empty_string = "{}\n"
        self.masters_tab = None
        if self.yg_font.is_variable_font:
            self.masters_tab = mastersWidget(self, self.yg_font)
        self.tabs.addTab(self.cv_tab, "Control Values")
        if self.yg_font.is_variable_font:
            self.tabs.addTab(self.masters_tab, "Masters")
        self.defaults_pane = defaultsPane(self.yg_font)
        self.tabs.addTab(self.defaults_pane, "Defaults")
        self.layout_obj.addWidget(self.tabs)
        self.setLayout(self.layout_obj)
        self.window().setWindowTitle("Font Info")

    def undo_state_active(self) -> None:
        if not self.yg_font.undo_stack.isActive():
            self.yg_font.undo_stack.setActive(True)

    def closeEvent(self, event) -> None:
        self.hide()

    @pyqtSlot()
    def refresh(self) -> None:
        self.cv_tab.refresh()
        self.defaults_pane.refresh()
        if self.masters_tab:
            self.masters_tab.refresh()

    def event(self, event) -> bool:
        if event.type() == event.Type.WindowActivate:
            self.undo_state_active()
            # self.yg_font.undo_stack.setActive(True)
        return super().event(event)


class mastersWidget(QWidget):
    """A pane for editing masters.

    params:

    owner: The owner of this widget.

    yg_font (ygFont): The font being edited.

    """

    def __init__(self, owner: fontInfoWindow, yg_font: ygFont) -> None:
        super().__init__()
        self.owner = owner
        self.yg_font = yg_font
        self.masters = self.yg_font.masters

        self.layout_obj = QHBoxLayout()
        self.master_list_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.master_list = QListWidget()
        self.master_list.addItems(self.masters.names)
        self.current_list_item = self.master_list.item(0)
        self.master_list.setCurrentItem(self.current_list_item)
        self.master_list.itemActivated.connect(self.new_item)

        self._current_master = self.masters.master_by_name(
            self.current_list_item.text()
        )

        # And the edit pane.

        self.edit_pane = masterWidget(
            self.masters, self._current_master[0], self.yg_font
        )

        self.master_list_layout.addWidget(self.master_list)
        add_button = QPushButton("Add")
        del_button = QPushButton("Delete")
        self.button_layout.addWidget(add_button)
        self.button_layout.addWidget(del_button)
        add_button.clicked.connect(self.add_master)
        del_button.clicked.connect(self.del_master)
        self.master_list_layout.addLayout(self.button_layout)
        self.refresh_variants_button = QPushButton("Generate Variant Control Values")
        self.refresh_variants_button.clicked.connect(self.yg_font.refresh_variant_cvs)
        self.master_list_layout.addWidget(self.refresh_variants_button)
        self.layout_obj.addLayout(self.master_list_layout)
        self.layout_obj.addWidget(self.edit_pane)
        self.setLayout(self.layout_obj)

    def current_master_name(self) -> str:
        return self._current_master[1]["name"]

    def current_master_id(self) -> str:
        return self._current_master[0]

    def new_item(self, list_item: QListWidgetItem, forced: bool = False) -> None:
        new_master_name = list_item.text()
        new_master = self.masters.master_by_name(new_master_name)
        if forced or new_master_name != self.current_master_name():
            old_pane = self.layout_obj.itemAt(1)
            self.layout_obj.removeItem(old_pane)
            old_pane.widget().deleteLater()
            self._current_master = new_master
            self.edit_pane = masterWidget(
                self.masters, self.current_master_id(), self.yg_font
            )
            self.layout_obj.addWidget(self.edit_pane)

    def add_master(self) -> None:
        master_dict = {}
        axis_tags = self.yg_font.axis_tags
        for a in axis_tags:
            master_dict[a] = 0.0
        master_id = random_id("master")
        master_vals = {"name": master_id, "vals": master_dict}
        self.yg_font.masters.add_master(master_id, master_vals)
        self.refresh()

    def del_master(self) -> None:
        self.yg_font.masters.del_by_name(self.current_master_name())
        self.master_list.clear()
        try:
            self._current_master = self.masters.master_by_name(
                self.yg_font.masters.names[0]
            )
        except IndexError:
            return
        self.refresh()

    def refresh(self) -> None:
        if not len(self.yg_font.masters):
            return
        self.master_list.clear()
        self.master_list.addItems(self.yg_font.masters.names)
        matches = self.master_list.findItems(
            self.current_master_name(), Qt.MatchFlag.MatchExactly
        )
        if len(matches) > 0:
            self.master_list.setCurrentItem(matches[0])
        else:
            try:
                current_item = self.master_list.item(0)
                self.master_list.setCurrentItem(current_item)
                self._current_master = self.yg_font.masters.master_by_name(
                    current_item.text()
                )
            except Exception:
                pass
        self.edit_pane.refresh(self._current_master)


class masterWidget(QWidget):
    """A pane for editing a master.

    params:

    masters (ygMasters): The masters for this font.

    m_id (str): The ID of the present master.

    yg_font (ygFont): The font being edited.

    """

    def __init__(self, masters: ygMasters, m_id: str, yg_font: ygFont) -> None:
        super().__init__()
        self.masters = masters
        self.m_id = m_id
        self.master_layout = QVBoxLayout()
        self.name_layout = QHBoxLayout()
        self.name_layout.addWidget(QLabel("Name"))
        self.master_name_widget = masterNameWidget(self.masters, self.m_id)
        self.name_layout.addWidget(self.master_name_widget)
        self.master_layout.addLayout(self.name_layout)
        self.names = []
        axis_tags = yg_font.axis_tags
        for axis_name in axis_tags:
            axis_val_layout = QHBoxLayout()
            axis_val_layout.addWidget(QLabel(axis_name))
            n = masterValWidget(self.masters, self.m_id, axis_name)
            self.names.append(n)
            axis_val_layout.addWidget(n)
            self.master_layout.addLayout(axis_val_layout)
        self.setLayout(self.master_layout)

    def refresh(self, m: Tuple[str, dict]) -> None:
        """Where m is a master tuple (id, dict of axis:val)"""
        self.m_id = m[0]
        self.master_name_widget.refresh(m)
        for n in self.names:
            n.refresh(m)

    # def event(self, event):
    #    print(event)
    #    print(event.type())
    #    print(event.spontaneous())
    #    return super().event(event)


class cvDeltaWidget(QTableView):
    """A table for creating and editing CV Deltas.

    params: cv_source (cvSource): The CV to which deltas will be applied.

    """

    def __init__(self, cv_source: cvSource) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.delta_data = self.cv_source.cvt().get_deltas(
            self.cv_source.current_cv_name()
        )
        self.setModel(self.delta_data)


class cvWidget(QWidget):
    """A pane for making and editing CVs. This class keeps a reference
    to the CV being edited and updates it as the user works with the
    controls.

    params:

    cv_source (cvSource): data from one CV.

    yg_font (ygFont): The font being edited.

    owner: The owner of this widget.

    parent: The parent of this widget.

    delta_pane (bool): Whether a delta pane should be included.

    variant_pane (bool): Whether (if this is a variable font) a
    variant pane should be included.

    """

    def __init__(
        self,
        cv_source: cvSource,
        yg_font: ygFont,
        owner: cvEditPane,
        parent=None,
        delta_pane: bool = True,
        variant_pane: bool = True,
    ):
        super().__init__(parent=parent)
        self.yg_font = yg_font
        self.owner = owner
        self.cv_source = cv_source
        self.layout_obj = QVBoxLayout()

        # Set up tabs

        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.link_tab = QWidget()
        self.delta_tab = None
        self.variants_tab = None
        self.masters = None
        if self.yg_font.is_variable_font and variant_pane:
            self.variants_tab = QWidget()
            self.masters = self.yg_font.masters
        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.link_tab, "Same As")
        if delta_pane:
            self.delta_tab = QWidget()
            self.tabs.addTab(self.delta_tab, "Deltas")
        if self.variants_tab:
            self.tabs.addTab(self.variants_tab, "Variants")

        # set up general tab

        self.general_tab_layout = QVBoxLayout()
        self.cv_type_widget = cvTypeWidget(self.cv_source)
        self.cv_color_widget = cvColorWidget(self.cv_source)
        self.cv_axis_widget = cvAxisWidget(self.cv_source)
        self.cv_val_widget = cvValueWidget(self.cv_source)
        self.cv_name_widget = cvNameWidget(self.cv_source, owner=self.owner)
        self.cv_cat_widget = cvUCatWidget(self.cv_source)
        self.cv_suffix_widget = cvSuffixWidget(self.cv_source)

        self.gen_widgets = []

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("name"))
        self.gen_widgets[-1].addWidget(self.cv_name_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("val"))
        self.gen_widgets[-1].addWidget(self.cv_val_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("type"))
        self.gen_widgets[-1].addWidget(self.cv_type_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("axis"))
        self.gen_widgets[-1].addWidget(self.cv_axis_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("cat"))
        self.gen_widgets[-1].addWidget(self.cv_cat_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("suffix"))
        self.gen_widgets[-1].addWidget(self.cv_suffix_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("distance type"))
        self.gen_widgets[-1].addWidget(self.cv_color_widget)

        # Set up link tab

        self.link_tab_layout = QVBoxLayout()

        self.cv_below_ppem_widget = cvPPEMWidget(self.cv_source, "below")
        self.cv_above_ppem_widget = cvPPEMWidget(self.cv_source, "above")
        self.cv_below_names_widget = cvNamesWidget(
            self.cv_source, "below", self.yg_font, ppem_widget=self.cv_below_ppem_widget
        )
        self.cv_above_names_widget = cvNamesWidget(
            self.cv_source, "above", self.yg_font, ppem_widget=self.cv_above_ppem_widget
        )
        self.cv_below_ppem_widget.name_widget = self.cv_below_names_widget # type: ignore
        self.cv_above_ppem_widget.name_widget = self.cv_above_names_widget # type: ignore

        self.link_widgets = []

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("same as"))
        self.link_widgets[-1].addWidget(self.cv_below_names_widget)

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("below"))
        self.link_widgets[-1].addWidget(self.cv_below_ppem_widget)
        self.link_widgets[-1].addWidget(QLabel("ppem"))

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("and"))

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("same as"))
        self.link_widgets[-1].addWidget(self.cv_above_names_widget)

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("above"))
        self.link_widgets[-1].addWidget(self.cv_above_ppem_widget)
        self.link_widgets[-1].addWidget(QLabel("ppem"))

        # Set up deltas tab

        self.delta_tab_layout = None
        if self.delta_tab:
            self.delta_tab_layout = QVBoxLayout()
            self.delta_pane = cvDeltaWidget(self.cv_source)
            self.delta_button_layout = QHBoxLayout()
            add_delta_button = QPushButton("Add")
            del_delta_button = QPushButton("Delete")
            add_delta_button.clicked.connect(self.delta_pane.model().new_row) # type: ignore
            del_delta_button.clicked.connect(self.del_delta_row)
            self.delta_button_layout.addWidget(add_delta_button)
            self.delta_button_layout.addWidget(del_delta_button)
            self.delta_tab_layout.addWidget(self.delta_pane)
            self.delta_tab_layout.addLayout(self.delta_button_layout)

        # Set up variants tab

        self.variants_tab_layout = None
        if self.variants_tab:
            self.variants_tab_layout = QVBoxLayout()
            self.var_widgets = []
            self.var_layouts = []
            master_keys = self.masters.keys # type: ignore
            for k in master_keys:
                self.var_layouts.append(QHBoxLayout())
                self.var_layouts[-1].addWidget(QLabel(self.masters.get_master_name(k))) # type: ignore
                self.var_widgets.append(cvVarWidget(k, self.cv_source))
                self.var_layouts[-1].addWidget(self.var_widgets[-1])

        for w in self.gen_widgets:
            self.general_tab_layout.addLayout(w)
        for w in self.link_widgets:
            self.link_tab_layout.addLayout(w)
        if self.variants_tab:
            for w in self.var_layouts:
                self.variants_tab_layout.addLayout(w) # type: ignore

        self.general_tab.setLayout(self.general_tab_layout)
        self.link_tab.setLayout(self.link_tab_layout)
        if self.delta_tab:
            self.delta_tab.setLayout(self.delta_tab_layout) # type: ignore
        if self.variants_tab:
            self.variants_tab.setLayout(self.variants_tab_layout) # type: ignore
        self.layout_obj.addWidget(self.tabs)
        self.setLayout(self.layout_obj)

    def del_delta_row(self) -> None:
        i = self.delta_pane.selectedIndexes()
        if len(i) > 0:
            self.delta_pane.model().deleteRows(i[0].row(), 1) # type: ignore

    def refresh(self, cv_source: cvSource) -> None:
        """If we're coming from the source pane, every cv in the
        cvt will have been replaced, so references to it have
        got to be refreshed and the widgets updated as needed.
        Think about whether there's a less awkward way to do
        this.
        """
        self.cv_source = cv_source
        self.cv_name_widget.refresh(self.cv_source)
        self.cv_type_widget.refresh(self.cv_source)
        self.cv_axis_widget.refresh(self.cv_source)
        self.cv_color_widget.refresh(self.cv_source)
        self.cv_val_widget.refresh(self.cv_source)
        self.cv_cat_widget.refresh(self.cv_source)
        self.cv_suffix_widget.refresh(self.cv_source)
        self.cv_below_ppem_widget.refresh(self.cv_source)
        self.cv_above_ppem_widget.refresh(self.cv_source)
        self.cv_below_names_widget.refresh(self.cv_source)
        self.cv_above_names_widget.refresh(self.cv_source)
        if self.masters:
            for w in self.var_widgets:
                w.refresh(self.cv_source)

    def fixup(self) -> None:
        self.cv_name_widget.fixup()
        self.cv_type_widget.fixup()
        self.cv_axis_widget.fixup()
        self.cv_color_widget.fixup()
        self.cv_val_widget.fixup()
        self.cv_cat_widget.fixup()
        self.cv_suffix_widget.fixup()
        self.cv_below_ppem_widget.fixup()
        self.cv_above_ppem_widget.fixup()
        self.cv_below_names_widget.fixup()
        self.cv_above_names_widget.fixup()
        if self.masters:
            for w in self.var_widgets:
                w.fixup()

    # def event(self, event):
    #    print(event)
    #    return super().event(event)


class defaultsPane(QWidget):
    """A tabbed pane holding two panes for editing font-wide
    defaults.

    params:

    yg_font (ygFont): The font being edited.

    """

    def __init__(self, yg_font: ygFont) -> None:
        super().__init__()
        self.layout_obj = QVBoxLayout()
        self.tabs = QTabWidget()
        self.round_widget = hintRoundWidget(yg_font)
        self.misc_widget = miscDefaultsWidget(yg_font)
        self.tabs.addTab(self.round_widget, "Rounding")
        self.tabs.addTab(self.misc_widget, "Miscellaneous")
        self.layout_obj.addWidget(self.tabs)
        self.setLayout(self.layout_obj)

    def refresh(self) -> None:
        self.round_widget.refresh()
        self.misc_widget.refresh()


class hintRoundWidget(QWidget):
    """Widget for editing the initial round state of the seven types of
    hint.

    params:

    yg_font (ygFont): The font being edited.

    """

    def __init__(self, yg_font: ygFont) -> None:
        super().__init__()
        self.yg_font = yg_font
        self.defaults = yg_font.defaults
        self.layout_obj = QVBoxLayout()
        self.ignore_signal = False

        self.anchor_layout = QHBoxLayout()
        self.anchor_checkbox = QCheckBox("Anchor")
        self.anchor_layout.addWidget(self.anchor_checkbox)
        self.layout_obj.addLayout(self.anchor_layout)

        self.blackdist_layout = QHBoxLayout()
        self.blackdist_checkbox = QCheckBox("Black distance")
        self.blackdist_layout.addWidget(self.blackdist_checkbox)
        self.layout_obj.addLayout(self.blackdist_layout)

        self.whitedist_layout = QHBoxLayout()
        self.whitedist_checkbox = QCheckBox("White distance")
        self.whitedist_layout.addWidget(self.whitedist_checkbox)
        self.layout_obj.addLayout(self.whitedist_layout)

        self.graydist_layout = QHBoxLayout()
        self.graydist_checkbox = QCheckBox("Gray distance")
        self.graydist_layout.addWidget(self.graydist_checkbox)
        self.layout_obj.addLayout(self.graydist_layout)

        self.shift_layout = QHBoxLayout()
        self.shift_checkbox = QCheckBox("Shift")
        self.shift_layout.addWidget(self.shift_checkbox)
        self.layout_obj.addLayout(self.shift_layout)

        self.align_layout = QHBoxLayout()
        self.align_checkbox = QCheckBox("Align")
        self.align_layout.addWidget(self.align_checkbox)
        self.layout_obj.addLayout(self.align_layout)

        self.interpolate_layout = QHBoxLayout()
        self.interpolate_checkbox = QCheckBox("Interpolate")
        self.interpolate_layout.addWidget(self.interpolate_checkbox)
        self.layout_obj.addLayout(self.interpolate_layout)

        self.refresh()

        self.anchor_checkbox.stateChanged.connect(self.button_state_changed)
        self.blackdist_checkbox.stateChanged.connect(self.button_state_changed)
        self.whitedist_checkbox.stateChanged.connect(self.button_state_changed)
        self.graydist_checkbox.stateChanged.connect(self.button_state_changed)
        self.shift_checkbox.stateChanged.connect(self.button_state_changed)
        self.align_checkbox.stateChanged.connect(self.button_state_changed)
        self.interpolate_checkbox.stateChanged.connect(self.button_state_changed)

        self.setLayout(self.layout_obj)

    def button_state_changed(self) -> None:
        if self.ignore_signal:
            return
        r = {}
        r["anchor"] = self.anchor_checkbox.isChecked()
        r["blackdist"] = self.blackdist_checkbox.isChecked()
        r["whitedist"] = self.whitedist_checkbox.isChecked()
        r["graydist"] = self.graydist_checkbox.isChecked()
        r["shift"] = self.shift_checkbox.isChecked()
        r["align"] = self.align_checkbox.isChecked()
        r["interpolate"] = self.interpolate_checkbox.isChecked()
        self.defaults.set_rounding_defaults(r)

    def fixup(self) -> None:
        pass

    def refresh(self) -> None:
        self.ignore_signal = True
        self.anchor_checkbox.setChecked(self.defaults.rounding_state("anchor"))
        self.blackdist_checkbox.setChecked(self.defaults.rounding_state("blackdist"))
        self.whitedist_checkbox.setChecked(self.defaults.rounding_state("whitedist"))
        self.graydist_checkbox.setChecked(self.defaults.rounding_state("graydist"))
        self.shift_checkbox.setChecked(self.defaults.rounding_state("shift"))
        self.align_checkbox.setChecked(self.defaults.rounding_state("align"))
        self.interpolate_checkbox.setChecked(
            self.defaults.rounding_state("interpolate")
        )
        self.ignore_signal = False


class miscDefaultsWidget(QWidget):
    """GUI for setting defaults that have nothing to do with rounding.

    params:

    yg_font (ygFont): the font now being edited.
    """

    def __init__(self, yg_font: ygFont) -> None:
        super().__init__()
        self.yg_font = yg_font
        self.defaults = yg_font.defaults
        self.layout_obj = QGridLayout()
        self.layout_obj.setHorizontalSpacing(20)
        self.layout_obj.setVerticalSpacing(0)
        self.ignore_signal = False

        self.tt_defaults = QCheckBox("Use TrueType defaults")
        s =  "<span>If</span> this is checked, all instructions in the CVT program that set "
        s += "defaults will be ignored."
        self.tt_defaults.setToolTip(s)
        self.tt_defaults.stateChanged.connect(self.toggle_tt_defaults)

        self.init_graphics = QCheckBox("Initialize graphics")
        s =  "<span>If</span> this is checked, code to initialize graphics variables will "
        s += "be inserted at the beginning of each glyph program. This should "
        s += "normally be left unchecked, as these variables are seldom "
        s += "consulted in modern TrueType hinting."
        self.init_graphics.setToolTip(s)
        self.init_graphics.stateChanged.connect(self.toggle_init_graphics)

        self.assume_always_y = QCheckBox("Assume axis always y")
        s =  "<span>Instructs</span> the compiler to assume that you are only hinting on "
        s += "y axis. When this is checked, Ygt will perform several optimizations."
        self.assume_always_y.setToolTip(s)
        self.assume_always_y.stateChanged.connect(self.toggle_assume_always_y)

        self.counterclockwise = QCheckBox("Outer contours counter-clockwise")
        s =  "<span>When</span> outer contours are counter-clockwise, Ygt will guess distance types "
        s += "wrongly. Check this box and it will guess correctly. You should also "
        s += "select View→Point coordinates since contours will probably be reversed "
        s += "when you generate the font, throwing off the point indices."
        self.counterclockwise.setToolTip(s)
        self.counterclockwise.stateChanged.connect(self.toggle_counterclockwise)

        self.cleartype = QCheckBox("Cleartype")
        s =  "<span>If</span> this box is checked, MS Windows will render your font"
        s += "in native ClearType mode."
        self.cleartype.setToolTip(s)
        self.cleartype.stateChanged.connect(self.toggle_cleartype)

        self.mergemode = QCheckBox("Merge mode")
        s =  "<span>Check</span> this box if you are hinting a font containing hints that you "
        s += "want to retain. Glyphs that you’ve hinted will use your hints. Your functions "
        s += "and control values will be appended to the ones already in the font."
        self.mergemode.setToolTip(s)
        self.mergemode.stateChanged.connect(self.toggle_mergemode)

        self.replaceprep = QCheckBox("Replace CVT program")
        s =  "<span>Only</span> available when merge mode is active. If you check this box, "
        s += "the CVT program generated by Ygt will replace the one in the font. Otherwise, "
        s += "the Ygt CVT program will be appended to the existing one."
        self.replaceprep.setToolTip(s)
        self.replaceprep.stateChanged.connect(self.toggle_replaceprep)

        self.functionbase = functionBaseWidget(self.defaults)
        s =  "In merge mode, <span>set</span> 'function-base' to a non-zero value if Ygt guesses wrongly "
        s += "about the highest-numbered function in the font to which you are adding hints."
        self.functionbase.setToolTip(s)

        self.layout_obj.addWidget(self.tt_defaults, 1, 1)
        self.layout_obj.addWidget(self.init_graphics, 2, 1)
        self.layout_obj.addWidget(self.cleartype, 3, 1)
        self.layout_obj.addWidget(self.assume_always_y, 4, 1)
        self.layout_obj.addWidget(self.counterclockwise, 1, 2)
        self.layout_obj.addWidget(self.mergemode, 2, 2)
        self.layout_obj.addWidget(self.replaceprep, 3, 2)
        self.functionbase.setFixedWidth(int(self.functionbase.width() /4))
        function_base_layout = QHBoxLayout()
        function_base_layout.addWidget(QLabel("Function base"))
        function_base_layout.addWidget(self.functionbase, alignment = Qt.AlignmentFlag.AlignLeft)
        self.layout_obj.addLayout(function_base_layout, 4, 2)

        self.setLayout(self.layout_obj)

        self.refresh()

    def toggle_counterclockwise(self) -> None:
        if self.ignore_signal:
            return
        if self.counterclockwise.isChecked():
            self.defaults.set_default({"counterclockwise": True})
        else:
            self.defaults.del_default("counterclockwise")

    def toggle_tt_defaults(self) -> None:
        if self.ignore_signal:
            return
        if self.tt_defaults.isChecked():
            self.defaults.set_default({"use-truetype-defaults": True})
        else:
            self.defaults.del_default("use-truetype-defaults")

    def toggle_init_graphics(self) -> None:
        if self.ignore_signal:
            return
        if not self.init_graphics.isChecked():
            self.defaults.set_default({"init-graphics": False})
        else:
            self.defaults.del_default("init-graphics")

    def toggle_assume_always_y(self) -> None:
        if self.ignore_signal:
            return
        if self.assume_always_y.isChecked():
            self.defaults.set_default({"assume-always-y": True})
        else:
            self.defaults.del_default("assume-always-y")

    def toggle_cleartype(self) -> None:
        if self.ignore_signal:
            return
        if self.cleartype.isChecked():
            self.defaults.set_default({"cleartype": True})
        else:
            self.defaults.del_default("cleartype")

    def toggle_mergemode(self) -> None:
        if self.ignore_signal:
            return
        if self.mergemode.isChecked():
            self.defaults.set_default({"merge-mode": True})
            self.replaceprep.setEnabled(True)
            self.functionbase.setEnabled(True)
        else:
            self.defaults.del_default("merge-mode")
            self.replaceprep.setEnabled(False)
            self.functionbase.setEnabled(False)

    def toggle_replaceprep(self) -> None:
        if self.ignore_signal:
            return
        if bool(self.defaults.get_default("merge-mode")) and self.replaceprep.isChecked():
            self.defaults.set_default({"replace-prep": True})
        else:
            self.defaults.del_default("replace-prep")

    def fixup(self) -> None:
        pass

    def refresh(self, ign: bool = True) -> None:
        self.ignore_signal = ign

        t = self.defaults.get_default("use-truetype-defaults")
        self.tt_defaults.setChecked(bool(t))

        t = self.defaults.get_default("init-graphics")
        if t == None:
            t = True
        self.init_graphics.setChecked(t)

        t = self.defaults.get_default("assume-always-y")
        self.assume_always_y.setChecked(bool(t))

        t = self.defaults.get_default("cleartype")
        self.cleartype.setChecked(bool(t))

        t = self.defaults.get_default("merge-mode")
        self.mergemode.setChecked(bool(t))

        t = self.defaults.get_default("replace-prep")
        self.replaceprep.setChecked(bool(t))

        if not bool(t):
            self.replaceprep.setEnabled(False)
            self.functionbase.setEnabled(False)

        self.ignore_signal = False


class makeCVDialog(QDialog, cvSource):
    """A dialog for creating a cv. This doesn't edit the cvt source
    directly, but instead works on a fragment of cv code to be
    added when the accept() function is called.

    params:

    p1 (ygPoint): The first selected point.

    p2 (ygPoint): The second selected point; or None if only one
    point is selected.

    yg_glyph (ygGlyph): The current glyph.

    preferences (ygPreferences): the preferences for this app.

    """
    def __init__(self, p1: ygPoint, p2: ygPoint, yg_glyph: ygGlyph, preferences: ygPreferences) -> None:
        super().__init__()
        self.top_window = preferences.top_window()
        self.yg_font = yg_glyph.yg_font
        self._cvt = self.yg_font.cvt
        self.cv = {}
        self.cv_name = ""
        self.axis = preferences.top_window().current_axis
        self.cv["axis"] = self.axis
        if p2 != None:
            init_type = "dist"
            origin_indices = [p1.index, p2.index]
        else:
            init_type = "pos"
            origin_indices = [p1.index]
        self.cv["type"] = init_type
        val = 0
        if self.axis == "y":
            if init_type == "pos":
                val = p1.font_y
            else:
                val = abs(p1.font_y - p2.font_y)
        else:
            if init_type == "pos":
                val = p1.font_x
            else:
                val = abs(p1.font_x - p2.font_x)
        self.cv["val"] = val
        self.cv["origin"] = {"glyph": yg_glyph.gname, "ptnum": origin_indices}

        self.layout_obj = QVBoxLayout()

        self.pane = cvWidget(
            self, self.yg_font, None, delta_pane=False, variant_pane=False
        )

        # Set up buttons

        QBtn = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout_obj.addWidget(self.pane)
        self.layout_obj.addWidget(self.buttonBox)
        self.setLayout(self.layout_obj)
        self.setWindowTitle("Make Control Value")

    def send_error_message(self, d: dict) -> None:
        self.yg_font.send_error_message(d)

    def cvt(self) -> ygcvt:
        return self._cvt

    def current_cv(self) -> dict:
        return self.cv

    def current_cv_name(self) -> str:
        return self.cv_name

    def set_cv_name(self, s: str):
        self.cv_name = s

    def from_current_cv(self, s: str) -> None:
        try:
            return self.cv[s]
        except KeyError:
            pass

    def set_in_current_cv(self, k: str, s: Any, fallback=None) -> None:
        if s == "None" or s == "" or s == None:
            if fallback != None:
                self.cv[k] = fallback
            else:
                if k in self.cv:
                    del self.cv[k]
                #if k in self._current_cv:
                #    del self._current_cv[k]
        else:
            self.cv[k] = s

    def has_key(self, k: str) -> bool:
        return k in self.cv

    def del_key(self, k: str) -> None:
        try:
            del self.cv[k]
        except KeyError:
            pass

    def accept(self) -> None:
        self.pane.fixup()
        if self.cv_name and len(self.cv) > 0:
            self._cvt.add_cv(self.cv_name, self.cv)
        super().accept()

    def showEvent(self, event) -> None:
        self.yg_font.undo_stack.setActive(True)


class cvNameWidget(QLineEdit):
    """A widget for editing the name of a cv. Disable when it shouldn't
    be edited.

    params:

    cv_source (cvSource): Data for currently selected CV.

    owner: The owner of this widget.
    """

    def __init__(self, cv_source: cvSource, owner: Any = None) -> None:
        super().__init__()
        self.owner = owner
        self.cv_source = cv_source
        self.cv_name = self.cv_source.current_cv_name()
        self.dirty = False
        if len(self.cv_name) > 0:
            self.setText(self.cv_name)
            if self.cv_name != NEW_CV_NAME:
                self.setEnabled(False)
        if self.isEnabled():
            self.editingFinished.connect(self.text_changed)
            self.textChanged.connect(self.set_dirty)
        self.last_val = self.cv_name

    def _text(self) -> str:
        return self.text().strip()

    def set_dirty(self) -> None:
        self.dirty = True

    def set_clean(self) -> None:
        self.dirty = False

    def fixup(self) -> None:
        t = self._text()
        if self.isEnabled() and self.dirty and t != self.last_val:
            # If the cv name changes, the original cv in the source tree
            # has to be deleted and a new cv entered under the new name.
            # We can either do that (at some risk of bugginess) or disable
            # the cv name widget when the cv is being edited (as opposed
            # to created).
            old_name = self.cv_source.current_cv_name()
            self.cv_source.set_cv_name(t)
            if self.owner != None:
                self.owner.change_name_in_list(t)
                self.owner.rename_cv(old_name, t)
            self.last_val = t
            self.set_clean()

    def text_changed(self) -> None:
        self.fixup()

    def refresh(self, cv_source: cvSource) -> None:
        self.cv_source = cv_source
        self.setText(self.cv_source.current_cv_name())
        self.set_clean()


class cvTypeWidget(QComboBox):
    """Widget for choosing a CV type.

    params:

    cv_source (cvSource): Data for currently selected CV.

    """

    def __init__(self, cv_source: cvSource) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.addItem("pos")
        self.addItem("dist")
        t = self.cv_source.from_current_cv("type")
        self.setCurrentText((lambda: "y" if not t else t)())
        self.currentTextChanged.connect(self.text_changed)
        self.last_val = self.currentText()

    def _text(self) -> str:
        return self.currentText()

    def fixup(self) -> None:
        t = self.currentText()
        if t != self.last_val:
            self.cv_source.set_in_current_cv("type", self.currentText(), None)
            self.last_val = t

    def text_changed(self, event) -> None:
        self.fixup()

    def refresh(self, cv_source: cvSource) -> None:
        self.cv_source = cv_source
        self.setCurrentText(self.cv_source.from_current_cv("type"))


class cvColorWidget(QComboBox):
    """Widget for choosing a distance type.

    params:

    cv_source (cvSource): Data for currently selected CV.

    """

    def __init__(self, cv_source: cvSource) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.addItem("None")
        self.addItem("black")
        self.addItem("white")
        self.addItem("gray")
        col = self.cv_source.from_current_cv("col")
        self.setCurrentText((lambda: "None" if not col else col)())
        self.currentTextChanged.connect(self.text_changed)
        self.last_val = self.currentText()

    def _text(self) -> str:
        return self.currentText()

    def fixup(self) -> None:
        new_text = self.currentText()
        if new_text != self.last_val:
            if self.cv_source.current_cv():
                if new_text != "None":
                    self.cv_source.set_in_current_cv("col", new_text, None)
                else:
                    self.cv_source.del_key("col")
            self.last_val = new_text

    def text_changed(self, s) -> None:
        self.fixup()

    def refresh(self, cv_source: cvSource) -> None:
        self.cv_source = cv_source
        if self.cv_source.has_key("col"):
            self.setCurrentText(self.cv_source.from_current_cv("col"))
        else:
            self.setCurrentText("None")


class cvAxisWidget(QComboBox):
    """Widget for choosing an axis for a CV.

    params:

    cv_source (cvSource): Data for currently selected CV.

    """

    def __init__(self, cv_source: cvSource) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.addItem("y")
        self.addItem("x")
        axis = self.cv_source.from_current_cv("axis")
        self.setCurrentText((lambda: "y" if not axis else axis)())
        self.currentTextChanged.connect(self.text_changed)
        self.last_val = self.currentText()

    def _text(self) -> str:
        return self.currentText()

    def fixup(self) -> None:
        t = self.currentText()
        if t != self.last_val:
            self.cv_source.set_in_current_cv("axis", self.currentText(), None)
            self.last_val = t

    def text_changed(self, s) -> None:
        self.fixup()

    def refresh(self, cv_source) -> None:
        self.cv_source = cv_source
        if self.cv_source.has_key("axis"):
            self.setCurrentText(self.cv_source.from_current_cv("axis"))
        else:
            self.setCurrentText("y")


class cvUCatWidget(QComboBox):
    """Widget for choosing a category for a CV.

    params:

    cv_source (cvSource): Data for currently selected CV.

    """

    def __init__(self, cv_source: cvSource) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.cats = unicode_cat_names.values()
        self.addItem("None")
        for c in self.cats:
            self.addItem(c)
        ct = "None"
        if self.cv_source.has_key("cat"):
            ct = unicode_cat_names[self.cv_source.from_current_cv("cat")]
        self.setCurrentText(ct)
        self.currentTextChanged.connect(self.text_changed)
        self.last_val = self.currentText()

    def _text(self) -> str:
        return self.currentText()

    def fixup(self) -> None:
        new_text = self.currentText()
        if new_text != self.last_val:
            if not new_text or new_text == "None":
                self.cv_source.del_key("cat")
            else:
                self.cv_source.set_in_current_cv(
                    "cat", reverse_unicode_cat_names[new_text], None
                )
            self.last_val = new_text

    def text_changed(self, s) -> None:
        self.fixup()

    def refresh(self, cv_source) -> None:
        self.cv_source = cv_source
        if self.cv_source.has_key("cat"):
            self.setCurrentText(
                unicode_cat_names[self.cv_source.from_current_cv("cat")]
            )
        else:
            self.setCurrentText("None")


class cvSuffixWidget(QLineEdit):
    """Widget for specifying a suffix (the CV is only available for glyphs with
    this suffix).

    params:

    cv_source (cvSource): Data for currently selected CV.

    """

    def __init__(self, cv_source: cvSource) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.dirty = False
        suff = self.cv_source.from_current_cv("suffix")
        self.setText((lambda: "None" if not suff else suff)())
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = self.text()

    def _text(self) -> str:
        return self.text().strip()

    def set_dirty(self) -> None:
        self.dirty = True

    def set_clean(self) -> None:
        self.dirty = False

    def fixup(self) -> None:
        if self.dirty:
            self.cv_source.set_in_current_cv("suffix", self._text(), None)
            self.set_clean()

    def text_changed(self) -> None:
        t = self._text()
        if t != self.last_val:
            self.fixup()
            self.last_val = t

    def refresh(self, cv_source: cvSource) -> None:
        self.cv_source = cv_source
        suff = self.cv_source.from_current_cv("suffix")
        self.setText((lambda: "None" if not suff else suff)())
        self.set_clean()


class cvVarWidget(QLineEdit):
    """Widget for editing variant CVs for the cvar table.

    params:

    var_id (str): ID of the master associated with this widget.

    cv_source (cvSource): Data for currently selected CV.

    """

    def __init__(self, var_id: str, cv_source: cvSource) -> None:
        super().__init__()
        self.var_id = var_id
        self.cv_source = cv_source
        self.dirty = False
        v = self.cv_source.from_current_cv("var")
        k = "None"
        if v and self.var_id in v:
            k = v[self.var_id]
        self.setText(str(k))
        self.setValidator(QIntValidator(-9999, 9999))
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = str(k)

    def _text(self) -> str:
        return self.text().strip()

    def set_dirty(self) -> None:
        self.dirty = True

    def set_clean(self) -> None:
        self.dirty = False

    def fixup(self) -> None:
        """The behavior we want is this: if the widget is blank,
        delete the value for this master and display "None"
        in the widget. If widget has a valid integer, plug
        that in.
        """
        if self.dirty:
            new_text = self._text()
            current_vars = self.cv_source.from_current_cv("var")
            if not current_vars:
                current_vars = {}
            if new_text:
                current_vars[self.var_id] = int(new_text)
                self.cv_source.set_in_current_cv("var", current_vars, None)
            else:
                if len(current_vars) == 0:
                    self.cv_source.del_key("var")
                    self.refresh(self.cv_source)
            self.set_clean()

    def text_changed(self) -> None:
        t = self._text()
        if t != self.last_val:
            self.fixup()
            self.last_val = t

    def refresh(self, cv_source: cvSource) -> None:
        self.cv_source = cv_source
        v = self.cv_source.from_current_cv("var")
        k = "None"
        if v and self.var_id in v:
            k = v[self.var_id]
        self.setText(str(k))
        self.set_clean()


class functionBaseWidget(QLineEdit):
    def __init__(self, defaults):
        super().__init__()
        self.defaults = defaults
        init_val = self.defaults.get_default("function-base")
        if init_val == None:
            init_val = 0
        self.setText(str(init_val))
        self.setValidator(QIntValidator(0, 255))
        self.editingFinished.connect(self.text_changed)
        self.last_val = self.text()

    def _text(self) -> str:
        return self.text().strip()

    def fixup(self) -> None:
        t = self._text()
        if t != self.last_val:
            try:
                i = int(t)
            except ValueError:
                i = 0
            self.defaults.set_default({"function-base": i})

    def text_changed(self) -> None:
        t = self._text()
        if t != self.last_val:
            self.fixup()
            self.last_val = t

    def refresh(self) -> None:
        fb = self.defaults.get_default("function-base")
        if fb == None:
            self.setText("0")
        else:
            self.setText(str(fb))


class cvValueWidget(QLineEdit):
    """Widget for editing the value of a CV.

    params:

    cv_source (cvSource): Data for currently selected CV.

    """

    def __init__(self, cv_source: cvSource) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.dirty = False
        self.setText(str(self.cv_source.from_current_cv("val")))
        self.setValidator(QIntValidator(-9999, 9999))
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = self.text()

    def _text(self) -> str:
        return self.text().strip()

    def set_dirty(self) -> None:
        self.dirty = True

    def set_clean(self) -> None:
        self.dirty = False

    def fixup(self) -> None:
        t = self._text()
        if t != self.last_val:
            try:
                i = int(t)
            except ValueError:
                i = 0
            self.cv_source.set_in_current_cv("val", i, fallback = 0)
            self.set_clean()

    def text_changed(self) -> None:
        t = self._text()
        if t != self.last_val:
            self.fixup()
            self.last_val = t

    def refresh(self, cv_source: cvSource) -> None:
        self.cv_source = cv_source
        i = self.cv_source.from_current_cv("val")
        self.setText((lambda: "0" if not i else str(i))())
        self.set_clean()


class cvPPEMWidget(QLineEdit):
    """Widget for editing a "ppem" value in the "same as" pane.

    params:

    cv_source (cvSource): Data for currently selected CV.

    above_below (str): Indicating which widget pair is being edited.

    """

    def __init__(self, cv_source: cvSource, above_below: str) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.above_below = above_below
        self.name_widget: Optional[cvNameWidget] = None
        self.dirty = False
        s = self.cv_source.from_current_cv("same-as")
        v = "40"
        if s:
            try:
                self.setText(s[self.above_below])
            except Exception:
                self.setText("40")
        self.setValidator(QIntValidator(0, 500))
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = "40"

    def _text(self) -> str:
        return self.text().strip()

    def set_dirty(self) -> None:
        self.dirty = True

    def set_clean(self) -> None:
        self.dirty = False

    def fixup(self) -> None:
        new_name = self.name_widget._text()
        name_valid = new_name != "None"
        try:
            new_val = int(self._text())
        except Exception:
            new_val = 40
            self.setText(str(new_val))
        if name_valid:
            s = self.cv_source.from_current_cv("same-as")
            if not s:
                s = {self.above_below: {}}
            s[self.above_below]["cv"] = new_name
            s[self.above_below]["ppem"] = new_val
            self.cv_source.set_in_current_cv("same-as", s, None)
        else:
            if self.cv_source.has_key("same-as"):
                s = self.cv_source.from_current_cv("same-as")
                if self.above_below in s:
                    del s[self.above_below]
                if len(s) == 0:
                    self.cv_source.del_key("same-as")
        self.set_clean()

    def text_changed(self) -> None:
        t = self._text()
        if t != self.last_val:
            self.fixup()
            self.last_val = t

    def refresh(self, cv_source: cvSource) -> None:
        self.cv_source = cv_source
        p = "40"
        s = self.cv_source.from_current_cv("same-as")
        if s and self.above_below in s:
            p = str(s[self.above_below]["ppem"])
        self.setText(p)
        self.set_clean()


class cvNamesWidget(QComboBox):
    """Widget for choosing a CV name in the "same as" pane.

    params:

    cv_source (cvSource): Data for currently selected CV.

    above_below (str): Indicating which widget pair is being edited.

    yg_font (ygFont): The font being edited.

    ppem_widget: The associated cvPPEMWidget (if any).

    """

    def __init__(
            self,
            cv_source: cvSource,
            above_below: str,
            yg_font: ygFont,
            ppem_widget: cvPPEMWidget = None
        ) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.yg_font = yg_font
        self.cvt = yg_font.cvt
        self.above_below = above_below
        self.ppem_widget = ppem_widget
        cv_list = self.cvt.get_list(None)
        self.addItem("None")
        for c in cv_list:
            self.addItem(c)
        n = "None"
        cv = self.cv_source.from_current_cv("same-as")
        if cv and self.above_below in cv:
            n = cv[self.above_below]["cv"]
        self.setCurrentText(n)
        self.currentTextChanged.connect(self.text_changed)

    def _text(self) -> str:
        return self.currentText()

    def fixup(self) -> None:
        if self.ppem_widget:
            self.ppem_widget.fixup()

    def text_changed(self, s) -> None:
        self.fixup()

    def refresh(self, cv_source: cvSource) -> None:
        self.cv_source = cv_source
        n = "None"
        if self.cv_source.has_key("same-as"):
            s = self.cv_source.from_current_cv("same-as")
            if self.above_below in s:
                n = s[self.above_below]["cv"]
        self.setCurrentText(n)


class masterNameWidget(QLineEdit):
    """Widget for editing the name of a master. This name is for
    display only: the master is referenced by an immutable id.

    params:

    masters (ygMasters): The collection of masters for this font.

    m_id (str): The ID of the master associated with this widget.

    """

    def __init__(self, masters: ygMasters, m_id: str) -> None:
        super().__init__()
        self.masters = masters
        self.m_id = m_id
        master_name = self.masters.get_master_name(self.m_id)
        self.setText(master_name)
        self.dirty = False
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = master_name

    def _text(self) -> str:
        return self.text().strip()

    def set_dirty(self) -> None:
        self.dirty = True

    def set_clean(self) -> None:
        self.dirty = False

    def refresh(self, m: tuple) -> None:
        """refresh is for updating editing widgets from the model."""
        self.m_id = m[0]
        self.setText(self.masters.get_master_name(self.m_id))
        self.set_clean()

    def fixup(self) -> None:
        """fixup is for changing the model based on what's in the editing
        widgets.
        """
        self.masters.set_master_name(self.m_id, self._text())
        self.set_clean()

    def text_changed(self) -> None:
        t = self._text()
        if self.dirty and t != self.last_val:
            self.fixup()
            self.last_val = t


class masterValWidget(QLineEdit):
    """Widget for editing the value of a master (-1.0 to 1.0)

    params:

    masters (ygMasters): The collection of masters for this font.

    m_id (str): The ID of the master associated with this widget.

    axis: The variation axis associated with this widget.

    """

    def __init__(self, masters: ygMasters, m_id: str, axis: str) -> None:
        super().__init__()
        self.masters = masters
        self.m_id = m_id
        self.axis = axis
        self.init_val = self.masters.get_axis_value(self.m_id, self.axis)
        if self.init_val == None:
            self.init_val = 0.0
        self.setText(str(self.init_val))
        self.setValidator(QDoubleValidator(-1.0, 1.0, 4))
        self.dirty = False
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = str(self.init_val)

    def _text(self) -> str:
        return self.text().strip()

    def set_dirty(self) -> None:
        self.dirty = True

    def set_clean(self) -> None:
        self.dirty = False

    def refresh(self, m: tuple) -> None:
        """refresh is for updating editing widgets from the model."""
        if m:
            self.m_id = m[0]
        self.setText(str(self.masters.get_axis_value(self.m_id, self.axis)))
        self.set_clean()

    def fixup(self) -> None:
        """fixup is for changing the model based on what's in the editing
        widgets.
        """
        try:
            v = self._text()
            if v == "" or v == "0.0":
                self.masters.del_axis(self.m_id, self.axis)
            else:
                try:
                    self.masters.set_axis_value(self.m_id, self.axis, float(v))
                except Exception:
                    self.masters.set_axis_value(self.m_id, self.axis, 0.0)
                self.refresh(None)
            self.set_clean()
        except Exception as e:
            print(e)
            pass

    def text_changed(self) -> None:
        t = self._text()
        if self.dirty and t != self.last_val:
            self.fixup()
            self.last_val = t
