import sys
sys.path.append('web-app')

# Import app configuration
from app import call_recommendation_api

# Test API call directly
print("🧪 Testing API call function directly...")
result = call_recommendation_api('recommendations', 3, num_recs=6)
print(f"Result: {result}")