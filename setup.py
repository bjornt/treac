from setuptools import setup

requires = ["bottle", "pysmbus"]

setup(
    name="treac",
    version="0.1",
    description="TREAC - The Treadmill Controller",
    py_modules=["treac"],
    include_package_data=True,
    zip_safe=True,
    test_suite="treac",
    install_requires=requires,
    entry_points={
        "console_scripts": [
            "treac = treac:main"
    ]})
