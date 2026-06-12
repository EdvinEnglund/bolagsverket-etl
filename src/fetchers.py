import requests
from dotenv import load_dotenv
import os
import uuid
import zipfile
import io

# API Functions
def get_token():
    load_dotenv()
    url = "https://portal.api.bolagsverket.se/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("BV_CLIENT"),
        "client_secret": os.getenv("BV_SECRET"),
        "scope": "vardefulla-datamangder:read vardefulla-datamangder:ping"
    }
    response = requests.post(url, data=data)

    if response.status_code != 200:
        print(f"Http Error: Get token status: {response.status_code}")

    response = response.json()
    return response["access_token"]

def get_bv_data(token, org_no):
    url = f"https://gw.api.bolagsverket.se/vardefulla-datamangder/v1/organisationer"
    request_id = str(uuid.uuid4())
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-Request-Id": f"{request_id}",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "identitetsbeteckning": f"{org_no}"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Http Error: Get bv data status: {response.status_code}")
    return response.json()

def get_doc_list(token, org_no):
    url = f"https://gw.api.bolagsverket.se/vardefulla-datamangder/v1/dokumentlista"
    request_id = str(uuid.uuid4())
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-Request-Id": f"{request_id}",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "identitetsbeteckning": f"{org_no}"
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"Http Error: Get doc list status: {response.status_code}")
        doc_list = response.json()["dokument"]
    except:
        print(f"Couldn't get doc list for org.no {org_no}")
        doc_list = []
    return doc_list

def get_doc_zip_bytes(token, doc_id):
    url = f"https://gw.api.bolagsverket.se/vardefulla-datamangder/v1/dokument/{doc_id}"

    headers = {
        "accept": "application/zip",
        "X-Request-Id": str(uuid.uuid4()),
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Http Error: Get token status: {response.status_code}")

    response.raise_for_status()
    return response.content

def unzip_documents(zip_bytes):
    xml_files = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            if name.endswith(".xml") or name.endswith(".xhtml"):
                with z.open(name) as f:
                    xml_files.append(f.read().decode("utf-8"))
    return xml_files

def get_latest_report(token, org_no):

    doc_list = get_doc_list(token, org_no)

    if len(doc_list) == 0:
        print(f"No documents to download for {org_no}")
        return None
    doc_id = doc_list[-1]["dokumentId"]
    zip_bytes = get_doc_zip_bytes(token = token, doc_id= doc_id)
    documents = unzip_documents(zip_bytes)
    if len(documents) == 0:
        return None
    # first index is annual report, second is revisionsberättelse (accountant statement)
    return documents[0]


if __name__ == "__main__":
    org_no = "5566086483"
    token = get_token()

    report = get_latest_report(token, org_no)

    #save_report_file(report, org_no = org_no)
