"""T2: strict argument schemas per tool."""
import re
from pathlib import PurePosixPath
from pydantic import BaseModel, Field, field_validator, ValidationError

class SearchDocsArgs(BaseModel, extra="forbid"):
    query: str = Field(max_length=200)

class ReadFileArgs(BaseModel, extra="forbid"):
    path: str
    @field_validator("path")
    @classmethod
    def confined(cls, v):
        p = PurePosixPath(v)
        if p.is_absolute() or ".." in p.parts:
            raise ValueError("path escapes sandbox")
        return v

class QueryDbArgs(BaseModel, extra="forbid"):
    sql: str
    @field_validator("sql")
    @classmethod
    def read_only(cls, v):
        s = v.strip().lower()
        if not s.startswith("select") or ";" in s.rstrip(";") or re.search(r"\b(drop|delete|update|insert|alter|attach|pragma)\b", s):
            raise ValueError("only single SELECT statements allowed")
        return v

class WriteNoteArgs(BaseModel, extra="forbid"):
    title: str = Field(max_length=80)
    body: str = Field(max_length=2000)

class SendEmailArgs(BaseModel, extra="forbid"):
    to: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
    subject: str = Field(max_length=120)
    body: str = Field(max_length=4000)

SCHEMAS = {"search_docs": SearchDocsArgs, "read_file": ReadFileArgs, "query_db": QueryDbArgs,
           "write_note": WriteNoteArgs, "send_email": SendEmailArgs}

def validate(name: str, args: dict) -> str | None:
    """Returns None if valid, else an error string."""
    try:
        SCHEMAS[name](**args)
        return None
    except ValidationError as e:
        return e.errors()[0]["msg"]
