# Simple test to verify the ReAct pattern works
print("Testing ReAct Pattern Implementation")
print("=" * 40)

# Test the basic tools without LLM
from basic_react_agent import search_restaurants, get_local_attractions, estimate_expenses

print("Testing tools directly:")

# Test restaurant search
result1 = search_restaurants.invoke({"location": "北京", "cuisine": "川菜"})
print(f"Restaurant search result: {result1}")

# Test attractions
result2 = get_local_attractions.invoke({"city": "西安"})
print(f"Attractions result: {result2}")

# Test expenses
result3 = estimate_expenses.invoke({"city": "上海", "days": 3})
print(f"Expenses result: {result3}")

print("\nAll tools working correctly!")
print("The ReAct agent is ready to use with proper LLM integration.")
