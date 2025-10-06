import asyncio
import os

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

import qrcode

from src.config import load_config


def print_qr_ascii(data: str, png_path: str | None = None):
    qr = qrcode.QRCode(border=1, box_size=2)
    qr.add_data(data)
    qr.make(fit=True)
    try:
        qr.print_ascii(invert=True)
    except Exception:
        pass
    if png_path:
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(png_path)
        print(f"QR is saved to: {os.path.abspath(png_path)}")


def prompt_2fa_password() -> str:
    env_pw = os.getenv("TELEGRAM_2FA_PASSWORD")
    if env_pw:
        print("Using 2FA password from .env TELEGRAM_2FA_PASSWORD.")
        return env_pw
    # Важно: используем input(), чтобы подсказка была видна даже в PyCharm/Windows
    return input("Enter 2FA password for authentication (2FA): ").strip()


async def login_via_qr(client: TelegramClient):
    print("Using QR for login. On mobile: Telegram → Settings → Devices → Привязать устройство → сканируйте QR ниже.")
    while True:
        qr_login = await client.qr_login()
        print("\nСканируйте этот QR (действителен ~1 минуту):")
        print_qr_ascii(qr_login.url, png_path="telegram_login_qr.png")
        try:
            # Ждём подтверждения на телефоне
            await asyncio.wait_for(qr_login.wait(), timeout=120)
        except asyncio.TimeoutError:
            print("QR истёк, генерирую новый…")
            continue
        except SessionPasswordNeededError:
            # Требуется пароль 2FA прямо в процессе QR
            pw = prompt_2fa_password()
            await client.sign_in(password=pw)

        # Если после QR всё ещё не авторизовано — запросим пароль 2FA явно
        if not await client.is_user_authorized():
            try:
                pw = prompt_2fa_password()
                await client.sign_in(password=pw)
            except SessionPasswordNeededError:
                pw = prompt_2fa_password()
                await client.sign_in(password=pw)

        if await client.is_user_authorized():
            print("Авторизация завершена.")
            break
        else:
            print("Не удалось авторизоваться через QR. Пробуем ещё раз…")


async def login_via_code(client: TelegramClient):
    phone = input("Введите номер телефона в формате +7XXXXXXXXXX: ").strip()
    force_sms = (input("Отправить код по SMS? [y/N]: ").strip().lower() == "y")
    await client.send_code_request(phone, force_sms=force_sms)
    code = input("Код из Telegram/SMS/звонка: ").strip()
    try:
        await client.sign_in(phone=phone, code=code)
    except SessionPasswordNeededError:
        pw = prompt_2fa_password()
        await client.sign_in(password=pw)
    print("Авторизация завершена.")


async def main():
    # Загружаем конфиг/креды API
    config = load_config()
    if not (config.telegram_api_id and config.telegram_api_hash):
        raise RuntimeError("TELEGRAM_API_ID / TELEGRAM_API_HASH не заданы в .env")

    client = TelegramClient(config.telegram_session_name, config.telegram_api_id, config.telegram_api_hash)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Уже авторизовано: {getattr(me, 'first_name', '')} ({me.id}). Файл сессии: {config.telegram_session_name}.session")
        await client.disconnect()
        return

    print("Выберите метод входа:")
    print("1 — QR-код (рекомендуется)")
    print("2 — Код по телефону/SMS")
    choice = (input("Ваш выбор [1/2]: ").strip() or "1")

    if choice == "1":
        await login_via_qr(client)
    else:
        await login_via_code(client)

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Готово. Вошли как: {getattr(me, 'first_name', '')} ({me.id}).")
        print(f"Сессия сохранена в файл: {config.telegram_session_name}.session")
    else:
        print("Не удалось авторизоваться.")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())