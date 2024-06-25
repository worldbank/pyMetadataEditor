import warnings
from json import JSONDecodeError
from numbers import Number
from typing import Annotated, Dict, List, Optional, Union

import pandas as pd
import requests
from pydantic import BaseModel, ConfigDict, PrivateAttr, UrlConstraints, model_validator
from pydantic_core import Url
from requests.exceptions import HTTPError, SSLError

from pymetadataeditor.schemas.pydantic_definitions.common_schemas import OriginDescription, ProvenanceSchema, Tag
from pymetadataeditor.schemas.pydantic_definitions.survey_schema import (
    AccessPolicy,
    DatafileSchema,
    DocDesc,
    Embedding,
    LdaTopic,
    NationItem,
    Overwrite,
    StudyDesc,
    StudyInfo,
    SurveyMicrodataSchema,
    TitleStatement,
    VariableGroupSchema,
    VariableSchema,
)
from pymetadataeditor.tools import SchemaBaseModel, update_metadata, validate_metadata

from .schemas import DataciteSchema, MetadataInformation, SeriesDescription, TimeseriesSchema

warnings.filterwarnings(
    "ignore", category=UserWarning, module="pydantic"
)  # suppresses warning when metadata passed as dict instead of a pydantic object

MetadataDict = Dict[str, Union[str, Number, "MetadataDict", List["MetadataDict"]]]


class DeleteNotAppliedError(Exception):
    def __init__(self, message="Delete request not accepted by system.", response=None):
        super().__init__(message)
        self.response = response


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

    api_url: Annotated[
        Url,
        UrlConstraints(max_length=2083, allowed_schemes=["https"]),
    ]
    api_key: str
    _metadata_types: dict = PrivateAttr(default={"timeseries": TimeseriesSchema, "survey": SurveyMicrodataSchema})

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
                raise PermissionError("Access to that URL is denied. " "Check that the API key is correct") from None
            elif response.status_code == 400 and id is not None:
                raise PermissionError(f"Access to this id is denied. Check that the id '{id}' is correct") from None
            else:
                raise Exception(f"Status Code: {response.status_code}, Response: {response.text}") from e
        # except Exception as e:
        #     raise Exception(f"An unexpected error occurred: {str(e)}") from e
        return response.json()

    def _get_request(self, pth: str, id: Optional[Union[int, str]] = None) -> Dict:
        """
        Args:
            pth (str): The path appended to the API_URL to which the GET request is sent.

        Returns:
            Dict[str, str]: The JSON response from the server, parsed into a dictionary.
        """
        return self._request("get", pth=pth, id=id)

    def _post_request(self, pth: str, metadata: Optional[MetadataDict] = None, id: Optional[Union[int, str]] = None):
        """
        Args:
            pth (str): The path appended to the API_URL to which the POST request is sent.
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

    def get_project_by_id(self, id: int) -> pd.Series:
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

    def get_project_metadata_by_id(
        self, id: int, exclude_unset: bool = True, as_object: bool = False
    ) -> Union[MetadataDict, SchemaBaseModel]:
        """
        Args:
            id (int): the id of the project, not to be confused with the idno.
            exclude_unset (bool): when returning a dictionary (that is when as_object is False), if True then fields
                that were not set or have a None value are removed from the dictionary. Defaults to True
            as_object (bool): If True, return the metadata as a pydantic object.
                Otherwise, return a dictionary. Defaults to False.

        Returns:
            Union[SchemaBaseModel, Dict]: The metadata as either a dictionary or an object.
        """
        project = self.get_project_by_id(id=id)
        project_type = project["type"]
        assert project_type in self._metadata_types, (
            f"this project is listed as a '{project_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        metadata_object = self._metadata_types[project_type](**project["metadata"])
        if as_object:
            return metadata_object
        else:
            return metadata_object.model_dump(exclude_none=exclude_unset, exclude_unset=exclude_unset)

    @staticmethod
    def skeleton_timeseries_metadata(
        idno: str, name: str, as_object: bool = False
    ) -> Union[SchemaBaseModel, MetadataDict]:
        """
        Create outline timeseries metadata, either as a dictionary or an object, with the minimally required information

        Args:
            idno (str): The unique identifier for the timeseries.
            name (str): The name of the timeseries.
            as_object (bool): If True, return the metadata as a pydantic object.
                Otherwise, return a dictionary instance. Defaults to False.

        Returns:
            Union[SchemaBaseModel, Dict]: The timeseries metadata as either a dictionary or as an object.
        """
        ts = TimeseriesSchema(
            idno=idno,
            metadata_information=MetadataInformation(),
            series_description=SeriesDescription(idno=idno, name=name),
            datacite=DataciteSchema(),
            provenance=[ProvenanceSchema()],
            tags=[Tag()],
            additional={},
        )
        if as_object:
            return ts
        else:
            return ts.model_dump()

    @staticmethod
    def skeleton_survey_microdata_metadata(
        idno: str, title: str, as_object: bool = False
    ) -> Union[SchemaBaseModel, MetadataDict]:
        """
        Create outline survey microdata metadata, either as a dictionary or as an object.

        Args:
            idno (str): The unique identifier for the microdata.
            title (str): The title of the survey microdata.
            as_object (bool): If True, return the metadata as a pydantic object.
                Otherwise, return a dictionary instance. Defaults to False.

        Returns:
            Union[SchemaBaseModel, Dict]: The survey microdata metadata as either a dictionary or as an object.
        """
        sm = SurveyMicrodataSchema(
            repositoryid=None,
            access_policy=None,
            published=None,
            overwrite=None,
            doc_desc=DocDesc(idno=idno, title=title),
            study_desc=StudyDesc(
                title_statement=TitleStatement(idno=idno, title=title),
                study_info=StudyInfo(nation=[NationItem(name="")]),
            ),
            data_files=[DatafileSchema(file_id="", file_name="")],
            variables=[VariableSchema(file_id="", vid="", name="", labl="")],
            variable_groups=[VariableGroupSchema(vgid="")],
            provenance=[ProvenanceSchema(origin_description=OriginDescription())],
            tags=[Tag()],
            lda_topics=[LdaTopic()],
            embeddings=[Embedding(id="", vector={})],
            additional={},
        )
        if as_object:
            return sm
        else:
            return sm.model_dump()

    def delete_project_by_id(self, id: int):
        """
        Checks the project exists, deletes it, then checks it was deleted.

        Args:
            id (int): the id of the project, not to be confused with the idno.

        Raises:
            DeleteNotAppliedError: This can be the result of system admins blocking data deletion
        """
        # first check that the project is there to be deleted
        self.get_project_by_id(id=id)

        pth = "editor/delete/{}"
        try:
            response = self._post_request(pth=pth, id=id)
            response.json()
        except JSONDecodeError:
            pass

        # check that the entity was deleted
        try:
            self.get_project_by_id(id=id)
        except PermissionError:
            pass  # evidently the entity was deleted because now it can't be found
        else:
            raise DeleteNotAppliedError()

    def create_and_log_timeseries(
        self,
        idno: str,
        series_description: Union[Dict, SeriesDescription],
        metadata_information: Optional[Union[Dict, MetadataInformation]] = None,
        datacite: Optional[Union[Dict, DataciteSchema]] = None,
        provenance: Optional[List[Union[Dict, ProvenanceSchema]]] = None,
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
            datacite (Optional[DataciteSchema or Dictionary]): DataCite metadata for generating DOI. Can be a
                DataciteSchema object or a Dictionary. Defaults to None.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Can be a list of ProvenanceSchema objects or a
                list of dictionaries. Defaults to None.
            tags (Optional[List[Tag or Dictionary]]): Can be a list of Tag objects or a list of dictionaries.
                Defaults to None.
            additional (Optional[Dictionary]): Any other custom metadata not covered by the schema. A dictionary.
                Defaults to None.

        Examples:
        >>> from pymetadataeditor.schemas import (SeriesDescription,
        ...                                       MetadataInformation,
        ...                                       DataciteSchema,
        ...                                       ProvenanceSchema,
        ...                                       ProvenanceSchema,
        ...                                       Tag)
        >>> series_description = SeriesDescription(idno = "TS001", name = "Sample Timeseries")
        >>> metadata_information = MetadataInformation(title="Example of a Timeseries")
        >>> datacite = DataciteSchema(doi="10.1234/sample.doi")
        >>> tags = [Tag(tag="tag1"), Tag(tag="tag2", tag_group="example group")]
        >>> additional = {"key1": "value1", "key2": "value2"}

        >>> response = self.create_and_log_timeseries(
        ...     idno="TS001",
        ...     series_description=series_description,
        ...     metadata_information=metadata_information,
        ...     datacite=datacite,
        ...     tags=tags,
        ...     additional=additional
        ... )
        """
        metadata = {
            "idno": idno,
            "metadata_information": metadata_information,
            "series_description": series_description,
            "datacite": datacite,
            "provenance": provenance,
            "tags": tags,
            "additional": additional,
        }
        self._create_and_log(metadata, "timeseries")

    def create_and_log_survey_microdata(
        self,
        repositoryid: Optional[str] = None,
        access_policy: Optional[Union[str, AccessPolicy]] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[str, Overwrite]] = None,
        doc_desc: Optional[Union[Dict, DocDesc]] = None,
        study_desc: Optional[Union[Dict, StudyDesc]] = None,
        data_files: Optional[Union[List[Dict], List[DatafileSchema]]] = None,
        variables: Optional[Union[List[Dict], List[VariableSchema]]] = None,
        variable_groups: Optional[Union[List[Dict], List[VariableGroupSchema]]] = None,
        provenance: Optional[Union[List[Dict], List[ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[Embedding]]] = None,
        additional: Optional[MetadataDict] = None,
    ):
        """
            Creates a record of your *survey microdata* metadata


        Args:
            repositoryid : Optional[str]
                The identifier for the repository where the survey microdata is to be stored.
            access_policy : Optional[Union[str, AccessPolicy]]
                The access policy for the survey data. Can be a string or an AccessPolicy object.
            published : Optional[int]
                The publication status of the survey data. Typically, 0 for unpublished and 1 for published.
            overwrite : Optional[Union[str, Overwrite]]
                Policy for overwriting existing data. Can be a string or an Overwrite object.
            doc_desc : Optional[Union[Dict, DocDesc]]
                Description of the documentation for the survey. Can be a dictionary or a DocDesc object.
            study_desc : Optional[Union[Dict, StudyDesc]]
                Description of the study. Can be a dictionary or a StudyDesc object.
            data_files : Optional[Union[List[Dict], List[DatafileSchema]]]
                List of data files associated with the survey. Each item can be a dictionary or a DatafileSchema object.
            variables : Optional[Union[List[Dict], List[VariableSchema]]]
                List of variables included in the survey. Each item can be a dictionary or a VariableSchema object.
            variable_groups : Optional[Union[List[Dict], List[VariableGroupSchema]]]
                List of variable groups included in the survey. Each item can be a dictionary or a VariableGroupSchema
                object.
            provenance : Optional[Union[List[Dict], List[ProvenanceSchema]]]
                Provenance information for the survey data. Each item can be a dictionary or a ProvenanceSchema object.
            tags : Optional[Union[List[Dict], List[Tag]]]
                Tags associated with the survey data. Each item can be a dictionary or a Tag object.
            lda_topics : Optional[Union[List[Dict], List[LdaTopic]]]
                List of LDA topics associated with the survey. Each item can be a dictionary or an LdaTopic object.
            embeddings : Optional[Union[List[Dict], List[Embedding]]]
                List of embeddings associated with the survey. Each item can be a dictionary or an Embedding object.
            additional : Optional[Dict[str, Any]]
                Any additional metadata to be associated with the survey data.


        >>> from pymetadataeditor.schemas import (
        ...     AccessPolicy,
        ...     DocDesc,
        ...     StudyDesc,
        ...     DatafileSchema,
        ...     VariableSchema,
        ...     VariableGroupSchema,
        ...     ProvenanceSchema,
        ...     Tag,
        ...     LdaTopic,
        ...     Embedding
        ... )
        >>> doc_desc = DocDesc(title="Survey Documentation")
        >>> study_desc = StudyDesc(title="Survey Study")
        >>> data_files = [DatafileSchema(id="file1", description="Data file 1")]
        >>> variables = [VariableSchema(id="var1", name="Variable 1")]
        >>> variable_groups = [VariableGroupSchema(id="group1", name="Group 1")]
        >>> provenance = [ProvenanceSchema(event="Created", date="2024-01-01")]
        >>> tags = [Tag(tag="tag1"), Tag(tag="tag2")]
        >>> lda_topics = [LdaTopic(id="topic1", description="Topic 1")]
        >>> embeddings = [Embedding(id="embed1", vector=[0.1, 0.2, 0.3])]
        >>> additional = {"key1": "value1", "key2": "value2"}

        >>> response = self.create_and_log_survey_microdata(
        ...     repositoryid="repo123",
        ...     access_policy=AccessPolicy(policy="open"),
        ...     published=1,
        ...     overwrite="yes",
        ...     doc_desc=doc_desc,
        ...     study_desc=study_desc,
        ...     data_files=data_files,
        ...     variables=variables,
        ...     variable_groups=variable_groups,
        ...     provenance=provenance,
        ...     tags=tags,
        ...     lda_topics=lda_topics,
        ...     embeddings=embeddings,
        ...     additional=additional
        ... )
        """
        metadata = {
            "repositoryid": repositoryid,
            "access_policy": access_policy,  # why access_policy on the microdata but not timeseries???
            "published": published,
            "overwrite": overwrite,  # similarly overwrite
            "doc_desc": doc_desc,
            "study_desc": study_desc,
            "data_files": data_files,
            "variables": variables,
            "variable_groups": variable_groups,
            "provenance": provenance,
            "tags": tags,
            "lda_topics": lda_topics,
            "embeddings": embeddings,
            "additional": additional,
        }
        self._create_and_log(metadata, "survey")

    def _create_and_log(self, metadata: MetadataDict, metadata_type: str):
        assert metadata_type in self._metadata_types, (
            f"this project is listed as a '{metadata_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        validate_metadata(metadata, self._metadata_types[metadata_type])
        md = self._metadata_types[metadata_type](**metadata)

        post_request_pth = f"/editor/create/{metadata_type}"
        self._post_request(pth=post_request_pth, metadata=md.model_dump(exclude_none=True, exclude_unset=True))

    def update_timeseries_by_id(
        self,
        id: int,
        # idno: Optional[str] = None,
        series_description: Optional[Union[Dict, SeriesDescription]] = None,
        metadata_information: Optional[Union[Dict, MetadataInformation]] = None,
        datacite: Optional[Union[Dict, DataciteSchema]] = None,
        provenance: Optional[List[Union[Dict, ProvenanceSchema]]] = None,
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
            datacite (Optional[DataciteSchema or Dictionary]): DataCite metadata for generating DOI. Can be a
                DataciteSchema object or a Dictionary. Leave blank if you don't want to replace the existing values.
            provenance (Optional[List[ProvenanceSchema or Dictionary]]): Can be a list of ProvenanceSchema objects or a
                list of dictionaries. Leave blank if you don't want to replace the existing values.
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

        self._update_by_id(
            id,
            "timeseries",
            series_description=series_description,
            metadata_information=metadata_information,
            datacite=datacite,
            provenance=provenance,
            tags=tags,
            additional=additional,
        )

    def update_survey_microdata_by_id(
        self,
        id: int,
        repositoryid: Optional[str] = None,
        access_policy: Optional[Union[str, AccessPolicy]] = None,
        published: Optional[int] = None,
        overwrite: Optional[Union[str, Overwrite]] = None,
        doc_desc: Optional[Union[Dict, DocDesc]] = None,
        study_desc: Optional[Union[Dict, StudyDesc]] = None,
        data_files: Optional[Union[List[Dict], List[DatafileSchema]]] = None,
        variables: Optional[Union[List[Dict], List[VariableSchema]]] = None,
        variable_groups: Optional[Union[List[Dict], List[VariableGroupSchema]]] = None,
        provenance: Optional[Union[List[Dict], List[ProvenanceSchema]]] = None,
        tags: Optional[Union[List[Dict], List[Tag]]] = None,
        lda_topics: Optional[Union[List[Dict], List[LdaTopic]]] = None,
        embeddings: Optional[Union[List[Dict], List[Embedding]]] = None,
        additional: Optional[MetadataDict] = None,
    ):
        """
        Args:
            id (int): the id of the project.
            repositoryid : Optional[str]
                The identifier for the repository where the survey microdata is to be stored.
            access_policy : Optional[Union[str, AccessPolicy]]
                The access policy for the survey data. Can be a string or an AccessPolicy object.
            published : Optional[int]
                The publication status of the survey data. Typically, 0 for unpublished and 1 for published.
            overwrite : Optional[Union[str, Overwrite]]
                Policy for overwriting existing data. Can be a string or an Overwrite object.
            doc_desc : Optional[Union[Dict, DocDesc]]
                Description of the documentation for the survey. Can be a dictionary or a DocDesc object.
            study_desc : Optional[Union[Dict, StudyDesc]]
                Description of the study. Can be a dictionary or a StudyDesc object.
            data_files : Optional[Union[List[Dict], List[DatafileSchema]]]
                List of data files associated with the survey. Each item can be a dictionary or a DatafileSchema object.
            variables : Optional[Union[List[Dict], List[VariableSchema]]]
                List of variables included in the survey. Each item can be a dictionary or a VariableSchema object.
            variable_groups : Optional[Union[List[Dict], List[VariableGroupSchema]]]
                List of variable groups included in the survey. Each item can be a dictionary or a VariableGroupSchema
                object.
            provenance : Optional[Union[List[Dict], List[ProvenanceSchema]]]
                Provenance information for the survey data. Each item can be a dictionary or a ProvenanceSchema object.
            tags : Optional[Union[List[Dict], List[Tag]]]
                Tags associated with the survey data. Each item can be a dictionary or a Tag object.
            lda_topics : Optional[Union[List[Dict], List[LdaTopic]]]
                List of LDA topics associated with the survey. Each item can be a dictionary or an LdaTopic object.
            embeddings : Optional[Union[List[Dict], List[Embedding]]]
                List of embeddings associated with the survey. Each item can be a dictionary or an Embedding object.
            additional : Optional[Dict[str, Any]]
                Any additional metadata to be associated with the survey data.

        """
        # instead of by id, we could update by repositoryId if that is a unique identifier?
        self._update_by_id(
            id,
            "survey",
            repositoryid=repositoryid,
            access_policy=access_policy,
            published=published,
            overwrite=overwrite,
            doc_desc=doc_desc,
            study_desc=study_desc,
            data_files=data_files,
            variables=variables,
            variable_groups=variable_groups,
            provenance=provenance,
            tags=tags,
            lda_topics=lda_topics,
            embeddings=embeddings,
            additional=additional,
        )

    def _update_by_id(self, id: int, expected_project_type: str, **kwargs):
        assert expected_project_type in self._metadata_types
        project_data = self.get_project_by_id(id)
        project_type = project_data["type"]
        assert project_type in self._metadata_types, (
            f"this project is listed as a '{project_type}' type project but this is"
            f" unknown. Projects must be one of {list(self._metadata_types.keys())}"
        )
        assert expected_project_type == project_type, (
            f"You are trying to perform a {expected_project_type} update, "
            f"but the actual data is listed as {project_type}"
        )
        metadata = self.get_project_by_id(id)["metadata"]
        md = self._metadata_types[project_type](**metadata)

        md = update_metadata(md, **kwargs)

        post_request_template_path = f"/editor/update/{project_type}/" + "{}"
        self._post_request(
            post_request_template_path, id=id, metadata=md.model_dump(exclude_none=True, exclude_unset=True)
        )
