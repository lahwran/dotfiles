import os
from setuptools import setup

setup(
    name = "at",
    version = "0.0.3",
    author = "lahwran",
    author_email = "lahwran0@gmail.com",
    description = "A set of utilities I use frequently in interactive environments",
    license = "MIT",
    keywords = "utility",
    url = "https://github.com/lahwran/dotfiles/tree/master/packages/at",
    packages=['at'],
    install_requires=['six'],
    long_description="",
    entry_points={
        'console_scripts': [
            '@ = at:_main'
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
)
