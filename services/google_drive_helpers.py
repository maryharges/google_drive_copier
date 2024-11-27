import logging
import os.path
from json import JSONDecodeError

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive"]

logger = logging.getLogger(__name__)


def get_credentials() -> Credentials | None:
    """
    credential helper for Google Drive -- this code was largely borrowed from the python quickstart
    from their documentation
    :return:
    """
    local_creds = None
    if os.path.exists("token.json"):
        try:
            local_creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except JSONDecodeError as e:
            logger.error(f"Could not load token.json with JSONDecodeError: {e}")
            return
        except Exception as e:
            # note: normally would try to be more specific than this
            logger.error(f"Could not load token.json with unknown error: {e}")
            return

    if not local_creds or not local_creds.valid:
        if local_creds and local_creds.expired and local_creds.refresh_token:
            local_creds.refresh(Request())
        else:
            if os.path.exists("credentials.json"):
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json",
                    SCOPES,
                )
                local_creds = flow.run_local_server(port=0)
            else:
                logger.error(
                    "Please refer to README on instructions for generating credentials.json"
                )
                return

        # Save the token for the next run
        with open("token.json", "w") as token:
            token.write(local_creds.to_json())
    return local_creds


class GoogleDrive:
    """
    A class used to represent our Google Drive API connection
    :param credentials: the token credentials for our api connection
    """

    def __init__(self, credentials: Credentials, config: dict):
        self.connection = build("drive", "v3", credentials=credentials)
        self.type_folder = "application/vnd.google-apps.folder"
        self.copy_exact_filename = config["copy_exact_filename"]

    def pagination_helper(self, last_request, last_response) -> dict:
        """
        a pagination helper for listing files
        :param last_request: the last list files request
        :param last_response: the last list files response
        :return: a response object with the full list of file items
        """
        response = {x: last_response[x] for x in last_response if x != "nextPageToken"}
        while True:
            new_request = self.connection.files().list_next(last_request, last_response)
            # from documentation - new request will be `None` if there is not another page of results
            if not new_request:
                break
            new_response = new_request.execute()
            response["files"] += new_response["files"]
            last_response = new_response
            last_request = new_request
        return response

    def get_files_and_folders(self, folder_id) -> dict:
        """
        gets the files and folders given a folder ID
        :param folder_id: the folder id to pull from
        :return:
        """
        try:
            request = self.connection.files().list(q=f"'{folder_id}' in parents")
            response = request.execute()
            if response["incompleteSearch"]:
                # ToDo investigate a better response if incomplete search is True rather than total failure
                logger.error(f"Unable to get full data: {response}")
                return {}
            if "nextPageToken" in response.keys():
                # if there is a nextPageToken we need to handle pagination for the folder
                response = self.pagination_helper(request, response)
            all_items = response["files"]
            folders, other_files = [], []
            for file_item in all_items:
                # Note: do we need to consider weird behavior here? Like is it possible you could put the parent
                # folder in one of the child folders and create some infinite self-referencing loop?
                if file_item["mimeType"] == self.type_folder:
                    folders.append(
                        {
                            "folder_id": file_item["id"],
                            "folder_name": file_item["name"],
                            "child_objects": {},
                            "nested_object_count": 0,
                        }
                    )
                else:
                    other_files.append(
                        {"file_id": file_item["id"], "file_name": file_item["name"]}
                    )
            return {
                "folder_id": folder_id,
                "folders": folders,
                "files": other_files,
                "local_object_count": len(all_items),
            }
        except HttpError as httpError:
            logger.error(f"get files and folders failed with HttpError: {httpError}")

    def get_nested_objects(self, file_id) -> tuple[dict, int, int]:
        """

        :param file_id: the file id to pull from
        :return:
        """
        # Note: could flag with something like a boolean value called copy to run copy commands at certain
        # stages like this
        # if copy:
        #     parent_object_info = self.drive.files().get(fileId=self.file_id).execute()
        #     self.parent_copy_id = self.copy_folder(parent_object_info['name'])

        files_and_folders = self.get_files_and_folders(file_id)
        # grab the number of files and folders in this source file_id to start our count
        total_nested_folders = len(files_and_folders["folders"])
        total_nested_files = len(files_and_folders["files"])
        # escape clause - we don't have any more nested objects
        if total_nested_folders == 0:
            return files_and_folders, total_nested_folders, total_nested_files

        # recursively get nested objects for each folder
        for folder in files_and_folders["folders"]:
            child_objects, folder_count, file_count = self.get_nested_objects(
                folder["folder_id"]
            )

            # let's store and count the nested child objects
            folder["child_objects"] = child_objects
            folder["nested_object_count"] += folder_count + file_count
            # add the nested counter values
            total_nested_folders += folder_count
            total_nested_files += file_count
        return files_and_folders, total_nested_folders, total_nested_files

    def copy_file(self, file_id, file_name=None, destination_folder_id=None) -> bool:
        """
        Copies a file given an id
        :param file_id: the file id to copy
        :param file_name: name of the new file (optional, if not provided the name will be 'Copy "original file name"')
        :param destination_folder_id: the parent id to copy the file to, if not it will drop it in the main part of the
        drive
        :return:
        """
        file_configuration = {}
        # set our configuration options if they have been provided
        if file_name:
            file_configuration["name"] = file_name
        if destination_folder_id:
            file_configuration["parents"] = [destination_folder_id]
        # try our copy file
        try:
            self.connection.files().copy(
                fileId=file_id, body=file_configuration
            ).execute()
            return True
        except HttpError as httpError:
            logging.error(f"copy file failed with HttpError: {httpError}")

    def copy_folder(self, folder_name: str, destination_folder_id: str = None) -> str:
        """
        Creates a "copy" of a folder. Drive does not support direct copies, so we just create a new folder with
        the existing name in a given destination (if provided, otherwise folder will go to main part of Drive)
        :param folder_name: name of the folder we're copying
        :param destination_folder_id: the destination id for the copy of the folder
        :return:
        """
        # set our configuration options
        folder_configuration = {
            "name": folder_name,
            "mimeType": self.type_folder,
        }
        if destination_folder_id:
            folder_configuration["parents"] = [destination_folder_id]
        # run our copy folder
        try:
            folder = (
                self.connection.files()
                .create(body=folder_configuration, fields="id")
                .execute()
            )
            return folder["id"]
        except HttpError as httpError:
            logging.error(f"create/copy folder failed with HttpError: {httpError}")

    def copy_nested_items(
        self, drive_data: dict, destination_folder_id: str = None
    ) -> str:
        """
        recursively create folders and copy files given the Google Drive data
        :param destination_folder_id: where we're copying to, if not specified we create a place
        :param drive_data: the Google Drive data we're copying
        :return:
        """
        # if there is no destination set, assume this is the first run from the source folder, we want to get the
        # info for our starting place
        if not destination_folder_id:
            # pull source info from the parent folder ID in the drive_data object
            try:
                source_file_info = (
                    self.connection.files()
                    .get(fileId=drive_data["folder_id"])
                    .execute()
                )
                if source_file_info["mimeType"] != self.type_folder:
                    self.copy_file(drive_data["folder_id"], source_file_info["name"])
                    logger.warning(
                        f"Source id of drive data is not folder type, copied file."
                    )
                    return ""
                else:
                    # the source folder is a folder type, so create our destination to copy to
                    destination_folder_id = self.copy_folder(source_file_info["name"])
            except HttpError as err:
                logging.error(f"get source file info failed with HttpError: {err}")
                return ""

        # copy our folders
        for folder in drive_data["folders"]:
            # create the new folder in the new destination
            new_folder_id = self.copy_folder(
                folder["folder_name"], destination_folder_id
            )
            logger.info(
                f"copied folder {folder['folder_name']} to {destination_folder_id} with new id {new_folder_id}"
            )
            # if the folder has children, copy those nested objects
            if folder["nested_object_count"] != 0:
                # as an improvement you could instead write the next iteration data to a queue for ingestion or
                # pass this along to a lambda for processing
                _ = self.copy_nested_items(
                    folder["child_objects"],
                    new_folder_id,
                )
        # copy our files
        for file in drive_data["files"]:
            # check if we want to copy the exact file name (ie Stranger Things -> Stranger Things)
            if self.copy_exact_filename:
                if self.copy_file(
                    file["file_id"],
                    file_name=file["file_name"],
                    destination_folder_id=destination_folder_id,
                ):
                    logger.info(f"copied file {file['file_name']} to {destination_folder_id}")
            else:
                # create Copy file (ie Stranger Things -> Copy of Stranger Things)
                if self.copy_file(file["file_id"], destination_folder_id=destination_folder_id):
                    logger.info(f"copied file {file['file_name']} to {destination_folder_id}")
        return destination_folder_id
