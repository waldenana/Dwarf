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
import hashlib
import json
import os
import time

import requests

from dwarf_debugger.lib import utils
from pathlib import Path


class Git(object):
    CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exec")
    DWARF_CACHE = CACHE_PATH + '/dwarf'
    DWARF_COMMITS_CACHE = CACHE_PATH + '/dwarf_commits'
    DWARF_SCRIPTS_CACHE = CACHE_PATH + '/dwarf_scripts'
    FRIDA_CACHE = CACHE_PATH + '/frida'

    def __init__(self):
        if not os.path.exists(Git.CACHE_PATH):
            os.mkdir(Git.CACHE_PATH)

    def _open_cache(self, path, url, _json=True):
        data = None
        now = time.time()
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                last_update = data['updated']
                data = data['data']
                if now - last_update < 60 * 15:
                    return data
        if utils.is_connected():
            try:
                r = requests.get(url)
            except:
                return data
            if r is None or r.status_code != 200:
                return data
            if _json:
                try:
                    data = r.json()
                except:
                    return None
            else:
                data = r.text
            with open(path, 'w') as f:
                f.write(json.dumps({
                    'updated': now,
                    'data': data
                }))
        return data

    def get_dwarf_releases(self):
        return self._open_cache(
            Git.DWARF_CACHE, 'https://api.github.com/repos/iGio90/dwarf/releases')

    def get_dwarf_commits(self):
        return self._open_cache(
            Git.DWARF_COMMITS_CACHE, 'https://api.github.com/repos/iGio90/dwarf/commits')

    def get_dwarf_scripts(self):
        return self._open_cache(
            Git.DWARF_SCRIPTS_CACHE,
            'https://raw.githubusercontent.com/iGio90/DwarfScripts/master/.gitmodules',
            _json=False)

    def get_frida_version(self):
        files = os.listdir(Git.FRIDA_CACHE)
        all_version = []
        last_version = "15.1.9"
        for file in files:
            all_version.append({"name": file, "browser_download_url": os.path.join(Git.FRIDA_CACHE, file)})

        return {
            "tag_name": last_version,
            "assets": all_version
        }

    def get_script(self, url):
        return self._open_cache(
            Git.CACHE_PATH + '/' + hashlib.md5(url.encode('utf8')).hexdigest(), url, _json=False)

    def get_script_info(self, url):
        return self._open_cache(
            Git.CACHE_PATH + '/' + hashlib.md5(url.encode('utf8')).hexdigest(), url)

    def _list_frida(self):
        files = os.listdir(Git.FRIDA_CACHE)
        all_version = [{"name": file, "browser_download_url": os.path.join(Git.FRIDA_CACHE, file)} for file in files]

        return all_version
