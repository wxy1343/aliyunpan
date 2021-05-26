#!/usr/bin/env python3
import click
from click_aliases import ClickAliasedGroup

from aliyunpan.cli.cli import Commander
from aliyunpan.exceptions import ConfigurationFileNotFoundError


@click.group(cls=ClickAliasedGroup)
@click.help_option('-h', '--help')
@click.version_option(version='2.1.0')
@click.option('-c', '--config-file', type=click.Path(), help='Specify the configuration file.',
              default='~/.config/aliyunpan.yaml', show_default=True)
@click.option('-t', 'refresh_token', type=click.STRING, help='Specify REFRESH_TOKEN.')
@click.option('-u', 'username', type=click.STRING, help='Specify USERNAME.')
@click.option('-p', 'password', type=click.STRING, help='Specify PASSWORD.')
@click.option('-d', '--depth', type=click.INT, help='File recursion depth.', default=3, show_default=True)
def cli(config_file, refresh_token, username, password, depth):
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
@click.option('-cs', '--chunk-size', type=click.INT, help='Chunk size(byte).', default=524288, show_default=True)
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


@cli.command(aliases=['d'], help='Download files.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
@click.option('-p', '--file', multiple=True, help='Select multiple files.', type=click.Path())
@click.argument('save_path', type=click.Path(), default='')
@click.option('-s', 'share', is_flag=True, help='Specify the shared sequence file')
def download(path, file, save_path, share):
    if not path and not file:
        raise click.MissingParameter(param=click.get_current_context().command.params[2])
    else:
        file_list = {*file, path}

    commander.download(file_list, save_path, share=share)


@cli.command(aliases=['t', 'show'], help='View file tree.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='root')
def tree(path):
    commander.tree(path)


@cli.command(aliases=['s'], help='Share file sharing link.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
@click.option('-f', '--file-id', type=click.STRING, default='', help='File id.')
@click.option('-t', '--expire-sec', type=click.INT, default=14400, help='Link expiration time(Max 14400).',
              show_default=True)
@click.option('-l', '--share-link', is_flag=True, help='Output share link.', default=True, show_default=True)
@click.option('-d', '--download-link', is_flag=True, help='Output download link.', show_default=True)
@click.option('-s', '--save', is_flag=True, help='Save to cloud disk and local.', show_default=True)
def share(path, file_id, expire_sec, share_link, download_link, save):
    if path or file_id:
        commander.share(path, file_id, expire_sec, share_link, download_link, save)
    else:
        raise click.MissingParameter(param=click.get_current_context().command.params[1])


@cli.command(aliases=['c'], help='Show file content.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
@click.option('-e', '--encoding', type=click.STRING, default='utf-8', show_default=True)
def cat(path, encoding):
    click.echo(commander.cat(path, encoding))


@cli.command(aliases=['tui'], help='Text-based User Interface.')
@click.help_option('-h', '--help')
def tui():
    commander.tui()


if __name__ == '__main__':
    commander = Commander()
    cli()
