"""
    Dwarf - Copyright (C) 2018-2022 Giovanni Rocca (iGio90)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>
"""
import os
import random
import sys

import requests
from PyQt5.QtCore import Qt, QSize, QRect, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPixmap, QIcon, QFontMetrics
from PyQt5.QtWidgets import (QWidget, QDialog, QLabel, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSizePolicy, QStyle, qApp)

from dwarf_debugger.lib import utils
from dwarf_debugger.lib.git import Git


class WelcomeDialog(QDialog):
    onSessionSelected = pyqtSignal(str, name='onSessionSelected')
    onUpdateComplete = pyqtSignal(name='onUpdateComplete')
    onIsNewerVersion = pyqtSignal(name='onIsNewerVersion')

    def __init__(self, parent=None):
        super(WelcomeDialog, self).__init__(parent=parent)

        self._prefs = parent.prefs
        self._sub_titles = [
            ['duck', 'dumb', 'doctor', 'dutch', 'dark', 'dirty', 'debugging'],
            ['warriors', 'wardrobes', 'waffles', 'wishes', 'worcestershire'],
            ['are', 'aren\'t', 'ain\'t', 'appears to be'],
            ['rich', 'real', 'riffle', 'retarded', 'rock'],
            [
                'as fuck', 'fancy', 'fucked', 'front-ended', 'falafel',
                'french fries'
            ],
        ]
        # setup size and remove/disable titlebuttons
        self.desktop_geom = qApp.desktop().availableGeometry()
        self.setFixedSize(int(self.desktop_geom.width() * .45),
                          int(self.desktop_geom.height() * .4))
        self.setGeometry(
            QStyle.alignedRect(Qt.LeftToRight, Qt.AlignCenter, self.size(),
                               qApp.desktop().availableGeometry()))
        self.setSizeGripEnabled(False)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setModal(True)

        # setup ui elements
        self.setup_ui()

        random.seed(a=None, version=2)

        self._base_path = getattr(
            sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

        # center
        self.setGeometry(
            QStyle.alignedRect(Qt.LeftToRight, Qt.AlignCenter, self.size(),
                               qApp.desktop().availableGeometry()))

    def setup_ui(self):
        """ Setup Ui
        """
        main_wrap = QVBoxLayout()
        main_wrap.setContentsMargins(0, 0, 0, 0)

        # main content
        head = QHBoxLayout()
        head.setContentsMargins(50, 10, 0, 10)
        # dwarf icon
        icon = QLabel()
        icon.setPixmap(QPixmap(utils.resource_path('assets/dwarf.svg')))
        icon.setAlignment(Qt.AlignCenter)
        icon.setMinimumSize(QSize(125, 125))
        icon.setMaximumSize(QSize(125, 125))
        head.addWidget(icon)

        # main title
        title_layout = QVBoxLayout()
        title = QLabel('Dwarf')
        title.setContentsMargins(0, 30, 0, 0)
        font = QFont('Anton', 100, QFont.Bold)
        font.setPixelSize(70)
        title.setFont(font)
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        title.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title)
        sub_title_text = (
                self._pick_random_word(0) + ' ' + self._pick_random_word(1) + ' ' +
                self._pick_random_word(2) + ' ' + self._pick_random_word(3) + ' ' +
                self._pick_random_word(4))
        sub_title_text = sub_title_text[:1].upper() + sub_title_text[1:]
        self._sub_title = QLabel(sub_title_text)
        font = QFont('OpenSans', 16, QFont.Bold)
        font.setPixelSize(24)
        self._sub_title.setFont(font)
        font_metric = QFontMetrics(self._sub_title.font())
        self._char_width = font_metric.widthChar('#')
        self._sub_title.setAlignment(Qt.AlignCenter)
        self._sub_title.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Minimum)
        title_layout.addWidget(self._sub_title)

        head.addLayout(title_layout)

        main_wrap.addLayout(head)

        v_type = QHBoxLayout()
        v_type.setContentsMargins(50, 50, 50, 50)
        btn = QPushButton()
        ico = QIcon(QPixmap(utils.resource_path('assets/android.svg')))
        btn.setIconSize(QSize(75, 75))
        btn.setIcon(ico)
        btn.setToolTip('New Android Session')
        btn.clicked.connect(self._on_android_button)
        v_type.addWidget(btn)

        btn = QPushButton()
        ico = QIcon(QPixmap(utils.resource_path('assets/apple.svg')))
        btn.setIconSize(QSize(75, 75))
        btn.setIcon(ico)
        btn.setToolTip('New iOS Session')
        btn.clicked.connect(self._on_ios_button)
        v_type.addWidget(btn)

        btn = QPushButton()
        ico = QIcon(QPixmap(utils.resource_path('assets/local.svg')))
        btn.setIconSize(QSize(75, 75))
        btn.setIcon(ico)
        btn.setToolTip('New Local Session')
        btn.clicked.connect(self._on_local_button)
        v_type.addWidget(btn)

        btn = QPushButton()
        ico = QIcon(QPixmap(utils.resource_path('assets/remote.svg')))
        btn.setIconSize(QSize(75, 75))
        btn.setIcon(ico)
        btn.setToolTip('New Remote Session')
        btn.clicked.connect(self._on_remote_button)
        v_type.addWidget(btn)
        main_wrap.addLayout(v_type)

        self.setLayout(main_wrap)

    def _update_finished(self):
        self.onUpdateComplete.emit()

    def _on_android_button(self):
        self.onSessionSelected.emit('Android')
        self.close()

    def _on_local_button(self):
        self.onSessionSelected.emit('Local')
        self.close()

    def _on_ios_button(self):
        self.onSessionSelected.emit('Ios')
        self.close()

    def _on_remote_button(self):
        self.onSessionSelected.emit('Remote')
        self.close()

    def _pick_random_word(self, arr):
        return self._sub_titles[arr][random.randint(
            0,
            len(self._sub_titles[arr]) - 1)]

    def showEvent(self, QShowEvent):
        """ override to change font size when subtitle is cutted
        """
        if len(self._sub_title.text()) * self._char_width > (
                self._sub_title.width() - 155):
            font = QFont('OpenSans', 14, QFont.Bold)
            font.setPixelSize(20)
            self._sub_title.setFont(font)
        return super().showEvent(QShowEvent)
