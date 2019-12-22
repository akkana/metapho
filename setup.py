#!/usr/bin/env python

# http://docs.python.org/distutils/setupscript.html

# from distutils.core import setup
from setuptools import setup, Command
import re
import os

def get_version():
    '''Read the module versions from */__init__.py'''
    with open("metapho/__init__.py") as fp:
        for line in fp:
            line = line.strip()
            if line.startswith("__version__"):
                versionpart = line.split("=")[-1] \
                                  .strip().replace('"', '').replace("'", '')
                if versionpart.startswith('"') or versionpart.startswith("'"):
                    versionpart = versionpart[1:]
                if versionpart.endswith('"') or versionpart.endswith("'"):
                    versionpart = versionpart[:-1]
                return versionpart

def get_readme_contents():
    with open("README.md", "r") as fh:
        return fh.read()

# Some people recommend this, but it returns '-0.6-' rather than '0.6'
# import pkg_resources  # part of setuptools
# version = pkg_resources.require("metapho")[0].version
# print "Version is '%s'" % version

class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        os.system('rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info ./docs/sphinxdoc/_build metapho/__pycache__')

setup(name='metapho',
      packages=['metapho', 'metapho.gtkpho'],
      version=get_version(),
      description='Image viewer and tagger',
      long_description=get_readme_contents(),
      long_description_content_type="text/markdown",
      author='Akkana Peck',
      author_email='akkana@shallowsky.com',
      url='https://github.com/akkana/metapho',
      download_url='https://github.com/akkana/metapho/tarball/1.0',

      install_requires=["PyGObject", "pycairo"],
      license="GPLv2+",

      keywords=['image', 'viewer', 'tagger'],
      classifiers = [
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
          'Intended Audience :: End Users/Desktop',
          'Topic :: Multimedia :: Graphics',
          'Topic :: Multimedia :: Graphics :: Viewers',
          'Topic :: Utilities'
        ],
      entry_points={
          # Python.org documentation doesn't mention gui_scripts, but
          # on Windows, console_scripts bring up a terminal, gui_scripts don't.
          # On Linux they're the same.
          'gui_scripts': [
              'metapho=metapho.gtkpho.main:main',
              'mpiv=metapho.gtkpho.ImageViewer:main'   # MetaPho Image Viewer
          ],
          'console_scripts': [
              'notags=metapho:main'
          ]
      },

      cmdclass={
          'clean': CleanCommand,
      }
     )
