import requests
from dotenv import load_dotenv
import os
import uuid
import zipfile
import io
from pathlib import Path

def get_token():
    load_dotenv()
    url = "https://portal.api.bolagsverket.se/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("BV_CLIENT"),
        "client_secret": os.getenv("BV_SECRET"),
        "scope": "vardefulla-datamangder:read vardefulla-datamangder:ping"
    }
    response = requests.post(url, data=data).json()
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
    except:
        print("Couldn't get doc list")
        response = {}
    return response.json()

def get_doc_zip_bytes(token, doc_id):
    url = f"https://gw.api.bolagsverket.se/vardefulla-datamangder/v1/dokument/{doc_id}"

    headers = {
        "accept": "application/zip",
        "X-Request-Id": str(uuid.uuid4()),
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)
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

def save_report_file(report, org_no):

    try:
        if len(report) == 0:
            print("No report to save")
            return ""

        project_root = Path(__file__).resolve().parent.parent

        save_dir = project_root / "data" / "example-xmls"
        save_dir.mkdir(parents=True, exist_ok=True)

        save_path = save_dir / f"{org_no}_report.xml"

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"Saved XML report to: {save_path}")

    except:
        print("Couldn't save report")
    return


def get_latest_report(token, org_no):
    try:
        document_list = get_doc_list(token, org_no)["dokument"]
    except:
        print("Couldn't get doc list")
        return None

    if len(document_list) == 0:
        print(f"No documents to download for {org_no}")
        return None

    doc_id = document_list[-1]["dokumentId"]
    zip_bytes = get_doc_zip_bytes(token = token, doc_id= doc_id)
    documents = unzip_documents(zip_bytes)
    if len(documents) == 0:
        print(f"No documents found for {org_no}")
        return None
    # first index is annual report, second is revisionsberättelse (accountant statement)
    return documents[0]


if __name__ == "__main__":
    org_no = "5561034249"
    token = get_token()
    print(get_bv_data(token, org_no))
    print(get_doc_list(token, org_no))

    report = get_latest_report(token, org_no)

    #save_report_file(report, org_no = org_no)
