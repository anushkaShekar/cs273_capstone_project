import requests

# Address of the running backend
BASE_URL = "http://localhost:8000"


def test_skills():
    # Ask the backend for the skill list
    response = requests.get(f"{BASE_URL}/skills")

    # Check that the request worked and the list is not empty
    if response.status_code == 200 and len(response.json()["skills"]) > 0:
        print("OK: /skills returned", len(response.json()["skills"]), "skills")
    else:
        print("FAILED: /skills, status code", response.status_code)


def test_recommend():
    # Send a few real skills, the same way the frontend does
    body = {
        "skills": ["python", "git", "structured query language sql"],
        "model": "one"
    }
    response = requests.post(f"{BASE_URL}/recommend", json=body)

    # Check that the request worked and 5 jobs came back
    if response.status_code == 200 and len(response.json()["results"]) == 5:
        print("OK: /recommend returned 5 jobs")
    else:
        print("FAILED: /recommend, status code", response.status_code)


# Run the checks when the script is started
if __name__ == "__main__":
    test_skills()
    test_recommend()
