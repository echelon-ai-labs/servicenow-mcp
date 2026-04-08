#!/usr/bin/env python
"""
ServiceNow OAuth Setup Script

This script helps set up and test OAuth authentication with ServiceNow.
It will:
1. Get an OAuth token using client credentials
2. Test the token with a simple API call
3. Update the .env file with the OAuth configuration

Usage:
    python scripts/setup_oauth.py
"""

import os
import sys
import requests
import base64
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def setup_oauth():
    # Load environment variables
    load_dotenv()
    
    # Get ServiceNow instance URL
    instance_url = os.getenv("SERVICENOW_INSTANCE_URL")
    if not instance_url or instance_url == "https://your-instance.service-now.com":
        instance_url = input("Enter your ServiceNow instance URL (e.g., https://dev296866.service-now.com): ")
    
    print("\n=== ServiceNow OAuth Setup ===")
    print("This script will help you set up OAuth authentication for your ServiceNow instance.")
    print("You'll need to create an OAuth API client in ServiceNow first.")
    print("\nTo create an OAuth API client:")
    print("1. Log in to your ServiceNow instance")
    print("2. Navigate to System OAuth > Application Registry")
    print("3. Click 'New'")
    print("4. Select 'Create an OAuth API endpoint for external clients'")
    print("5. Fill in the required fields:")
    print("   - Name: MCP Client (or any name you prefer)")
    print("   - Redirect URL: http://localhost (for testing)")
    print("   - Active: Checked")
    print("   - Refresh Token Lifespan: 8 hours (or your preference)")
    print("   - Access Token Lifespan: 30 minutes (or your preference)")
    print("6. Save the application and note down the Client ID and Client Secret")
    print("7. Go to the 'OAuth Scopes' related list and add appropriate scopes (e.g., 'admin')")
    
    # Get OAuth credentials
    client_id = input("\nEnter your Client ID: ")
    client_secret = input("Enter your Client Secret: ")
    
    # Get username and password for resource owner grant
    username = os.getenv("SERVICENOW_USERNAME")
    password = os.getenv("SERVICENOW_PASSWORD")
    
    if not username or username == "your-username":
        username = input("Enter your ServiceNow username: ")
    
    if not password or password == "your-password":
        password = input("Enter your ServiceNow password: ")
    
    # Set token URL
    token_url = f"{instance_url}/oauth_token.do"
    
    print(f"\nTesting OAuth connection to {instance_url}...")
    print("Trying different OAuth grant types...")
    
    # Try different OAuth grant types
    access_token = None
    
    # 1. Try client credentials grant
    try:
        print("\nAttempting client_credentials grant...")
        # Create authorization header
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        token_response = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "client_credentials"
            }
        )
        
        if token_response.status_code == 200:
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            print("✅ Successfully obtained OAuth token using client_credentials grant!")
        else:
            print(f"❌ Failed with client_credentials grant: {token_response.status_code}")
            print(f"Response: {token_response.text}")
    except Exception as e:
        print(f"❌ Error with client_credentials grant: {e}")
    
    # 2. Try password grant if client credentials failed
    if not access_token:
        try:
            print("\nAttempting password grant...")
            token_response = requests.post(
                token_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "password",
                    "username": username,
                    "password": password
                }
            )
            
            if token_response.status_code == 200:
                token_data = token_response.json()
                access_token = token_data.get("access_token")
                print("✅ Successfully obtained OAuth token using password grant!")
            else:
                print(f"❌ Failed with password grant: {token_response.status_code}")
                print(f"Response: {token_response.text}")
        except Exception as e:
            print(f"❌ Error with password grant: {e}")
    
    # If we have a token, test it
    if access_token:
        # Test the token with a simple API call
        test_url = f"{instance_url}/api/now/table/incident?sysparm_limit=1"
        test_response = requests.get(
            test_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )
        
        if test_response.status_code == 200:
            print("✅ Successfully tested OAuth token with API call!")
            data = test_response.json()
            print(f"Retrieved {len(data.get('result', []))} incident(s)")
            
            # Update .env file
            update_env = input("\nDo you want to update your .env file with these OAuth credentials? (y/n): ")
            if update_env.lower() == 'y':
                env_path = Path(__file__).parent.parent / '.env'
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()

                # Helper to update or insert a key
                def set_env_var(lines, key, value):
                    found = False
                    for i, line in enumerate(lines):
                        if line.strip().startswith(f'{key}=') or line.strip().startswith(f'#{key}='):
                            lines[i] = f'{key}={value}\n'
                            found = True
                            break
                    if not found:
                        lines.append(f'{key}={value}\n')
                    return lines

                # Update or insert OAuth configuration
                env_lines = set_env_var(env_lines, 'SERVICENOW_AUTH_TYPE', 'oauth')
                env_lines = set_env_var(env_lines, 'SERVICENOW_CLIENT_ID', client_id)
                env_lines = set_env_var(env_lines, 'SERVICENOW_CLIENT_SECRET', client_secret)
                env_lines = set_env_var(env_lines, 'SERVICENOW_TOKEN_URL', token_url)
                env_lines = set_env_var(env_lines, 'SERVICENOW_USERNAME', username)
                env_lines = set_env_var(env_lines, 'SERVICENOW_PASSWORD', password)

                with open(env_path, 'w') as f:
                    f.writelines(env_lines)

                print("✅ Updated .env file with OAuth configuration!")
                print("\nYou can now use OAuth authentication with the ServiceNow MCP server.")
                print("To test it, run: python scripts/test_connection.py")
            
            return True
        else:
            print(f"❌ Failed to test OAuth token with API call: {test_response.status_code}")
            print(f"Response: {test_response.text}")
            return False
    else:
        print("\n❌ Failed to obtain OAuth token with any grant type.")
        print("\nPossible issues:")
        print("1. The OAuth client may not have the correct scopes")
        print("2. The client ID or client secret may be incorrect")
        print("3. The OAuth client may not be active")
        print("4. The username/password may be incorrect")
        print("\nPlease check your ServiceNow instance OAuth configuration and try again.")
        return False

if __name__ == "__main__":
    setup_oauth() 