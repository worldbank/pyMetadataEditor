import json
from typing import Dict, Union

import pandas as pd
import requests
from requests.exceptions import HTTPError

from .schemas import validate_metadata

MetadataDict = Dict[str, Union[str, Dict]]


class MetadataEditor:
    def __init__(self, api_key: str):
        """
        MetadataEditor allows you to list and create projects on the World Bank metadataeditorqa.
        First obtain an API key by logging into the editor (https://metadataeditorQA.worldbank.org) and go to your user
        profile page where you will see an option at the bottom to generate an API key.

        Then run

            from pymetadataeditor import MetadataEditor

            api_key = "<the api key you generated on https://metadataeditorQA.worldbank.org>"
            me = MetadataEditor(api_key)

        Then you can list and create new projects like so:

            me.list_projects()
            me.create_timeseries(metadata={"idno": "<unique id of your metadata>", <other metadata>})
        """
        if not isinstance(api_key, str):
            raise ValueError(f"api_key must be a string but a '{type(api_key)}' was passed")
        self.api_key = api_key

    def get_api_key(self) -> str:
        return self.api_key

    def _request(self, method: str, url: str, **kwargs) -> Dict:
        """
        Sends a GET or POST request to the specified URL with the API key in the headers and returns the JSON response.

        Args:
            url (str): The URL to which the GET or POST request is sent.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.

        Raises:
            ValueError: If the URL does not start with 'https'.
            PermissionError: If the response status code is 403, indicating that access is denied.
            Exception: If the request fails due to other HTTP errors, with details of the status code and response text.
            Exception: If any other unexpected error occurs during the request.
        """
        method = method.lower()
        assert method in ["get", "post"], f"unknown method {method}"
        if method == "post":
            assert "json" in kwargs, "when using post, json cannot be none"

        if not url.startswith("https://"):
            raise ValueError(f"URL must start with 'https://' not {url[:8]}")

        try:
            response = requests.request(method, url, headers={"x-api-key": self.api_key}, **kwargs)
            response.raise_for_status()
        except HTTPError as e:
            if response.status_code == 403:
                raise PermissionError(f"Access Denied. Check that the API key '{self.api_key}' is correct")
            else:
                raise Exception(
                    f"Status Code: {response.status_code}, Response: {json.loads(response.text)['message']}"
                ) from e
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {str(e)}") from e
        return response.json()

    def _get_request(self, url: str) -> Dict:
        """
        Args:
            url (str): The URL to which the GET request is sent.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("get", url=url)

    def _post_request(self, url: str, metadata: MetadataDict):
        """
        Args:
            url (str): The URL to which the POST request is sent.
            metadata (dict): The metadata to be sent with the POST request.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        self._request("post", url=url, json=metadata)

    def list_projects(self) -> pd.DataFrame:
        """
        Lists all the projects associated with your API key which are listed at
        https://metadataeditorqa.worldbank.org/

        Returns:
            pd.DataFrame: Projects sorted by the date on which they were created
        """
        list_projects_get_url = "https://metadataeditorqa.worldbank.org/index.php/api/editor"
        response = self._get_request(list_projects_get_url)
        projects = response["projects"]

        return pd.DataFrame.from_dict(projects).set_index("id").sort_values("created")

    def get_project_by_id(self, id: Union[str, int]):
        """"""
        get_project_template = "https://metadataeditorqa.worldbank.org/index.php/api/editor/{}"
        get_project_url = get_project_template.format(id)
        response = self._get_request(get_project_url)
        project_collection = response["project"]
        return pd.Series(project_collection)

    def create_timeseries(self, metadata: MetadataDict):
        """
        Creates a record of your *timeseries* metadata on https://metadataeditorqa.worldbank.org/

        Args:
            metadata (dict): The timeseries metadata to be recorded
        """
        validate_metadata(metadata, "TimeSeries")

        post_request_url = "https://metadataeditorqa.worldbank.org/index.php/api/editor/create/timeseries"
        self._post_request(post_request_url, metadata=metadata)
