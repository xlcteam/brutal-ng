#!/usr/bin/env python

import brutal

from setuptools import setup, find_packages

setup(
    name='brutal-ng',
    version=brutal.__version__,

    description='The new generation of brutal, a multi-network asynchronous' +
                'chat bot framework using twisted',
    long_description=open('README.rst').read(),

    author='XLC Team',
    author_email='contact@mail.xlc-team.info',

    url='https://github.com/xlcteam/brutal-ng',

    scripts=['brutal/bin/brutal-overlord.py', ],

    include_package_data=True,
    packages=find_packages(),

    license=open('LICENSE').read(),

    install_requires=[
        'Twisted >= 12.1.0',
        'wokkel == 0.7.1',
        'pyOpenSSL == 0.13',
        'service-identity == 14.0.0',
    ],

    keywords='twisted',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Framework :: Twisted',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Topic :: Communications :: Chat',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'License :: OSI Approved :: Apache Software License',
    ],
)
