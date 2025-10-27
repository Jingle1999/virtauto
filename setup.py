from pathlib import Path
from setuptools import setup, find_packages

README = (Path(__file__).parent / "README.md")
long_desc = README.read_text(encoding="utf-8") if README.exists() else "virtauto – agents & ops"

setup(
    name="virtauto",
    version="0.1.0",
    description="virtauto – Self-Agents, ops tools, and site automations",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    author="virtauto",
    python_requires=">=3.11",
    packages=find_packages(include=["tools", "tools.*", "scripts", "scripts.*"]),
    include_package_data=True,
    install_requires=[
        "requests>=2.32,<3",
        "pydantic>=2,<3",
        "python-dateutil>=2.9,<3",
        "PyYAML>=6,<7",
        "Jinja2>=3.1,<4",
        "beautifulsoup4>=4.12,<5",
        "lxml>=5,<6",
        "readability-lxml>=0.8,<0.9",
        "markdownify>=0.12,<0.13",
        "tqdm>=4,<5",
        "rich>=13,<14",
        "orjson>=3,<4",
        # "google-api-python-client>=2,<3",  # optional
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
