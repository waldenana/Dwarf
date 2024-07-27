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
import logging

import frida
from PyQt5.Qt import (Qt, pyqtSignal, QThread, QTimer)
from PyQt5.QtWidgets import (QWidget, QLabel, QHBoxLayout, QPushButton, qApp, QComboBox)

from dwarf_debugger.lib import utils
from dwarf_debugger.lib.adb import Adb
from dwarf_debugger.lib.git import Git

logger = logging.getLogger(__name__)


class FridaUpdateThread(QThread):
    """ FridaServer Update Thread
        signals:
            onStatusUpdate(str)
            onFinished()
            onError(str)
    """
    # ************************************************************************
    # **************************** Signals ***********************************
    # ************************************************************************
    onStatusUpdate = pyqtSignal(str, name='onStatusUpdate')
    onFinished = pyqtSignal(name='onFinished')
    onError = pyqtSignal(str, name='onError')

    # ************************************************************************
    # **************************** Properties ********************************
    # ************************************************************************
    @property
    def adb(self):
        return self._adb

    @adb.setter
    def adb(self, value):
        if isinstance(value, Adb):
            self._adb = value

    @property
    def frida_path(self):
        return self._frida_path

    @frida_path.setter
    def frida_path(self, value):
        if isinstance(value, str):
            self._frida_path = value

    # ************************************************************************
    # **************************** Functions *********************************
    # ************************************************************************
    def __init__(self, parent=None):
        super().__init__(parent)
        self._frida_path = None
        self._adb = None

    def run(self):
        """Runs the UpdateThread
        """
        if self._adb is None:
            self.onError.emit('ADB not set')
            return

        if not self._adb.min_required:
            self.onError.emit('ADB MinRequired')
            return

        if not utils.is_connected():
            self.onError.emit('Not connected')
            return

        self.onStatusUpdate.emit('Downloading frida ' + self.frida_path)
        # mount system rw
        self.onStatusUpdate.emit('Pushing to device')
        logger.debug("install frida " + self.frida_path)
        # push file to device
        self.onStatusUpdate.emit('Setting up and starting frida')
        # kill frida
        self._adb.kill_frida()

        _device_path = '/data/local/tmp'
        self._adb.push(self._frida_path, _device_path + '/frida-server')
        # just to make sure
        self._adb.su_cmd('chown root:root ' + _device_path + '/frida-server')
        # make it executable
        self._adb.su_cmd('chmod 06755 ' + _device_path + '/frida-server')

        # start it
        if self._adb.get_frida_version():
            if not self._adb.start_frida():
                self.onError.emit('Failed to start fridaserver on Device')
        self.onFinished.emit()


class DevicesUpdateThread(QThread):
    """ Updates DeviceSelector
        signals:
            add_device(devicename, customdata, currentitem)
            devices_updated()
    """
    onAddDevice = pyqtSignal(dict, name="onAddDevice")
    onDevicesUpdated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        # get frida devices
        devices = frida.get_device_manager().enumerate_devices()
        for device in devices:
            logger.debug("get device %s", device.name)
            self.onAddDevice.emit({'id': device.id, 'name': device.name, 'type': device.type})

        self.onDevicesUpdated.emit()


class DeviceBar(QWidget):
    """ DeviceBar

        Signals:
            onDeviceUpdated()
            onDeviceSelected(str) # str = id
            onDeviceChanged(str) # str = id

    """

    onDeviceUpdated = pyqtSignal(str, name="onDeviceUpdated")
    onDeviceSelected = pyqtSignal(str, name="onDeviceSelected")
    onDeviceChanged = pyqtSignal(str, name="onDeviceChanged")

    def __init__(self, parent=None, device_type='usb'):
        super().__init__(parent=parent)

        # dont show for local
        self._devices_combobox = None
        self.update_label = None
        self._install_btn = None
        self._start_btn = None
        self._restart_btn = None
        self._doing_btn = None
        if device_type != 'usb':
            return

        self.parent = parent
        self.wait_for_devtype = device_type
        self.is_waiting = True
        self._adb = Adb()

        if not self._adb.min_required:
            raise Exception('Adb missing or no Device')

        self._git = Git()
        self.setAutoFillBackground(True)
        self.setStyleSheet('background-color: crimson; color: white; font-weight: bold; margin: 0; padding: 10px;')
        self.setup()
        self._timer = QTimer()
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._on_timer)
        self._timer.start()
        self._timer_step = 0
        frida.get_device_manager().on('added', self._on_device)
        frida.get_device_manager().on('removed', self._on_device)
        self.devices_thread = DevicesUpdateThread(self)
        self.devices_thread.onAddDevice.connect(self.on_add_deviceitem)
        self.devices_thread.onDevicesUpdated.connect(self._on_devices_finished)
        self._update_thread = FridaUpdateThread(self)
        self._update_thread._adb = self._adb
        self._update_thread.onStatusUpdate.connect(self._update_statuslbl)
        self._update_thread.onFinished.connect(self._frida_updated)
        self._update_thread.onError.connect(self._on_download_error)
        self.updated_frida_version = '15.1.9'
        self.updated_frida_assets_url = {}
        self._device_id = None
        self._devices = []
        remote_frida = self._git.get_frida_version()
        if remote_frida is None:
            self.updated_frida_version = ''
            self.updated_frida_assets_url.clear()
        else:
            self.updated_frida_version = remote_frida['tag_name']
            for asset in remote_frida['assets']:
                if 'name' not in asset:
                    continue

                asset_name = asset['name']

                if not asset_name.startswith('frida-server-'):
                    continue

                if 'android' not in asset_name:
                    continue

                tag_start = asset_name.index('android-')
                if asset_name.index('server') >= 0:
                    tag = asset_name[tag_start + 8:]
                    self.updated_frida_assets_url[tag] = asset['path']
                    logger.debug("get frida server tag:%s ,name:%s path:%s", tag, asset_name,
                                 asset['path'])

    def setup(self):
        """ Setup ui
        """
        h_box = QHBoxLayout()
        h_box.setContentsMargins(0, 0, 0, 0)
        self.update_label = QLabel('Waiting for Device')
        self.update_label.setFixedWidth(self.parent.width())
        self.update_label.setOpenExternalLinks(True)
        self.update_label.setTextFormat(Qt.RichText)
        self.update_label.setFixedHeight(35)
        self.update_label.setTextInteractionFlags(Qt.TextBrowserInteraction)

        self._install_btn = QPushButton('Install Frida', self.update_label)
        self._install_btn.setStyleSheet('padding: 0; border-color: white;')
        self._install_btn.setGeometry(self.update_label.width() - 110, 5, 100, 25)
        self._install_btn.clicked.connect(self._on_install_btn)
        self._install_btn.setVisible(False)
        self._start_btn = QPushButton('Start Frida', self.update_label)
        self._start_btn.setStyleSheet('padding: 0; border-color: white;')
        self._start_btn.setGeometry(self.update_label.width() - 110, 5, 100, 25)
        self._start_btn.clicked.connect(self._on_start_btn)
        self._start_btn.setVisible(False)

        self._update_btn = QPushButton('Update Frida', self.update_label)
        self._update_btn.setStyleSheet('padding: 0; border-color: white;')
        self._update_btn.setGeometry(self.update_label.width() - 110, 5, 100, 25)
        self._update_btn.clicked.connect(self._on_install_btn)
        self._update_btn.setVisible(False)

        self._restart_btn = QPushButton('Restart Frida', self.update_label)
        self._restart_btn.setStyleSheet('padding: 0; border-color: white;')
        self._restart_btn.setGeometry(self.update_label.width() - 110, 5, 100, 25)
        self._restart_btn.clicked.connect(self._on_restart_btn)
        self._restart_btn.setVisible(False)

        self._doing_btn = QLabel('Waiting...', self.update_label)
        self._doing_btn.setStyleSheet('padding: 0; border-color: white;')
        self._doing_btn.setGeometry(self.update_label.width() - 110, 5, 100, 25)
        self._doing_btn.setVisible(False)

        self._devices_combobox = QComboBox(self.update_label)
        self._devices_combobox.setStyleSheet('padding: 2px 5px; border-color: white;')
        self._devices_combobox.setGeometry(self.update_label.width() - 320, 5, 200, 25)
        self._devices_combobox.currentIndexChanged.connect(self._on_device_changed)
        self._devices_combobox.setVisible(False)
        h_box.addWidget(self.update_label)
        self.setLayout(h_box)

    def on_add_deviceitem(self, device_ident):
        """ Adds an Item to the DeviceComboBox
        """
        logger.debug("on_add_deviceitem")
        if device_ident['type'] == self.wait_for_devtype:
            if device_ident['name'] not in self._devices:
                self._devices.append(device_ident)
            self._timer_step = -1
            self.is_waiting = False

    def _on_device_changed(self, index):
        device = None
        device_id = self._devices_combobox.itemData(index)
        if device_id:
            try:
                device = frida.get_device(device_id)
            except:
                return

            if device:
                self._device_id = device.id
                self._check_device(device)
                self.onDeviceChanged.emit(self._device_id)

    def _check_device(self, frida_device):
        self.update_label.setStyleSheet('background-color: crimson;')
        self._install_btn.setVisible(False)
        self._update_btn.setVisible(False)
        self._start_btn.setVisible(False)
        self._restart_btn.setVisible(False)
        self._adb.device = frida_device.id
        self._device_id = frida_device.id
        if self._adb.available():
            self.update_label.setText('Device: ' + frida_device.name)
            # try getting frida version
            device_frida = self._adb.get_frida_version()
            # frida not found show install button
            if device_frida is None:
                self._install_btn.setVisible(True)
            else:
                # frida is old show update button
                if self.updated_frida_version != device_frida:
                    self._start_btn.setVisible(True)
                    self._update_btn.setVisible(False)
                    # old frida is running allow use of this version
                    if self._adb.is_frida_running():
                        self._start_btn.setVisible(False)
                        if self.updated_frida_assets_url:
                            self._update_btn.setVisible(True)
                        self.update_label.setStyleSheet('background-color: yellowgreen;')
                        self.onDeviceUpdated.emit(frida_device.id)
                # frida not running show start button
                elif device_frida and not self._adb.is_frida_running():
                    self._start_btn.setVisible(True)
                # frida is running with last version show restart button
                elif device_frida and self._adb.is_frida_running():
                    self.update_label.setStyleSheet('background-color: yellowgreen;')
                    self._restart_btn.setVisible(True)
                    self.onDeviceUpdated.emit(frida_device.id)

        elif self._adb.non_root_available():
            self.update_label.setText('Device: ' + frida_device.name + ' (NOROOT!)')
            self.onDeviceUpdated.emit(frida_device.id)

    def _on_devices_finished(self):
        logger.debug(f"_on_devices_finished {self._devices}")
        if self._devices:
            if len(self._devices) > 1:
                self._devices_combobox.clear()
                self._devices_combobox.setVisible(True)
                self.update_label.setText('Please select the Device: ')
                for device in self._devices:
                    self._devices_combobox.addItem(device['name'], device['id'])
            else:
                self._devices_combobox.setVisible(False)
                try:
                    device = frida.get_device(self._devices[0]['id'])
                    self._check_device(device)
                except:
                    pass

    def _on_timer(self):
        if self._timer_step == -1:
            self._timer.stop()
            return

        if self._timer_step == 0:
            self.update_label.setText(self.update_label.text() + ' .')
            self._timer_step = 1
        elif self._timer_step == 1:
            self.update_label.setText(self.update_label.text() + '.')
            self._timer_step = 2
        elif self._timer_step == 2:
            self.update_label.setText(self.update_label.text() + '.')
            self._timer_step = 3
        else:
            self.update_label.setText(self.update_label.text()[:-self._timer_step])
            self._timer_step = 0
            if self.is_waiting and self.devices_thread is not None:
                if not self.devices_thread.isRunning():
                    self.devices_thread.start()

    def _on_download_error(self, text):
        self._timer_step = -1
        self.update_label.setStyleSheet('background-color: crimson;')
        self.update_label.setText(text)
        self._install_btn.setVisible(True)
        self._update_btn.setVisible(False)

    def _on_device(self):
        self.update_label.setText('Waiting for Device ...')
        self._timer_step = 3
        self.is_waiting = True
        self._on_timer()

    def _on_install_btn(self):
        # urls are empty
        if not self.updated_frida_assets_url:
            return

        arch = self._adb.get_device_arch()
        request_url = ''

        if arch is not None and len(arch) > 1:
            arch = arch.join(arch.split())

            if arch == 'arm64' or arch == 'arm64-v8a':
                request_url = self.updated_frida_assets_url['arm64']
            elif arch == 'armeabi-v7a':
                request_url = self.updated_frida_assets_url['arm']
            else:
                if arch in self.updated_frida_assets_url:
                    request_url = self.updated_frida_assets_url[arch]

            try:
                if self._adb.available():
                    self._install_btn.setVisible(False)
                    self._update_btn.setVisible(False)
                    qApp.processEvents()
                    if self._update_thread is not None:
                        if not self._update_thread.isRunning():
                            self._update_thread.frida_path = request_url
                            self._update_thread.adb = self._adb
                            self._update_thread.start()

            except ValueError:
                # something wrong in .git_cache folder
                print("request_url not set")
                utils.show_message_box("Install failed")

    def _update_statuslbl(self, text):
        self._timer.stop()
        self._timer_step = 0
        self._timer.start()
        self.update_label.setText(text)

    def _frida_updated(self):
        # self._timer_step = 3
        # self.is_waiting = True
        self._on_devices_finished()

    def _on_start_btn(self):
        if self._adb.available():
            self._start_btn.setVisible(False)
            self._doing_btn.setVisible(True)
            qApp.processEvents()
            if self._adb.start_frida():
                # self.onDeviceUpdated.emit(self._device_id)
                self._on_devices_finished()
            else:
                self._doing_btn.setVisible(False)
                self._start_btn.setVisible(True)

    def _on_restart_btn(self):
        if self._adb.available():
            self._restart_btn.setVisible(False)
            self._doing_btn.setVisible(True)
            qApp.processEvents()
            if self._adb.start_frida(restart=True):
                self._doing_btn.setVisible(False)
                self._restart_btn.setVisible(True)
                # self.onDeviceUpdated.emit(self._device_id)
                self._on_devices_finished()
