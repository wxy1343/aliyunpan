#!/usr/bin/env python3
import click
from click_aliases import ClickAliasedGroup

from aliyunpan.api.utils import logger
from aliyunpan.cli.cli import Commander
from aliyunpan.exceptions import ConfigurationFileNotFoundError

__version__ = '2.5.1'


@click.group(cls=ClickAliasedGroup)
@click.help_option('-h', '--help')
@click.version_option(version=__version__)
@click.option('-c', '--config-file', type=click.Path(), help='Specify the configuration file.',
              default='~/.config/aliyunpan.yaml', show_default=True)
@click.option('-t', 'refresh_token', type=click.STRING, help='Specify REFRESH_TOKEN.')
@click.option('-u', 'username', type=click.STRING, help='Specify USERNAME.')
@click.option('-p', 'password', type=click.STRING, help='Specify PASSWORD.')
@click.option('-d', '--depth', type=click.INT, help='File recursion depth.', default=3, show_default=True)
@click.option('--debug', is_flag=True, help='Debug mode.')
def cli(config_file, refresh_token, username, password, depth, debug):
    logger.info(f'Version:{__version__}')
    if debug:
        logger.setLevel('DEBUG')
    if refresh_token:
        commander.init(refresh_token=refresh_token, depth=depth)
    elif username:
        commander.init(username=username, password=password, depth=depth)
    elif config_file:
        commander.init(config_file=config_file, depth=depth)
    else:
        raise ConfigurationFileNotFoundError


@cli.command(aliases=['l', 'list', 'dir'], help='List files.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='root')
@click.option('-l', is_flag=True, help='View details.')
def ls(path, l):
    commander.ls(path, l)


@cli.command(aliases=['search'], help='Search for file.')
@click.help_option('-h', '--help')
@click.argument('query', type=click.STRING)
@click.option('-l', is_flag=True, help='View details.')
def search(query, l):
    commander.ls(path=None, l=l, query=query)


@cli.command(aliases=['delete', 'del'], help='Delete Files.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path())
def rm(path):
    commander.rm(path)


@cli.command(aliases=['r'], help='Rename file.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path())
@click.argument('name', type=click.STRING)
def rename(path, name):
    commander.rename(path, name)


@cli.command(aliases=['move'], help='Move files.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path())
@click.argument('target_path', type=click.Path())
def mv(path, target_path):
    commander.mv(path, target_path)


@cli.command(aliases=['u'], help='Upload files.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
@click.option('-p', '--file', multiple=True, help='Select multiple files.', type=click.Path())
@click.argument('upload_path', default='root')
@click.option('-t', '--time-out', type=click.FLOAT, help='Chunk upload timeout(sec).', default=10.0, show_default=True)
@click.option('-r', '--retry', type=click.INT, help='number of retries.', default=3, show_default=True)
@click.option('-f', '--force', is_flag=True, help='Force overlay file.')
@click.option('-s', '--share', is_flag=True, help='Specify the shared sequence file.')
@click.option('-cs', '--chunk-size', type=click.INT, help='Chunk size(byte).')
@click.option('-c', is_flag=True, help='Breakpoint continuation.')
def upload(path, file, upload_path, time_out, retry, force, share, chunk_size, c):
    if not path and not file:
        raise click.MissingParameter(param=click.get_current_context().command.params[2])
    else:
        path_list = {*file, path}
    commander.upload(path_list, upload_path, time_out, retry, force, share, chunk_size, c)


@cli.command(aliases=['m'], help='Create folder.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
def mkdir(path):
    commander.mkdir(path)


@cli.command(aliases=['d'], help='Download files.',
             context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
@click.option('-p', '--file', multiple=True, help='Select multiple files.', type=click.Path())
@click.argument('save_path', type=click.Path(), default='')
@click.option('-s', 'share', is_flag=True, help='Specify the shared sequence file')
@click.option('-cs', '--chunk-size', type=click.INT, help='Chunk size(byte).', default=1048576, show_default=True)
@click.option('-a', '--aria2', is_flag=True, help='Send to aria2.')
@click.pass_context
def download(ctx, path, file, save_path, share, chunk_size, aria2):
    if not path and not file:
        raise click.MissingParameter(param=click.get_current_context().command.params[2])
    else:
        file_list = {*file, path}
    kwargs = {}
    for i in ctx.args:
        kwargs[i.split('=')[0]] = i.split('=')[1]
    commander.download(file_list, save_path=save_path, share=share, chunk_size=chunk_size, aria2=aria2, **kwargs)


@cli.command(aliases=['t', 'show'], help='View file tree.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='root')
def tree(path):
    commander.tree(path)


@cli.command(aliases=['s'], help='Share file sharing link.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
@click.option('-p', '--file', multiple=True, help='Select multiple files.', type=click.Path())
@click.option('-f', '--file-id', multiple=True, type=click.STRING, help='File id.')
@click.option('-t', '--expire-sec', type=click.INT, help='Link expiration time(Max 14400 or permanent).')
@click.option('-l', '--share-link', is_flag=True, help='Output share link.', default=True, show_default=True)
@click.option('-d', '--download-link', is_flag=True, help='Output download link.', show_default=True)
@click.option('-s', '--save', is_flag=True, help='Save to cloud disk and local.', show_default=True)
@click.option('-S', '--share-official', is_flag=True, help='Output official share link.', show_default=True)
def share(path, file, file_id, expire_sec, share_link, download_link, save, share_official):
    if not path and not file and not file_id:
        raise click.MissingParameter(param=click.get_current_context().command.params[2])
    else:
        path_list = list(filter(None, {*file, path}))
        file_id_list = list(filter(None, {*file_id}))
    if share_official:
        commander.share_link(path_list, file_id_list, expire_sec)
    elif path_list:
        for path in path_list:
            if path:
                commander.share(path, expire_sec, share_link, download_link, save)
    else:
        raise click.MissingParameter(param=click.get_current_context().command.params[1])


@cli.command(aliases=['c'], help='Show file content.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
@click.option('-e', '--encoding', type=click.STRING, default='utf-8', show_default=True)
def cat(path, encoding):
    click.echo(commander.cat(path, encoding))


@cli.command(aliases=['sync'], help='Synchronize files.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path())
@click.argument('upload_path', default='root')
@click.option('-cs', '--chunk-size', type=click.INT, help='Chunk size(byte).')
@click.option('-t', '--time-out', type=click.FLOAT, help='Chunk upload timeout(sec).', default=10.0, show_default=True)
@click.option('-r', '--retry', type=click.INT, help='number of retries.', default=3, show_default=True)
@click.option('--sync-time', type=click.FLOAT, help='Synchronization interval time(sec).')
def sync(path, upload_path, time_out, chunk_size, retry, sync_time):
    commander.sync(path, upload_path, sync_time, time_out, chunk_size, retry)


@cli.command(aliases=['tui'], help='Text-based User Interface.')
@click.help_option('-h', '--help')
def tui():
    commander.tui()


if __name__ == '__main__':
    commander = Commander()
    cli()
