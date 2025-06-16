from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.utils import trigger_report_generation, report_status
from app.database import db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/reports", StaticFiles(directory="reports"), name="reports")

@app.post("/trigger_report")
def trigger_report():
    """
    Starts the report generation process and returns a report ID.
    """
    report_id = trigger_report_generation()
    return {"report_id": report_id}

@app.get("/get_report")
def get_report(report_id: str):
    """
    Returns the report file if it's ready, or the current status.
    """
    status = report_status.get(report_id)

    if status == "Running":
        return {"status": "Running"}

    if status == "Complete":
        file_path = f"reports/report_{report_id}.csv"
        return FileResponse(
            file_path,
            media_type="text/csv",
            filename="report.csv"
        )

    report = db.reports.find_one({"report_id": report_id})
    if report:
        if report.get("status") == "Complete":
            return FileResponse(
                f"reports/{report['filename']}",
                media_type="text/csv",
                filename="report.csv"
            )
        return {"status": "Running"}

    return {"status": "Invalid Report ID"}
