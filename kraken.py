import urllib.parse
import hashlib
import hmac
import base64
from time import time
from env import kraken_secret, kraken_api_key
import requests

def get_kraken_signature(urlpath, data):
	postdata = urllib.parse.urlencode(data)
	encoded = (str(data['nonce']) + postdata).encode()
	message = urlpath.encode() + hashlib.sha256(encoded).digest()
	mac = hmac.new(base64.b64decode(kraken_secret), message, hashlib.sha512)
	sigdigest = base64.b64encode(mac.digest())
	return sigdigest.decode()

# Read Kraken API key and secret stored in environment variables
api_url = "https://api.kraken.com"

# Attaches auth headers and returns results of a POST request
def kraken_request(uri_path, data={}):
	data["nonce"] = str(int(1000*time()))
	headers = {}
	headers['API-Key'] = kraken_api_key
	# get_kraken_signature() as defined in the 'Authentication' section
	headers['API-Sign'] = get_kraken_signature(uri_path, data)
	req = requests.post((api_url + uri_path), headers=headers, data=data)
	return req.json()['result']
