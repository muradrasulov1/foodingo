# 🍔 Foodingo - AI Cooking Assistant

An intelligent, voice-guided cooking companion that adapts to real kitchen chaos. Think "GPS for cooking" - it knows where you are, handles interruptions gracefully, and keeps you on track.

## 🎯 Core Philosophy

**Cooking is messy and unpredictable.** Traditional recipe apps are linear and dumb. Foodingo is different:

- ✅ **Handles interruptions**: Burger patty falls? AI pauses and helps you recover
- ✅ **Adapts to your pace**: No rushing, no getting lost
- ✅ **Context-aware**: Remembers what happened, provides relevant guidance
- ✅ **Conversational**: Talk naturally, not with rigid commands

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Try the Demo (No API Key Required)
```bash
python test_demo.py
```

This runs a mock version that demonstrates the core conversation flow without needing OpenAI API access.

### 3. For Full AI Features
Create a `.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
```

Then run the API server:
```bash
python -m api.main
```

## 🧠 How It Works

### Core Architecture

```
┌─────────────────────────────────────┐
│         AI Conversation Engine      │  ← The Brain
│  • Context Understanding            │
│  • Interruption Handling            │
│  • Dynamic Response Generation      │
└─────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────┐
│         Cooking Service             │  ← The Orchestrator
│  • Session Management               │
│  • State Tracking                   │
│  • Action Execution                 │
└─────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────┐
│         Recipe & Session Models     │  ← The Data
│  • Recipe Structure                 │
│  • Cooking Progress                 │
│  • Interruption History             │
└─────────────────────────────────────┘
```

### Key Features

**🎤 Intelligent Conversation**
- Understands natural language: "Wait, my patty fell!"
- Provides contextual responses: "No problem! Kitchen accidents happen..."
- Remembers conversation history

**⏸️ Smart Interruption Handling**
- Pause/resume with context
- Disaster recovery (spills, burns, dropped food)
- Timing adjustments ("My onions aren't ready yet")

**🔄 Adaptive Flow**
- Goes back to previous steps
- Repeats instructions
- Adjusts pacing to your speed

## 📁 Project Structure

```
Foodingo/
├── models/              # Data models
│   ├── recipe.py       # Recipe, CookingSession, Interruption models
│   └── __init__.py
├── ai/                  # AI conversation engine
│   ├── conversation_engine.py
│   └── __init__.py
├── services/            # Business logic
│   ├── cooking_service.py
│   └── __init__.py
├── data/               # Sample data
│   ├── sample_recipes.py
│   └── __init__.py
├── api/                # FastAPI web server
│   ├── main.py
│   └── __init__.py
├── config.py           # Configuration
├── requirements.txt    # Dependencies
├── test_demo.py       # Demo script
└── README.md
```

## 🍔 Example Conversation Flow

```
🤖 AI: Great! Let's cook Classic Beef Burger together. First, we'll season the ground beef. Get your mixing bowl ready!

👤 You: Wait, I dropped the patty on the floor

🤖 AI: Oh no! Kitchen accidents happen to everyone. No worries at all! Do you need to start this step over, or can you continue?

👤 You: I need to make a new patty

🤖 AI: Perfect! Let's start fresh. Take your ground beef and gently form a new patty. Remember, don't overmix - we want it tender!

👤 You: Okay, ready to continue

🤖 AI: Welcome back! You were forming patties. We need 4 patties about 3/4 inch thick. You've got this!
```

## 🛠️ API Endpoints

### Start Cooking Session
```bash
POST /cooking/start
{
  "recipe_id": "classic_beef_burger"
}
```

### Send User Input
```bash
POST /cooking/input
{
  "session_id": "uuid-here",
  "recipe_id": "classic_beef_burger", 
  "user_input": "I dropped the patty"
}
```

### Get Cooking Status
```bash
GET /cooking/status/{session_id}?recipe_id=classic_beef_burger
```

### WebSocket for Real-time
```javascript
ws://localhost:8000/ws/{session_id}
```

## 🧪 Testing the Core Functionality

The `test_demo.py` script lets you experience the core conversation flow:

```bash
python test_demo.py
```

**Try these interactions:**
- `"start"` - Begin cooking
- `"next"` - Move to next step  
- `"pause"` - Pause cooking
- `"I dropped the patty"` - Simulate disaster
- `"resume"` - Continue cooking
- `"repeat"` - Repeat current step
- `"help"` - Get assistance

## 🎯 What Makes This Different

### Traditional Recipe Apps:
- Linear, scripted instructions
- No interruption handling
- Keep playing when you're not ready
- Generic, one-size-fits-all

### Foodingo:
- **Conversational & adaptive**
- **Interruption-first design**
- **Context-aware responses**
- **Handles real kitchen chaos**

## 🔮 Next Steps

1. **Voice Integration**: Add speech-to-text and text-to-speech
2. **Mobile App**: React Native frontend
3. **Recipe Library**: Expand beyond burgers
4. **Smart Timers**: Integration with kitchen devices
5. **Visual Recognition**: Camera-based progress tracking

## 🤝 Contributing

This is the foundational core of an AI cooking assistant. The conversation engine and interruption handling are the key differentiators.

## 📝 License

MIT License - Build something amazing with this!

---

**The goal**: Make cooking as seamless as driving with GPS. You have a smart companion that knows where you are, adapts to problems, and keeps you on track. 🚗➡️🍳 