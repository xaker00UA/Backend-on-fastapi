from abc import ABC, abstractmethod


class Data_class(ABC):
    @abstractmethod
    def result(self, other):
        pass

    @classmethod
    @abstractmethod
    def general(cls):
        return f"Class: {cls.__name__}"


class Session(ABC):
    @abstractmethod
    def __sub__(self, other) -> "Session":
        return isinstance(other, type(self))

    @abstractmethod
    def result(self) -> dict:
        pass

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return all(getattr(self, k) == getattr(other, k) for k in self.__dict__)
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


class Singleton:
    _instance = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super().__new__(cls)
        return cls._instance[cls]
