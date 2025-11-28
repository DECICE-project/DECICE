import asyncio
import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from auth.security import get_auth_service
from config.config import get_settings
from db.models import PlatformIdentity, User
from domain.user_schemas import UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_database():
    """
    Connects to the database and seeds it with initial admin/user accounts
    and their default platform identities in a single session.
    """
    logger.info("Starting database seeding process...")
    settings = get_settings()

    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    auth_service = await get_auth_service()

    users_to_seed = [
        {
            "id": uuid4(),
            "username": "admin",
            "email": "admin@example.com",
            "full_name": "Admin User",
            "active": True,
            "hashed_password": auth_service.get_password_hash("admin"),
            "role": UserRole.ADMIN,
            "project": "decice",
        },
        {
            "id": uuid4(),
            "username": "user",
            "email": "user@example.com",
            "full_name": "Regular User",
            "active": True,
            "hashed_password": auth_service.get_password_hash("user"),
            "role": UserRole.USER,
            "project": "decice",
        },
    ]

    try:
        async with AsyncSessionLocal() as session:
            # Seed Users
            logger.info("Seeding users (admin, user)...")
            for user_data in users_to_seed:
                stmt = insert(User).values(**user_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["email"],
                    set_={
                        "username": user_data["username"],
                        "full_name": user_data["full_name"],
                        "active": user_data["active"],
                        "hashed_password": user_data["hashed_password"],
                        "role": user_data["role"],
                        "project": user_data["project"],
                    },
                )
                await session.execute(stmt)
            await session.commit()
            logger.info("User seeding complete or users already exist.")

            # Get the User IDs
            logger.info("Fetching user IDs for identity seeding...")
            admin_user_result = await session.execute(
                select(User.id).where(User.username == "admin")
            )
            admin_user_id = admin_user_result.scalar_one_or_none()

            user_user_result = await session.execute(
                select(User.id).where(User.username == "user")
            )
            user_user_id = user_user_result.scalar_one_or_none()

            # Seed Platform Identities
            logger.info("Seeding platform identities...")
            identities_to_seed = []

            if admin_user_id:
                logger.info(f"Found admin user ID: {admin_user_id}")
                identities_to_seed.append(
                    {
                        "id": uuid4(),
                        "user_id": admin_user_id,
                        "platform": "hpc-main",
                        "platform_username": "admin-hpc-user",
                        "default_working_dir": "/home/admin-hpc-user",
                    }
                )
            else:
                logger.warning("Could not find 'admin' user to seed platform identity.")

            if user_user_id:
                logger.info(f"Found user user ID: {user_user_id}")
                identities_to_seed.append(
                    {
                        "id": uuid4(),
                        "user_id": user_user_id,
                        "platform": "hpc-main",
                        "platform_username": "regular-hpc-user",
                        "default_working_dir": "/home/regular-hpc-user",
                    }
                )
            else:
                logger.warning("Could not find 'user' user to seed platform identity.")

            if not identities_to_seed:
                logger.warning("No users found, skipping platform identity seeding.")
            else:
                for identity_data in identities_to_seed:
                    stmt = insert(PlatformIdentity).values(**identity_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["user_id", "platform", "platform_username"],
                        set_={
                            "default_working_dir": identity_data["default_working_dir"],
                        },
                    )
                    await session.execute(stmt)
                await session.commit()
                logger.info("Platform identity seeding complete.")

    except Exception as e:
        logger.critical(
            f"An error occurred during the seeding process: {e}", exc_info=True
        )
    finally:
        await engine.dispose()
        logger.info("Database seeding process finished.")


if __name__ == "__main__":
    asyncio.run(seed_database())
