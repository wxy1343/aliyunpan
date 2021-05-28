import curses
import functools
import platform
import time
from pathlib import PurePosixPath, Path
from threading import Thread

import npyscreen
import pyperclip

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
        npyscreen.setTheme(npyscreen.Themes.ColorfulTheme)
        self.file_menu = self.add_menu(name='Menu')
        file = self.add(FileGrid)
        self.download_menu = self.file_menu.addNewSubmenu(name='Download Menu', shortcut='^D')
        self.download_menu.addItemsFromList([
            ('Copy the download link', file.copy_download_link, '^C'),
            ('Download file', file.download, '^D')
        ])
        self.file_menu.addItemsFromList([
            ('Show file details', file.show_file_info, '^X'),
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


class Time(npyscreen.TitleText):
    def set_up_handlers(self):
        super(Time, self).set_up_handlers()
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
            ('Pause', self.pause, '^P'),
            ('Continue', self.continue_, '^O'),
            ('Mute', self.mute, '^Q'),
            ('Unmute', self.unmute, '^E'),
            ('Stop', self.stop, '^S'),
            ('Back', self.back, '^X'),
            ('Refresh Device', self.refresh_device, '^R')
        ])
        self.devices = []
        self.device_select = self.add(DeviceSelect, scroll_exit=False, name='Devices', max_height=5,
                                      value_changed_callback=self.device_changed_callback)
        self.add(npyscreen.TitleSlider, color='STANDOUT', name='Volume', out_of=10,
                 value_changed_callback=self.volume_changed_callback)
        self.position = '00:00:00'
        self.second = self.add(Time, name='sec', value='00')
        self.minute = self.add(Time, name='min', value='00')
        self.hour = self.add(Time, name='hour', value='00')
        self._volume = 0
        self.add(npyscreen.ButtonPress, relx=0, name='Set time', when_pressed_function=self.set_time)

    def back(self):
        self.parentApp.switchFormPrevious()

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

    def device_changed_callback(self, widget):
        if widget.value and len(self.devices):
            device = self.devices[widget.value[0]]
            url = self.parentApp._cli._disk.get_download_url(self.file_info.id)
            logger.info(f'Device {device} is playing {self.file_info.name}')
            if url:
                device.set_current_media(url)

    def play(self):
        if len(self.devices):
            if self.device_select.value:
                self.device_changed_callback(self.device_select)
            else:
                self.device_select.value = [self.device_select.entry_widget.cursor_line]
                self.device_changed_callback(self.device_select)

    def pause(self):
        if len(self.devices) and self.device_select.entry_widget.value:
            device = self.devices[self.device_select.entry_widget.value[0]]
            device.pause()

    def continue_(self):
        if len(self.devices) and self.device_select.entry_widget.value:
            device = self.devices[self.device_select.entry_widget.value[0]]
            device.play()

    def stop(self):
        if len(self.devices) and self.device_select.entry_widget.value:
            device = self.devices[self.device_select.entry_widget.value[0]]
            self.device_select.entry_widget.value = []
            device.stop()

    def mute(self):
        if len(self.devices) and self.device_select.entry_widget.value:
            device = self.devices[self.device_select.entry_widget.value[0]]
            device.mute()

    def unmute(self):
        if len(self.devices) and self.device_select.entry_widget.value:
            device = self.devices[self.device_select.entry_widget.value[0]]
            device.unmute()

    def discover(self):
        self.name = 'Refresh Device...'
        allDevices = self.dlnap.discover(st=self.dlnap.URN_AVTransport)
        self.name = str(Text(self.file_info.name))
        for device in allDevices:
            if device not in self.devices:
                self.devices.append(device)
        self.device_select.values = [Text(i) for i in self.devices]
        logger.debug(self.devices)
        if self.editing:
            self.display()

    def refresh_device(self):
        Thread(target=Dlna.discover, args=(self,), daemon=True).start()

    def volume_changed_callback(self, widget):
        if len(self.devices) and self.device_select.entry_widget.value and self._volume != widget.value:
            self._volume = widget.value
            device = self.devices[self.device_select.entry_widget.value[0]]
            device.volume(int(widget.value) * 10)

    def set_position(self, second=None, minute=None, hour=None):
        position = '{:02d}:{:02d}:{:02d}'
        if len(self.devices) and self.device_select.entry_widget.value:
            position = position.format(hour, minute, second)
            npyscreen.notify_confirm(position)
            device = self.devices[self.device_select.entry_widget.value[0]]
            device.seek(position)

    def set_time(self):
        try:
            self.set_position(second=int(self.second.value), minute=int(self.minute.value), hour=int(self.hour.value))
        except ValueError:
            pass


class FileGrid(npyscreen.SimpleGrid):
    def __init__(self, *args, **kwargs):
        super(FileGrid, self).__init__(*args, **kwargs)
        self._file_name = None
        self._file_list = []
        self._parent_file_info = None
        self.parent.name = 'root'
        self.update_file_list(file_id='root')

    file_name = property(lambda self: self.values[self.edit_cell[0]][self.edit_cell[1]])
    _file_info = property(lambda self: [file_info for file_info in self._file_list if file_info.name == self.file_name])
    file_info = property(lambda self: self._file_info[0] if self._file_info else None)

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
        if self._parent_file_info:
            self.update_file_list(file_id=self._parent_file_info.pid)

    def _exit(self, _):
        raise KeyboardInterrupt

    def download(self):
        if self.file_info:
            if self.file_info.type:
                Thread(
                    target=functools.partial(self.parent.parentApp._cli.download_file, path=Path(self.file_info.name),
                                             url=self.file_info.download_url)).start()
            else:
                path = Path(self.file_info.name)
                if self.parent.name != 'root':
                    path = self.parent.name / Path(self.file_info.name)
                Thread(target=functools.partial(self.parent.parentApp._cli.download, path=str(path))).start()

    def copy_download_link(self):
        if self.file_info and self.file_info.name == self.file_name and self.file_info.type:
            url = self.parent.parentApp._cli._disk.get_download_url(self.file_info.id)
            if url:
                pyperclip.copy(url)
                npyscreen.notify_confirm(f'Already copied to clipboard!\n{Text(self.file_info.name)}\n{url}')

    def dlna(self):
        if self.file_info:
            if self.file_info.name == self.file_name and self.file_info.type:
                self.parent.parentApp.file_info = self.file_info
                self.parent.parentApp.switchForm('DLNA')

    def show_file_info(self, file_info=None):
        if not file_info:
            file_info = self.file_info
        info = f'name:{Text(file_info.name)}\n' \
               f'file_id:{file_info.id}\n' \
               f'type:{"file" if file_info.type else "folder"}\n' \
               f'create_time:{time.strftime("%d %b %H:%M", file_info.ctime)}\n' \
               f'update_time:{time.strftime("%d %b %H:%M", file_info.update_time)}\n' \
               f'category:{file_info.category}\n' \
               f'content_type:{file_info.content_type}\n' \
               f'size:{file_info.size}\n' \
               f'content_hash_name:{file_info.content_hash_name}\n' \
               f'content_hash:{file_info.content_hash}'
        npyscreen.notify_confirm(info, 'File info')

    def update_file_list(self, name=None, file_id=None):
        file_list = []
        if name == '..' and self._parent_file_info and self._parent_file_info.pid:
            # 返回父目录且有父目录
            return self.update_file_list(file_id=self._parent_file_info.pid)
        elif name:
            # 进入目录name
            file_info = self.file_info
            if file_info:
                if file_info.type:
                    self.show_file_info(file_info)
                    return
                self._file_list = self.parent.parentApp._cli._path_list.get_fid_list(file_info.id, update=False)
                # 保存当前目录信息
                self._parent_file_info = file_info
        elif file_id:
            # 进入目录file_id
            self._file_list = self.parent.parentApp._cli._path_list.get_fid_list(file_id, update=False)
            # 保存当前目录信息
            self._parent_file_info = None
            if file_id != 'root':
                self._parent_file_info = self.parent.parentApp._cli._path_list._tree.get_node(file_id).data
        for file_info in self._file_list:
            file_list.append(file_info.name)
        if self._parent_file_info and self._parent_file_info.pid:
            # 有父目录
            file_list.insert(0, '..')
        if file_list:
            self.set_grid_values_from_flat_list(file_list)
        path = 'root'
        if self._parent_file_info:
            path = PurePosixPath(self._parent_file_info.name)
        pid = self._parent_file_info.pid if self._parent_file_info else None
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
