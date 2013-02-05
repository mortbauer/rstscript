#!/usr/bin/env python

from setuptools import setup
import litscript

setup(name='litscript',
      entry_points = {
          'console_scripts' :
              ['litscript = litscript.main:main.run'
               ]},
      version=litscript.__version__,
      description=litscript.__description__,
      author=litscript.__author__,
      author_email=litscript.__author_email__,
      url=litscript.__url__,
      download_url=litscript.__url__,
      license=litscript.__copyright__,
      packages=['litscript'],
      package_data={'litscript':['defaults/litscript.rc.spec']},
      install_requires=[
          'argparse >=0.9',
          'colorama'],
      provides='litscript',
      classifiers=[
        'Development Status :: Alpha',
        'Topic :: Text Processing :: Markup',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Documentation',
        'License :: OSI Approved :: GNU General Public License (GPL)'],
)
