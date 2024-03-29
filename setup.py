from setuptools import setup, find_packages

setup(name='ztwit',
      version='0.7',
      py_modules=['ztwitgw', 'zpost', 'lengthener'],
      packages=find_packages(),
      install_requires=[
          "tweepy",
      ],
      description='Zephyr/Twitter Gateway Tools',
      author='Mark Eichin',
      author_email='eichin@thok.org',
      url='http://thok.org/intranet/python/ztwit/README.html',
      )
