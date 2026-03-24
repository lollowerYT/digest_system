from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.database.models.token_transaction import TokenTransaction


class TokenService:
    
    @staticmethod
    async def add_tokens(
        session: AsyncSession,
        user: User,
        amount: int,
        reason: str = "MANUAL_ADD"
    ):
        if amount < 0:
            raise ValueError("Tokens cannot be negative")
        
        user.token_balance += amount
        
        transaction = TokenTransaction(
            user_id=user.id,
            amount=amount,
            description=reason
        )
        
        session.add(transaction)
    
    @staticmethod
    async def subtract_tokens(
        session: AsyncSession,
        user: User,
        amount: int,
        reason: str = "USAGE"
    ):
        if amount < 0:
            raise ValueError("Tokens cannot be negative")

        if user.token_balance < amount:
            raise ValueError("Not enough tokens")

        user.token_balance -= amount

        transaction = TokenTransaction(
            user_id=user.id,
            amount=-amount,
            type=reason
        )

        session.add(transaction)
    
    @staticmethod
    async def set_tokens(
        session: AsyncSession,
        user: User,
        amount: int,
        reason: str = "MANUAL_SET"
    ):
        if amount < 0:
            raise ValueError("Tokens cannot be negative")

        delta = amount - user.token_balance
        user.token_balance = amount

        transaction = TokenTransaction(
            user_id=user.id,
            amount=delta,
            description=reason
        )

        session.add(transaction)
