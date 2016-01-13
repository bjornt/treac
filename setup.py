from setuptools import setup

requires = ["Flask", "flask-socketio", "eventlet", "pysmbus"]

setup(
    name="treac",
    version="0.1",
    description="TREAC - The Treadmill Controller",
    packages=["treac"],
    package_dir={"": "."},
    include_package_data=True,
    package_data={"": ["html/*"]},
    test_suite="treac",
    install_requires=requires,
    entry_points={
        "console_scripts": [
            "treac = treac:main"
    ]})
