#!/usr/bin/env python

# http://docs.python.org/distutils/setupscript.html

# from distutils.core import setup
from setuptools import setup, Command
import re
import os

def read(fname):
    '''Utility function to read the README file, for the long_description.'''
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def get_version_re():
    '''Read the pytopo module versions from pytopo/__init__.py'''
    with open("metapho/__init__.py") as fp:
        version_file = fp.read()
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                                  version_file, re.M)
        if version_match:
            return version_match.group(1)
        print "No version information!"
        return None

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
        os.system('rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info ./docs/sphinxdoc/_build')

setup(name='metapho',
      packages=['metapho', 'metapho.gtkpho'],
      version=get_version_re(),
      description='Image viewer and tagger',
      scripts=['helpers/notags'],
      author='Akkana Peck',
      author_email='akkana@shallowsky.com',
      url='https://github.com/akkana/metapho',
      download_url='https://github.com/akkana/metapho/tarball/0.6',
      # install_requires=["pygtk"],
      license="GPLv2+",
      keywords=['image', 'viewer', 'tagger'],
      classifiers = [
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
          'Intended Audience :: End Users/Desktop',
          'Topic :: Multimedia :: Graphics',
          'Topic :: Multimedia :: Graphics :: Viewers',
          'Topic :: Utilities'
        ],
      entry_points={
          # This probably should be gui_scripts according to some
          # pages I've found, but none of the official documentation
          # mentions gui_scripts at all.
          'console_scripts': [
              'metapho=metapho.gtkpho.main:main',
              'mpiv=metapho.gtkpho.ImageViewer:main'
          ]
      },

      cmdclass={
          'clean': CleanCommand,
      }
     )
