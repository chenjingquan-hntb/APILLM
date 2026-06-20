"""创建/更新用户并生成 API Key。

用法:
  python scripts/create_user.py                        # 默认创建 admin 用户
  python scripts/create_user.py --username test --password 123456 --role user
  python scripts/create_user.py --username admin --password admin123 --role admin --update  # 更新已有用户
"""
import argparse
import asyncio
import hashlib
import hmac
import secrets
from sqlalchemy import select
from app.services.auth import hash_password
from app.core.config import settings
from app.db.base import async_session_factory
from app.db.models import ApiKey, User


async def main():
    parser = argparse.ArgumentParser(description="创建/更新用户并生成 API Key")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=None)
    parser.add_argument("--role", default="admin", choices=("admin", "user"))
    parser.add_argument("--balance", type=float, default=100.0)
    parser.add_argument("--update", action="store_true", help="更新已有用户而非报错")
    args = parser.parse_args()

    async with async_session_factory() as s:
        # 检查用户是否已存在
        result = await s.execute(select(User).where(User.username == args.username))
        user = result.scalar_one_or_none()

        if user is not None:
            if not args.update:
                print(f"用户 '{args.username}' 已存在。使用 --update 更新角色和密码。")
                return
            print(f"更新已有用户: {args.username}")
            user.role = args.role
            user.balance = args.balance
            if args.password:
                user.password_hash = hash_password(args.password)
            await s.commit()
            await s.refresh(user)
        else:
            print(f"创建新用户: {args.username} (role={args.role})")
            password_hash = hash_password(args.password) if args.password else None
            user = User(
                username=args.username,
                password_hash=password_hash,
                role=args.role,
                balance=args.balance,
            )
            s.add(user)
            await s.flush()

        # 检查是否已有 API Key
        key_result = await s.execute(
            select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.is_active.is_(True))
        )
        existing_key = key_result.scalar_one_or_none()

        if existing_key:
            print(f"API Key 已存在 (id={existing_key.id})")
        else:
            # 生成新 API Key
            raw_key = secrets.token_hex(24)
            key_hash = hmac.new(
                settings.secret_key.encode(),
                raw_key.encode(),
                hashlib.sha256,
            ).hexdigest()
            s.add(ApiKey(user_id=user.id, key_hash=key_hash, label="default"))
            await s.commit()
            print(f"API Key: sk-relay-{raw_key}")
            print("请妥善保管此 Key，它仅显示一次。")

    print(f"用户 '{args.username}' 就绪 (role={args.role}, balance={args.balance})")


if __name__ == "__main__":
    asyncio.run(main())
