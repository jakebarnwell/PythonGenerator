import urllib
import urllib2
import time
import hashlib
import hmac
import binascii

req = urllib2.Request("http://localhost:56151/testWebsite/")
r = urllib2.urlopen(req)
print r.read()

methodType = "GET"
host = "https://api.tradeking.com"
path = "/v1/accounts/balances.xml"

strTime = str(int(time.time()))

#0auth headers
auth_consumer_key = urllib.quote_plus("&oauth_consumer_key=################")
auth_token = urllib.quote_plus("&oauth_token=################")
auth_signature_method = urllib.quote_plus("&oauth_signature_method=HMAC-SHA1")
auth_timestamp = urllib.quote_plus("&oauth_timestamp=" + strTime)
auth_nonce = urllib.quote_plus("&oauth_nonce=" + hashlib.sha224(strTime).hexdigest())



base_string = methodType + "&" + urllib.quote_plus(host) + urllib.quote_plus(path) + "&" + auth_consumer_key + auth_nonce + auth_signature_method + auth_timestamp + auth_token

#print base_string

secret = urllib.quote_plus("################")
token_secret = urllib.quote_plus("################")

key = secret + "&" + token_secret

try:
    import hashlib # 2.5
    hashed = hmac.new(key, base_string, hashlib.sha1)
except:
    import sha # Deprecated
    hashed = hmac.new(key, base_string, sha)

# Calculate the digest base 64.
auth_signature2 = "oauth_signature=\"" + binascii.b2a_base64(hashed.digest())[:-1] + "\""

auth_Authversion2 = "OAuth oauth_version=\"1.0\""
auth_consumer_key2 = "oauth_consumer_key=\"################\""
auth_token2 = "oauth_token=\"################\""
auth_signature_method2 = "oauth_signature_method=\"HMAC-SHA1\""

auth_timestamp2 = "oauth_timestamp=\"" + strTime + "\""
auth_nonce2 = "oauth_timestamp=\"" + hashlib.sha224(strTime).hexdigest() + "\""

req = urllib2.Request(host + path)
#req.add_header('Referer', 'http://www.python.org/')
req.add_header("Authorization", auth_Authversion2 + "," + auth_consumer_key2 + "," + auth_token2 + "," + auth_signature_method2 + "," + auth_signature2 + "," + auth_timestamp2 + "," + auth_nonce2)
r = urllib2.urlopen(req)
print r.read()
