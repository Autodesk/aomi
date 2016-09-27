#!/usr/bin/env python
import os
import sys
from setuptools import setup
from pkg_resources import resource_filename

vsn_path = resource_filename(__name__, 'aomi/version')
if not os.path.exists(vsn_path):
    vsn_path = resource_filename(__name__, 'version')
    if not os.path.exists(vsn_path):
        print("%s is missing" % vsn_path)
        sys.exit(1)

setup(name='aomi',
      version=open(vsn_path, 'r').read(),
      description='Easy access to secrets is not as bad as it sounds',
      author='Jonathan Freedman',
      author_email='jonathan.freedman@autodesk.com',
      license='MIT',
      url='https://github.com/autodesk/aomi',
      install_requires=['PyYAML', 'hvac', 'jinja2'],
      include_package_data=True,
      packages=['aomi'],
      entry_points={
          'console_scripts': ['aomi = aomi.cli:main']
      },
      package_data={'aomi':['version', 'templates/*.j2']}
)
