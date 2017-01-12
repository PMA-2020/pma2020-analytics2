from distutils.core import setup


from analytics import __version__


setup(
    name='analytics',
    version=__version__,
    author='James K. Pringle',
    author_email='jpringle@jhu.edu',
    url='http://www.pma2020.org',
    packages=[
        'analytics',
        'analytics.formdata'
    ],
    package_data={
        'analytics.formdata': ['*.json']
    },
    license='LICENSE.txt',
    description='Utility to produce intermediate dataset from all logs',
    long_description=open('README.md').read()
)
