import requests, urllib3
from datetime import datetime, timezone, timedelta
urllib3.disable_warnings()

AUTH = ("atp_operations", "ATPOperations_2025")
H = {"kbn-xsrf": "true", "Content-Type": "application/json"}
IDX = "http-rest-service-*"

ahora = datetime.now(timezone.utc)
ini = (ahora - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
fin = ahora.strftime("%Y-%m-%dT%H:%M:%S.000Z")
print("Rango:", ini, fin)

URLS = [
    "http://localhost:8088/api/console/proxy?path=http-rest-service-*/_search&method=POST",
    "https://localhost:8088/api/console/proxy?path=http-rest-service-*/_search&method=POST",
    "https://localhost:8443/api/console/proxy?path=http-rest-service-*/_search&method=POST",
    "http://localhost:8084/http-rest-service-*/_search",
    "https://localhost:8443/http-rest-service-*/_search",
]

for url in URLS:
    try:
        r = requests.post(url, auth=AUTH, headers=H, verify=False, timeout=10,
            json={"size": 0, "track_total_hits": True, "query": {"match_all": {}}})
        print("STATUS:", r.status_code, "URL:", url)
        if r.status_code == 200:
            t = r.json().get("hits", {}).get("total", {})
            print("TOTAL:", t.get("value", 0) if isinstance(t, dict) else t)
    except Exception as e:
        print("ERROR:", str(e)[:60], url)