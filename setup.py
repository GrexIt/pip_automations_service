import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="automations_get_actions",
    version="0.0.1",
    author="Raghav CS",
    author_email="raghav@grexit.com",
    description="A small pip package to get automation contidions from Redis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GrexIt/pip_automation_actions",
    packages=setuptools.find_packages(),
    license='unlicense',
    install_requires=[
        'redis',
    ],
)
