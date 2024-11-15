import time
from typing import Optional

from open_webui.apps.webui.internal.db import Base, get_db
from open_webui.apps.webui.models.groups import Groups

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON

####################
# Prompts DB Schema
####################


class Prompt(Base):
    __tablename__ = "prompt"

    command = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(Text)
    content = Column(Text)
    timestamp = Column(BigInteger)

    access_control = Column(JSON, nullable=True)  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }


class PromptModel(BaseModel):
    command: str
    user_id: str
    title: str
    content: str
    timestamp: int  # timestamp in epoch

    access_control: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class PromptForm(BaseModel):
    command: str
    title: str
    content: str


class PromptsTable:
    def insert_new_prompt(
        self, user_id: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        prompt = PromptModel(
            **{
                "user_id": user_id,
                "command": form_data.command,
                "title": form_data.title,
                "content": form_data.content,
                "timestamp": int(time.time()),
            }
        )

        try:
            with get_db() as db:
                result = Prompt(**prompt.dict())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return PromptModel.model_validate(result)
                else:
                    return None
        except Exception:
            return None

    def get_prompt_by_command(self, command: str) -> Optional[PromptModel]:
        try:
            with get_db() as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                return PromptModel.model_validate(prompt)
        except Exception:
            return None

    def get_prompts(self) -> list[PromptModel]:
        with get_db() as db:
            return [
                PromptModel.model_validate(prompt) for prompt in db.query(Prompt).all()
            ]

    def get_prompts_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[PromptModel]:
        prompts = self.get_prompts()

        groups = Groups.get_groups_by_member_id(user_id)
        group_ids = [group.id for group in groups]

        if permission == "write":
            return [
                prompt
                for prompt in prompts
                if prompt.user_id == user_id
                or (
                    prompt.access_control
                    and (
                        any(
                            group_id
                            in prompt.access_control.get(permission, {}).get(
                                "group_ids", []
                            )
                            for group_id in group_ids
                        )
                        or (
                            user_id
                            in prompt.access_control.get(permission, {}).get(
                                "user_ids", []
                            )
                        )
                    )
                )
            ]
        elif permission == "read":
            return [
                prompt
                for prompt in prompts
                if prompt.user_id == user_id
                or prompt.access_control is None
                or (
                    prompt.access_control
                    and (
                        any(
                            prompt.access_control.get(permission, {}).get(
                                "group_ids", []
                            )
                            in group_id
                            for group_id in group_ids
                        )
                        or (
                            user_id
                            in prompt.access_control.get(permission, {}).get(
                                "user_ids", []
                            )
                        )
                    )
                )
            ]

    def update_prompt_by_command(
        self, command: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        try:
            with get_db() as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                prompt.title = form_data.title
                prompt.content = form_data.content
                prompt.timestamp = int(time.time())
                db.commit()
                return PromptModel.model_validate(prompt)
        except Exception:
            return None

    def delete_prompt_by_command(self, command: str) -> bool:
        try:
            with get_db() as db:
                db.query(Prompt).filter_by(command=command).delete()
                db.commit()

                return True
        except Exception:
            return False


Prompts = PromptsTable()
