from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from app.utils import trigger_report_generation, report_status
from app.database import db  # <-- Add this line

app = FastAPI()

@app.post("/trigger_report")
def trigger():
    report_id = trigger_report_generation()
    return {"report_id": report_id}

@app.get("/get_report")
def get_report(report_id: str):
    status = report_status.get(report_id)

    if status == "Running":
        return {"status": "Running"}

    if status == "Complete":
        return FileResponse(f"reports/report_{report_id}.csv", media_type="text/csv", filename="report.csv")

    report = db.reports.find_one({"report_id": report_id})
    if report:
        if report["status"] == "Complete":
            return FileResponse(f"reports/{report['filename']}", media_type="text/csv", filename="report.csv")
        else:
            return {"status": "Running"}

    return {"status": "Invalid Report ID"}
