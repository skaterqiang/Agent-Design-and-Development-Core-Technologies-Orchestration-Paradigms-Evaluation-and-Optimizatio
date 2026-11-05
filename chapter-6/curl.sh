curl http://localhost:6006/v1/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "gpt2",
        "prompt": "who are you",
        "max_tokens": 50
    }'
