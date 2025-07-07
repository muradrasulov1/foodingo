from models import Recipe, RecipeStep, Ingredient

# Sample burger recipe for testing
BEEF_BURGER_RECIPE = Recipe(
    id="classic_beef_burger",
    name="Classic Beef Burger",
    description="A delicious homemade beef burger with all the classic toppings",
    servings=4,
    prep_time=15,
    cook_time=10,
    difficulty="easy",
    ingredients=[
        Ingredient(name="Ground beef", amount="1", unit="lb", substitutes=["Ground turkey", "Plant-based patties"]),
        Ingredient(name="Burger buns", amount="4", unit="pieces"),
        Ingredient(name="Salt", amount="1", unit="tsp"),
        Ingredient(name="Black pepper", amount="1/2", unit="tsp"),
        Ingredient(name="Garlic powder", amount="1/2", unit="tsp"),
        Ingredient(name="Onion powder", amount="1/2", unit="tsp"),
        Ingredient(name="Lettuce", amount="4", unit="leaves", optional=True),
        Ingredient(name="Tomato", amount="1", unit="large", optional=True),
        Ingredient(name="Cheese slices", amount="4", unit="pieces", optional=True),
        Ingredient(name="Pickles", amount="8", unit="slices", optional=True),
        Ingredient(name="Ketchup", amount="to taste", optional=True),
        Ingredient(name="Mustard", amount="to taste", optional=True),
    ],
    steps=[
        RecipeStep(
            step_number=1,
            instruction="In a large bowl, gently mix the ground beef with salt, pepper, garlic powder, and onion powder. Don't overmix - this keeps the burgers tender.",
            estimated_time=120,  # 2 minutes
            ingredients_used=["Ground beef", "Salt", "Black pepper", "Garlic powder", "Onion powder"],
            equipment_needed=["Large mixing bowl"],
            tips=["Don't overmix the meat - it makes tough burgers", "Mix with your hands gently"]
        ),
        RecipeStep(
            step_number=2,
            instruction="Divide the seasoned beef into 4 equal portions and gently shape them into patties about 3/4 inch thick. Make a small indent in the center of each patty with your thumb.",
            estimated_time=180,  # 3 minutes
            ingredients_used=["Ground beef mixture"],
            equipment_needed=["Clean hands"],
            tips=["The thumb indent prevents the burger from puffing up while cooking", "Make patties slightly larger than your buns - they'll shrink"]
        ),
        RecipeStep(
            step_number=3,
            instruction="Heat a large skillet or grill pan over medium-high heat. You don't need oil - the beef has enough fat.",
            estimated_time=120,  # 2 minutes
            equipment_needed=["Large skillet or grill pan"],
            tips=["The pan should be hot enough that water sizzles when dropped on it", "Cast iron works great for burgers"]
        ),
        RecipeStep(
            step_number=4,
            instruction="Place the patties in the hot pan. Cook for 3-4 minutes without moving them - this creates a nice crust. You'll hear them sizzling!",
            estimated_time=240,  # 4 minutes
            ingredients_used=["Beef patties"],
            equipment_needed=["Spatula"],
            tips=["Don't press down on the patties - you'll squeeze out the juices", "Resist the urge to move them around"]
        ),
        RecipeStep(
            step_number=5,
            instruction="Flip the patties and cook for another 3-4 minutes for medium doneness. If adding cheese, place it on top during the last minute of cooking.",
            estimated_time=240,  # 4 minutes
            ingredients_used=["Cheese slices"],
            equipment_needed=["Spatula"],
            tips=["For well-done, cook 2 more minutes per side", "The cheese will melt perfectly in the last minute"]
        ),
        RecipeStep(
            step_number=6,
            instruction="While the burgers finish cooking, quickly toast the buns in a dry pan or toaster until lightly golden.",
            estimated_time=120,  # 2 minutes
            ingredients_used=["Burger buns"],
            equipment_needed=["Toaster or dry pan"],
            tips=["Toasted buns hold up better to juicy burgers", "Just 30 seconds per side in the pan"]
        ),
        RecipeStep(
            step_number=7,
            instruction="Remove the patties from heat and let them rest for 1 minute. This helps the juices redistribute.",
            estimated_time=60,  # 1 minute
            tips=["This resting step makes a juicier burger", "Use this time to prep your toppings"]
        ),
        RecipeStep(
            step_number=8,
            instruction="Assemble your burgers! Start with the bottom bun, add lettuce, then the patty, cheese, tomato, pickles, and condiments. Top with the other bun half.",
            estimated_time=180,  # 3 minutes
            ingredients_used=["Lettuce", "Tomato", "Pickles", "Ketchup", "Mustard"],
            tips=["Lettuce on the bottom prevents the bun from getting soggy", "Don't overload - you want to be able to bite it!"]
        )
    ],
    tags=["beef", "burger", "american", "grill", "easy", "quick"],
    nutrition={
        "calories": 520,
        "protein": "28g",
        "carbs": "31g",
        "fat": "32g"
    }
)

# Dictionary to easily access recipes
SAMPLE_RECIPES = {
    "classic_beef_burger": BEEF_BURGER_RECIPE
}

def get_recipe(recipe_id: str) -> Recipe:
    """Get a recipe by ID"""
    return SAMPLE_RECIPES.get(recipe_id) 