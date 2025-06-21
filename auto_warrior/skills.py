"""This is the skills module for the Auto Warrior game.

Skills are used to perform actions in the game.
"""

import logging
import time
from dataclasses import dataclass

from auto_warrior.constants import DEFAULT_SKILL_KEYS
from auto_warrior.input_control import InputController

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class SkillConfig:
    """Configuration for a skill.
    
    cooldown > duration
    
    
    Attributes:
        id (int): Unique identifier for the skill.
        cooldown (int): Seconds before skill is ready to be used again.
        #TODO: duration is not even needed if we are not going to Check
        #because cooldown and usage_time is determine when to skill going to be use
        duration (int): Skill active time in seconds.
        usage_time (int): Skill used time in seconds. (e.g 1 to 4 second)
        key (str): Skill keyboard key.
        sleep_time (int): Seconds before next skill usage.
    """

    id: int
    cooldown: int
    duration: int
    usage_time: int
    key: str
    sleep_time: int = 2


class Skill:
    """Manages individual skill state and usage."""

    def __init__(self, config: SkillConfig, input_controller: InputController) -> None:
        """Initialize the skill with its configuration and input controller."""
        self.config = config
        self.input_controller = input_controller
        self.last_used_time = 0.0
        self.activation_end_time = 0.0

    def is_ready(self) -> bool:
        """Check if the skill is ready to be used based on cooldown."""
        current_time = time.time()
        return current_time >= self.last_used_time + self.config.cooldown

    def is_active(self) -> bool:
        """Check if the skill is currently active based on its duration."""
        current_time = time.time()
        return current_time < self.activation_end_time

    def get_cooldown_remaining(self) -> float:
        """Get the remaining cooldown time for the skill."""
        if self.is_ready():
            return 0.0

        current_time = time.time()
        remaining = (self.last_used_time + self.config.cooldown) - current_time
        return max(0.0, remaining)

    def get_duration_remaining(self) -> float:
        """Get the remaining duration of the skill."""
        if not self.is_active():
            return 0.0

        current_time = time.time()
        remaining = self.activation_end_time - current_time
        return max(0.0, remaining)

    def use_skill(self) -> bool:
        """Use the skill if it is ready and not currently active, meaning it is not on cooldown."""
        if not self.is_ready() or self.is_active():
            return False

        try:
            # Press the skill key
            self.input_controller.press_key(self.config.key, self.config.usage_time)
            # Update the last used time and activation end time
            current_time = time.time()
            self.last_used_time = current_time
            self.activation_end_time = current_time + self.config.duration

            logger.info(
                f"Skill {self.config.id} used at {current_time:.2f} with key: "
                f"{self.config.key}, duration: {self.config.duration}s, "
                f"cooldown: {self.config.cooldown}s"
            )
            return True
        except Exception as e:
            logger.error(f"Error using skill {self.config.id}: {e}")
            return False


class SkillManager:
    """Manages a collection of skills and their usage."""

    def __init__(self, input_controller: InputController) -> None:
        """Initialize the skill manager with an input controller."""
        self.input_controller = input_controller
        self.skills: dict[int, Skill] = {}

        # Initialize default skills
        self._setup_default_skills()

    def _setup_default_skills(self) -> None:
        """Setup default skill configurations."""
        skill_3_config = SkillConfig(
            id=3, cooldown=75, duration=72, usage_time=2, key=DEFAULT_SKILL_KEYS[0]
        )

        skill_4_config = SkillConfig(
            id=4, cooldown=36, duration=33, usage_time=2, key=DEFAULT_SKILL_KEYS[1]
        )

        self.add_skill(skill_3_config)
        self.add_skill(skill_4_config)

    def add_skill(self, config: SkillConfig) -> None:
        """Add a new skill to the manager."""
        skill = Skill(config, self.input_controller)
        self.skills[config.id] = skill
        logger.debug(
            f"Skill {config.id} added with key: {config.key}, "
            f"cooldown: {config.cooldown}s, duration: {config.duration}s"
        )

    def get_skill(self, skill_id: int) -> Skill | None:
        """Get a skill by its ID."""
        return self.skills.get(skill_id)

    def use_skill(self, skill_id: int) -> bool:
        """Use a skill by its ID if it is ready."""
        skill = self.get_skill(skill_id)
        if skill and skill.use_skill():
            logger.info(f"Skill {skill_id} used successfully.")
            return True
        else:
            logger.warning(f"Skill {skill_id} is not ready or does not exist.")
            return False

    def get_skill_status(self, skill_id: int) -> dict[str, float | bool | int | str]:
        """Get the status of a skill by its ID."""
        skill = self.get_skill(skill_id)
        if skill:
            return {
                "id": skill.config.id,
                "key": skill.config.key,
                "cooldown_remaining": skill.get_cooldown_remaining(),
                "duration_remaining": skill.get_duration_remaining(),
                "is_ready": skill.is_ready(),
                "is_active": skill.is_active(),
            }
        else:
            logger.warning(f"Skill {skill_id} does not exist.")
            return {}

    def get_active_skills(self) -> list[Skill]:
        """Get a list of currently active skills."""
        return [skill for skill in self.skills.values() if skill.is_active()]

    def get_ready_skills(self) -> list[Skill]:
        """Get a list of skills that are ready to be used."""
        return [skill for skill in self.skills.values() if skill.is_ready()]

    def get_all_skills_status(self) -> dict[int, dict[str, float | bool | int | str]]:
        """Get status of all skills."""
        return {
            skill_id: self.get_skill_status(skill_id) for skill_id in self.skills.keys()
        }

    def use_available_skills(self) -> list[int]:
        """Use all available skills that are ready.

        Returns:
            List of skill IDs that were successfully used
        """
        used_skills = []
        ready_skills = self.get_ready_skills()

        for skill in ready_skills:
            if skill.use_skill():
                used_skills.append(skill.config.id)

        return used_skills
