"""
Dwarf - Copyright (C) 2019 Giovanni Rocca (iGio90)

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
import socket
import subprocess
import sys

import pyperclip

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QSizePolicy, QApplication

from lib.prefs import Prefs

VERSION = sys.version_info

def do_shell_command(cmd, timeout=60):
    """ Execute cmd
    """
    try:
        # capture output is only supported in py 3.7
        if VERSION.minor >= 7:
            result = subprocess.run(cmd.split(' '), timeout=timeout, capture_output=True)
        else:
            result = subprocess.run(
                cmd.split(' '),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout
            )

        if result.stderr:
            return result.stderr.decode('utf8')

        return result.stdout.decode('utf8')

    except subprocess.TimeoutExpired:
        return None  # todo: timeout doesnt mean cmd failed


def get_app_icon():
    """ Returns Icon (QPixmap)
    """
    return QPixmap(resource_path('assets/dwarf.png')).scaledToHeight(75, Qt.SmoothTransformation)


def parse_ptr(ptr):
    """ ptr parsing
    """
    if isinstance(ptr, str):
        if ptr.startswith('#'):
            ptr = ptr[1:]
        if ptr.startswith('0x'):
            ptr = int(ptr, 16)
        else:
            try:
                ptr = int(ptr)
            except ValueError:
                ptr = 0
    if not isinstance(ptr, int):
        ptr = 0
    return ptr


def resource_path(relative_path):
    """get path to resource
    """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    # its /lib/ now so move one up os.pardir
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(base_path, relative_path)
    else:
        return os.path.join(base_path, os.pardir, relative_path)


def show_message_box(text, details=None):
    """ Shows a MessageBox
    """
    msg = QMessageBox()
    msg.setIconPixmap(get_app_icon())

    msg.setText(text)
    if details and isinstance(details, str):
        msg.setDetailedText(details)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()


def get_os_monospace_font():
    """ Get MonospaceFont for OS
    """
    platform = sys.platform

    if 'linux' in platform:
        return QFont('Monospace', 10)
    elif 'darwin' in platform:
        return QFont('Monaco', 11)
    elif 'freebsd' in platform:
        return QFont('Bitstream Vera Sans Mono', 10)
    else:
        # windows
        return QFont('Courier', 10)  # Consolas ??

    # return QFontDatabase.systemFont(QFontDatabase.FixedFont) ??


def copy_str_to_clipboard(text):
    """ Helper for copying text
    """
    if isinstance(text, str):
        pyperclip.copy(text)


def copy_hex_to_clipboard(hex_str):
    """ Helper for copying hexstr in prefered style
    """
    _prefs = Prefs()
    uppercase = (_prefs.get('dwarf_ui_hexstyle', 'upper').lower() == 'upper')
    if isinstance(hex_str, str):
        if hex_str.startswith('0x'):
            if uppercase:
                hex_str = hex_str.upper().replace('0X', '0x')
            else:
                hex_str = hex_str.lower()

            pyperclip.copy(hex_str)
    elif isinstance(hex_str, int):
        str_fmt = '0x{0:x}'
        if uppercase:
            str_fmt = '0x{0:X}'

        pyperclip.copy(str_fmt.format(hex_str))


def safe_read_map(map, key, default):
    if key not in map:
        return default
    return map[key]


def progress_dialog(message):
    progress_dialog = QProgressDialog()
    progress_dialog.setFixedSize(300, 50)
    progress_dialog.setAutoFillBackground(True)
    progress_dialog.setWindowModality(Qt.WindowModal)
    progress_dialog.setWindowTitle('Please wait')
    progress_dialog.setLabelText(message)
    progress_dialog.setSizeGripEnabled(False)
    progress_dialog.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    progress_dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
    progress_dialog.setWindowFlag(Qt.WindowCloseButtonHint, False)
    progress_dialog.setModal(True)
    progress_dialog.setCancelButton(None)
    progress_dialog.setRange(0, 0)
    progress_dialog.setMinimumDuration(0)
    progress_dialog.setAutoClose(False)
    return progress_dialog


def is_connected():
    try:
        socket.setdefaulttimeout(2)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except:
        return False


# https://github.com/ActiveState/code/tree/master/recipes/Python/391367_deprecated
def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used."""
    def newFunc(*args, **kwargs):
        import warnings
        warnings.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning)
        return func(*args, **kwargs)
    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc


def set_theme(theme, prefs=None):
    if theme:
        theme = theme.replace(os.pardir, '').replace('.', '')
        theme = theme.join(theme.split()).lower()
        theme_style = 'assets/' + theme + '_style.qss'
        if not os.path.exists(resource_path(theme_style)):
            return

        if prefs is not None:
            prefs.put('dwarf_ui_theme', theme)

        try:
            _app = QApplication.instance()
            with open(theme_style) as stylesheet:
                _app.setStyleSheet(_app.styleSheet() + '\n' +
                                   stylesheet.read())
        except Exception as e:
            pass
            # err = self.dwarf.spawn(dwarf_args.package, dwarf_args.script)
