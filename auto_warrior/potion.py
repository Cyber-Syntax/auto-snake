import logging
import time

from auto_warrior.constants import (
    CRITICAL_HEALTH_THRESHOLD,
    DEFAULT_HEALTH_THRESHOLD,
    EMERGENCY_HEALING_WAIT,
    LOW_HEALTH_THRESHOLD,
    MULTIPLE_POTION_DELAY,
    POST_RESPAWN_POTION_DELAY,
    POST_RESPAWN_WAIT,
    POTION_EFFECT_WAIT,
    POTION_USAGE_MAP,
)
from auto_warrior.input_control import InputController

logger = logging.getLogger(__name__)

class PotionManager:
    """Manages potion usage based on health levels."""

    def __init__(self, input_controller: InputController, debug_mode: bool = False) -> None:
        """Initialize potion manager.

        Args:
            input_controller: Input controller for key presses
            debug_mode: Whether to enable debug logging
        """
        self.input_controller = input_controller
        self.debug_mode = debug_mode
        self.health_threshold = DEFAULT_HEALTH_THRESHOLD

    def use_health_potion(
        self, health_percent: float, force_heal: bool = False, emergency_mode: bool = False
    ) -> bool | str:
        """Use health potion based on health percentage.

        Args:
            health_percent: Current health percentage (0.0 to 1.0)
            force_heal: Whether to force healing (post-respawn)
            emergency_mode: Whether this is emergency healing (don't return "empty")

        Returns:
            True if potions were used, False if not needed, "empty" if health is empty (non-emergency only)
        """
        if self.debug_mode:
            logger.debug(
                f"Checking health status: {health_percent:.2%} (emergency: {emergency_mode})"
            )

        if force_heal:
            return self._force_heal()

        # Check if health is effectively empty - but not during emergency mode
        if health_percent <= 0.01 and not emergency_mode:
            return "empty"

        # Determine potion usage
        potions_needed = self._calculate_potions_needed(health_percent)

        # In emergency mode, always use at least some potions if health is very low
        if emergency_mode and health_percent <= 0.05 and potions_needed == 0:
            potions_needed = POTION_USAGE_MAP["emergency"]
            if self.debug_mode:
                logger.debug(
                    f"Emergency mode: forcing {potions_needed} potions for critical health"
                )

        if potions_needed > 0:
            return self._use_multiple_potions(potions_needed, health_percent)

        if self.debug_mode:
            logger.debug(
                f"Health {health_percent:.2%} > {self.health_threshold:.2%}, no potion needed"
            )

        return False

    def _force_heal(self) -> bool:
        """Force healing mode for post-respawn.

        Returns:
            True indicating potions were used
        """
        potions_to_use = POTION_USAGE_MAP["post_respawn"]
        print(f"Post-respawn healing: Using {potions_to_use} health potion(s)...")

        for i in range(potions_to_use):
            if self.debug_mode:
                logger.debug(f"Pressing potion {i + 1}/{potions_to_use}")

            self.input_controller.press_health_potion()

            if i < potions_to_use - 1:
                time.sleep(POST_RESPAWN_POTION_DELAY)

        time.sleep(POST_RESPAWN_WAIT)

        if self.debug_mode:
            logger.debug(f"Finished post-respawn healing with {potions_to_use} potion(s)")

        return True

    def _calculate_potions_needed(self, health_percent: float) -> int:
        """Calculate number of potions needed based on health level.

        Args:
            health_percent: Current health percentage

        Returns:
            Number of potions to use
        """
        if health_percent <= CRITICAL_HEALTH_THRESHOLD:
            if self.debug_mode:
                logger.debug(f"Critical health ({health_percent:.2%}) - using 4 potions")
            return POTION_USAGE_MAP["critical"]

        elif health_percent <= LOW_HEALTH_THRESHOLD:
            if self.debug_mode:
                logger.debug(f"Low health ({health_percent:.2%}) - using 2 potions")
            return POTION_USAGE_MAP["low"]

        elif health_percent <= self.health_threshold:
            if self.debug_mode:
                logger.debug(f"Medium health ({health_percent:.2%}) - using 1 potion")
            return POTION_USAGE_MAP["medium"]

        return 0

    def _use_multiple_potions(self, potions_needed: int, health_percent: float) -> bool:
        """Use multiple health potions.

        Args:
            potions_needed: Number of potions to use
            health_percent: Current health percentage for logging

        Returns:
            True indicating potions were used
        """
        print(f"Using {potions_needed} health potion(s) (Health: {health_percent:.2%})...")

        for i in range(potions_needed):
            if self.debug_mode:
                logger.debug(f"Pressing potion {i + 1}/{potions_needed}")

            self.input_controller.press_health_potion()

            if i < potions_needed - 1:
                time.sleep(MULTIPLE_POTION_DELAY)

        time.sleep(POTION_EFFECT_WAIT)

        if self.debug_mode:
            logger.debug(f"Finished using {potions_needed} potion(s)")

        return True

    def use_emergency_potions(self) -> bool:
        """Use emergency potions when health is critically low before confirming death.

        This method is called when empty health is detected to give the character
        a chance to recover before confirming death status.

        Returns:
            True indicating emergency potions were used
        """
        potions_to_use = POTION_USAGE_MAP["emergency"]
        print(
            f"⚡ Emergency healing: Using {potions_to_use} health potion(s) before death check..."
        )

        for i in range(potions_to_use):
            if self.debug_mode:
                logger.debug(f"Emergency potion {i + 1}/{potions_to_use}")

            self.input_controller.press_health_potion()

            if i < potions_to_use - 1:
                time.sleep(MULTIPLE_POTION_DELAY)

        # Wait for potions to take effect before checking results
        print(f"⏳ Waiting {EMERGENCY_HEALING_WAIT}s for emergency potions to take effect...")
        time.sleep(EMERGENCY_HEALING_WAIT)

        if self.debug_mode:
            logger.debug(f"Finished emergency healing with {potions_to_use} potion(s)")

        return True

    def set_health_threshold(self, threshold: float) -> None:
        """Set the health threshold for potion usage.

        Args:
            threshold: Health threshold (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Health threshold must be between 0.0 and 1.0, got {threshold}")

        self.health_threshold = threshold

        if self.debug_mode:
            logger.debug(f"Health threshold set to: {threshold:.2%}")
