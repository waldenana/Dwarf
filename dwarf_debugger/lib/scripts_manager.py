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
import os.path

from PyQt5.QtCore import QObject, pyqtSignal
from dwarf_debugger.lib.git import Git


class ScriptsManager(QObject):
    """ ScriptManager

        signals:
            scriptsUpdated()
    """

    scriptsUpdated = pyqtSignal(name='scriptsUpdated')

    def __init__(self):
        super(ScriptsManager, self).__init__()
        self._git = Git()
        self.scripts = {}
        self.update_scripts()

    def update_scripts(self):
        scripts = self._git.get_dwarf_scripts()

        if scripts is None:
            return

        for module in scripts:
            module_name = module['name']
            module_dir = module['path']
            info_url = os.path.join(module_dir, 'dwarf.json')
            script_url = os.path.join(module_dir, 'index.js')
            info = self._git.get_script_info(info_url)
            if info is None:
                continue
            self.scripts[module_name] = {
                'info': info,
                'script': script_url
            }

        self.scriptsUpdated.emit()

    def get_script(self, script_name):
        return self.scripts[script_name]

    def get_scripts(self):
        return self.scripts
