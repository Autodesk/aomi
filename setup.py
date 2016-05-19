#!/usr/bin/env python
import sys, os
from setuptools import setup

vsn_path = "%s/version" % os.path.dirname(os.path.abspath(__file__))
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
      scripts=['aomi'],
      include_package_data=True,
      package_data={'aomi':['version']}
)
