# Create a new run
out=$(curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '[
    {
      "trace_id": "944ce838-b5c5-4628-8f23-089fbda8b9e3",
      "name": "Weather Query",
      "inputs": {"query": "What is the weather in San Francisco?"},
      "outputs": {"response": "It is currently 65°F and sunny in San Francisco."},
      "metadata": {"model": "gpt-4", "temperature": 0.7, "tokens": 42}
    }
  ]')

echo $out


run_id=$(echo $out | jq -r '.run_ids.[0]')

curl -X GET http://localhost:8000/runs/$run_id
