from typing import Optional

import pandas as pd
import pytest
import requests

from pymetadataeditor import MetadataEditor
from pymetadataeditor.interface import MetadataDict


class MockResponse:
    def __init__(self, status_code: int, error_message: Optional[str] = None, json_data: Optional[MetadataDict] = None):
        """
        Used to create mock responses from the API so that we don't actually call the API everytime we run tests
        """
        self.status_code = status_code
        self.json_data = json_data if json_data is not None else {}
        self.text = error_message if error_message is not None else "{}"
        self.response = requests.Response()
        self.response.status_code = self.status_code
        self.response._content = self.text.encode("utf-8")
        self.response.headers["Content-Type"] = "application/json"
        self.response.url = "https://example.com/api/resource"

    def raise_for_status(self):
        if self.status_code == 403:
            raise requests.exceptions.HTTPError("403 Client Error: Forbidden for url", response=self)
        elif self.status_code == 400:
            raise requests.exceptions.HTTPError(
                "400 Client Error: Bad Request for url: example.com", response=self.response
            )

        elif self.status_code != 200:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error")

    def json(self) -> MetadataDict:
        if self.json_data is not None:
            return self.json_data
        else:
            return {}


@pytest.mark.parametrize("method", ["get", "post"])
def test_given_request(monkeypatch, method: str):
    me = MetadataEditor(api_key="test")
    if method == "get":

        def func(*args, **kwargs):
            return me._get_request(*args, **kwargs)

    elif method == "post":

        def func(*args, **kwargs):
            return me._post_request(*args, **kwargs, metadata={})

    # url is not https
    url = "http://example.com"
    with pytest.raises(ValueError):
        func(url)

    # api key raises Access Denied
    url = "https://example.com"

    def mock_response(*args, **kwargs):
        return MockResponse(status_code=403)

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(PermissionError):
        func(url)

    # api raises some other http error
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=502)

    monkeypatch.setattr(requests, "request", mock_response)
    with pytest.raises(Exception):
        func(url)

    # response is good
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200, json_data={})

    monkeypatch.setattr(requests, "request", mock_response)
    func(url)


def test_list_collections(monkeypatch):
    collections = {
        "status": "success",
        "projects": [
            {"id": "1", "created": "2024-06-11T09:58:14-04:00"},
            {"id": "2", "created": "2024-06-11T09:58:14-04:00"},
        ],
    }

    def mock_get(*args, **kwargs):
        return MockResponse(status_code=200, json_data=collections)

    monkeypatch.setattr(requests, "request", mock_get)

    me = MetadataEditor(api_key="test")
    actual_collections = me.list_projects()
    assert type(actual_collections) == pd.DataFrame
    assert actual_collections.shape == (2, 1)
    assert actual_collections.columns == ["created"]


def test_get_project_by_id(monkeypatch):
    # id is bad

    def mock_get(*args, **kwargs):
        return MockResponse(
            status_code=400,
            json_data={},
            error_message="""{"message": "You don't have permission to access this project"}""",
        )

    monkeypatch.setattr(requests, "request", mock_get)
    me = MetadataEditor(api_key="test")
    with pytest.raises(Exception) as e:
        me.get_project_by_id(1)
    assert str(e.value) == "Status Code: 400, Response: You don't have permission to access this project"

    # id is good
    collection = {"status": "success", "project": {"id": "1", "created": "2024-06-11T09:58:14-04:00"}}

    def mock_get(*args, **kwargs):
        return MockResponse(status_code=200, json_data=collection)

    monkeypatch.setattr(requests, "request", mock_get)
    me = MetadataEditor(api_key="test")
    actual_project = me.get_project_by_id(2)
    assert type(actual_project) == pd.Series
    assert len(actual_project) == 2


def test_create_timeseries(monkeypatch):
    def mock_post(*args, **kwargs):
        return MockResponse(status_code=200)

    monkeypatch.setattr(requests, "request", mock_post)

    me = MetadataEditor(api_key="test")

    # metadata no series description
    with pytest.raises(TypeError):
        me.create_timeseries(idno="GB123")

    # metadata series description has no idno
    with pytest.raises(ValueError):
        me.create_timeseries(
            idno="GB123", series_description={"doi": "string", "name": "Gordons Test", "display_name": "string"}
        )

    me.create_timeseries(
        idno="GB123",
        series_description={"idno": "string", "doi": "string", "name": "Gordons Test", "display_name": "string"},
    )
