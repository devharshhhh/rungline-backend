from app.services import judge0_client

result = judge0_client.run_against_test_cases(
    code='print("Hello, World!")',
    language="python",
    test_cases=[{"input": "", "expected_output": "Hello, World!"}],
)

for r in result:
    print(r)