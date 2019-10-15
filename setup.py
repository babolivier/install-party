import os
import setuptools


def read_file(path_segments):
    """Read a file from the package. Takes a list of strings to join to
    make the path"""
    file_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), *path_segments
    )
    with open(file_path) as f:
        return f.read()


def exec_file(path_segments):
    """Execute a single python file to get the variables defined in it"""
    result = {}
    code = read_file(path_segments)
    exec(code, result)
    return result


version = exec_file(("install_party", "__init__.py"))["__version__"]
long_description = read_file(("README.md",))

setuptools.setup(
    name='install-party',
    version=version,
    author="Brendan Abolivier",
    author_email="babolivier@matrix.org",
    description="Instantiate and manage hosts for Matrix homeserver install parties",
    install_requires=[
        "ovh==0.5.0",
        "python-novaclient==15.1.0",
        "PyYAML==5.1.2",
        "requests==2.22.0",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/babolivier/install-party",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.5",
    data_files=[
        ("scripts", ["scripts/post_create.sh"])
    ],
)
