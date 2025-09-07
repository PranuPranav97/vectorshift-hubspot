# slack.py

from fastapi import Request
import base64
import json
import secrets
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import requests
from datetime import datetime
CLIENT_ID = 'XXX'
CLIENT_SECRET = 'XXX'
encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
from integrations.integration_item import IntegrationItem

REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
authorization_url=f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&scope=crm.objects.contacts.read crm.objects.deals.read crm.objects.companies.read'

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)
    return f'{authorization_url}&redirect_uri={REDIRECT_URI}&state={json.dumps(state_data)}'

async def oauth2callback_hubspot(request: Request):
     # Get the full query parameters dict
    params = request.query_params
    # Extract 'code'
    code = params.get("code")
    # Extract and parse 'state' JSON
    state_raw = params.get("state")
    
    state = json.loads(state_raw) if state_raw else {}
    
    org_id = state.get("org_id")
    user_id=state.get("user_id")
   
    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data = {
                    "grant_type": "authorization_code",
                    "redirect_uri": REDIRECT_URI,
                    "code": code,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET
                },
                headers={
                   
                    'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )
       
        x=await add_key_value_redis(f'hubspot_credentials:{org_id}_{user_id}', json.dumps(response.json()), expire=1800)
        user_cred=await get_value_redis(f'hubspot_credentials:{org_id}_{user_id}')
        
    
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)
    

async def get_hubspot_credentials(user_id, org_id):
    user_cred=await get_value_redis(f'hubspot_credentials:{org_id}_{user_id}')
   
    return json.loads(user_cred) if user_cred else None



async def create_integration_item_metadata_object(response_json: dict) -> IntegrationItem:
    """Creates an IntegrationItem object from a HubSpot CRM object."""
    properties = response_json.get("properties", {})

    firstname = properties.get("firstname") or ""
    lastname = properties.get("lastname") or ""
    name = (firstname + " " + lastname).strip() or "Unnamed Contact"

    created_at = response_json.get("createdAt")
    updated_at = response_json.get("updatedAt")

    item = IntegrationItem(
        id=response_json.get("id"),
        type=response_json.get("objectType", "hubspot_contact"),
        name=name,
        creation_time=datetime.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else None,
        last_modified_time=datetime.fromisoformat(updated_at.replace("Z", "+00:00")) if updated_at else None,
        url=None
    )

    return item


async def get_items_hubspot(credentials: str) -> list:
    """Fetches HubSpot CRM contacts and returns a list of IntegrationItem objects."""

    credentials = json.loads(credentials)
    access_token = credentials.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    object_types = {
        "contacts": "https://api.hubapi.com/crm/v3/objects/contacts",
        "companies": "https://api.hubapi.com/crm/v3/objects/companies",
        "deals": "https://api.hubapi.com/crm/v3/objects/deals",
        "tickets": "https://api.hubapi.com/crm/v3/objects/tickets",
    }

    url = "https://api.hubapi.com/crm/v3/objects/contacts"

    
    all_items: list[IntegrationItem] = []

    for object_type, url in object_types.items():
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            results = response.json().get("results", [])
            for result in results:
                result["objectType"] = object_type  # Tag the type
                item =await create_integration_item_metadata_object(result)
                all_items.append(item)
        else:
            print(f"Error fetching {object_type}: {response.text}")

    print("Fetched Integration Items:", all_items)
    return all_items