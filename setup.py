#!/usr/bin/env python

# http://docs.python.org/distutils/setupscript.html

# from distutils.core import setup
from setuptools import setup

setup(name='metapho',
      packages=['metapho'],
      version='0.5',
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
      # data_files=[ ('/usr/bin', ['helpers/notags']) ],
      entry_points={
          # This probably should be gui_scripts according to some
          # pages I've found, but none of the official documentation
          # mentions gui_scripts at all.
          'console_scripts': [
              'metapho=metapho.main:main'
          ]
      }
     )

