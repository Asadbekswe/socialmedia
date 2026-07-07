from typing import Generic, TypeVar

from pydantic import BaseModel, computed_field

T = TypeVar("T")

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page * self.size < self.total
