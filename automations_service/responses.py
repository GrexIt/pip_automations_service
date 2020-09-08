import enum
from typing import Literal, Union
from pydantic import BaseModel, Field, conlist


class ActionsEnum(str, enum.Enum):
    assign = 'assign'
    status = 'status'
    add_tag = 'add_tag'


class StatusEnum(str, enum.Enum):
    open = 'open'
    close = 'close'
    pending = 'pending'


class BaseAction(BaseModel):
    type: ActionsEnum = Field(..., title="type of action")


class AssignActionData(BaseModel):
    user_id: int = Field(..., title="user id to be assigned")


class AssignAction(BaseAction):
    type: Literal["assign"]
    data: AssignActionData = Field(..., title="data for assign action")


class StatusActionData(BaseModel):
    status: StatusEnum = Field(..., title="new status of the gmailunit")


class StatusAction(BaseAction):
    type: Literal["status"]
    data: StatusActionData = Field(..., title="data for status action")


class TagAddActionData(BaseModel):
    tag_ids: conlist(int, min_items=1) = Field(
        ..., title="tag ids to be added to gmailunit"
    )


class TagAddAction(BaseAction):
    type: Literal["add_tag"]
    data: TagAddActionData = Field(..., title="data for tag_add action")


class GetActionsResponse(BaseModel):
    actions: conlist(
        Union[AssignAction, StatusAction, TagAddAction], min_items=1
    ) = Field(None, title="List of actions to be applied by the automation")
