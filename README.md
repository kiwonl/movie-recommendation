```
export ENDPOINT=104.197.96.172

curl -X POST -H "Content-Type: application/json" -d '{
  "movies": ["Despicable Me 4", "Inside Out 2"],
  "scenario": "가족들과 함께 보기 좋은"
}' "$ENDPOINT/recommendations"
```
