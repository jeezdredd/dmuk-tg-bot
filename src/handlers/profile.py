from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os

from src.storage import Storage
from src.handlers.common_keyboards import kb_main

router = Router(name="profile")

# Кнопки
BTN_BACK = "⬅️ Back"
BTN_SET_ID = "🆔 Set ID"
BTN_SET_NAME = "👤 Set Name"
BTN_UPLOAD_PHOTO = "🖼 Upload Photo"
BTN_REMOVE_PHOTO = "🗑 Remove Photo"
BTN_SKIP = "⏭ Skip"

# RU алиасы (поддержка двух языков)
BTN_SET_ID_SET = {BTN_SET_ID, "Изменить ID", "ID"}
BTN_SET_NAME_SET = {BTN_SET_NAME, "Изменить ФИО", "Имя"}
BTN_UPLOAD_PHOTO_SET = {BTN_UPLOAD_PHOTO, "Загрузить фото"}
BTN_REMOVE_PHOTO_SET = {BTN_REMOVE_PHOTO, "Удалить фото"}
BTN_BACK_SET = {BTN_BACK, "Назад"}
BTN_SKIP_SET = {BTN_SKIP, "/skip"}

PROFILE_PHOTO_DIR = "data/profile_photos"
os.makedirs(PROFILE_PHOTO_DIR, exist_ok=True)

class StudentFSM(StatesGroup):
    waiting_id = State()
    waiting_name = State()
    waiting_photo = State()

VALID_STUDENT_IDS = {"P1234567", "P7654321", "P1112223"}  # demo allowlist

def kb_profile_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SET_ID), KeyboardButton(text=BTN_SET_NAME)],
            [KeyboardButton(text=BTN_UPLOAD_PHOTO), KeyboardButton(text=BTN_REMOVE_PHOTO)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True
    )

def kb_back_or_skip() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SKIP)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True
    )

# Профиль — открывается в любом состоянии
@router.message(StateFilter("*"), Command("profile"))
@router.message(StateFilter("*"), F.text.in_({"👤 Profile", "Профиль"}))
async def show_profile(message: Message, storage: Storage):
    user_id = message.from_user.id
    student_id, full_name, profile_photo = await storage.get_student_profile(user_id)
    student_id = student_id or "Not set"
    full_name = full_name or "Not set"

    text = (
        "👤 <b>Your profile</b>\n"
        f"• Student ID: {student_id}\n"
        f"• Name: {full_name}\n\n"
        "Choose action below:"
    )

    if profile_photo and os.path.exists(profile_photo):
        try:
            await message.answer_photo(FSInputFile(profile_photo), caption=text, parse_mode="HTML", reply_markup=kb_profile_menu())
            return
        except Exception:
            # Если файл недоступен/повреждён — падаем в текстовый вариант и очищаем ссылку
            try:
                await storage.set_student_profile(user_id, student_id if student_id != "Not set" else "", full_name if full_name != "Not set" else "", profile_photo=None)
            except Exception:
                pass

    await message.answer(text, parse_mode="HTML", reply_markup=kb_profile_menu())

# Назад в главное меню — в любом состоянии
@router.message(StateFilter("*"), F.text.in_(BTN_BACK_SET))
async def return_to_main_menu(message: Message, storage: Storage, admin_ids: set[int], state: FSMContext):
    user_id = message.from_user.id
    is_admin = user_id in admin_ids
    subscribed = await storage.is_subscribed(user_id)
    await message.answer("⬅️ <b>Main menu:</b>", reply_markup=kb_main(subscribed, is_admin), parse_mode="HTML")
    await state.clear()

# Установить/изменить Student ID
@router.message(StateFilter("*"), F.text.in_(BTN_SET_ID_SET))
@router.message(Command("student"))
async def set_student_id(message: Message, state: FSMContext):
    await state.set_state(StudentFSM.waiting_id)
    await message.answer("Please send your student ID (format: P1234567)", reply_markup=kb_back_or_skip())

@router.message(StudentFSM.waiting_id, F.text)
async def handle_student_id(message: Message, state: FSMContext, storage: Storage):
    student_id = (message.text or "").strip().upper()
    if student_id in BTN_BACK_SET or student_id in BTN_SKIP_SET:
        await state.clear()
        return await show_profile(message, storage)

    if not (student_id.startswith("P") and len(student_id) == 8 and student_id[1:].isdigit()):
        return await message.answer("❌ Invalid ID. Please send a valid student ID (e.g. P1234567).", reply_markup=kb_back_or_skip())

    # Сохраняем ID, не трогая имя/фото
    cur_id, cur_name, cur_photo = await storage.get_student_profile(message.from_user.id)
    await storage.set_student_profile(message.from_user.id, student_id, cur_name or "", profile_photo=cur_photo)
    await state.clear()
    await message.answer("✅ Student ID saved.", reply_markup=kb_profile_menu())

# Установить/изменить ФИО
@router.message(StateFilter("*"), F.text.in_(BTN_SET_NAME_SET))
async def set_full_name(message: Message, state: FSMContext):
    await state.set_state(StudentFSM.waiting_name)
    await message.answer("Send your full name (Firstname Lastname)", reply_markup=kb_back_or_skip())

@router.message(StudentFSM.waiting_name, F.text)
async def handle_full_name(message: Message, state: FSMContext, storage: Storage):
    full_name = (message.text or "").strip()
    if full_name in BTN_BACK_SET or full_name in BTN_SKIP_SET:
        await state.clear()
        return await show_profile(message, storage)

    if len(full_name.split()) < 2:
        return await message.answer("❌ Please send your full name (Firstname Lastname).", reply_markup=kb_back_or_skip())

    # Сохраняем имя, не трогая ID/фото
    cur_id, cur_name, cur_photo = await storage.get_student_profile(message.from_user.id)
    await storage.set_student_profile(message.from_user.id, cur_id or "", full_name, profile_photo=cur_photo)
    await state.clear()
    await message.answer("✅ Full name saved.", reply_markup=kb_profile_menu())

# Загрузить фото
@router.message(StateFilter("*"), F.text.in_(BTN_UPLOAD_PHOTO_SET))
async def ask_photo(message: Message, state: FSMContext):
    await state.set_state(StudentFSM.waiting_photo)
    await message.answer("Send a profile photo (or press Skip).", reply_markup=kb_back_or_skip())

@router.message(StudentFSM.waiting_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext, storage: Storage):
    file_id = message.photo[-1].file_id
    os.makedirs(PROFILE_PHOTO_DIR, exist_ok=True)
    photo_path = os.path.join(PROFILE_PHOTO_DIR, f"profile_{message.from_user.id}.jpg")
    await message.bot.download(file_id, destination=photo_path)

    # Если ID/имя не в state (редактирование только фото), подтянем текущие
    data = await state.get_data()
    student_id = data.get("student_id")
    full_name = data.get("full_name")
    if student_id is None or full_name is None:
        cur_id, cur_name, _cur_photo = await storage.get_student_profile(message.from_user.id)
        student_id = student_id if student_id is not None else (cur_id or "")
        full_name = full_name if full_name is not None else (cur_name or "")

    await storage.set_student_profile(message.from_user.id, student_id, full_name, profile_photo=photo_path)
    await state.clear()
    await message.answer("✅ Profile photo saved.", parse_mode="HTML", reply_markup=kb_profile_menu())

# Скип фото (и из мастера, и из одиночной загрузки)
@router.message(StudentFSM.waiting_photo, F.text.in_(BTN_SKIP_SET))
async def skip_photo(message: Message, state: FSMContext, storage: Storage):
    await state.clear()
    await message.answer("⏭ Skipped.", parse_mode="HTML", reply_markup=kb_profile_menu())

# Удалить фото
@router.message(StateFilter("*"), F.text.in_(BTN_REMOVE_PHOTO_SET))
async def remove_photo(message: Message, storage: Storage):
    user_id = message.from_user.id
    cur_id, cur_name, cur_photo = await storage.get_student_profile(user_id)
    if cur_photo and os.path.exists(cur_photo):
        try:
            os.remove(cur_photo)
        except Exception:
            pass
    await storage.set_student_profile(user_id, cur_id or "", cur_name or "", profile_photo=None)
    await message.answer("🗑 Profile photo removed.", reply_markup=kb_profile_menu())