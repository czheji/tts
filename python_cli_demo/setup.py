from setuptools import setup, find_packages

setup(
    name = "ttsDemo",
    version = "0.2",
    description = "Azuru tts Command line Demo",
    author = "czj",
    packages = ['pkg'],
    platforms = "any",
    install_requires = [
        'requests',
        'websockets',
        'pyyaml',
        'mako',
        'pydub'
    ],
    entry_points = {
        "console_scripts": ['mstts = pkg.tts:cmd'] 
    }
)