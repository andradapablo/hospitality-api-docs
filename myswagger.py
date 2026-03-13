from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, HTMLResponse
import os
import json

app = FastAPI(docs_url=None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OPENAPI_DIR = os.path.join(BASE_DIR, "rest-api-specs/property")


@app.get("/openapi/{file_name:path}")
def openapi_file(file_name: str):

    path = os.path.join(OPENAPI_DIR, file_name)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    with open(path) as f:
        data = json.load(f)

    return JSONResponse(data)


@app.get("/swagger/{file_name:path}")
def swagger(file_name: str):

    return get_swagger_ui_html(
        openapi_url=f"/openapi/{file_name}",
        title=file_name
    )


@app.get("/docs", response_class=HTMLResponse)
def list_docs():

    entries = []

    for root, _, filenames in os.walk(OPENAPI_DIR):

        for name in filenames:

            if name.endswith(".json"):

                full = os.path.join(root, name)
                rel = os.path.relpath(full, OPENAPI_DIR)

                with open(full) as f:
                    data = json.load(f)

                title = data.get("info", {}).get("title", name)

                title = title.replace("OPERA Cloud", "")
                title = title.replace("API", "")
                title = " ".join(title.split())

                entries.append((rel, title))

    entries.sort(key=lambda x: x[1])

    links = "\n".join(
        f'<li><a href="/swagger/{f}">{title}</a> <small>({f})</small></li>'
        for f, title in entries
    )

    html = f"""
    <html>
    <head>
        <title>Oracle Hospitality APIs</title>
    </head>
    <body>
        <h1>Available APIs</h1>
        <ul>
        {links}
        </ul>
    </body>
    </html>
    """

    return html