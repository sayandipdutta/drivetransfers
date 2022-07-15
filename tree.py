from functools import singledispatchmethod
from typing import TypeVar, Literal, NewType, TypedDict, NotRequired

from files import File, Folder, Generic, ItemID, Item, overload

T = TypeVar('T', File, Folder)

class ItemData(TypedDict, Generic[T]):
    info: T
    ancestors: list[Folder]
    items: NotRequired['FileTree']
    nitems: NotRequired[int]
    size: int

class ItemDataDict(dict):
    def __missing__(self, key):
        if key == 'ancestors':
            return list()
        elif key == 'items':
            return FileTree()
        elif key == 'nitems':
            return 0
        elif key == 'size':
            return 0

class FileTree(dict, Generic[T]):
    @singledispatchmethod
    def __overloaded_missing__(self, key):
        raise NotImplementedError("Keys must be string.")

    @__overloaded_missing__.register
    def _(self, key: ItemID[T]) -> ItemData[T]:
        self[key] = dict.fromkeys(['info', 'ancestors', 'size'])
        self[key]['ancestors'] = list[Folder]()
        if isinstance(key, ItemID) and key.type == Folder:
            self[key]['items'] = type(self)()
            self[key]['nitems'] = 0
        self[key]['size'] = 0
        return self[key]

    @__overloaded_missing__.register
    def _(self, key: str) -> 'FileTree':
        self[key] = type(self)()
        return self[key]

    @overload
    def __missing__(self, key: ItemID[Folder]) -> ItemData[Folder]:
        ...

    @overload
    def __missing__(self, key: ItemID[File]) -> ItemData[File]:
        ...

    @overload
    def __missing__(self, key: str) -> 'FileTree':
        ...

    def __missing__(self, key: ItemID | str) -> ItemData | 'FileTree':
        return self.__overloaded_missing__(key)

    def __delitem__(self, key):
        val = self[key]
        if isinstance(val, type(self)):
            if not val['ancestors']:
                del self[key]
                return
            for ancestor in val['ancestors']:
                ancestor['size'] -= val['size']
            ancestor['nitems'] -= 1
            if ancestor['nitems'] == 0 and ancestor['size'] == 0:
                del ancestor
        del self[key]
