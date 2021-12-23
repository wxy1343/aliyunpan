import pathlib

from setuptools import setup

from aliyunpan.about import __version__

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')
install_requires = []
with open('requirements.txt', 'r') as f:
    while True:
        req = f.readline()
        if not req:
            break
        install_requires.append(req.strip('\n'))
setup(
    name='aliyunpan',
    version=__version__,
    description='aliyunpan cli',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/wxy1343/aliyunpan',
    author='wxy1343',
    author_email='1343890272@qq.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'Framework :: Flask',
        'Topic :: Internet',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Multimedia',
        'Topic :: Multimedia :: Graphics',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Video',
        'Topic :: Communications :: File Sharing',
        'Topic :: Utilities',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='aliyunpan, aliyundrive, cli, tui',
    py_modules=["aliyunpan"],
    packages=['aliyunpan', 'aliyunpan/api', 'aliyunpan/cli', 'dlnap/dlnap'],
    python_requires='>=3.6, <4',
    install_requires=install_requires,
    data_files=[
        'requirements.txt'
    ],
    entry_points={
        'console_scripts': [
            'aliyunpan-cli=aliyunpan.main:main',
            'aliyunpan=aliyunpan.main:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/wxy1343/aliyunpan/issues',
        'Funding': 'https://donate.pypi.org',
        'Say Thanks!': 'https://saythanks.io/to/1343890272@qq.com',
        'Source': 'https://github.com/wxy1343/aliyunpan',
    },
    zip_safe=False
)
