from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import json

from config import Config
from services.cooking_service import CookingService
from data.sample_recipes import get_recipe, SAMPLE_RECIPES
from models import InterruptionType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate configuration
Config.validate()

# Initialize FastAPI app
app = FastAPI(
    title="Foodingo - AI Cooking Assistant",
    description="An AI-powered cooking assistant that guides you through recipes with voice interaction",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
cooking_service = CookingService()

# Request/Response models
class StartCookingRequest(BaseModel):
    recipe_id: str
    user_id: Optional[str] = None

class UserInputRequest(BaseModel):
    session_id: str
    recipe_id: str
    user_input: str

class InterruptionRequest(BaseModel):
    session_id: str
    interruption_type: str
    reason: str
    user_message: Optional[str] = None

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Foodingo AI Cooking Assistant is running!"}

@app.get("/recipes")
async def list_recipes():
    """List all available recipes"""
    return {
        "recipes": [
            {
                "id": recipe.id,
                "name": recipe.name,
                "description": recipe.description,
                "difficulty": recipe.difficulty,
                "prep_time": recipe.prep_time,
                "cook_time": recipe.cook_time,
                "servings": recipe.servings
            }
            for recipe in SAMPLE_RECIPES.values()
        ]
    }

@app.get("/recipes/{recipe_id}")
async def get_recipe_details(recipe_id: str):
    """Get detailed information about a specific recipe"""
    recipe = get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    return recipe

@app.post("/cooking/start")
async def start_cooking(request: StartCookingRequest):
    """Start a new cooking session"""
    recipe = get_recipe(request.recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    session = cooking_service.start_cooking_session(recipe, request.user_id)
    
    # Generate welcome message
    welcome_message = f"""
    Great! Let's cook {recipe.name} together. This recipe serves {recipe.servings} and should take about {recipe.prep_time + recipe.cook_time} minutes total.
    
    Before we start, make sure you have all your ingredients ready. When you're ready to begin, just say "Let's start" or "Begin cooking"!
    """
    
    return {
        "session_id": session.session_id,
        "recipe": {
            "id": recipe.id,
            "name": recipe.name,
            "description": recipe.description,
            "total_steps": len(recipe.steps),
            "estimated_total_time": recipe.prep_time + recipe.cook_time
        },
        "welcome_message": welcome_message.strip(),
        "status": "ready_to_start"
    }

@app.post("/cooking/input")
async def process_user_input(request: UserInputRequest):
    """Process user input during cooking"""
    recipe = get_recipe(request.recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    result = cooking_service.process_user_input(
        session_id=request.session_id,
        user_input=request.user_input,
        recipe=recipe
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@app.get("/cooking/status/{session_id}")
async def get_cooking_status(session_id: str, recipe_id: str):
    """Get current status of a cooking session"""
    recipe = get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    status = cooking_service.get_cooking_status(session_id, recipe)
    
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return status

@app.post("/cooking/interrupt")
async def handle_interruption(request: InterruptionRequest):
    """Handle a cooking interruption (disaster, timing issue, etc.)"""
    try:
        interruption_type = InterruptionType(request.interruption_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interruption type")
    
    result = cooking_service.handle_interruption(
        session_id=request.session_id,
        interruption_type=interruption_type,
        reason=request.reason,
        user_message=request.user_message
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@app.delete("/cooking/{session_id}")
async def end_cooking_session(session_id: str):
    """End a cooking session"""
    success = cooking_service.end_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Cooking session ended successfully"}

# WebSocket endpoint for real-time communication
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time cooking assistance"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "user_input":
                # Process user input
                recipe = get_recipe(message["recipe_id"])
                if not recipe:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Recipe not found"
                    }))
                    continue
                
                result = cooking_service.process_user_input(
                    session_id=session_id,
                    user_input=message["input"],
                    recipe=recipe
                )
                
                await websocket.send_text(json.dumps({
                    "type": "ai_response",
                    "data": result
                }))
                
            elif message["type"] == "get_status":
                # Get cooking status
                recipe = get_recipe(message["recipe_id"])
                if recipe:
                    status = cooking_service.get_cooking_status(session_id, recipe)
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "data": status
                    }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "An error occurred"
        }))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.HOST, port=Config.PORT, log_level="info") 