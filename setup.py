from setuptools import find_packages, setup

setup(
    name='pathlib-extensions',
    version='0.0.1',
    description="Utilities to make working with Python's built-in pathlib easier.",
    author='Libo Yin',
    author_email='liboyin830@gmail.com',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=[],
    extras_require={
        # mypy might also require types-setuptools
        'dev': ['mypy', 'pytest', 'pytest-cov', 'pytest-randomly'],
    },
)
