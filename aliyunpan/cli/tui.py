import curses
import functools
import platform
import time
from pathlib import PurePosixPath, Path
from threading import Thread

import npyscreen
import pyperclip

from aliyunpan.api.utils import logger, stop_thread, get_open_port

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

    def __repr__(self):
        text = self._text
        if platform.system() == 'Windows':
            text = ''
            del_list = []
            for i, _char in enumerate(self._text):
                if len(_char.encode()) > 1:
                    if len(self._text) > i + 1 and self._text[i + 1] == ' ':
                        del_list.append(i + 1)
            for i, _char in enumerate(self._text):
                if i not in del_list:
                    text += _char
        return text

    def __eq__(self, other):
        return str(self) == str(other)


class AliyunpanFileForm(npyscreen.FormBaseNewWithMenus):
    def create(self):
        npyscreen.setTheme(npyscreen.Themes.ColorfulTheme)
        self.file_menu = self.add_menu(name='Menu')
        file = self.add(FileGrid)
        self.download_menu = self.file_menu.addNewSubmenu(name='Download Menu', shortcut='^D')
        self.download_menu.addItemsFromList([
            ('Copy the download link', file.copy_download_link, '^C'),
            ('Download file', file.download, '^D'),
            ('Aria2', file.aria2, '^A')
        ])
        self.file_menu.addItemsFromList([
            ('Show file details', file.show_file_info, '^X'),
            ('Cast screen to TV', file.dlna, '^A'),
            ('Search', file.search, '^F'),
            ('Remove', file.remove, '^R'),
            ('Mkdir', file.mkdir, 'm')
        ])


class Select(npyscreen.TitleSelectOne):
    def set_up_handlers(self):
        super(Select, self).set_up_handlers()
        self.handlers.update({
            '^C': self._exit
        })

    def _exit(self, _):
        raise KeyboardInterrupt


class DeviceSelect(Select):
    pass


class QualitySelect(Select):
    pass


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
            ('Proxy Play', self.proxy_play, 'y'),
            ('Local redirection Play', self.redirect_play, 'r'),
            ('Pause', self.pause, 'p'),
            ('Continue', self.continue_, 'c'),
            ('Mute', self.mute, '^Q'),
            ('Unmute', self.unmute, '^E'),
            ('Stop', self.stop, '^S'),
            ('Back', self.back, '^X'),
            ('Refresh Device', self.refresh_device, '^R')
        ])
        self.devices = []
        self.quality_dict = {}
        self.quality = 'default'
        self.device_select = self.add(DeviceSelect, scroll_exit=False, name='Devices', max_height=5,
                                      value_changed_callback=self.device_changed_callback)
        self.quality_select = self.add(QualitySelect, scroll_exit=True, name='Quality', max_height=5,
                                       value_changed_callback=self.quality_changed_callback)
        self.add(npyscreen.TitleSlider, color='STANDOUT', name='Volume', out_of=10,
                 value_changed_callback=self.volume_changed_callback)
        self.position = '00:00:00'
        self.second = self.add(Time, name='sec', value='00')
        self.minute = self.add(Time, name='min', value='00')
        self.hour = self.add(Time, name='hour', value='00')
        self._volume = 0
        self._proxy_port = 8000
        self._change_lock_time = 0
        self.add(npyscreen.ButtonPress, relx=0, name='Set time', when_pressed_function=self.set_time)
        self._proxy_thread = None
        self._redirect_thread = None
        self.proxy = None
        self.redirect = None

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
            self._refresh()

    def afterEditing(self):
        self.parentApp.setNextFormPrevious()

    def device_changed_callback(self, widget):
        if time.time() - self._change_lock_time > 1:
            self._change_lock_time = 0
        if widget.value and len(self.devices) and not self._change_lock_time:
            self._change_lock_time = time.time()
            device = self.devices[widget.value[0]]
            if self.quality and self.quality_dict:
                url = self.quality_dict[self.quality]
            else:
                url = self.parentApp._cli._disk.get_download_url(self.file_info.id)
            logger.info(f'Device {device} is playing {self.file_info.name}')
            if url:
                if self.proxy:
                    ip = self.dlnap._get_serve_ip(device.ip)
                    if self._proxy_thread:
                        stop_thread(self._proxy_thread)
                    self._proxy_thread = Thread(target=self.dlnap.runProxy, daemon=True,
                                                kwargs={'ip': ip, 'port': get_open_port()})
                    self._proxy_thread.start()
                    url = 'http://{}:{}/{}'.format(ip, self._proxy_port, url)
                elif self.redirect:
                    ip = self.dlnap._get_serve_ip(device.ip)
                    if self._redirect_thread:
                        stop_thread(self._redirect_thread)
                    port = get_open_port()
                    self._redirect_thread = Thread(target=Dlna._redirect, args=(url, port), daemon=True).start()
                    url = 'http://{}:{}/'.format(ip, port)
                logger.debug(url)
                device.set_current_media(url)
                device.play()

    def quality_changed_callback(self, widget):
        if widget.value:
            try:
                self.quality = list(self.quality_dict.keys())[widget.value[0]]
            except IndexError:
                self.quality = 'default'
            self.play()

    def play(self, proxy=False, redirect=False):
        if proxy:
            self.proxy = True
            self.redirect = False
        elif redirect:
            self.redirect = True
            self.proxy = False
        if len(self.devices):
            if self.device_select.value:
                self.device_changed_callback(self.device_select)
            else:
                self.device_select.value = [self.device_select.entry_widget.cursor_line]
                self.device_changed_callback(self.device_select)

    def proxy_play(self):
        self.play(proxy=True)

    @staticmethod
    def _redirect(url, port):
        from flask import Flask, redirect

        app = Flask(__name__)

        @app.route('/')
        def index():
            return redirect(url, code=301)

        app.run(host='0.0.0.0', port=port)

    def redirect_play(self):
        self.play(redirect=True)

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

    def refresh_device(self):
        t = Thread(target=Dlna.discover, args=(self,), daemon=True)
        t.start()
        return t

    def refresh_quality(self):
        t = Thread(target=Dlna.get_quality_info, args=(self,), daemon=True)
        t.start()
        return t

    def _refresh(self):
        def t():
            self.refresh_device().join()
            self.refresh_quality().join()
            if self.editing:
                self.display()

        Thread(target=t).start()

    def get_quality_info(self):
        self.quality_dict = {'default': self.parentApp._cli._disk.get_download_url(self.file_info.id)}
        self.quality_dict.update(
            self.parentApp._cli._disk.get_play_info(file_id=self.file_info.id, category=self.file_info.category))
        self.quality_select.values = list(self.quality_dict.keys())
        logger.debug(self.quality_dict)

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
        self._file_list = []
        self._parent_file_info = None
        self.parent.name = 'root'
        self.update_file_list(file_id='root')

    file_name = property(lambda self: self.values[self.edit_cell[0]][self.edit_cell[1]])
    _file_info = property(lambda self: [file_info for file_info in self._file_list if file_info.name == self.file_name])
    file_info = property(lambda self: self._file_info[0] if self._file_info else None)
    parent_file_info = property(lambda self: self._parent_file_info)

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

    def download(self, aria2=False):
        if self.file_info:
            path = Path(Text(self.parent.name).__repr__()) / Path(self.file_info.name)
            if self.file_info.type:
                if aria2:
                    Thread(target=functools.partial(self.parent.parentApp._cli.download, str(path), aria2=True)).start()
                else:
                    Thread(target=functools.partial(self.parent.parentApp._cli.download_file,
                                                    path=Path(self.file_info.name),
                                                    url=self.file_info.download_url)).start()
            else:
                if self.parent.name == 'root':
                    path = Path(self.file_info.name)
                if aria2:
                    Thread(target=functools.partial(self.parent.parentApp._cli.download, str(path), aria2=True)).start()
                else:
                    Thread(target=functools.partial(self.parent.parentApp._cli.download, path=str(path))).start()

    def aria2(self):
        self.download(aria2=True)

    def copy_download_link(self):
        if self.file_info and self.file_info.name == self.file_name and self.file_info.type:
            url = self.parent.parentApp._cli._disk.get_download_url(self.file_info.id)
            if url:
                pyperclip.copy(url)
                npyscreen.notify_confirm(f'Already copied to clipboard!\n{Text(self.file_info.name)}\n{url}')

    def dlna(self):
        if self.file_info and self.file_info.name == self.file_name and self.file_info.type:
            self.parent.parentApp.file_info = self.file_info
            self.parent.parentApp.switchForm('DLNA')

    def search(self):
        self.parent.parentApp.file_grid = self
        self.parent.parentApp.switchForm('Search')

    def remove(self):
        if self.file_info and Text(self.file_info.name) == Text(self.file_name):
            self.parent.parentApp._cli.rm(path=None, file_id=self.file_info.id)
            file_list = []
            for i in self.values:
                file_list.extend(i)
            file_list.remove(self.file_info.name)
            self.set_grid_values_from_flat_list(file_list)

    def mkdir(self):
        self.parent.parentApp.file_grid = self
        self.parent.parentApp.switchForm('Mkdir')

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
        self.searched = False
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
        else:
            self._file_list = self.parent.parentApp._cli._path_list.get_fid_list(self._parent_file_info.id,
                                                                                 update=False)
        for file_info in self._file_list:
            file_list.append(file_info.name)
        if self._parent_file_info and self._parent_file_info.pid:
            # 有父目录
            file_list.insert(0, '..')
        if file_list:
            self.set_grid_values_from_flat_list(file_list)
        self.update_path()

    def update_path(self):
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
            self._display()

    def _display(self):
        if platform.system() == 'Windows':
            self.parent.display()
        else:
            self.parent.DISPLAY()

    def keyboard_handlers(self, _):
        self.update_file_list(self.file_name)

    def custom_print_cell(self, actual_cell, cell_display_value):
        pass

    def display_value(self, vl):
        return Text(vl)


class Search(npyscreen.ActionPopup):
    def create(self):
        self.query = self.add(npyscreen.TitleText, name='query')

    def afterEditing(self):
        self.parentApp.setNextFormPrevious()

    def on_ok(self):
        file_info_list = self.parentApp._cli._path_list.get_file_info(
            self.parentApp._cli._disk.search(self.query.value))
        if not self.parentApp.file_grid.searched:
            self.parentApp.file_grid.searched = True
            self.parentApp.file_grid._parent_file_info = self.parentApp.file_grid.file_info
        self.parentApp.file_grid._file_list = file_info_list
        file_list = ['..']
        for file_info in file_info_list:
            file_list.append(file_info.name)
        self.parentApp.file_grid.set_grid_values_from_flat_list(file_list)
        self.parentApp.file_grid.parent.name = f'{self.query.value}'
        self.parentApp.file_grid._display()

    def on_cancel(self):
        pass


class Mkdir(npyscreen.ActionPopup):
    def create(self):
        self.name = self.add(npyscreen.TitleText, name='name')

    def afterEditing(self):
        self.parentApp.setNextFormPrevious()

    def on_ok(self):
        if not self.parentApp.file_grid.searched:
            if self.parentApp.file_grid.parent_file_info:
                parent_file_id = self.parentApp.file_grid.parent_file_info.id
            else:
                parent_file_id = 'root'
            file_id = self.parentApp._cli.mkdir(path=None, name=self.name.value, parent_file_id=parent_file_id)[0][0]
            file_list = []
            for i in self.parentApp.file_grid.values:
                file_list.extend(i)
            file_list.append(str(Text(self.name.value)))
            self.parentApp.file_grid._file_list.append(self.parentApp._cli._path_list._tree.get_node(file_id).data)
            self.parentApp.file_grid.set_grid_values_from_flat_list(file_list)

    def on_cancel(self):
        pass


class AliyunpanTUI(npyscreen.NPSAppManaged):
    def __init__(self, cli):
        self._cli = cli
        self.file_info = None
        super(AliyunpanTUI, self).__init__()

    def onStart(self):
        self.addForm('MAIN', AliyunpanFileForm)
        self.addForm('DLNA', Dlna)
        self.addForm('Search', Search)
        self.addForm('Mkdir', Mkdir)
