"""Setup configuration for the auto-snake package."""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split("\n")
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith("#")]

setup(
    name="auto-snake",
    version="1.0.0",
    author="Cyber-syntax",
    author_email="",
    description="Game automation tool for health monitoring and respawn management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cyber-syntax/auto-snake",
    project_urls={
        "Bug Reports": "https://github.com/cyber-syntax/auto-snake/issues",
        "Source": "https://github.com/cyber-syntax/auto-snake",
        "Documentation": "https://github.com/cyber-syntax/auto-snake/blob/main/docs/",
    },
    package_dir={"": "auto_snake"},
    packages=find_packages(where="auto_snake"),
    python_requires=">=3.10",
    install_requires=[
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "Pillow>=10.0.0",
        "pyautogui>=0.9.54",
        "pynput>=1.7.6",
        "PyYAML>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "ruff>=0.11.12",
            "isort>=5.12.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
            "sphinx-autodoc-typehints>=1.24.0",
        ],
        "test": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "hypothesis>=6.82.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "auto-snake=auto_snake.main:cli_entry_point",
            "auto-snake-gui=auto_snake.gui:main",  # Future GUI entry point
        ],
    },
    include_package_data=True,
    package_data={
        "auto_snake": [
            "config/*.yaml",
            "templates/*.png",
        ],
    },
    zip_safe=False,
    keywords=[
        "automation",
        "gaming",
        "health-monitoring",
        "opencv",
        "computer-vision",
        "game-automation",
        "respawn-detection",
        "educational",
    ],
    license="BSD-3-Clause",
)
