# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
# To use a consistent encoding
import codecs
import os
from os import path


# Get the long description from the README file
description = 'A URL scheme to share code'
try:
    here = path.abspath(path.dirname(__file__))
    with codecs.open(path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except IOError:
    long_description = description


def package_files(directory):
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


def post_install():
    " Install the system URL handler "
    # Sync PYTHONPATH after install
    try:
        from imp import reload
    except ImportError:
        pass  # Old Python
    import site
    reload(site)

    import dcode.install
    dcode.install.install()


class my_install(install):
    def run(self):
        install.run(self)
        self.execute(post_install, [], msg="Installing URL handler")


class my_develop(develop):
    def run(self):
        develop.run(self)
        self.execute(post_install, [], msg="Installing URL handler")


setup(
    name='dcode',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.3.0',

    description=description,
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/deckardai/dcode',

    # Author details
    author='Aurélien Nicolas',
    author_email='info@deckard.ai',

    # Choose your license
    license='Apache2',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache Software License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    # What does your project relate to?
    keywords='url code file sharing development',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=["dcode"],

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #py_modules=[],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    #install_requires=[],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    #extras_require={},

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        "dcode": package_files("dcode/macos/") +
                 package_files("dcode/linux/") +
                 ["demo.txt"],
    },
    zip_safe=False,

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    #data_files=[],

    # Post install
    #cmdclass={'install': my_install,
    #          'develop': my_develop},

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'dcode=dcode.dcode:main',
        ],
    },
)
