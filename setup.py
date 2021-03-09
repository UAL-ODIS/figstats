from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fr:
    requirements = fr.read().splitlines()

setup(
    name='figstats',
    version='v0.0.1',
    packages=['figstats'],
    url='https://github.com/UAL-ODIS/figstats',
    license='MIT License',
    author='Chun Ly',
    author_email='astro.chun@gmail.com',
    description='Python tool to retrieve stats from Figshare API',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=requirements
)
