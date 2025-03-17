# Cloudflare DDNS Updater

A simple Flask-based Dynamic DNS (DDNS) updater service that allows you to automatically update your Cloudflare DNS records with your current IP address. This is particularly useful for home servers with dynamic IP addresses.

## Features

- Automatically updates Cloudflare DNS records with your current public IP address
- Basic authentication for secure access
- Works behind reverse proxies (like Nginx)
- Handles both subdomains and apex domains
- Simple HTTP endpoint that can be called from any device
- Configurable via config file
- Systemd service integration for reliable operation

## Prerequisites

- Python 3.6+
- A Cloudflare account with:
  - An API token with DNS editing permissions
  - A zone ID for your domain

## Dependencies

- Flask
- Requests
- Configparser (included in Python standard library)
- Werkzeug (installed with Flask)

To install the required dependencies:

```bash
pip install flask requests
```

## Setup

1. Clone this repository or download the script files:

```bash
git clone https://github.com/yourusername/cloudflare-ddns.git
cd cloudflare-ddns
```

2. Create a configuration file named `config.ini` with the following structure:

```ini
[credentials]
username = your_ddns_username
password = your_ddns_password

[cloudflare]
api_token = your_cloudflare_api_token
zone_id = your_cloudflare_zone_id

[server]
port = 5000
```

3. Replace the placeholder values with your actual credentials:
   - `username` and `password`: Create secure credentials for accessing the DDNS service
   - `api_token`: Your Cloudflare API token with DNS edit permissions
   - `zone_id`: Your Cloudflare zone ID for the domain
   - `port`: The port on which the service will listen (default: 5000)

## Running the Service

### Manual Execution

You can run the script manually using Python:

```bash
python3 ddns.py
```

### Setting up as a Systemd Service

1. Copy the provided `ddns.service` file to your systemd services directory:

```bash
sudo cp ddns.service /etc/systemd/system/
```

2. Edit the service file to match your installation path and user:

```bash
sudo nano /etc/systemd/system/ddns.service
```

Make sure to update the following lines with your actual paths and username:
```
User=yourusername
WorkingDirectory=/path/to/your/ddns
ExecStart=/usr/bin/python3 /path/to/your/ddns/ddns.py
```

3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ddns.service
sudo systemctl start ddns.service
```

4. Check the service status:

```bash
sudo systemctl status ddns.service
```

## Usage

To update your DNS record, make an HTTP request to the service with your domain as a query parameter:

```
https://[your_ddns_username]:[your_ddns_password]@your-server.com:[port]/?domain=yourdomain.com
```

Or if you're using a reverse proxy like Nginx:

```
https://[your_ddns_username]:[your_ddns_password]@ddns.your-domain.com/?domain=yourdomain.com
```

### Example with curl

```bash
curl -u "your_ddns_username:your_ddns_password" "http://your-server.com:5000/?domain=yourdomain.com"
```

The service will automatically detect your public IP address from the request and update the specified domain's A record in Cloudflare.

## Nginx Reverse Proxy Configuration (Optional)

If you want to access the service through a domain name instead of an IP:port combination, you can set up an Nginx reverse proxy. Here's a sample configuration:

```nginx
server {
    listen 80;
    server_name ddns.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

- Check the systemd logs for errors:
  ```bash
  journalctl -u ddns.service
  ```

- Verify your config.ini file has the correct permissions and is readable by the service user

- Make sure your Cloudflare API token has the correct permissions (Zone:DNS:Edit)

- If you're having trouble with IP detection behind a proxy, check that the X-Forwarded-For headers are being properly passed

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
