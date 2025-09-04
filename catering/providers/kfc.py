from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    COOKING = "cooking"
    COOKED = "cooked"
