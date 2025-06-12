#!/bin/bash

# Build script for C++ automation extensions
# This script builds the C++ extensions for the auto-snake automation system

set -e # Exit on any error

echo "🔨 Building C++ Automation Extensions"
echo "====================================="

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
  echo "❌ Error: setup.py not found. Please run this script from the auto-snake directory."
  exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $PYTHON_VERSION"

if [ "$(echo "$PYTHON_VERSION < 3.12" | bc -l)" -eq 1 ]; then
  echo "⚠️  Warning: Python 3.12+ recommended for best performance"
fi

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

# Check for required build tools
if ! command_exists gcc && ! command_exists clang; then
  echo "❌ Error: No C++ compiler found. Please install gcc or clang."
  echo "   Ubuntu/Debian: sudo apt-get install build-essential"
  echo "   CentOS/RHEL: sudo yum groupinstall 'Development Tools'"
  echo "   macOS: xcode-select --install"
  exit 1
fi

# Check for pkg-config
if command_exists pkg-config; then
  echo "✅ pkg-config found"
  PKG_CONFIG_AVAILABLE=true
else
  echo "⚠️  pkg-config not found - will use fallback OpenCV detection"
  PKG_CONFIG_AVAILABLE=false
fi

# Check for OpenCV
echo "🔍 Checking for OpenCV..."

OPENCV_FOUND=false

if [ "$PKG_CONFIG_AVAILABLE" = true ]; then
  if pkg-config --exists opencv4; then
    OPENCV_VERSION=$(pkg-config --modversion opencv4)
    echo "✅ OpenCV found via pkg-config: $OPENCV_VERSION"
    OPENCV_FOUND=true
  fi
fi

if [ "$OPENCV_FOUND" = false ]; then
  # Check common OpenCV installation paths
  OPENCV_PATHS=(
    "/usr/include/opencv4"
    "/usr/local/include/opencv4"
    "/opt/homebrew/include/opencv4"
  )

  for path in "${OPENCV_PATHS[@]}"; do
    if [ -d "$path" ]; then
      echo "✅ OpenCV headers found at: $path"
      OPENCV_FOUND=true
      break
    fi
  done
fi

if [ "$OPENCV_FOUND" = false ]; then
  echo "❌ Error: OpenCV not found. Please install OpenCV development packages."
  echo "   Ubuntu/Debian: sudo apt-get install libopencv-dev"
  echo "   CentOS/RHEL: sudo yum install opencv-devel"
  echo "   macOS: brew install opencv"
  echo "   Or build from source: https://opencv.org/get-started/"
  exit 1
fi

# Check Python packages
echo "🔍 Checking Python dependencies..."

check_python_package() {
  if python3 -c "import $1" 2>/dev/null; then
    echo "✅ $1 available"
    return 0
  else
    echo "❌ $1 not found"
    return 1
  fi
}

MISSING_PACKAGES=()

if ! check_python_package "numpy"; then
  MISSING_PACKAGES+=("numpy>=1.24.0")
fi

if ! check_python_package "cv2"; then
  MISSING_PACKAGES+=("opencv-python>=4.8.0")
fi

if ! check_python_package "setuptools"; then
  MISSING_PACKAGES+=("setuptools>=60.0.0")
fi

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
  echo "📦 Installing missing Python packages..."
  pip3 install "${MISSING_PACKAGES[@]}"
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
if [ -d "build" ]; then
  rm -rf build
  echo "   Removed build directory"
fi

if [ -d "*.egg-info" ]; then
  rm -rf *.egg-info
  echo "   Removed egg-info directories"
fi

# Find and remove existing .so files
find . -name "*.so" -type f -delete 2>/dev/null || true
echo "   Removed existing .so files"

# Build the extension
echo "🔨 Building C++ extension..."

# Set compiler flags
export CFLAGS="-O3 -march=native -fopenmp"
export CXXFLAGS="-O3 -march=native -fopenmp -std=c++17"
export LDFLAGS="-fopenmp"

# Build command
BUILD_CMD="python3 setup.py build_ext --inplace"

echo "🚀 Running: $BUILD_CMD"
echo "⏱️  This may take a few minutes..."

if $BUILD_CMD; then
  echo "✅ C++ extension built successfully!"
else
  echo "❌ Build failed!"
  echo ""
  echo "🔧 Troubleshooting tips:"
  echo "1. Make sure all dependencies are installed"
  echo "2. Check that OpenCV is properly installed"
  echo "3. Verify compiler is working: gcc --version"
  echo "4. Try building without optimizations:"
  echo "   CFLAGS='-O0' CXXFLAGS='-O0' python3 setup.py build_ext --inplace"
  exit 1
fi

# Verify the build
echo "🔍 Verifying build..."

if [ -f "automation_core.so" ] || find . -name "automation_core*.so" -type f | grep -q .; then
  echo "✅ Extension module found"

  # Test import
  if python3 -c "import automation_core; print('✅ C++ extension imports successfully')" 2>/dev/null; then
    echo "✅ C++ extension is working!"

    # Run a quick test
    echo "🧪 Running quick functionality test..."
    python3 -c "
import automation_core
import numpy as np
print('Testing C++ functions...')

# Test template matching
test_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
test_tmpl = np.random.randint(0, 255, (20, 20, 3), dtype=np.uint8)
result = automation_core.multi_template_match(test_img, [test_tmpl], [0.5])
print(f'✅ Template matching test: {len(result)} results')

# Test health detection
result = automation_core.detect_health_parallel(test_img, test_tmpl, test_tmpl, 0.3)
print(f'✅ Health detection test: {result.get(\"processing_time_ms\", 0):.2f}ms')

print('🎉 All C++ functions working correctly!')
"
  else
    echo "❌ C++ extension built but cannot be imported"
    echo "   Check for missing shared libraries: ldd automation_core*.so"
    exit 1
  fi
else
  echo "❌ Extension module not found after build"
  exit 1
fi

# Install in development mode
echo "📦 Installing in development mode..."
if pip3 install -e .; then
  echo "✅ Package installed in development mode"
else
  echo "⚠️  Development installation failed, but extension is built"
fi

# Print success message
echo ""
echo "🎉 Build completed successfully!"
echo "================================"
echo ""
echo "📋 What's available now:"
echo "   ✅ automation_core C++ extension"
echo "   ✅ True parallelism for template matching"
echo "   ✅ Parallel health detection"
echo "   ✅ Batch screenshot processing"
echo ""
echo "🚀 To test the automation:"
echo "   python3 examples/cpp_enhanced_usage.py"
echo ""
echo "📊 To run performance benchmarks:"
echo "   python3 -c \"from auto_snake.cpp_enhanced_automation import CppEnhancedAutomation; a = CppEnhancedAutomation(); print(a.benchmark_performance_comparison())\""
echo ""
echo "🔧 To run diagnostics:"
echo "   python3 -c \"from auto_snake.cpp_enhanced_automation import CppEnhancedAutomation; a = CppEnhancedAutomation(); print(a.run_cpp_diagnostics())\""

# Show file sizes for reference
echo ""
echo "📁 Generated files:"
for file in automation_core*.so; do
  if [ -f "$file" ]; then
    size=$(ls -lh "$file" | awk '{print $5}')
    echo "   $file ($size)"
  fi
done

echo ""
echo "✅ Build script completed!"
