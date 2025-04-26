import requests
import json

# Test data
test_email = {
    "subject": "Test Email Subject",
    "content": "This is a test email content. Just checking if the server works correctly."
}

try:
    # Send POST request
    print("Sending request to server...")
    response = requests.post(
        'http://localhost:8000/analyze',
        json=test_email
    )
    
    # Print response details
    print("\nResponse Details:")
    print("Status Code:", response.status_code)
    print("Headers:", response.headers)
    print("Raw Response:", response.text)
    
    try:
        print("JSON Response:", response.json())
    except json.JSONDecodeError as e:
        print("Could not parse JSON response:", str(e))

    # Check if CSV was created
    import os
    if os.path.exists('data/email_analysis.csv'):
        print("\nCSV file created successfully!")
        with open('data/email_analysis.csv', 'r') as f:
            print("\nCSV contents:")
            print(f.read())
    else:
        print("\nCSV file was not created!")
        
except requests.exceptions.ConnectionError:
    print("Could not connect to server. Is it running on port 8000?") 