import json

from api_client import API_BASE_URL, api_request


def main():
    print(f"Calling API: {API_BASE_URL}/sync?background=false")
    result = api_request("POST", "/sync?background=false")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
