from setuptools import setup, find_packages

setup(
    name='discolytics',
    version='2.0.0',
    author='Discolytics',
    author_email='collin@discolytics.com',
    description='Core python library for interfacing with Discolytics APIs',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/discolytics/discolytics-pycore',
    packages=find_packages(),
    install_requires=[
        'numpy>=1.19.2',
        'requests>=2.24.0',
        'pandas>=1.1.3'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
