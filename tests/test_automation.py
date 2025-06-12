"""Tests for the automation module.

This module contains unit tests for the core automation functionality
including health detection, respawn management, and potion usage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from PIL import Image

from auto_snake.automation import (
    GameAutomation,
    HealthDetector,
    RespawnDetector,
    PotionManager,
    AutomationState,
)
from auto_snake.exceptions import AutoSnakeError, TemplateMatchError
from auto_snake.templates import TemplateManager
from auto_snake.input_control import InputController, ClickController


class TestAutomationState:
    """Test cases for AutomationState dataclass."""
    
    def test_automation_state_initialization(self):
        """Test AutomationState initializes with correct defaults."""
        state = AutomationState()
        
        assert state.empty_health_detected is False
        assert state.empty_health_count == 0
        assert state.last_empty_health_message == 0.0
        assert state.is_dead is False
        assert state.respawn_wait_start is None
        assert state.post_respawn_heal_time is None
        assert state.automation_running is False
        assert state.loop_count == 0


class TestHealthDetector:
    """Test cases for HealthDetector class."""
    
    @pytest.fixture
    def mock_template_manager(self):
        """Create a mock template manager."""
        manager = Mock(spec=TemplateManager)
        manager.has_health_templates.return_value = True
        manager.get_all_health_templates.return_value = {
            "20": np.ones((50, 100, 3), dtype=np.uint8) * 100,
            "50": np.ones((50, 100, 3), dtype=np.uint8) * 150,
            "full": np.ones((50, 100, 3), dtype=np.uint8) * 200,
        }
        manager.get_empty_health_template.return_value = np.ones((50, 100, 3), dtype=np.uint8) * 50
        return manager
    
    @pytest.fixture
    def health_detector(self, mock_template_manager):
        """Create HealthDetector instance with mocked dependencies."""
        return HealthDetector(mock_template_manager, debug_mode=True)
    
    @pytest.fixture
    def sample_screenshot(self):
        """Create a sample screenshot array."""
        return np.ones((800, 1200, 3), dtype=np.uint8) * 128
    
    def test_health_detector_initialization(self, mock_template_manager):
        """Test HealthDetector initializes correctly."""
        detector = HealthDetector(mock_template_manager, debug_mode=True)
        
        assert detector.template_manager == mock_template_manager
        assert detector.debug_mode is True
    
    def test_get_health_percentage_no_templates(self, sample_screenshot):
        """Test health percentage detection when no templates are loaded."""
        mock_manager = Mock(spec=TemplateManager)
        mock_manager.has_health_templates.return_value = False
        
        detector = HealthDetector(mock_manager, debug_mode=False)
        result = detector.get_health_percentage(sample_screenshot)
        
        assert result == 1.0
    
    @patch('cv2.matchTemplate')
    @patch('cv2.minMaxLoc')
    def test_get_health_percentage_success(
        self, 
        mock_minmaxloc, 
        mock_match_template, 
        health_detector, 
        sample_screenshot
    ):
        """Test successful health percentage detection."""
        # Mock OpenCV functions
        mock_match_template.return_value = np.array([[0.8]])
        mock_minmaxloc.return_value = (0.0, 0.8, (0, 0), (50, 25))
        
        result = health_detector.get_health_percentage(sample_screenshot)
        
        # Should return a valid percentage
        assert 0.0 <= result <= 1.0
    
    def test_is_health_empty_no_template(self, sample_screenshot):
        """Test empty health detection when no template is available."""
        mock_manager = Mock(spec=TemplateManager)
        mock_manager.get_empty_health_template.return_value = None
        mock_manager.has_health_templates.return_value = True
        mock_manager.get_all_health_templates.return_value = {
            "full": np.ones((50, 100, 3), dtype=np.uint8) * 200
        }
        
        detector = HealthDetector(mock_manager, debug_mode=False)
        
        with patch.object(detector, 'get_health_percentage', return_value=0.005):
            result = detector.is_health_empty(sample_screenshot)
            assert result is True
    
    @patch('cv2.matchTemplate')
    @patch('cv2.minMaxLoc')
    def test_is_health_empty_with_template(
        self, 
        mock_minmaxloc, 
        mock_match_template, 
        health_detector, 
        sample_screenshot
    ):
        """Test empty health detection with template matching."""
        # Mock high confidence match for empty health
        mock_match_template.return_value = np.array([[0.9]])
        mock_minmaxloc.return_value = (0.0, 0.9, (0, 0), (50, 25))
        
        result = health_detector.is_health_empty(sample_screenshot)
        assert result is True


class TestRespawnDetector:
    """Test cases for RespawnDetector class."""
    
    @pytest.fixture
    def mock_template_manager(self):
        """Create a mock template manager for respawn detection."""
        manager = Mock(spec=TemplateManager)
        manager.get_respawn_button_template.return_value = np.ones((40, 80, 3), dtype=np.uint8) * 180
        return manager
    
    @pytest.fixture
    def mock_click_controller(self):
        """Create a mock click controller."""
        return Mock(spec=ClickController)
    
    @pytest.fixture
    def respawn_detector(self, mock_template_manager, mock_click_controller):
        """Create RespawnDetector instance with mocked dependencies."""
        return RespawnDetector(mock_template_manager, mock_click_controller, debug_mode=True)
    
    @pytest.fixture
    def sample_screenshot(self):
        """Create a sample screenshot array."""
        return np.ones((800, 1200, 3), dtype=np.uint8) * 128
    
    def test_respawn_detector_initialization(self, mock_template_manager, mock_click_controller):
        """Test RespawnDetector initializes correctly."""
        detector = RespawnDetector(mock_template_manager, mock_click_controller, debug_mode=True)
        
        assert detector.template_manager == mock_template_manager
        assert detector.click_controller == mock_click_controller
        assert detector.debug_mode is True
    
    def test_detect_respawn_button_no_template(self, sample_screenshot):
        """Test respawn button detection when no template is available."""
        mock_manager = Mock(spec=TemplateManager)
        mock_manager.get_respawn_button_template.return_value = None
        mock_click = Mock(spec=ClickController)
        
        detector = RespawnDetector(mock_manager, mock_click, debug_mode=False)
        found, position = detector.detect_respawn_button(sample_screenshot)
        
        assert found is False
        assert position is None
    
    @patch('cv2.matchTemplate')
    @patch('cv2.minMaxLoc')
    def test_detect_respawn_button_success(
        self, 
        mock_minmaxloc, 
        mock_match_template, 
        respawn_detector, 
        sample_screenshot
    ):
        """Test successful respawn button detection."""
        # Mock high confidence match
        mock_match_template.return_value = np.array([[0.9]])
        mock_minmaxloc.return_value = (0.0, 0.9, (0, 0), (100, 50))
        
        found, position = respawn_detector.detect_respawn_button(sample_screenshot)
        
        assert found is True
        assert position == (140, 70)  # Center of 40x80 button at (100, 50)
    
    @patch('cv2.matchTemplate')
    @patch('cv2.minMaxLoc')
    def test_click_respawn_button_success(
        self, 
        mock_minmaxloc, 
        mock_match_template, 
        respawn_detector, 
        sample_screenshot
    ):
        """Test successful respawn button clicking."""
        # Mock high confidence match
        mock_match_template.return_value = np.array([[0.9]])
        mock_minmaxloc.return_value = (0.0, 0.9, (0, 0), (100, 50))
        
        result = respawn_detector.click_respawn_button(sample_screenshot)
        
        assert result is True
        respawn_detector.click_controller.click_at_position.assert_called_once()


class TestPotionManager:
    """Test cases for PotionManager class."""
    
    @pytest.fixture
    def mock_input_controller(self):
        """Create a mock input controller."""
        return Mock(spec=InputController)
    
    @pytest.fixture
    def potion_manager(self, mock_input_controller):
        """Create PotionManager instance with mocked dependencies."""
        return PotionManager(mock_input_controller, debug_mode=True)
    
    def test_potion_manager_initialization(self, mock_input_controller):
        """Test PotionManager initializes correctly."""
        manager = PotionManager(mock_input_controller, debug_mode=True)
        
        assert manager.input_controller == mock_input_controller
        assert manager.debug_mode is True
        assert manager.health_threshold == 0.5
    
    def test_use_health_potion_empty_health(self, potion_manager):
        """Test potion usage when health is empty."""
        result = potion_manager.use_health_potion(0.005)
        assert result == "empty"
    
    @patch('time.sleep')
    def test_use_health_potion_force_heal(self, mock_sleep, potion_manager):
        """Test forced healing mode."""
        result = potion_manager.use_health_potion(0.0, force_heal=True)
        
        assert result is True
        # Should press health potion 2 times for post-respawn healing
        assert potion_manager.input_controller.press_health_potion.call_count == 2
    
    @patch('time.sleep')
    def test_use_health_potion_critical_health(self, mock_sleep, potion_manager):
        """Test potion usage for critical health."""
        result = potion_manager.use_health_potion(0.15)  # 15% health
        
        assert result is True
        # Should use 4 potions for critical health
        assert potion_manager.input_controller.press_health_potion.call_count == 4
    
    @patch('time.sleep')
    def test_use_health_potion_low_health(self, mock_sleep, potion_manager):
        """Test potion usage for low health."""
        result = potion_manager.use_health_potion(0.35)  # 35% health
        
        assert result is True
        # Should use 2 potions for low health
        assert potion_manager.input_controller.press_health_potion.call_count == 2
    
    @patch('time.sleep')
    def test_use_health_potion_medium_health(self, mock_sleep, potion_manager):
        """Test potion usage for medium health."""
        result = potion_manager.use_health_potion(0.45)  # 45% health
        
        assert result is True
        # Should use 1 potion for medium health
        assert potion_manager.input_controller.press_health_potion.call_count == 1
    
    def test_use_health_potion_no_need(self, potion_manager):
        """Test no potion usage when health is sufficient."""
        result = potion_manager.use_health_potion(0.8)  # 80% health
        
        assert result is False
        potion_manager.input_controller.press_health_potion.assert_not_called()
    
    def test_set_health_threshold_valid(self, potion_manager):
        """Test setting valid health threshold."""
        potion_manager.set_health_threshold(0.3)
        assert potion_manager.health_threshold == 0.3
    
    def test_set_health_threshold_invalid(self, potion_manager):
        """Test setting invalid health threshold raises error."""
        with pytest.raises(ValueError):
            potion_manager.set_health_threshold(1.5)
        
        with pytest.raises(ValueError):
            potion_manager.set_health_threshold(-0.1)


class TestGameAutomation:
    """Test cases for main GameAutomation class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mocked dependencies for GameAutomation."""
        with patch('auto_snake.automation.TemplateManager') as mock_template_manager, \
             patch('auto_snake.automation.ScreenshotManager') as mock_screenshot_manager, \
             patch('auto_snake.automation.InputController') as mock_input_controller, \
             patch('auto_snake.automation.ClickController') as mock_click_controller, \
             patch('auto_snake.automation.AutomationController') as mock_automation_controller:
            
            # Configure template manager mock
            template_instance = mock_template_manager.return_value
            template_instance.load_all_templates.return_value = None
            template_instance.has_health_templates.return_value = True
            template_instance.get_template_info.return_value = {
                'health_templates_count': 3,
                'health_templates_loaded': ['20', '50', 'full'],
                'empty_health_loaded': True,
                'respawn_button_loaded': True,
            }
            
            # Configure input controller mock
            input_instance = mock_input_controller.return_value
            input_instance.get_key_bindings.return_value = {
                'health_potion_key': '1',
                'mana_potion_key': '2',
                'skill_keys': ['3', '4', '5', '6'],
            }
            
            yield {
                'template_manager': mock_template_manager,
                'screenshot_manager': mock_screenshot_manager,
                'input_controller': mock_input_controller,
                'click_controller': mock_click_controller,
                'automation_controller': mock_automation_controller,
            }
    
    def test_game_automation_initialization(self, mock_dependencies):
        """Test GameAutomation initializes correctly."""
        automation = GameAutomation(debug_mode=True)
        
        assert automation.debug_mode is True
        assert isinstance(automation.state, AutomationState)
        assert automation.state.automation_running is False
    
    def test_game_automation_initialization_with_custom_params(self, mock_dependencies):
        """Test GameAutomation initialization with custom parameters."""
        automation = GameAutomation(
            debug_mode=False,
            images_path="custom/path",
            health_threshold=0.3
        )
        
        assert automation.debug_mode is False
    
    def test_game_automation_template_load_failure(self):
        """Test GameAutomation handles template loading failure."""
        with patch('auto_snake.automation.TemplateManager') as mock_template_manager:
            template_instance = mock_template_manager.return_value
            template_instance.load_all_templates.side_effect = Exception("Template load failed")
            
            with pytest.raises(AutoSnakeError) as exc_info:
                GameAutomation(debug_mode=False)
            
            assert "Template loading failed" in str(exc_info.value)
    
    def test_use_skill(self, mock_dependencies):
        """Test skill usage functionality."""
        automation = GameAutomation(debug_mode=False)
        automation.use_skill(2)
        
        automation.input_controller.press_skill.assert_called_once_with(2)
    
    def test_set_health_threshold(self, mock_dependencies):
        """Test setting health threshold."""
        automation = GameAutomation(debug_mode=False)
        automation.set_health_threshold(0.3)
        
        automation.potion_manager.set_health_threshold.assert_called_once_with(0.3)
    
    def test_get_automation_info(self, mock_dependencies):
        """Test getting automation information."""
        automation = GameAutomation(debug_mode=False)
        info = automation.get_automation_info()
        
        assert 'template_info' in info
        assert 'key_bindings' in info
        assert 'state' in info
        assert 'debug_mode' in info
        assert info['debug_mode'] is False


class TestIntegration:
    """Integration tests for automation components."""
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample PIL image for testing."""
        return Image.new('RGB', (800, 600), color='red')
    
    @patch('auto_snake.automation.pyautogui')
    def test_full_automation_cycle_mock(self, mock_pyautogui, sample_image):
        """Test a full automation cycle with mocked components."""
        # This test would require extensive mocking and is more suitable
        # for integration testing in a separate test suite
        pass


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def sample_templates():
    """Create sample template images for testing."""
    templates = {}
    for name in ["20", "40", "50", "full", "empty"]:
        # Create simple colored rectangles as templates
        color_value = {"20": 50, "40": 100, "50": 150, "full": 200, "empty": 30}[name]
        templates[name] = np.ones((50, 100, 3), dtype=np.uint8) * color_value
    return templates


def test_module_imports():
    """Test that all required modules can be imported."""
    from auto_snake.automation import GameAutomation
    from auto_snake.templates import TemplateManager
    from auto_snake.screenshot import ScreenshotManager
    from auto_snake.input_control import InputController
    from auto_snake.exceptions import AutoSnakeError
    
    # If we get here, all imports succeeded
    assert True