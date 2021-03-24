import click
from click_aliases import ClickAliasedGroup

from aliyunpan.cli.cli import Commander


@click.group(cls=ClickAliasedGroup)
@click.help_option('-h', '--help')
@click.version_option(version='0.1')
@click.argument('refresh_token', type=str, default='')
def cli(refresh_token):
    commander.disk_init(refresh_token)


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


@cli.command(aliases=['move'], help='Move files.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path())
@click.argument('parent_path', type=click.Path())
def mv(path, parent_path):
    commander.mv(path, parent_path)


@cli.command(aliases=['u'], help='Upload files.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
@click.option('-p', '--file', multiple=True, help='Select multiple files.', type=click.Path())
@click.argument('upload_path', default='root')
@click.option('-t', '--time-out', type=float, help='Upload timeout.', default=10.0, show_default=True)
@click.option('-r', '--retry', type=int, help='number of retries.', default=3, show_default=True)
@click.option('-f', '--force', is_flag=True, help='Force overlay file.')
def upload(path, file, upload_path, time_out, retry, force):
    if not path and not file:
        raise click.MissingParameter(param=click.get_current_context().command.params[2])
    else:
        path_list = set((*file, path))
    commander.upload(upload_path, path_list, time_out, retry, force)


@cli.command(aliases=['d'], help='Download files.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='')
@click.option('-p', '--file', multiple=True, help='Select multiple files.', type=click.Path())
@click.argument('save_path', type=click.Path(), default='')
def download(path, file, save_path):
    if not path and not file:
        raise click.MissingParameter(param=click.get_current_context().command.params[2])
    else:
        file_list = set((*file, path))
    commander.download(file_list, save_path)


@cli.command(aliases=['t', 'show'], help='View file tree.')
@click.help_option('-h', '--help')
@click.argument('path', type=click.Path(), default='root')
def tree(path):
    commander.tree(path)


if __name__ == '__main__':
    commander = Commander()
    cli.add_command(ls)
    cli.add_command(upload)
    cli()
