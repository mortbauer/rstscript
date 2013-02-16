#!/usr/bin/env python

import re
import sys
import rstscript
#from setuptools import setup
from cx_Freeze import setup,Executable

# from http://cburgmer.posterous.com/pip-requirementstxt-and-setuppy
def parse_requirements(file_name):
    requirements = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'(\s*#)|(\s*$)', line):
            continue
        if re.match(r'\s*-e\s+', line):
            requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1', line))
        elif re.match(r'\s*-f\s+', line):
            pass
        else:
            requirements.append(line)

    return requirements


def parse_dependency_links(file_name):
    dependency_links = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'\s*-[ef]\s+', line):
            dependency_links.append(re.sub(r'\s*-[ef]\s+', '', line))

    return dependency_links


base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(name='rstscript',
      entry_points = {
          'console_scripts' :
              ['rstscript = rstscript.main:run'
               ]},
      version=rstscript.__version__,
      description=rstscript.__description__,
      author=rstscript.__author__,
      author_email=rstscript.__author_email__,
      url=rstscript.__url__,
      download_url=rstscript.__url__,
      license=rstscript.__copyright__,
      packages=['rstscript'],
      package_data={'rstscript':['defaults/config.json']},
      install_requires=parse_requirements('requirements.txt'),
      dependency_links=parse_dependency_links('requirements.txt'),
      executables = [Executable(script = "rstscript/client.py")],
      extras_require = {
        'autofigure':  ["matplotlib"]
      },
      provides='rstscript',
      classifiers=[
        'Development Status :: Alpha',
        'Topic :: Text Processing :: Markup',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Documentation',
        'License :: OSI Approved :: GNU General Public License (GPL)'],
)
