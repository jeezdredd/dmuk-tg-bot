from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import random

from src.handlers.common_keyboards import kb_main
from src.storage import Storage

router = Router(name="schedule")

BTN_BACK = "⬅️ Back"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "All"]

TEACHERS = [
    {"name": "Ivan Ivanov", "email": "ivan.ivanov@dmuk.kz"},
    {"name": "Jane Doe", "email": "jane.doe@dmuk.kz"},
    {"name": "Daniyar Akhmetov", "email": "daniyar.akhmetov@dmuk.kz"},
    {"name": "Svetlana Kim", "email": "svetlana.kim@dmuk.kz"},
    {"name": "Aidos Mukhtar", "email": "aidos.mukhtar@dmuk.kz"},
]
SUBJECTS = [
    {"code": "CS101", "name": "Intro to Computer Science"},
    {"code": "CS202", "name": "Algorithms"},
    {"code": "CS301", "name": "Database Systems"},
    {"code": "CS404", "name": "Artificial Intelligence"},
    {"code": "CS303", "name": "Operating Systems"},
    {"code": "CS220", "name": "Web Development"},
]

class ScheduleFSM(StatesGroup):
    waiting_day = State()

def random_room():
    building = random.choice(["B", "C"])
    floor = random.randint(1, 4)
    room = random.randint(1, 9)
    return f"{building}{floor}.{room}", building

def random_timepair():
    return random.choice(["09:00-11:30", "11:40-14:10", "14:30-17:00", "16:00-18:00"])

def generate_schedule():
    schedule = {}
    for day in DAYS[:-1]:
        items = []
        for _ in range(random.randint(1, 2)):  # максимум 2, минимум 1
            subj = random.choice(SUBJECTS)
            teacher = random.choice(TEACHERS)
            room_code, building = random_room()
            items.append({
                "subject": f"{subj['code']} {subj['name']}",
                "teacher": f"{teacher['name']} ({teacher['email']})",
                "room": room_code,
                "building": building,
                "time": random_timepair(),
            })
        schedule[day] = items
    return schedule

SAMPLE_SCHEDULE = generate_schedule()

def kb_days_with_back() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text=day)] for day in DAYS]
    keyboard.append([KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

@router.message(Command("schedule"))
@router.message(F.text.in_({"📅 Schedule", "Расписание"}))
async def ask_day(message: Message, state: FSMContext):
    await state.set_state(ScheduleFSM.waiting_day)
    await message.answer("Choose a day for your schedule:", reply_markup=kb_days_with_back())

# ВАЖНО: перехват профиля прямо из состояния расписания
@router.message(ScheduleFSM.waiting_day, F.text.in_({"👤 Profile", "Профиль"}))
@router.message(ScheduleFSM.waiting_day, F.text.regexp(r"^/profile\b"))
async def open_profile_from_schedule(message: Message, state: FSMContext, storage: Storage):
    # Сначала выходим из FSM расписания, потом открываем профиль
    await state.clear()
    # Локальный импорт, чтобы не создать циклический импорт модулей
    from src.handlers.profile import show_profile
    await show_profile(message, storage)

@router.message(ScheduleFSM.waiting_day, F.text == BTN_BACK)
async def return_to_main_menu(message: Message, storage: Storage, admin_ids: set[int]):
    user_id = message.from_user.id
    is_admin = user_id in admin_ids
    subscribed = await storage.is_subscribed(user_id)
    await message.answer("⬅️ <b>Main menu:</b>", reply_markup=kb_main(subscribed, is_admin), parse_mode="HTML")
    await message.fsm_context().clear()

@router.message(ScheduleFSM.waiting_day, F.text)
async def send_schedule(message: Message, state: FSMContext):
    day = (message.text or "").strip()
    if day not in DAYS:
        return await message.answer("❌ Please choose a valid day.", reply_markup=kb_days_with_back())

    if day == "All":
        # Двойные отступы между днями
        parts = []
        for d in DAYS[:-1]:
            items = SAMPLE_SCHEDULE.get(d, [])
            if not items:
                continue
            block_lines = [f"<b>📅 {d}</b>"]
            for item in items:
                block_lines.append(
                    f"📚 <b>{item['subject']}</b>\n"
                    f"👨‍🏫 {item['teacher']}\n"
                    f"🏢 Room: {item['room']} ({item['building']})\n"
                    f"⏰ {item['time']}"
                )
            parts.append("\n".join(block_lines))
        text = "\n\n".join(parts) if parts else "No lectures this week."
        await message.answer(text, reply_markup=kb_days_with_back(), parse_mode="HTML")
        return

    items = SAMPLE_SCHEDULE.get(day, [])
    if not items:
        return await message.answer("No lectures for this day.", reply_markup=kb_days_with_back())

    lines = [f"<b>📅 {day}</b>"]
    for item in items:
        lines.append(
            f"📚 <b>{item['subject']}</b>\n"
            f"👨‍🏫 {item['teacher']}\n"
            f"🏢 Room: {item['room']} ({item['building']})\n"
            f"⏰ {item['time']}"
        )
    await message.answer("\n\n".join(lines), reply_markup=kb_days_with_back(), parse_mode="HTML")