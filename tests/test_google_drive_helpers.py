from unittest import TestCase
from unittest.mock import Mock, MagicMock

from services.google_drive_helpers import GoogleDrive


class TestGoogleDrive(TestCase):
    def setup(self):
        """
        Run setup of commonly used objects / mocks / expectations
        :return:
        """
        self.test_response = {
            "files": ["one"]
        }
        self.test_response_two = {
            "files": ["two"]
        }

        self.mock_drive = Mock()
        self.mock_drive.type_folder = "application/vnd.google-apps.folder"
        self.mock_files = self.mock_drive.connection.files()

        self.mock_request = MagicMock()

        self.expected_files_and_folders = {
            "folder_id": "folder-id",
            "folders": [
                {
                    "folder_id": "123",
                    "folder_name": "test_folder",
                    "child_objects": {},
                    "nested_object_count": 0,
                }

            ],
            "files": [
                {
                    "file_id": "321",
                    "file_name": "test_file"
                }
            ],
            "local_object_count": 2,
        }
        self.child_object = {
            "folder_id": "123",
            "folders": [],
            "files": [
                {
                    "file_id": "456789",
                    "file_name": "Untitled spreadsheet 1"
                },
            ],
            "local_object_count": 1
        }
        self.test_drive_data = {
            "folder_id": "folder-id",
            "folders": [
                {
                    "folder_id": "123",
                    "folder_name": "test_folder",
                    "child_objects": self.child_object,
                    "nested_object_count": 1
                },
            ],
            "files": [
                {
                    "file_id": "321",
                    "file_name": "test_file"
                },
            ],
            "local_object_count": 2
        }

    def test_pagination_helper_no_next_page(self):
        # run setup
        self.setup()
        
        # except no next page for pagination helper
        self.mock_drive.connection.files().list_next.return_value = None
        # assert we get the response we expect
        self.assertEqual(self.test_response, GoogleDrive.pagination_helper(
            self.mock_drive, self.mock_request, self.test_response
        ))

    def test_pagination_helper_next_page(self):
        # run setup
        self.setup()

        # loop through 1x, return our second test response
        self.mock_files.list_next.side_effect = [self.mock_request, None]
        self.mock_request.execute.return_value = self.test_response_two

        # assert we get the stuff we expect
        expected_response = {
            "files": ["one", "two"]
        }
        self.assertEqual(expected_response, GoogleDrive.pagination_helper(
            self.mock_drive, self.mock_request, self.test_response
        ))

    def test_get_files_and_folders_incomplete_search(self):
        # run setup
        self.setup()

        # set expectations
        self.mock_files.list.return_value = self.mock_request
        self.mock_request.execute.return_value = {
            "incompleteSearch": True
        }
        # get nothing back because we obtained an incomplete Search
        self.assertEqual({}, GoogleDrive.get_files_and_folders(self.mock_drive, "folder-id"))

    def test_get_files_and_folders(self):
        # run setup
        self.setup()
        # set expectations
        self.mock_files.list.return_value = self.mock_request
        self.mock_request.execute.return_value = {
            "incompleteSearch": False,
            "files": [
                {
                    "id": "123",
                    "name": "test_folder",
                    "mimeType": "application/vnd.google-apps.folder"
                },
                {
                    "id": "321",
                    "name": "test_file",
                    "mimeType": "application/vnd.google-apps.sheet"
                }
            ]
        }
        # make sure we match on the expected files and folders
        self.assertEqual(self.expected_files_and_folders,
                         GoogleDrive.get_files_and_folders(self.mock_drive, "folder-id"))

    def test_get_nested_objects_no_nesting(self):
        # run setup
        self.setup()

        # set expectations that there's no nested objects here
        empty_files = {"files": [], "folders": []}
        self.mock_drive.get_files_and_folders.return_value = empty_files
        # ensure we actually get zeros all the way through
        files_and_folders, nested_folders, nested_files = GoogleDrive.get_nested_objects(self.mock_drive, "1234")
        self.assertEqual(0, nested_files)
        self.assertEqual(0, nested_folders)
        self.assertEqual(empty_files, files_and_folders)

    def test_get_nested_objects(self):
        # run setup
        self.setup()

        # test with actual nesting
        self.mock_drive.get_files_and_folders.return_value = self.expected_files_and_folders
        self.mock_drive.get_nested_objects.return_value = self.child_object, 0, 1
        # ensure we see the objects and level of nesting we'd expect
        files_and_folders, nested_folders, nested_files = GoogleDrive.get_nested_objects(self.mock_drive, "1234")
        self.assertEqual(2, nested_files)
        self.assertEqual(1, nested_folders)
        self.assertEqual(self.test_drive_data, files_and_folders)

    def test_copy_file_fail(self):
        # run setup
        self.setup()

        # throw an HttpError here
        self.mock_files.copy(fileId="test_file_id", body={
            "name": "test_file_name",
            "parents": ["test_destination_id"]
        }).execute.side_effect = HttpError("error")

        # ensure it raises
        self.assertRaises(
            HttpError, GoogleDrive.copy_file, self.mock_drive, "test_file_id", "test_file_name", "test_destination_id"
        )

    def test_copy_file(self):
        # run setup
        self.setup()
        # simple successful copy execution
        self.mock_files.copy.execute.return_value = None
        self.assertTrue(GoogleDrive.copy_file(self.mock_drive, "test_file_id", "test_file_name", "test_destination_id"))

    def test_copy_folder(self):
        # run setup
        self.setup()
        # simple successful folder creation
        self.mock_drive.copy_exact_filename = True
        self.mock_files.create(
            {"name": "folder-name", "mimeType": self.mock_drive.type_folder}
        ).execute.return_value = {"id": "copied-folder-id"}
        self.assertEqual("copied-folder-id", GoogleDrive.copy_folder(self.mock_drive, "folder-name"))

    def test_copy_folder_fail(self):
        # run setup
        self.setup()
        self.mock_drive.copy_exact_filename = True
        # throw an HTTP error here
        self.mock_files.create(
            {"name": "folder-name", "mimeType": self.mock_drive.type_folder}
        ).execute.side_effect = HttpError("error")
        # ensure it raises
        self.assertRaises(HttpError, GoogleDrive.copy_folder, self.mock_drive, "folder-name")

    def test_copy_nested_items(self):
        # run setup
        self.setup()

        self.mock_files.get("folder-id").execute.return_value = {
            "mimeType": self.mock_drive.type_folder,
            "name": "test folder name"
        }
        self.mock_drive.copy_folder.side_effect = ["test-destination-parent-id", "second-id"]
        self.mock_drive.copy_file.return_value = True

        self.assertEqual(
            "test-destination-parent-id", GoogleDrive.copy_nested_items(self.mock_drive, self.test_drive_data)
        )
        # this test is failure simple since we run through a lot of the steps already in other tests
        # ensure we call ourselves recursively once
        self.mock_drive.copy_nested_items.assert_called_once()
        self.mock_drive.copy_file.assert_called_once()


class HttpError(Exception):
    pass


if __name__ == "__main__":
    TestGoogleDrive(
        "runTest"
    )
