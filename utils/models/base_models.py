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
    def __sub__(self, other):
        return isinstance(other, type(self))


class Singleton:
    _instance = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super().__new__(cls)
        return cls._instance[cls]
