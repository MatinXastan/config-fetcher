import os
import requests
import base64
import socket
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_and_decode_content(url):
    # Fetches content from a URL and decodes it if it's Base64 encoded.
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content = response.text
        try:
            decoded_content = base64.b64decode(content.strip()).decode('utf-8')
            return decoded_content.strip().split('\n')
        except Exception:
            return content.strip().split('\n')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from {url}: {e}")
        return []

def extract_ip_port(config_uri):
    # Extracts IP address and port from a config URI.
    try:
        # For vless/trojan: vless://uuid@ip:port...
        match = re.search(r'(vless|trojan)://.*?@(.*?):(\d+)', config_uri)
        if match:
            # For domain names, resolve to IP first
            hostname = match.group(2)
            try:
                ip_address = socket.gethostbyname(hostname)
                return ip_address, int(match.group(3))
            except socket.gaierror:
                return None, None # Could not resolve domain

        # For vmess (which is base64 encoded)
        if config_uri.startswith('vmess://'):
            try:
                decoded_part = base64.b64decode(config_uri[8:]).decode('utf-8')
                add_match = re.search(r'"add":"(.*?)"', decoded_part)
                port_match = re.search(r'"port":"(\d+)"', decoded_part)
                if add_match and port_match:
                    hostname = add_match.group(1)
                    try:
                        ip_address = socket.gethostbyname(hostname)
                        return ip_address, int(port_match.group(1))
                    except socket.gaierror:
                        return None, None # Could not resolve domain
            except Exception:
                return None, None
    except Exception:
        return None, None
    return None, None

def check_server_connectivity(server_ip, port, timeout=2):
    # Checks if a TCP connection can be established to a specific IP and port.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((server_ip, port))
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def test_config(config):
    # Tests a single config and returns it if it's active.
    ip, port = extract_ip_port(config)
    if ip and port:
        if check_server_connectivity(ip, port):
            print(f"  [SUCCESS] {ip}:{port} is reachable.")
            return config
    return None

def main():
    # Main function to run the script.
    urls_str = os.environ.get('CONFIG_URLS')
    if not urls_str:
        print("CONFIG_URLS secret not found or is empty.")
        return

    urls = urls_str.strip().split('\n')
    all_configs = []

    print(f"Processing {len(urls)} URLs...")
    for url in urls:
        if url.strip():
            print(f"Fetching from: {url.strip()}")
            configs = fetch_and_decode_content(url.strip())
            if configs:
                all_configs.extend(configs)

    # Filter valid protocols and remove duplicates
    valid_protocols = ('vless://', 'vmess://', 'trojan://')
    initial_valid_configs = [c for c in all_configs if c and c.strip().startswith(valid_protocols)]
    unique_configs = list(dict.fromkeys(initial_valid_configs))
    
    print(f"\nFound {len(unique_configs)} unique configs. Now testing connectivity...")
    
    active_configs = []
    # Use a thread pool to test configs concurrently for speed
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_config = {executor.submit(test_config, config): config for config in unique_configs}
        for future in as_completed(future_to_config):
            result = future.result()
            if result:
                active_configs.append(result)

    if active_configs:
        output_filename = 'v2ray_configs.txt'
        with open(output_filename, 'w', encoding='utf-8') as f:
            for config in active_configs:
                f.write(config + '\n')
        
        print(f"\n✅ Success! Found {len(active_configs)} active configs.")
        print(f"Output saved to '{output_filename}'.")
    else:
        print("\n⚠️ No active configs found after testing.")

if __name__ == "__main__":
    main()
