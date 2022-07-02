import sys
import requests

url = sys.argv[1]

req = requests.post(url, data={'username':sys.argv[2],'password':sys.argv[3],'matchingPassword':sys.argv[3],'agree':'agree'})

print(req.request.url)
print(req.request.body)
print(req.request.headers)
