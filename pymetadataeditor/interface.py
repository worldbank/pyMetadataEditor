from typing import Dict, Union

import pandas as pd
import requests
from requests.exceptions import HTTPError

MetadataDict = Dict[str, Union[str, Dict]]


class MetadataEditor:
    def __init__(self, api_key: str):
        """
        MetadataEditor allows you to list and create collections stored on https://metadataeditorqa.worldbank.org/
        First obtain an API key by logging into the editor (https://metadataeditorQA.worldbank.org) and go to your user
        profile page where you will see an option at the bottom to generate an API key.

        Then run

            from pymetadataeditor import MetadataEditor

            api_key = "<the api key you generated on https://metadataeditorQA.worldbank.org>"
            me = MetadataEditor(api_key)

        Then you can list and create new collections like so:

            me.list_collections()
            me.create_timeseries(metadata={"idno": "<unique id of your metadata>", ...})
        """
        if not isinstance(api_key, str):
            raise ValueError(f"api_key must be a string but a '{type(api_key)}' was passed")
        self.api_key = api_key

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
                    f"Error: Failed to get collections. Status code: {response.status_code} Response: {response.text}"
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

    def list_collections(self) -> pd.DataFrame:
        """
        Lists all the collections associated with your API key which are listed at
        https://metadataeditorqa.worldbank.org/

        Returns:
            pd.DataFrame: Collections sorted by the date on which they were created
        """
        list_collections_get_url = "https://metadataeditorqa.worldbank.org/index.php/api/editor"
        response = self._get_request(list_collections_get_url)
        project_collection = response["projects"]

        return pd.DataFrame.from_dict(project_collection).set_index("id").sort_values("created")

    def _quick_validate_metadata(self, metadata: MetadataDict):
        """
        Checks that the metadata contains the key information that all metadata must have, namely idno

        Args:
            metadata (dict): The metadata to be validated

        Raises:
            ValueError: If the metadata is deemed invalid for whatever reason.

        """
        if not isinstance(metadata, dict):
            raise ValueError(f"Metadata must be passed as a python dictionary, but {type(metadata)} was passed instead")
        required_keys = ["idno"]  # todo(gblackadder) what are the fields all datatypes must have

        for key in required_keys:
            if key not in metadata:
                raise ValueError(f"Metadata is missing required key: '{key}'")

    def create_timeseries(self, metadata: MetadataDict):
        """
        Creates a record of your *timeseries* metadata on https://metadataeditorqa.worldbank.org/

        Args:
            metadata (dict): The timeseries metadata to be recorded
        """
        self._quick_validate_metadata(metadata)

        post_request_url = "https://metadataeditorqa.worldbank.org/index.php/api/editor/create/timeseries"
        self._post_request(post_request_url, metadata=metadata)
