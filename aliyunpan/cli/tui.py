import curses
import platform
from pathlib import PurePosixPath, Path
import npyscreen
import functools
import pyperclip
from threading import Thread
from aliyunpan.api.utils import logger

__all__ = ['AliyunpanTUI']


class Text:
    def __init__(self, text):
        self._text = str(text)

    def __str__(self):
        text = self._text
        if platform.system() == 'Windows':
            text = ''
            for _char in self._text:
                text += _char
                if len(_char.encode()) > 1:
                    text += ' '
        return text


class AliyunpanFileForm(npyscreen.FormBaseNewWithMenus):
    def create(self):
        self.file_menu = self.add_menu(name='Menu')
        file = self.add(FileGrid)
        self.download_menu = self.file_menu.addNewSubmenu(name='Download Menu', shortcut='^D')
        self.download_menu.addItemsFromList([
            ('Copy the download link', file.copy_download_link, '^C'),
            ('Download file', file.download, '^D')
        ])
        self.file_menu.addItemsFromList([
            ('Cast screen to TV', file.dlna, '^A')
        ])


class DeviceSelect(npyscreen.TitleSelectOne):
    def set_up_handlers(self):
        super(DeviceSelect, self).set_up_handlers()
        self.handlers.update({
            '^C': self._exit
        })

    def _exit(self, _):
        raise KeyboardInterrupt


class Dlna(npyscreen.FormWithMenus):
    def create(self):
        self.device_menu = self.add_menu(name='Device Menu')
        self.device_menu.addItemsFromList([
            ('Play', self.play, '^A'),
            ('Stop', self.stop, '^S'),
            ('Refresh Device', self.refresh_device, '^R')
        ])
        self.devices = []
        self.device_select = self.add(DeviceSelect, scroll_exit=False, name='Devices',
                                      value_changed_callback=self.value_changed_callback)

    def beforeEditing(self):
        self.file_info = self.parentApp.file_info
        self.name = str(Text(self.file_info.name))
        try:
            from dlnap.dlnap import dlnap
        except ImportError as e:
            self.name = e.__str__()
            logger.error('Cannot find submodule dlnap.')
        else:
            self.dlnap = dlnap
            self.refresh_device()

    def afterEditing(self):
        self.parentApp.setNextFormPrevious()

    def value_changed_callback(self, widget):
        if widget.value and len(self.devices):
            device = self.devices[widget.value[0]]
            url = self.parentApp._cli._disk.get_download_url(self.file_info.id)
            logger.info(f'Device {device} is playing {self.file_info.name}')
            if url:
                device.set_current_media(url)

    def play(self):
        self.device_select.value = [self.device_select.entry_widget.cursor_line]

    def stop(self):
        if len(self.devices):
            self.device_select.value = []
            device = self.devices[self.device_select.entry_widget.cursor_line]
            device.stop()

    def discover(self):
        self.name = 'Refresh Device...'
        allDevices = self.dlnap.discover(st=self.dlnap.URN_AVTransport)
        self.name = str(Text(self.file_info.name))
        for device in allDevices:
            if device not in self.devices:
                self.devices.append(device)
        self.device_select.values = [Text(i) for i in self.devices]
        logger.debug(self.devices)
        self.display()

    def refresh_device(self):
        Thread(target=Dlna.discover, args=(self,), daemon=True).start()


class FileGrid(npyscreen.SimpleGrid):
    def __init__(self, *args, **kwargs):
        super(FileGrid, self).__init__(*args, **kwargs)
        self._file_name = None
        self._file_list = []
        self._file_info = None
        self.parent.name = 'root'
        self.update_file_list(file_id='root')

    file_name = property(lambda self: self.values[self.edit_cell[0]][self.edit_cell[1]])

    def set_up_handlers(self):
        super(FileGrid, self).set_up_handlers()
        self.handlers.update({
            curses.ascii.NL: self.keyboard_handlers,
            curses.ascii.CR: self.keyboard_handlers,
            curses.ascii.SP: self.keyboard_handlers,
            curses.ascii.ESC: self.back,
            '^C': self._exit
        })

    def back(self, _):
        if self._file_info:
            self.update_file_list(file_id=self._file_info.pid)

    def _exit(self, _):
        raise KeyboardInterrupt

    def download(self):
        for file_info in self._file_list:
            if file_info.name == self.file_name:
                Thread(target=functools.partial(self.parent.parentApp._cli.download_file, path=Path(file_info.name),
                                                url=file_info.download_url),
                       daemon=True).start()

    def copy_download_link(self):
        for file_info in self._file_list:
            if file_info.name == self.file_name:
                url = self.parent.parentApp._cli._disk.get_download_url(file_info.id)
                if url:
                    pyperclip.copy(url)
                    npyscreen.notify_confirm(f'Already copied to clipboard!\n{Text(file_info.name)}\n{url}')
                break

    def dlna(self):
        for file_info in self._file_list:
            if file_info.name == self.file_name and file_info.type:
                self.parent.parentApp.file_info = file_info
                self.parent.parentApp.switchForm('DLNA')
                return

    def update_file_list(self, name=None, file_id=None):
        file_list = []
        if name == '..' and self._file_info and self._file_info.pid:
            # 返回父目录且有父目录
            return self.update_file_list(file_id=self._file_info.pid)
        elif name:
            # 进入目录name
            for file_info in self._file_list:
                if file_info.name == name:
                    self._file_list = self.parent.parentApp._cli._path_list.get_fid_list(file_info.id, update=False)
                    # 保存当前目录信息
                    self._file_info = file_info
                    break
        elif file_id:
            # 进入目录file_id
            self._file_list = self.parent.parentApp._cli._path_list.get_fid_list(file_id, update=False)
            # 保存当前目录信息
            self._file_info = None
            if file_id != 'root':
                self._file_info = self.parent.parentApp._cli._path_list._tree.get_node(file_id).data
        for file_info in self._file_list:
            file_list.append(file_info.name)
        if self._file_info and self._file_info.pid:
            # 有父目录
            file_list.insert(0, '..')
        if file_list:
            self.set_grid_values_from_flat_list(file_list)
        path = 'root'
        if self._file_info:
            path = PurePosixPath(self._file_info.name)
        pid = self._file_info.pid if self._file_info else None
        while True:
            if pid:
                file_info = self.parent.parentApp._cli._path_list._tree.get_node(pid).data
                if file_info:
                    path = file_info.name / path
                    pid = file_info.pid
                else:
                    pid = None
            else:
                break
        if path:
            self.parent.name = str(Text(path))
            self.parent.display()

    def keyboard_handlers(self, _):
        self.update_file_list(self.file_name)

    def custom_print_cell(self, actual_cell, cell_display_value):
        pass

    def display_value(self, vl):
        return Text(vl)


class AliyunpanTUI(npyscreen.NPSAppManaged):
    def __init__(self, cli):
        self._cli = cli
        self.file_info = None
        super(AliyunpanTUI, self).__init__()

    def onStart(self):
        self.addForm('MAIN', AliyunpanFileForm)
        self.addForm('DLNA', Dlna)
