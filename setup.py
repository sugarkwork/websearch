import setuptools

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="ai_web_search",
    version="0.1",
    install_requires=requirements,
    packages=setuptools.find_packages(),
    description="A search tool for AI-based web data",
    author="sugarkwork",
    python_requires='>=3.10',
)
