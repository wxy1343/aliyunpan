import click
from click_aliases import ClickAliasedGroup

from aliyunpan.about import __version__
from aliyunpan.api.utils import logger
from aliyunpan.cli import Commander

__all__ = ['main']


@click.group(cls=ClickAliasedGroup)
@click.help_option('-h', '--help')
@click.version_option(version=__version__)
@click.option('-c', '--config-file', type=click.Path(), help='Specify the configuration file.',
              default='~/.config/aliyunpan.yaml', show_default=True)
@click.option('-t', '--refresh-token', type=click.STRING, help='Specify REFRESH_TOKEN.')
@click.option('-u', '--username', type=click.STRING, help='Specify USERNAME.')
@click.option('-p', '--password', type=click.STRING, help='Specify PASSWORD.')
@click.option('-d', '--depth', type=click.INT, help='File recursion depth.', default=3, show_default=True)
@click.option('-D', '--debug', is_flag=True, help='Debug mode.')
@click.option('-T', '--timeout', type=click.FLOAT, help='Api request timeout.')
@click.option('-id', '--drive-id', type=click.STRING, help='Specify DRIVE_ID.')
@click.option('-a', '--album', is_flag=True, help='Specify album.')
@click.option('-s', '--share-id', type=click.STRING, help='Specify share_id.')
@click.option('-sp', '--share-pwd', type=click.STRING, help='Specify share_pwd.')
@click.option('-f', '--filter-file', multiple=True, type=click.STRING, help='Filter files.')
@click.option('-w', '--whitelist', is_flag=True, help='Filter files using whitelist.')
@click.option('-m', '--match', is_flag=True, help='Specify to use regular matching files.')
def cli(config_file, refresh_token, username, password, depth, debug, timeout, drive_id, album, share_id, share_pwd,
        filter_file, whitelist, match):
    logger.info(f'Version:{__version__}')
    if debug:
        logger.setLevel('DEBUG')
    commander.init(config_file=None if refresh_token or username else config_file,
                   refresh_token=None if username else refresh_token, username=username, password=password, depth=depth,
                   timeout=timeout, drive_id=drive_id, album=album, share_id=share_id, share_pwd=share_pwd,
                   filter_file=set(filter_file), whitelist=whitelist, match=match)


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
        path_list = set(filter(None, {*file, path}))
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
        if '=' in i:
            kwargs[i.split('=')[0]] = i.split('=')[1]
        else:
            kwargs[i.strip('-')] = True
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


@cli.command(aliases=['sync'], help='Synchronize files.',
             context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.help_option('-h', '--help')
@click.argument('local_path', type=click.Path())
@click.argument('remote_path', default='root')
@click.option('-cs', '--chunk-size', type=click.INT, help='Chunk size(byte).')
@click.option('-t', '--time-out', type=click.FLOAT, help='Chunk upload timeout(sec).', default=10.0, show_default=True)
@click.option('-r', '--retry', type=click.INT, help='number of retries.', default=3, show_default=True)
@click.option('-st', '--sync-time', type=click.FLOAT, help='Synchronization interval time(sec).')
@click.option('-n', '--no-delete', is_flag=True, help='Do not delete the cloud/local files.')
@click.option('-d', '--delete', is_flag=True, help='Allow deletion of cloud/local files.')
@click.option('-l', '--local', is_flag=True, help='Sync cloud drive files to local.')
@click.pass_context
def sync(ctx, local_path, remote_path, time_out, chunk_size, retry, sync_time, no_delete, delete, local):
    kwargs = {}
    for i in ctx.args:
        if '=' in i:
            kwargs[i.split('=')[0]] = i.split('=')[1]
        else:
            kwargs[i.strip('-')] = True
    if local:
        commander.sync_local(remote_path, local_path, sync_time, chunk_size, delete, **kwargs)
    else:
        commander.sync(local_path, remote_path, sync_time, time_out, chunk_size, retry, delete)


@cli.command(aliases=['tui'], help='Text-based User Interface.')
@click.help_option('-h', '--help')
def tui():
    commander.tui()


@cli.command(aliases=['r', 'refresh_token'], help='Get refresh_token.')
@click.help_option('-h', '--help')
@click.option('--refresh', '-r', is_flag=True, help='Refresh the token of the configuration file.')
@click.option('--refresh-time', '-t', type=click.FLOAT, help='Auto refresh token interval time(sec).')
@click.option('--change', '-c', type=click.STRING, help='Set new refresh_token.')
def token(refresh, refresh_time, change):
    if refresh:
        commander.disk.token_refresh()
    elif refresh_time:
        commander.auto_refresh_token(refresh_time)
    elif change:
        if commander.disk.token_refresh(change):
            commander.disk.refresh_token = change
    click.echo(commander.disk.refresh_token)


commander: Commander


def main():
    global commander
    commander = Commander(init=False)
    cli()


if __name__ == '__main__':
    main()
