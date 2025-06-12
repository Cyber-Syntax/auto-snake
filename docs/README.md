# Auto Snake Game Automation Documentation

## Overview

Auto Snake is a sophisticated game automation system designed for educational purposes. It provides intelligent health monitoring, automatic potion usage, respawn detection, and character revival management using computer vision and template matching techniques.

## Features

### Core Functionality
- **Smart Health Monitoring**: Uses template matching to detect health bar levels
- **Intelligent Potion Usage**: Automatically uses health potions based on health percentage
- **Respawn Detection**: Detects character death and automatically handles respawn
- **Cross-Platform Support**: Works on Linux (with scrot), Windows, and macOS
- **Modular Architecture**: Clean separation of concerns with dedicated modules

### Advanced Features
- **Multi-Level Potion Strategy**: Different potion quantities based on health severity
- **Post-Respawn Healing**: Automatic healing sequence after character revival
- **Debug Mode**: Comprehensive logging and screenshot saving for troubleshooting
- **Template Validation**: Robust template loading with fallback mechanisms
- **Safety Features**: Built-in failsafe mechanisms and error handling

## Architecture

The system follows modern Python practices with a clean, modular architecture:

```
auto-snake/
├── src/auto_snake/          # Main package
│   ├── __init__.py          # Package initialization
│   ├── automation.py        # Core automation logic
│   ├── constants.py         # Configuration constants
│   ├── exceptions.py        # Custom exception classes
│   ├── input_control.py     # Keyboard/mouse input handling
│   ├── main.py             # CLI entry point
│   ├── screenshot.py        # Screenshot utilities
│   └── templates.py         # Template management
├── config/                  # Configuration files
├── docs/                   # Documentation
├── tests/                  # Unit tests
└── images/                 # Template images (user-provided)
```

## Installation

### Prerequisites
- Python 3.10 or higher
- Required template images (see Template Setup section)

### Using pip (Recommended)
```bash
# Clone the repository
git clone https://github.com/cyber-syntax/auto-snake.git
cd auto-snake

# Install in development mode
pip install -e .

# Or install with optional dependencies
pip install -e .[dev,test,docs]
```

### Manual Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run from source
python -m auto_snake.main
```

## Template Setup

The system requires template images for health bar detection and respawn button recognition. Create an `images/` directory in your project root with the following files:

### Required Templates

#### Health Bar Templates
- `20_health_bar.png` - Health bar at 20%
- `40_health_bar.png` - Health bar at 40%
- `50_health_bar.png` - Health bar at 50%
- `full_health_bar.png` - Full health bar
- `empty_health_bar.png` - Empty health bar (character dead)

#### Respawn System
- `respawn_button.png` - Respawn/revival button

### Creating Templates

1. **Take Screenshots**: Capture screenshots of your game showing different health levels
2. **Crop Templates**: Use an image editor to crop just the health bar portion
3. **Save as PNG**: Save templates in PNG format for best quality
4. **Test Templates**: Run the system in debug mode to verify template matching

### Template Guidelines

- **Consistent Size**: Keep templates roughly the same size
- **Clear Images**: Ensure templates are clear and not blurry
- **Proper Lighting**: Capture templates under normal game lighting
- **Minimal Background**: Include minimal background in templates

## Usage

### Basic Usage

```bash
# Run with default settings
auto-snake

# Enable debug mode
auto-snake --debug

# Custom health threshold (30%)
auto-snake --health-threshold 0.3

# Custom images directory
auto-snake --images-path ./my_templates
```

### Controls

- **R Key**: Start/restart automation
- **Q Key**: Quit automation
- **Mouse**: Move to any corner to trigger PyAutoGUI failsafe

### Configuration

The system can be configured through:

1. **Command Line Arguments**: Override defaults for single runs
2. **Configuration File**: `config/automation.yaml` for persistent settings
3. **Environment Variables**: For system-wide settings

## API Reference

### GameAutomation Class

Main automation controller that orchestrates all functionality.

```python
from auto_snake import GameAutomation

# Initialize automation
automation = GameAutomation(
    debug_mode=False,
    images_path="./images",
    health_threshold=0.5
)

# Run automation
automation.run_automation()

# Use specific skill
automation.use_skill(skill_index=2)

# Get system information
info = automation.get_automation_info()
```

### Key Components

#### HealthDetector
Handles health bar detection and analysis.

```python
from auto_snake.automation import HealthDetector

detector = HealthDetector(template_manager, debug_mode=True)
health_percent = detector.get_health_percentage(screenshot_array)
is_empty = detector.is_health_empty(screenshot_array)
```

#### PotionManager
Manages intelligent potion usage based on health levels.

```python
from auto_snake.automation import PotionManager

manager = PotionManager(input_controller, debug_mode=True)
result = manager.use_health_potion(health_percent=0.3)
manager.set_health_threshold(0.4)
```

#### RespawnDetector
Handles respawn button detection and clicking.

```python
from auto_snake.automation import RespawnDetector

detector = RespawnDetector(template_manager, click_controller)
found, position = detector.detect_respawn_button(screenshot_array)
success = detector.click_respawn_button(screenshot_array)
```

## Configuration

### Default Settings

The system comes with sensible defaults in `auto_snake/constants.py`:

- **Health Threshold**: 50% (use potions when health drops below)
- **Critical Health**: 20% (use 4 potions)
- **Low Health**: 40% (use 2 potions)
- **Medium Health**: 50% (use 1 potion)
- **Respawn Wait**: 7.5 seconds before clicking respawn button

### Customization

#### Key Bindings
```python
# Default key bindings
HEALTH_POTION_KEY = "1"
MANA_POTION_KEY = "2"  # Future feature
SKILL_KEYS = ["3", "4", "5", "6"]
```

#### Timing Settings
```python
# Timing constants (seconds)
POTION_EFFECT_WAIT = 1.5
RESPAWN_WAIT_DURATION = 7.5
POST_RESPAWN_HEAL_DURATION = 3.0
AUTOMATION_LOOP_DELAY = 2.0
```

#### Template Matching
```python
# Confidence thresholds
MIN_TEMPLATE_CONFIDENCE = 0.3
EMPTY_HEALTH_CONFIDENCE = 0.7
RESPAWN_BUTTON_CONFIDENCE = 0.8
```

## Debugging

### Debug Mode

Enable debug mode for detailed logging and troubleshooting:

```bash
auto-snake --debug
```

Debug mode provides:
- Detailed console logging
- Screenshot saving for analysis
- Template matching scores
- Timing information
- Error stack traces

### Debug Files

When debug mode is enabled, the system saves:
- `debug_screenshot.png` - Current screen capture
- `debug_region_*.png` - Test regions for template matching
- Console logs with detailed information

### Common Issues

#### Template Not Found
**Problem**: "Template file not found" error
**Solution**: 
- Verify `images/` directory exists
- Check template file names match exactly
- Ensure PNG format is used

#### Low Template Confidence
**Problem**: Templates not matching reliably
**Solution**:
- Recapture templates under current game conditions
- Adjust `MIN_TEMPLATE_CONFIDENCE` in constants.py
- Check game resolution and scaling

#### Permission Errors (Linux)
**Problem**: Screenshot capture fails
**Solution**:
- Install scrot: `sudo apt-get install scrot`
- Grant necessary permissions
- Run from terminal, not as background process

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/cyber-syntax/auto-snake.git
cd auto-snake

# Install with development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Format code
black src/
isort src/

# Type checking
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=auto_snake

# Run specific test file
pytest tests/test_automation.py

# Run with verbose output
pytest -v
```

### Code Quality

The project follows strict code quality standards:

- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Static type checking
- **flake8**: Linting
- **pytest**: Unit testing

### Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Follow code style guidelines
6. Submit a pull request

## Safety and Legal

### Educational Purpose

This software is created for **educational purposes only**. It demonstrates:
- Computer vision techniques
- Template matching algorithms
- Automation system design
- Modern Python development practices

### Responsible Use

- **Respect Terms of Service**: Ensure automation complies with game ToS
- **Fair Play**: Don't use for competitive advantage
- **Learning Focus**: Use as a learning tool for automation concepts
- **Testing Environment**: Test in appropriate environments only

### Disclaimers

- The authors are not responsible for any consequences of using this software
- Users must comply with applicable terms of service and laws
- This tool should not be used to gain unfair advantages in games
- Always respect intellectual property rights

## Troubleshooting

### Common Error Messages

#### "No health templates loaded"
- Check that `images/` directory exists
- Verify template files are present and correctly named
- Ensure files are valid PNG images

#### "Screenshot capture failed"
- On Linux: Install scrot (`sudo apt-get install scrot`)
- Check display permissions
- Verify display server is running

#### "Template matching failed"
- Game resolution may have changed
- Recapture templates under current conditions
- Check template file integrity

#### "Key press failed"
- Verify game window has focus
- Check keyboard permissions
- Ensure input simulation is allowed

### Performance Optimization

#### Reduce CPU Usage
- Disable debug mode for production use
- Increase `AUTOMATION_LOOP_DELAY` for less frequent checks
- Use smaller template images when possible

#### Improve Accuracy
- Capture templates at current game resolution
- Use high-quality, clear template images
- Adjust confidence thresholds in configuration

## FAQ

### Q: Can this be used with any game?
A: The system is designed to be game-agnostic, but requires appropriate template images for each specific game's UI elements.

### Q: Does this work on all operating systems?
A: Yes, it supports Windows, macOS, and Linux. Linux users need to install `scrot` for optimal screenshot performance.

### Q: How accurate is the health detection?
A: Accuracy depends on template quality and game conditions. With good templates, accuracy is typically >95%.

### Q: Can I modify the key bindings?
A: Yes, key bindings can be customized in the configuration or by modifying the constants file.

### Q: Is there a GUI version?
A: Currently, only a command-line interface is available. A GUI version is planned for future releases.

### Q: How do I add new health levels?
A: Add new template files to the images directory and update the `HEALTH_TEMPLATE_FILES` configuration accordingly.

## Version History

### Version 1.0.0
- Initial release with core automation features
- Health monitoring and potion usage
- Respawn detection and handling
- Cross-platform support
- Comprehensive test suite
- Modern Python architecture

## License

This project is licensed under the BSD 3-Clause License. See the LICENSE file for details.

## Contact

- **GitHub**: [cyber-syntax/auto-snake](https://github.com/cyber-syntax/auto-snake)
- **Issues**: Report bugs and feature requests on GitHub Issues
- **Discussions**: Use GitHub Discussions for questions and community support

---

**Note**: This software is provided as-is for educational purposes. Please use responsibly and in accordance with applicable terms of service and laws.