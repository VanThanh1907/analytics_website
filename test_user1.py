import sys
sys.path.append('web-app')
from app import call_recommendation_api

result = call_recommendation_api('recommendations', 1, num_recs=6)
print('User 1 recommendations:', result.get('total', 0) if result else 0)
if result and result.get('recommendations'):
    for rec in result['recommendations']:
        print(f'- {rec["name"]} ({rec["category"]})')