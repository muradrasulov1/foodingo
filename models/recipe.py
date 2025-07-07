from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    SKIPPED = "skipped"

class InterruptionType(str, Enum):
    PAUSE = "pause"
    QUESTION = "question"
    DISASTER = "disaster"
    SUBSTITUTION = "substitution"
    TIMING_ISSUE = "timing_issue"

class RecipeStep(BaseModel):
    step_number: int
    instruction: str
    estimated_time: Optional[int] = None  # in seconds
    temperature: Optional[str] = None
    ingredients_used: List[str] = []
    equipment_needed: List[str] = []
    tips: List[str] = []
    dependencies: List[int] = []  # step numbers that must be completed first

class Ingredient(BaseModel):
    name: str
    amount: str
    unit: Optional[str] = None
    optional: bool = False
    substitutes: List[str] = []

class Recipe(BaseModel):
    id: str
    name: str
    description: str
    servings: int
    prep_time: int  # minutes
    cook_time: int  # minutes
    difficulty: str  # easy, medium, hard
    ingredients: List[Ingredient]
    steps: List[RecipeStep]
    tags: List[str] = []
    nutrition: Optional[Dict[str, Any]] = None

class CookingInterruption(BaseModel):
    type: InterruptionType
    reason: str
    timestamp: datetime
    step_number: int
    user_message: Optional[str] = None
    resolved: bool = False

class CookingSession(BaseModel):
    session_id: str
    recipe_id: str
    user_id: Optional[str] = None
    current_step: int = 0
    step_status: StepStatus = StepStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.now)
    context: Dict[str, Any] = {}
    interruptions: List[CookingInterruption] = []
    conversation_history: List[Dict[str, str]] = []
    
    def add_interruption(self, interruption: CookingInterruption):
        """Add an interruption to the session"""
        self.interruptions.append(interruption)
    
    def get_current_step(self, recipe: Recipe) -> Optional[RecipeStep]:
        """Get the current step from the recipe"""
        if 0 <= self.current_step < len(recipe.steps):
            return recipe.steps[self.current_step]
        return None
    
    def advance_step(self):
        """Move to the next step"""
        self.current_step += 1
        self.step_status = StepStatus.PENDING
    
    def pause_step(self, reason: str):
        """Pause the current step"""
        self.step_status = StepStatus.PAUSED
        interruption = CookingInterruption(
            type=InterruptionType.PAUSE,
            reason=reason,
            timestamp=datetime.now(),
            step_number=self.current_step
        )
        self.add_interruption(interruption)
    
    def resume_step(self):
        """Resume the current step"""
        self.step_status = StepStatus.IN_PROGRESS
        # Mark the last pause interruption as resolved
        for interruption in reversed(self.interruptions):
            if interruption.type == InterruptionType.PAUSE and not interruption.resolved:
                interruption.resolved = True
                break 