import codecs
import setuptools

with codecs.open('requirements.txt', 'r', encoding='utf-16') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="ai_web_search",
    version="0.3.1",
    install_requires=requirements,
    packages=setuptools.find_packages(),
    description="A search tool for AI-based web data",
    author="sugarkwork",
    python_requires='>=3.10',
)
