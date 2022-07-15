from abc import ABC, abstractmethod
from collections import namedtuple
import re
from typing import (
        Any,
        Callable,
        ClassVar,
        Generic,
        Literal,
        Self,
        TypeGuard,
        TypeVar,
        cast,
        overload,
    )

FOLDER_MIME_TYPE: Literal['application/vnd.google-apps.folder'] = 'application/vnd.google-apps.folder'
T = TypeVar('T')


class Validator(ABC, Generic[T]):
    def __set_name__(self, owner: type[object], name: str):
        self.private_name = '_' + name

    @overload
    def __get__(self, obj: None, objtype: None) -> 'Validator[T]':
        ...

    @overload
    def __get__(self, obj: object, objtype: type[object]) -> T:
        ...

    def __get__(self, obj: object | None, objtype: type[object] | None = None) -> 'Validator[T]' | T:
        return getattr(obj, self.private_name)

    def __set__(self, obj: object, value: Any):
        if self.validate(value):
            setattr(obj, self.private_name, value)

    @abstractmethod
    def validate(self, value: Any) -> TypeGuard[T]:
        pass


class String(Validator[str]):
    def __init__(
            self,
            minlen: int = 0, 
            maxlen: int = 9999,
            predicate: Callable[[str], bool] = None,
            pattern: re.Pattern = None,
    ):
        self.minlen = minlen
        self.maxlen = maxlen
        self.predicate = predicate
        self.pattern = pattern

    def validate(self, value: Any) -> TypeGuard[str]:
        if not isinstance(value, str):
            raise TypeError(f"{value} must be a str, got {type(value)}.")
        if (length := len(value)) < self.minlen:
            raise ValueError(f"Length of string must be at least {self.minlen}, got {length}")
        if length > self.maxlen:
            raise ValueError(f"Length of string must be at most {self.minlen}, got {length}")
        if self.predicate is not None and not self.predicate(value):
            raise ValueError(f"String didn't match the predicate.")
        if self.pattern is not None and self.pattern.fullmatch(value) is None:
            raise ValueError(f"String didn't match the pattern.")
        return True

class NonNegativeInt(Validator[int]):
    def __init__(self, maxval: int = None) -> None:
        self.maxval = maxval

    def validate(self, value: Any) -> TypeGuard[int]:
        if not isinstance(value, int):
            raise TypeError(f"Expected int, got {type(value)}")
        if value < 0:
            raise ValueError(f"value must not be negative, got {value}.")
        if self.maxval is not None and value > self.maxval:
            raise ValueError(f"value should not be greater than {self.maxval}, got {value}.")
        return True

class Item:
    pattern: ClassVar[re.Pattern] = re.compile(r'[-\w]{25,}')
    checksum: ClassVar[re.Pattern] = re.compile(r'[a-fA-F\d]{32}')

    @classmethod
    def is_valid_id(cls, id_: str) -> TypeGuard[str]:
        return cls.pattern.fullmatch(id_) is not None

F = TypeVar('F', bound=Item)

class IDMeta(type):
    @classmethod
    def __isinstancecheck__(cls, other):
        return isinstance(other, str) and Item.pattern.fullmatch(other) is not None

class ItemID(str, Generic[F], metaclass=IDMeta):
    def __new__(cls, arg: str, /, *, type: type[F]) -> 'ItemID[F]':
        if not Item.is_valid_id(arg):
            raise TypeError("Not a valid ItemID.")
        self = super().__new__(cls, arg)
        return self

    def __init__(self, arg, /, *, type: type[F]):
        self.type = type

class File(Item):
    __slots__ = ('_id', 'name', '_mimeType', 'parents', '_size', '_md5checksum', 'trashed', 'kind')
    id = String(pattern=Item.pattern)
    mimeType = String(predicate=FOLDER_MIME_TYPE.__ne__)
    size = NonNegativeInt()
    md5checksum = String(pattern=Item.checksum)

    def __init__(
        self,
        id: str,
        name: str,
        mimeType: str,
        parents: list[ItemID],
        trashed: bool,
        size: str | int,
        md5checksum: str,
    ):
        self.id = id
        self.kind: Literal['File'] = 'File'
        self.name = name
        self.mimeType = mimeType
        self.parents = [ItemID(parent, type=Folder) for parent in parents]
        self.size = int(size)
        self.md5checksum = md5checksum
        self.trashed = trashed

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other) -> bool:
        if not issubclass(type(other), type(self)):
            return NotImplemented
        return self.md5checksum == other.md5checksum
    

class Folder(Item):
    id = String(pattern=Item.pattern)
    mimeType = String(predicate=FOLDER_MIME_TYPE.__eq__)
    __slots__ = ('_id', 'name', '_mimeType', 'parents', 'trashed', 'kind')

    def __init__(
        self,
        id: str,
        name: str,
        parents: list[ItemID['Folder']],
        trashed: bool,
        mimeType: str = FOLDER_MIME_TYPE,
    ):
        self.id = id
        self.kind: Literal['Folder'] = 'Folder'
        self.name = name
        self.mimeType = mimeType
        self.parents = [ItemID(parent, type=Folder) for parent in parents]
        self.trashed = trashed

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not issubclass(type(other), type(self)):
            return NotImplemented
        return self.id == other.id

