#!/usr/bin/env python3
"""
Setup script for package.
"""

from setuptools import setup

SHORT_DESCRIPTION = """
""".strip()

LONG_DESCRIPTION = """
DIY powder trickler control software.""".strip()

DEPENDENCIES = [
    'bluezero<=0.9.0',
    'pybleno',
    'pyserial',
    'gpiozero',
    'pymemcache',
    'RPi.GPIO',
    'grpcio',
]

TEST_DEPENDENCIES = []

VERSION = '2.2.1'
URL = 'https://github.com/ammolytics/open-trickler-peripheral/'

setup(
    name='opentrickler',
    version=VERSION,
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    url=URL,

    author='Eric Higgins',
    author_email='eric@ammolytics.com',
    license='MIT',

    classifiers=[
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],

    keywords='',

    packages=[],

    install_requires=DEPENDENCIES,
    tests_require=TEST_DEPENDENCIES,
)
