# Submission summary


### Initial Benchmark Results
```
----------------------------------------------------------------------------------------------- benchmark: 2 tests -----------------------------------------------------------------------------------------------
Name (time in ms)                          Min                   Max                  Mean              StdDev                Median                 IQR            Outliers     OPS            Rounds  Iterations
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_create_batch_runs_50_100kb       535.8392 (1.0)        574.8675 (1.0)        551.7946 (1.0)       15.1240 (1.0)        546.3017 (1.0)       20.1775 (1.0)           2;0  1.8123 (1.0)           5           1
test_create_batch_runs_500_10kb     1,675.0273 (3.13)     1,973.3075 (3.43)     1,882.2039 (3.41)     119.1980 (7.88)     1,930.0932 (3.53)     107.9891 (5.35)          1;1  0.5313 (0.29)          5           1
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

```

### Benchmark Results After Changes
```

------------------------------------------------------------------------------------------------------ benchmark: 4 tests -----------------------------------------------------------------------------------------------------
Name (time in ms)                                         Min                   Max                  Mean             StdDev                Median                IQR            Outliers     OPS            Rounds  Iterations
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_create_batch_runs_50_100kb (NOW)                326.2121 (1.0)        380.1544 (1.0)        352.7962 (1.0)      24.9902 (1.29)       341.9212 (1.0)      44.8347 (1.42)          3;0  2.8345 (1.0)           5           1
test_create_batch_runs_50_100kb (0006_baselin)       336.4015 (1.03)       386.7313 (1.02)       364.1179 (1.03)     23.6905 (1.22)       373.5293 (1.09)     43.8231 (1.39)          1;0  2.7464 (0.97)          5           1
test_create_batch_runs_500_10kb (NOW)              1,051.4855 (3.22)     1,097.5493 (2.89)     1,070.3113 (3.03)     19.3510 (1.0)      1,071.1837 (3.13)     31.5749 (1.0)           1;0  0.9343 (0.33)          5           1
test_create_batch_runs_500_10kb (0006_baselin)     1,114.2992 (3.42)     1,189.4287 (3.13)     1,140.6321 (3.23)     29.6558 (1.53)     1,130.1563 (3.31)     35.9423 (1.14)          1;0  0.8767 (0.31)          5           1
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

```

I identified that the main bottleneck was in the `create_batch_runs` function, specifically in the way it handled large JSON payloads.
It would search the entire json payload for the metadata key range.
Initially, I was going to just have it trim the payload to only include the remaining payload, but I realized 
the instructions said "The entire batch must still be written to object storage, but you can change how this is done."
Then I realized I could just write one JSON file per run instead of one large JSON file for the entire batch.
Now I do not store the metadate locations in of the metadata, since I can just read the entire file and return its contents.

I also made the database queries more efficient by using `bulk_create` for inserting runs, which significantly reduced the time taken for batch inserts.



----
# ls-py-handler
A simple FastAPI server with endpoints for ingesting and fetching runs.

## Features

- `POST /runs` endpoint to create new runs
- `GET /runs/{id}` endpoint to retrieve run information by UUID

## Quick Start

```bash
# 1. Install dependencies
poetry install

# 2. Start database services (required before running the server)
make db-up

# 3. Run migrations and start the server
make server
```

The API will be available at http://localhost:8000

### Example API Usage

#### Creating Runs

```bash
# Create a new run
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '[
    {
      "trace_id": "944ce838-b5c5-4628-8f23-089fbda8b9e3",
      "name": "Weather Query",
      "inputs": {"query": "What is the weather in San Francisco?"},
      "outputs": {"response": "It is currently 65°F and sunny in San Francisco."},
      "metadata": {"model": "gpt-4", "temperature": 0.7, "tokens": 42}
    }
  ]'
```

Response:
```json
{
  "ids": ["<generated-uuid>"]
}
```

#### Retrieving a Run

```bash
# Get a run by ID (replace <run-id> with an actual UUID)
curl -X GET http://localhost:8000/runs/<run-id>
```

Response:
```json
{
  "id": "<run-id>",
  "trace_id": "944ce838-b5c5-4628-8f23-089fbda8b9e3",
  "name": "Weather Query",
  "inputs": {"query": "What is the weather in San Francisco?"},
  "outputs": {"response": "It is currently 65°F and sunny in San Francisco."},
  "metadata": {"model": "gpt-4", "temperature": 0.7, "tokens": 42}
}
```

## Setup Details

This project uses Poetry for dependency management.

```bash
# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

## Database Setup

This project uses PostgreSQL for data storage and MinIO for object storage. Docker Compose is used to manage these services.

```bash
# Start database services (PostgreSQL and MinIO)
make db-up

# Stop database services
make db-down

# Run database migrations
make db-migrate

# Revert the most recent migration
make db-downgrade
```

## Running the Server

```bash
# Start the server with migrations applied
make server

# Or manually start the server
poetry run uvicorn ls_py_handler.main:app --reload
```

## Linting and Formatting

This project uses Ruff for linting and formatting Python code.

```bash
# Format code
make format

# Check code for linting issues
make lint

# Automatically fix linting issues when possible
make lint-fix
```

## API Documentation

Once the server is running, you can access the auto-generated API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

The project uses pytest for testing and includes a dedicated test environment configuration.

```bash
# Run tests (this automatically sets up the test environment)
make test
```

The test command will:
1. Set up a clean test environment (drop and recreate the test database and S3 bucket)
2. Run migrations on the test database
3. Execute all tests with the test environment settings

### Test Environment Setup

The test environment uses:
- A separate database (`postgres_test`)
- A separate S3 bucket (`runs-test`)
- Environment variables from `.env.test`

You can manually set up the test environment without running tests:

```bash
# Just set up the test environment
make test-setup
```

### Environment Configuration

The application uses environment-specific configuration:
- Development: Uses the default `.env` file
- Testing: Uses the `.env.test` file when `RUN_HANDLER_ENV=test` is set

This allows tests to run with isolated resources without affecting your development environment.

## Benchmarking and Profiling

The project includes tools for performance benchmarking and memory profiling to help identify bottlenecks and optimize resource usage.

### Performance Benchmarks

Performance benchmarks measure execution time of key operations using `pytest-benchmark`. The benchmarks are designed to isolate the API request handling time from data preparation and JSON serialization.

```bash
# Run performance benchmarks
make benchmark
```

This will:
1. Set up a clean test environment
2. Run the benchmark tests
3. Save the results to `.benchmarks` directory for comparison with future runs

Example benchmark scenarios:
- Processing 500 runs with 10KB of data per field
- Processing 50 runs with 100KB of data per field

### Memory Profiling

Memory profiling using `pytest-memray` helps identify memory usage.

```bash
# Run memory profiling
make memprofile
```

Memory profiling results will show:
- Peak memory usage for different operations
- Memory allocation patterns
- Memory-intensive functions and call paths
