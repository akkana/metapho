#!/usr/bin/env python

# http://docs.python.org/distutils/setupscript.html

from distutils.core import setup

setup(name='MetaPho',
      packages=['MetaPho'],
      version='0.5',
      description='Image viewer and tagger',
      author='Akkana Peck',
      author_email='akkana@shallowsky.com',
      url='https://github.com/akkana/metapho',
      download_url='https://github.com/akkana/metapho/tarball/0.5',
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
          'console_scripts': [
              'metapho=MetaPho.metapho:main'
          ]
      }
     )

