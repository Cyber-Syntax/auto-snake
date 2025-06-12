"""Setup script for building C++ automation extensions."""

import os
from pathlib import Path

import numpy
from setuptools import Extension, find_packages, setup

try:
    import pkg_config

    PKG_CONFIG_AVAILABLE = True
except ImportError:
    PKG_CONFIG_AVAILABLE = False
    print("Warning: pkg-config not available, using fallback OpenCV detection")


# Function to find OpenCV
def find_opencv():
    """Find OpenCV installation paths."""
    opencv_paths = {"include_dirs": [], "library_dirs": [], "libraries": []}

    # Try pkg-config first
    if PKG_CONFIG_AVAILABLE:
        try:
            opencv_flags = pkg_config.parse("opencv4")
            opencv_paths["include_dirs"].extend(opencv_flags["include_dirs"])
            opencv_paths["library_dirs"].extend(opencv_flags["library_dirs"])
            opencv_paths["libraries"].extend(opencv_flags["libraries"])
            print("Found OpenCV using pkg-config")
            return opencv_paths
        except:
            pass

    # Common OpenCV installation paths
    common_include_paths = [
        "/usr/include/opencv4",
        "/usr/local/include/opencv4",
        "/opt/homebrew/include/opencv4",  # macOS Homebrew
        "/usr/include/opencv4/opencv2",
        "/usr/local/include/opencv4/opencv2",
        "/usr/share/opencv4" # Linux
    ]

    common_lib_paths = [
        "/usr/lib",
        "/usr/local/lib",
        "/usr/lib/x86_64-linux-gnu",
        "/usr/lib/aarch64-linux-gnu",
        "/opt/homebrew/lib",  # macOS Homebrew
    ]

    # Find include directories
    for path in common_include_paths:
        if os.path.exists(path):
            opencv_paths["include_dirs"].append(path)
            break

    # Find library directories
    for path in common_lib_paths:
        if os.path.exists(path):
            opencv_paths["library_dirs"].append(path)

    # OpenCV libraries
    opencv_paths["libraries"] = [
        "opencv_core",
        "opencv_imgproc",
        "opencv_imgcodecs",
        "opencv_highgui",
        "opencv_features2d",
    ]

    return opencv_paths


# Get OpenCV paths
opencv_info = find_opencv()

# Define the C++ extension
cpp_extension = Extension(
    "automation_core",
    sources=[
        "cpp_extensions/automation_core.cpp",
    ],
    include_dirs=[
        numpy.get_include(),
        *opencv_info["include_dirs"],
    ],
    libraries=opencv_info["libraries"],
    library_dirs=opencv_info["library_dirs"],
    extra_compile_args=[
        "-std=c++17",
        "-O3",
        "-march=native",  # Optimize for your CPU
        "-fopenmp",  # Enable OpenMP for additional parallelism
        "-fPIC",  # Position independent code
        "-Wall",  # Enable warnings
        "-Wextra",  # Extra warnings
    ],
    extra_link_args=[
        "-fopenmp",
        "-lpthread",  # Threading support
    ],
    language="c++",
    define_macros=[
        ("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION"),
    ],
)

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split("\n")
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith("#")]

# Add C++ extension requirements
cpp_requirements = [
    "numpy>=1.24.0",
    "opencv-python>=4.8.0",
]

# Ensure we have the basic requirements even if requirements.txt doesn't exist
if not requirements:
    requirements = [
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "Pillow>=10.0.0",
        "pyautogui>=0.9.54",
        "pynput>=1.7.6",
        "PyYAML>=6.0",
    ]

for req in cpp_requirements:
    if not any(req.split(">=")[0] in existing_req for existing_req in requirements):
        requirements.append(req)

setup(
    name="auto-snake-cpp",
    version="1.0.0",
    author="Cyber-syntax",
    author_email="",
    description="High-performance C++ enhanced game automation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cyber-syntax/auto-snake",
    project_urls={
        "Bug Reports": "https://github.com/cyber-syntax/auto-snake/issues",
        "Source": "https://github.com/cyber-syntax/auto-snake",
        "Documentation": "https://github.com/cyber-syntax/auto-snake/blob/main/docs/",
    },
    packages=find_packages(),
    ext_modules=[cpp_extension],
    python_requires=">=3.12",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
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
        "cpp": [
            "setuptools>=60.0.0",
            "wheel>=0.37.0",
            "Cython>=0.29.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "auto-snake=auto_snake.main:cli_entry_point",
            "auto-snake-cpp=auto_snake.cpp_enhanced_main:main",
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
        "cpp-extensions",
        "performance",
        "parallelism",
    ],
    license="BSD-3-Clause",
)
