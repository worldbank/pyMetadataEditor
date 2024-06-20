import warnings
from typing import Annotated, Dict, List, Optional, Union

import pandas as pd
import requests
from pydantic import BaseModel, ConfigDict, UrlConstraints, model_validator
from pydantic_core import Url
from requests.exceptions import HTTPError, SSLError

from pymetadataeditor.tools import update_metadata, validate_metadata

from .schemas import Datacite, MetadataInformation, Provenance, SeriesDescription, Tag, TimeSeriesMetadataSchema

warnings.filterwarnings(
    "ignore", category=UserWarning, module="pydantic"
)  # suppresses warning when metadata passed as dict instead of a pydantic object


MetadataDict = Dict[str, Union[str, Dict]]

HttpsUrl = Annotated[
    Url,
    UrlConstraints(max_length=2083, allowed_schemes=["https"]),
]


class MetadataEditor(BaseModel):
    """
    MetadataEditor allows you to list and create projects in a metadata database.
    First obtain an API key.

    Then run

        from pymetadataeditor import MetadataEditor

        api_url = <Generally the required URL looks like 'https://<name_of_your_metadata_database>.org/index.php/api'>
        api_key = "<the api key you generated for accessing the metadata database"
        me = MetadataEditor(api_url = api_url, api_key = api_key)

    Then you can list and create new projects like so:

        me.list_projects()
        me.create_timeseries(idno = "<unique id of your metadata>", series_description = {...}, ...)
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    api_url: HttpsUrl
    api_key: str

    @model_validator(mode="after")
    def check_endpoint_accessible(self):
        self.list_projects()
        return self

    # def get_api_key(self) -> str:
    #     return self.api_key

    def _request(
        self, method: str, pth: str, json: Optional[MetadataDict] = None, id: Optional[Union[int, str]] = None
    ) -> Dict:
        """
        Sends a GET or POST request to the specified URL with the API key in the headers and returns the JSON response.

        Args:
            pth (str): The path appended to the API_URL to which the GET or POST request is sent.

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
        request_kwargs = {}
        if method == "post":
            assert "json" != None, "when using post, json cannot be none"
            request_kwargs["json"] = json

        if "{" in pth:
            assert id is not None, "If passing a url format, an id must be passed"
            pth = pth.format(id)
        url = str(self.api_url).strip("/") + "/" + pth.strip("/")

        try:
            response = None
            response = requests.request(method, url, headers={"x-api-key": self.api_key}, **request_kwargs)
            response.raise_for_status()
        except (HTTPError, SSLError) as e:
            if response is None or response.status_code == 404:
                error_msg = (
                    f"Page not found. Try checking the URL.\nGenerally the required URL looks like "
                    f"'https://<name_of_your_metadata_database>.org/index.php/api', but the URL that was passed "
                    f"was '{self.api_url}'"
                )
                raise HTTPError(error_msg) from None
            elif response.status_code == 403:
                raise PermissionError(
                    f"Access to that URL is denied. " f"Check that the API key '{self.api_key}' is correct"
                ) from None
            elif response.status_code == 400 and id is not None:
                raise PermissionError(f"Access to this id is denied. Check that the id '{id}' is correct") from None
            else:
                raise Exception(
                    f"Status Code: {response.status_code}, Response: {json.loads(response.text)['message']}"
                ) from e
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {str(e)}") from e
        return response.json()

    def _get_request(self, pth: str, id: Optional[Union[int, str]] = None) -> Dict:
        """
        Args:
            pth (str): The path appended to the API_URL to which the GET or POST request is sent.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("get", pth=pth, id=id)

    def _post_request(self, pth: str, metadata: MetadataDict, id: Union[int, str] = None):
        """
        Args:
            pth (str): The path appended to the API_URL to which the GET or POST request is sent.
            metadata (dict): The metadata to be sent with the POST request.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("post", pth=pth, id=id, json=metadata)

    def list_projects(self) -> pd.DataFrame:
        """
        Lists all the projects associated with your API key.

        Returns:
            pd.DataFrame: Projects sorted by the date on which they were created
        """
        list_projects_get_path = "/editor"
        response = self._get_request(list_projects_get_path)
        try:
            projects = response["projects"]
        except KeyError:  # is this the best way to cope with new accounts with no projects?
            return pd.DataFrame()
        return pd.DataFrame.from_dict(projects).set_index("id").sort_values("created")

    def get_project_by_id(self, id: int):
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.

        Raises:
            Exception: You don't have permission to access this project - often this means the id is incorrect
        """
        #  todo(gblackadder) we could implement a get project by **idno** by using list projects and then filtering
        get_project_template = "/editor/{}"
        response = self._get_request(get_project_template, id=id)
        return pd.Series(response["project"])

    def create_timeseries(
        self,
        idno: str,
        series_description: Union[Dict, SeriesDescription],
        metadata_information: Optional[Union[Dict, MetadataInformation]] = None,
        datacite: Optional[Union[Dict, Datacite]] = None,
        provenance: Optional[List[Union[Dict, Provenance]]] = None,
        tags: Optional[Union[Dict, List[Tag]]] = None,
        additional: Optional[Dict] = None,
    ):
        """
        Creates a record of your *timeseries* metadata

        Args:
            idno (str): The unique identifier for the timeseries.
            series_description (SeriesDescription or Dictionary): Can be an instance of SeriesDescription defined like
                SeriesDescription(idno="", name="", etc). Or as a dictionary like {"idno": "", "name": "", etc}
            metadata_information (Optional[MetadataInformation or Dictionary]): Information on who generated the
                documentation. Can be a MetadataInformation object or a dictionary. Defaults to None
            datacite (Optional[Datacite or Dictionary]): DataCite metadata for generating DOI. Can be a Datacite object
                or a Dictionary. Defaults to None.
            provenance (Optional[List[Provenance or Dictionary]]): Can be a list of Provenance objects or a list of
                dictionaries. Defaults to None.
            tags (Optional[List[Tag or Dictionary]]): Can be a list of Tag objects or a list of dictionaries.
                Defaults to None.
            additional (Optional[Dictionary]): Any other custom metadata not covered by the schema. A dictionary.
                Defaults to None.

        Examples:
        >>> from pymetadataeditor.schemas import (SeriesDescription,
        ...                                       MetadataInformation,
        ...                                       Datacite,
        ...                                       Provenance,
        ...                                       Provenance,
        ...                                       Tag)
        >>> series_description = SeriesDescription(idno = "TS001", name = "Sample Timeseries")
        >>> metadata_information = MetadataInformation(title="Example of a Timeseries")
        >>> datacite = Datacite(doi="10.1234/sample.doi")
        >>> tags = [Tag(tag="tag1"), Tag(tag="tag2", tag_group="example group")]
        >>> additional = {"key1": "value1", "key2": "value2"}

        >>> response = self.create_timeseries(
        ...     idno="TS001",
        ...     series_description=series_description,
        ...     metadata_information=metadata_information,
        ...     datacite=datacite,
        ...     tags=tags,
        ...     additional=additional
        ... )
        """

        # todo(gblackadder): question - why does pyNada create_timeseries_dataset include args:
        #        repositroy_id, access_policy,  data_remote_url,  published
        #   that aren't in the schema, and doesn't include args that are:
        #        datacite, provenance, tags
        #   https://metadataeditorqa.worldbank.org/api-documentation/editor/#tag/Timeseries

        metadata = {
            "idno": idno,
            "metadata_information": metadata_information,
            "series_description": series_description,
            "datacite": datacite,
            "provenance": provenance,
            "tags": tags,
            "additional": additional,
        }

        validate_metadata(metadata, TimeSeriesMetadataSchema)
        ts = TimeSeriesMetadataSchema(**metadata)

        post_request_pth = "/editor/create/timeseries"
        self._post_request(pth=post_request_pth, metadata=ts.model_dump(exclude_none=True, exclude_unset=True))

    def update_timeseries_by_id(
        self,
        id: int,
        # idno: Optional[str] = None,
        series_description: Optional[Union[Dict, SeriesDescription]] = None,
        metadata_information: Optional[Union[Dict, MetadataInformation]] = None,
        datacite: Optional[Union[Dict, Datacite]] = None,
        provenance: Optional[List[Union[Dict, Provenance]]] = None,
        tags: Optional[Union[Dict, List[Tag]]] = None,
        additional: Optional[Dict] = None,
    ):
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.
            series_description (Optional[SeriesDescription or Dictionary]): Can be an instance of SeriesDescription
                defined like SeriesDescription(idno="", name="", etc). Or as a dictionary like
                {"idno": "", "name": "", etc}. Leave blank if you don't want to replace the existing values.
            metadata_information (Optional[MetadataInformation or Dictionary]): Information on who generated the
                documentation. Can be a MetadataInformation object or a dictionary. Leave blank if you don't want to
                replace the existing values.
            datacite (Optional[Datacite or Dictionary]): DataCite metadata for generating DOI. Can be a Datacite object
                or a Dictionary. Leave blank if you don't want to replace the existing values.
            provenance (Optional[List[Provenance or Dictionary]]): Can be a list of Provenance objects or a list of
                dictionaries. Leave blank if you don't want to replace the existing values.
            tags (Optional[List[Tag or Dictionary]]): Can be a list of Tag objects or a list of dictionaries.
                Leave blank if you don't want to replace the existing values.
            additional (Optional[Dictionary]): Any other custom metadata not covered by the schema. A dictionary.
                Leave blank if you don't want to replace the existing values.

        """
        # todo(gblackadder) as implemented, if the user wants to update a single value within series_description, for
        # example, they need to write out the entire series description, writing out again the elements they don't want
        # changed. A good workflow would be to get metadata by id as a TimeSeriesMetadata object and help users update
        # that object. But only if there is a user friendly way of doing that.

        # todo(gblackadder) check that it's correct you can't update the idno. The documentation
        #   https://metadataeditorqa.worldbank.org/api-documentation/editor/#operation/createTimeseries
        #   implies you can but in my observation from calling the api, you cannot
        metadata = self.get_project_by_id(id)["metadata"]
        ts = TimeSeriesMetadataSchema(
            idno=metadata["idno"],
            metadata_information=metadata.get("metadata_information", None),
            series_description=metadata.get("series_description", None),
            datacite=metadata.get("datacite", None),
            provenance=metadata.get("provenance", None),
            tags=metadata.get("tags", None),
            additional=metadata.get("additional", None),
        )

        ts = update_metadata(
            ts,
            series_description=series_description,
            metadata_information=metadata_information,
            datacite=datacite,
            provenance=provenance,
            tags=tags,
            additional=additional,
        )

        post_request_template_path = "/editor/update/timeseries/{}"
        self._post_request(
            post_request_template_path, id=id, metadata=ts.model_dump(exclude_none=True, exclude_unset=True)
        )
