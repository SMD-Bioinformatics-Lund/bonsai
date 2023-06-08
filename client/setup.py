from setuptools import setup, find_packages

setup(
   name='bonsai',
   version='0.1',
   description='Bonsai app',
   author='Markus Johansson',
   author_email='markus.johansson@me.com',
   packages=find_packages(),
   python_requires=">=3.6",
   install_requires=[
    'setuptools',
    'wheel',
    'Flask',
    "flask-login",
    "requests",
    "pydantic",
    "python-dateutil",
    "pydantic-factories",
    "jsonpath2"
   ],
   entry_points={
    "console_scripts": ["bonsai = app.cli:cli"]
   },
   scripts=[]
)
