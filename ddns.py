#!/usr/bin/env python3

from flask import Flask, request, Response
import os
import requests
import json
import logging
import configparser

### TO CALL IT
#
# https://[DDNS_USERNAME]:[DDNS_PASSWORD]@your-server.com:[DDNS_PORT]/?domain=<domain_you_wish_to_update>
# IP will be the one from the client calling the endpoint
# I tested it behind nginx reverse proxy with success
#
### CONFIG FILE config.ini
#
#[credentials]
#username = your_username
#password = your_password
#
#[cloudflare]
#api_token = your_token
#zone_id = your_zone_id
#
#[server]
#port = 5000

# Load configuration
config = configparser.ConfigParser()
config.read('/home/jpfranca/ddns/config.ini')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure Flask to trust the X-Forwarded-For header
app.config['PROXY_FIX'] = True
# Import and apply ProxyFix after configuring
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Use configuration values
DDNS_USERNAME = config.get('credentials', 'username', fallback='ddns')
DDNS_PASSWORD = config.get('credentials', 'password', fallback='pass123')
DDNS_CF_API_TOKEN = config.get('cloudflare', 'api_token', fallback='')
DDNS_CF_ZONE_ID = config.get('cloudflare', 'zone_id', fallback='')
DDNS_PORT = config.getint('server', 'port', fallback=5000)

def update_cloudflare_dns(domain, ip_address):
    """
    Update a Cloudflare DNS record to point to the given IP address
    """
    if not DDNS_CF_API_TOKEN or not DDNS_CF_ZONE_ID:
        logger.error("Cloudflare API credentials not configured")
        return False, "Cloudflare API credentials not configured"
    
    # First, get the existing DNS record ID
    headers = {
        "Authorization": f"Bearer {DDNS_CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Extract domain name from domain parameter
    # If domain is subdomain.example.com, we only need the subdomain part for the DNS record name
    domain_parts = domain.split('.')
    record_name = domain
    if len(domain_parts) > 2:
        # This is a subdomain, extract the subdomain part
        record_name = domain_parts[0]
    
    # Get existing records
    try:
        records_url = f"https://api.cloudflare.com/client/v4/zones/{DDNS_CF_ZONE_ID}/dns_records"
        params = {"name": domain}
        response = requests.get(records_url, headers=headers, params=params)
        response.raise_for_status()
        
        records = response.json()
        if records["success"] and len(records["result"]) > 0:
            # Record exists, update it
            record_id = records["result"][0]["id"]
            update_url = f"https://api.cloudflare.com/client/v4/zones/{DDNS_CF_ZONE_ID}/dns_records/{record_id}"
            
            data = {
                "type": "A",
                "name": record_name,
                "content": ip_address,
                "ttl": 60,  # Short TTL for DDNS
                "proxied": False  # Typically false for DDNS
            }
            
            update_response = requests.put(update_url, headers=headers, data=json.dumps(data))
            update_response.raise_for_status()
            
            if update_response.json()["success"]:
                logger.info(f"DNS record for {domain} updated to {ip_address}")
                return True, f"DNS record for {domain} updated to {ip_address}"
            else:
                logger.error(f"Failed to update DNS record: {update_response.json()}")
                return False, f"Failed to update DNS record: {update_response.json()}"
        else:
            # Record doesn't exist, create it
            create_url = f"https://api.cloudflare.com/client/v4/zones/{DDNS_CF_ZONE_ID}/dns_records"
            
            data = {
                "type": "A",
                "name": record_name,
                "content": ip_address,
                "ttl": 60,  # Short TTL for DDNS
                "proxied": False  # Typically false for DDNS
            }
            
            create_response = requests.post(create_url, headers=headers, data=json.dumps(data))
            create_response.raise_for_status()
            
            if create_response.json()["success"]:
                logger.info(f"DNS record for {domain} created with IP {ip_address}")
                return True, f"DNS record for {domain} created with IP {ip_address}"
            else:
                logger.error(f"Failed to create DNS record: {create_response.json()}")
                return False, f"Failed to create DNS record: {create_response.json()}"
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with Cloudflare API: {str(e)}")
        return False, f"Error communicating with Cloudflare API: {str(e)}"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def display_auth_info(path):
    # Get the original client IP address (considering proxies)
    client_ip = request.remote_addr
    x_real_ip = request.headers.get('X-Real-IP')
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    
    # Try different headers to get the real client IP
    if x_real_ip:
        client_ip = x_real_ip
    elif x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[0].strip()
        
    # Get authorization info from the request
    auth = request.authorization
    
    # Get query parameters (now using domain instead of hostname)
    query_params = request.args
    domain = query_params.get('domain', '')
    
    # Verify credentials
    if auth and auth.username == DDNS_USERNAME and auth.password == DDNS_PASSWORD:
        # Valid credentials - log the information
        logger.info(f"Username: {auth.username}")
        logger.info(f"Client IP: {client_ip}")
        logger.info(f"Domain: {domain}")
        
        # Update Cloudflare DNS if domain is provided
        if domain and domain != '[DOMAIN]':
            success, message = update_cloudflare_dns(domain, client_ip)
            logger.info(message)
            # Return a simple OK response with the DNS update status
            return message if success else f"Error: {message}", 200 if success else 500
        else:
            logger.warning("No valid domain provided, DNS not updated")
            return "No valid domain provided", 400
    else:
        # Log failed attempt
        if auth:
            logger.warning(f"Failed login attempt - Username: {auth.username}")
        else:
            logger.warning("No authorization provided")
        logger.warning(f"Client IP: {client_ip}")
        
        # Return unauthorized response
        return Response(
            "Unauthorized", 
            401,
            {'WWW-Authenticate': 'Basic realm="Authentication Required"'}
        )

if __name__ == '__main__':
    port = int(DDNS_PORT)
   
    app.run(host='127.0.0.1', port=port, debug=True)
