#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from setuptools import find_packages, setup

import topdon

setup(
    name='topdon',
    version=topdon.__version__,
    description='Topdon Viewer',
    url='https://github.com/tna76874/topdon.git',
    author='maaaario',
    author_email='',
    license='BSD 2-clause',
    packages=find_packages(),
    install_requires=[
        "numpy",
        "argparse",
        "opencv_python",
        "pyudev",
	"Flask",
	"flask_socketio",
	"pyqrcode",
    ],
    package_data={
        'topdon': ['video.py'],
    },
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.9',
    ],
    python_requires = ">=3.9",
    entry_points={
        "console_scripts": [
            "topdon = topdon.topdon:main",
        ],
    },
    )
