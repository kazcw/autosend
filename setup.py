#!/usr/bin/env python

from distutils.core import setup

setup(name='autosend',
      version='1.0',
      description='Triggered-Transaction Tool',
      author='Kaz Wesley',
      author_email='keziahw@gmail.com',
      url='http://github.com/kazcw/autosend',
      scripts=['autosend'],
      package_dir={'autosend': 'src'},
      packages=['autosend'],
      requires=['bitcoinrpc'],
)
