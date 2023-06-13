from typing import Optional, Union, List, Any
from pydantic import BaseModel
from kubiya import ActionStore
import requests, base64, json, os

action_store = ActionStore("confluence", version="0.0.1")
action_store.uses_secrets(["JIRA_API_TOKEN"])

def get_confluence_email():
    return os.environ.get("CONFLUENCE_EMAIL")

def get_base_url():
    return os.environ.get("CONFLUENCE_BASE_URL")

def get_api_token():
    return action_store.secrets.get("JIRA_API_TOKEN")


def post_wrapper(endpoint: str, data: Optional[dict] = None) -> dict:
    email = get_confluence_email()
    api_token = get_api_token()
    base_url = get_base_url()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    headers["Authorization"] = f"Basic {base64.b64encode(f'{email}:{api_token}'.encode()).decode()}"

    response = requests.post(
        f"{base_url}{endpoint}",
        headers=headers,
        data=json.dumps(data) if data else None,
    )

    # Raises a HTTPError if the response was unsuccessful
    response.raise_for_status()

    return response.json()


def get_wrapper(endpoint: str) -> Optional[dict]:
    email = get_confluence_email()
    api_token = get_api_token()
    base_url = get_base_url()

    headers = {
        "Accept": "application/json",
    }

    headers["Authorization"] = f"Basic {base64.b64encode(f'{email}:{api_token}'.encode()).decode()}"

    response = requests.get(
        f"{base_url}{endpoint}",
        headers=headers,
    )

    # Raises a HTTPError if the response was unsuccessful
    response.raise_for_status()

    if response.status_code != 204:
        return response.json()
    else:
        return None


class PageBodyWrite(BaseModel):
    type: Optional[str]
    content: str

class PageNestedBodyWrite(BaseModel):
    type: str
    content: dict

class Version(BaseModel):
    number: int

class Body(BaseModel):
    storage: dict

class CreatePageRequest(BaseModel):
    spaceId: str
    title: Optional[str]
    parentId: Optional[str]
    body: str

class PageResponse(BaseModel):
    id: Union[str, int]
    status: str
    title: str
    spaceId: Union[str, int]
    parentId: Union[str, int]
    authorId: str
    createdAt: str
    version: Version
    body: Body

class SpaceParams(BaseModel):
    space_key: str

class ContentId(BaseModel):
    content_id: str

@action_store.kubiya_action()
def create_page(params: CreatePageRequest) -> dict:
    endpoint = "/wiki/api/v2/pages"
    data = {
        "spaceId": params.spaceId,
        "status": "current",
        "title": params.title,
        "parentId": params.parentId,
        "body": {
            "representation": "storage",
            "value": params.body
        }
    }
    response = post_wrapper(endpoint, data=data)
    return response

@action_store.kubiya_action()
def get_parent_id(params: ContentId) -> dict:
    return get_wrapper(f"/wiki/rest/api/content/{params.content_id}?expand=ancestors")


class ContentSummary(BaseModel):
    id: str
    title: str
    type: str

class GetAllContentResponse(BaseModel):
    results: List[ContentSummary]

class SpaceDetails(BaseModel):
    id: int
    key: str
    name: str
    description: Optional[str] = None

@action_store.kubiya_action()
def get_space_id(params: SpaceParams) -> SpaceDetails:
    return get_wrapper(f"/wiki/rest/api/space/{params.space_key}")

@action_store.kubiya_action()
def get_all_content(_: Any = None) -> GetAllContentResponse:
    endpoint = "/wiki/rest/api/content"
    try:
        response = get_wrapper(endpoint)
        return GetAllContentResponse(results=response["results"])
    except Exception as e:
        return GetAllContentResponse(results=[], message=str(e))

@action_store.kubiya_action()
def get_space_details(request: SpaceParams) -> dict:
    endpoint = f"/wiki/rest/api/space/{request.space_key}"
    try:
        response = get_wrapper(endpoint)
        return response
    except Exception as e:
        return {'message': str(e)}


class SpaceSummary(BaseModel):
    id: str
    key: str
    name: str
    type: str
    status: str
    description: Optional[str] = None

class GetAllSpacesResponse(BaseModel):
    results: List[SpaceSummary]

@action_store.kubiya_action()
def get_all_spaces(_: Any = None) -> GetAllSpacesResponse:
    endpoint = "/wiki/rest/api/space"
    try:
        response = get_wrapper(endpoint)
        results = [
            SpaceSummary(id=space["id"], key=space["key"], name=space["name"], type=space["type"], status=space["status"])
            for space in response["results"]
        ]
        return GetAllSpacesResponse(results=results)
    except Exception as e:
        return GetAllSpacesResponse(results=[], message=str(e))


class GetAvailableParentsPayload(BaseModel):
    space_id: int

@action_store.kubiya_action()
def get_available_parents(request: GetAvailableParentsPayload) -> List[str]:
    endpoint = f"/wiki/api/v2/spaces/{request.space_id}/pages"
    try:
        response = get_wrapper(endpoint)
        pages = response["results"]

        # Filter out pages with status other than "current"
        current_pages = [page for page in pages if page["status"] == "current"]

        response["results"] = current_pages
        return response
    except Exception as e:
        return {'message': str(e)}