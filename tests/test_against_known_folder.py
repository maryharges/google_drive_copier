import json
import yaml

from services import assessments
from services import google_drive_helpers

if __name__ == "__main__":
    # load config
    config = yaml.safe_load(open("../config.yaml"))
    file_id = config["test_case_id"]

    # get credentials and instantiate Google Drive connection and object
    credentials = google_drive_helpers.get_credentials()
    if credentials:
        google_drive = google_drive_helpers.GoogleDrive(credentials, config)

        assessments.assessment_one(google_drive, file_id)
        assessments.assessment_two(google_drive, file_id)
        assessments.assessment_three(google_drive, file_id)

    expected_r1 = {
        "num_folders": 1,
        "num_files": 4,
        "total_objects": 5
    }

    expected_r2 = {
        "total_nested_files": 6,
        "total_nested_folders": 2,
        "nested_object_counts_by_folder": {
            "Test Folder 2": 3
        },
        "total_nested_object_count": 8
    }

    with open("reports/assessment_1_report.json") as f:
        actual_r1 = json.load(f)

    print(f"Expected matches actual for assessment 1: {actual_r1 == expected_r1}")

    with open("reports/assessment_2_report.json") as f:
        actual_r2 = json.load(f)

    print(f"Expected matches actual for assessment 1: {actual_r2 == expected_r2}")

