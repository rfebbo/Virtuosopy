#!/usr/bin/env python

from distutils.core import setup

setup(name='Virtuosopy',
      version='0.1',
      description='Python Interface to Virtuoso through Skillbridge',
      author='Rocco Febbo',
      author_email='febbo87@gmail.com',
      url='https://github.com/rfebbo/Virtuosopy',
      packages=['virtuosopy'],
      install_requires=[
          'skillbridge',
          'matplotlib',
          'ipykernel',
          'ipympl',
          'regex',
          'dataclasses'
      ],
     )