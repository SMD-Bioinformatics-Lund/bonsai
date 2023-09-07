from setuptools import setup, find_packages

setup(
   name='bonsai_api',
   version='0.1',
   description='Bonsai REST api',
   author='Markus Johansson',
   author_email='markus.johansson@me.com',
   packages=find_packages(),
   python_requires=">=3.6",
   install_requires=[
    'setuptools',
    'wheel',
    'click',
    "motor",
    "fastapi[all]",
    "uvicorn[standard]",
    "python-jose[cryptography]",
    "python-multipart",
    "passlib",
    "ldap3",
    "pandas",
    "sourmash",
    "biopython",
    "scipy",
    "scikit-bio",
    "pydantic-factories"
   ],
   entry_points={
    "console_scripts": ["bonsai_api = app.cli:cli"]
   },
)
