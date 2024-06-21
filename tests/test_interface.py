from json import JSONDecodeError
from typing import List, Optional, Union

import pandas as pd
import pytest
import requests
from pydantic import ValidationError

from pymetadataeditor import MetadataEditor
from pymetadataeditor.interface import DeleteNotAppliedError, MetadataDict
from pymetadataeditor.schemas import SeriesDescription


class MockResponse:
    def __init__(
        self,
        status_code: int,
        error_message: Optional[str] = None,
        json_data: Optional[MetadataDict] = None,
        raise_json_decode_error: bool = False,
    ):
        """
        Used to create mock responses from the API so that we don't actually call the API everytime we run tests
        """
        self.status_code = status_code
        self.json_data = json_data if json_data is not None else {}
        self.text = error_message if error_message is not None else "{}"
        self.raise_json_decode_error = raise_json_decode_error

        self.response = requests.Response()
        self.response.status_code = self.status_code
        self.response._content = self.text.encode("utf-8")
        self.response.headers["Content-Type"] = "application/json"
        self.response.url = "https://example.com/api/resource"

    def raise_for_status(self):
        if self.status_code == 404:
            raise requests.exceptions.HTTPError("404")
        elif self.status_code == 403:
            raise requests.exceptions.HTTPError("403")  # Client Error: Forbidden for url", response=self)
        elif self.status_code == 400:
            raise requests.exceptions.HTTPError(
                "400 Client Error: Bad Request for url: example.com", response=self.response
            )

        elif self.status_code != 200:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error")

    def json(self) -> MetadataDict:
        if self.raise_json_decode_error:
            raise JSONDecodeError(msg="could not decode", doc="...", pos=2)
        if self.json_data is not None:
            return self.json_data
        else:
            return {}


@pytest.fixture
def metadata_editor(monkeypatch):
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200)

    monkeypatch.setattr(requests, "request", mock_response)
    return MetadataEditor(api_url="https://example.com", api_key="test")


def test_MetadataEditor_instantiation(monkeypatch):
    # url is not https
    with pytest.raises(ValidationError) as e:
        MetadataEditor(api_url="http://example.com", api_key="test")
    assert len(e.value.errors()) == 1
    assert e.value.errors()[0]["msg"] == "URL scheme should be 'https'"

    # bad URL
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=404)

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(requests.HTTPError) as e:
        MetadataEditor(api_url="https://example.com", api_key="test")
    assert str(e.value).split(".")[0] == "Page not found"

    # bad key
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=403)

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(PermissionError) as e:
        MetadataEditor(api_url="https://example.com", api_key="test")
    assert str(e.value).split(".")[0] == "Access to that URL is denied"

    # good instantiation
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200)

    monkeypatch.setattr(requests, "request", mock_response)
    MetadataEditor(api_url="https://example.com", api_key="test")


@pytest.mark.parametrize("method", ["get", "post"])
def test_given_request(monkeypatch, metadata_editor, method: str):
    if method == "get":

        def func(*args, **kwargs):
            return metadata_editor._get_request(*args, **kwargs)

    elif method == "post":

        def func(*args, **kwargs):
            return metadata_editor._post_request(*args, **kwargs, metadata={})

    # api raises some http error
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=502)

    monkeypatch.setattr(requests, "request", mock_response)

    with pytest.raises(Exception):
        func("/editor")

    # response is good
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200, json_data={})

    monkeypatch.setattr(requests, "request", mock_response)
    func("/editor")


def test_list_projects(monkeypatch, metadata_editor):
    projects = {
        "status": "success",
        "projects": [
            {"id": "1", "created": "2024-06-11T09:58:14-04:00"},
            {"id": "2", "created": "2024-06-11T09:58:14-04:00"},
        ],
    }

    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200, json_data=projects)

    monkeypatch.setattr(requests, "request", mock_response)

    actual_projects = metadata_editor.list_projects()
    assert type(actual_projects) == pd.DataFrame
    assert actual_projects.shape == (2, 1)
    assert actual_projects.columns == ["created"]


def test_get_project_by_id(monkeypatch, metadata_editor):
    # id is bad
    def mock_response(*args, **kwargs):
        return MockResponse(
            status_code=400,
            json_data={},
            error_message="""{"message": "You don't have permission to access this project"}""",
        )

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(Exception) as e:
        metadata_editor.get_project_by_id(1)
    assert str(e.value) == "Access to this id is denied. Check that the id '1' is correct"

    # id is good
    project = {"status": "success", "project": {"id": "1", "created": "2024-06-11T09:58:14-04:00"}}

    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200, json_data=project)

    monkeypatch.setattr(requests, "request", mock_response)
    actual_project = metadata_editor.get_project_by_id(2)
    assert type(actual_project) == pd.Series
    assert len(actual_project) == 2


def test_create_timeseries(monkeypatch, metadata_editor):
    # metadata no series description
    with pytest.raises(TypeError):
        metadata_editor.create_timeseries(idno="GB123")

    # metadata series description has no idno
    with pytest.raises(ValueError):
        metadata_editor.create_timeseries(
            idno="GB123", series_description={"doi": "string", "name": "Gordons Test", "display_name": "string"}
        )

    metadata_editor.create_timeseries(
        idno="GB123",
        series_description={"idno": "string", "doi": "string", "name": "Gordons Test", "display_name": "string"},
    )


def test_update_timeseries_by_id(monkeypatch, metadata_editor):
    series_description = SeriesDescription(idno="17", name="1")
    metadata_information = {"title": "check we can pass in a dict as well as a pydantic object"}

    # id is bad
    def mock_response(*args, **kwargs):
        return MockResponse(
            status_code=400,
            json_data={},
            error_message="""{"message": "You don't have permission to access this project"}""",
        )

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(Exception) as e:
        metadata_editor.update_timeseries_by_id(
            1, series_description=series_description, metadata_information=metadata_information
        )
    assert str(e.value) == "Access to this id is denied. Check that the id '1' is correct"

    # id is good
    def mock_response(*args, **kwargs):
        return MockResponse(
            status_code=200,
            json_data={
                "project": {"metadata": {"idno": "12", "series_description": {"idno": "12", "name": "oldname"}}}
            },
        )

    monkeypatch.setattr(requests, "request", mock_response)
    metadata_editor.update_timeseries_by_id(
        1, series_description=series_description, metadata_information=metadata_information
    )


class MockGetProjectById:
    def __init__(self, passes: Union[bool, List[bool]]):
        self.passes = passes

    def __call__(self, *args, **kwargs):
        if isinstance(self.passes, list):
            passes = self.passes.pop(0)
        else:
            passes = self.passes
        if passes:
            return True
        else:
            raise PermissionError


def test_delete_project_by_id(monkeypatch, metadata_editor):
    """
    This feels like a bad test - it's testing the implementation instead of focusing on the functionality
       But then, because of all the mocking that happens, maybe that's how it has to be?
       Then the functionality will be tested in an integration test
    """

    # raises an error when there is no such project to delete
    monkeypatch.setattr(MetadataEditor, "get_project_by_id", MockGetProjectById(False))

    def mock_response(*args, **kwargs):
        return MockResponse(
            status_code=400,
            error_message="""{"message": "You don't have permission to access this project"}""",
        )

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(Exception):
        metadata_editor.delete_project_by_id(1)

    # raises DeleteNotAppliedError when request was good but the json was bad
    #   and the project is still there
    monkeypatch.setattr(MetadataEditor, "get_project_by_id", MockGetProjectById([True, True]))

    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200, raise_json_decode_error=True)

    monkeypatch.setattr(MetadataEditor, "_post_request", mock_response)
    with pytest.raises(DeleteNotAppliedError):
        metadata_editor.delete_project_by_id(1)

    # the project was deleted even though the json was bad
    monkeypatch.setattr(MetadataEditor, "get_project_by_id", MockGetProjectById([True, False]))

    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200, raise_json_decode_error=True)

    monkeypatch.setattr(MetadataEditor, "_post_request", mock_response)
    metadata_editor.delete_project_by_id(1)

    # the project was deleted
    monkeypatch.setattr(MetadataEditor, "get_project_by_id", MockGetProjectById([True, False]))

    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200, raise_json_decode_error=False)

    monkeypatch.setattr(MetadataEditor, "_post_request", mock_response)
    monkeypatch.setattr(MetadataEditor, "_post_request", mock_response)
    metadata_editor.delete_project_by_id(1)
