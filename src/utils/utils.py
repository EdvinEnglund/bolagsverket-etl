import zipfile
import io

# --- Unzip helper ---
def unzip_documents(zip_bytes):
    xml_files = []
    if zip_bytes is None:
        return xml_files
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in z.namelist():
                if name.endswith(".xml") or name.endswith(".xhtml"):
                    with z.open(name) as f:
                        xml_files.append(f.read().decode("utf-8"))
    except Exception as e:
        print(f"Couldn't unzip documents: {e}")

    return xml_files if len(xml_files) > 0 else None