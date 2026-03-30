import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from back import *

BOT_TOKEN = open("token.txt").readline().strip()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

ADMINS = []
with open("admins.txt", 'r') as f:
    ADMINS.append(int(i.strip()) for i in f)


#----------КНОПКИ----------

#Начальное меню пользователя
user_greetings_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Задать вопрос", callback_data="ask_a_question")]]
)

#Меню пользователя
user_reply_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Позвать оператора", callback_data="call_the_operator")],
        [InlineKeyboardButton(text="Задать еще вопрос", callback_data="ask_a_question")]
    ]
)

user_reply_to_admin_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Завершить диалог с оператором", callback_data="end_dialog")]
    ]
)

#Начальное меню админа
admin_greetings_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[ [InlineKeyboardButton(text="Начать работу", callback_data="go_to_admin_main_menu")] ]
)

#Главное меню админа
admin_main_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Открыть заявки", callback_data="see_the_problems")
        ],
        [
            InlineKeyboardButton(text="Добавить админа", callback_data="add_the_admin")
        ],
        [
            InlineKeyboardButton(text="Настройки бота", callback_data="go_to_settings")
        ]
    ]
)

#Назад в главное меню админа
admin_back_to_main_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Назад в главное меню", callback_data="back_to_main_menu")]]
)

#Меню ответа пользователю админа
admin_reply_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Закрыть обращение", callback_data="close_the_problem")
        ],
        [
            InlineKeyboardButton(text="Выйти", callback_data="exit")
        ],
        [
            InlineKeyboardButton(text="Создать Прецедент", callback_data="create_precedent")
        ]
    ]
)


#----------HANDLERS----------

#Приветствие для админа
@dp.message(CommandStart(), F.from_user.id.in_(ADMINS))
async def cmd_start(message: types.Message):
    create_user(message.from_user.id, True)
    await message.answer("Добро пожаловать, Админ! Для начала работы нажми \"Начать работу\"", reply_markup=admin_greetings_menu_kb)

#Приветствие для пользователя
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    create_user(message.from_user.id)
    await message.answer("Здравствуйте! Я бот поддержки. Для начала работы нажмите на кнопку \"Задать вопрос\"", reply_markup=user_greetings_menu_kb)

#Обработка сообщений админа
@dp.message(F.from_user.id.in_(ADMINS), F.text)
async def text_message(message: types.Message):
    admin_id = message.from_user.id
    admin_current_state = get_user_current_state(admin_id)
    
    if admin_current_state == "looking at problems":
        problem_id = get_unsolved_problems_id(int(message.text))
        if problem_id is not None:
            change_user_current_state(admin_id, new_state="chating")
            change_problem_admin_id(admin_id, problem_id)
            await message.answer(get_chat_history_from_problem(problem_id), reply_markup=admin_reply_menu_kb)

    if admin_current_state == "chating":
        problem_id = get_unsolved_problems_id(admin_tg_id=admin_id)
        user_id = get_user_id_in_problems(problem_id)
        change_problem_chat_history(problem_id, get_chat_history_from_problem(problem_id) + "Админ: "+ message.text)
        await bot.send_message(chat_id=user_id, text=message.text, reply_markup=user_reply_to_admin_menu_kb)
        await message.answer(text="Что делаем дальше?", reply_markup=admin_reply_menu_kb)

#Обработка сообщений пользователя
@dp.message(F.text)
async def text_message(message: types.Message):
    user_tg_id = message.from_user.id
    user_current_state = get_user_current_state(user_tg_id)
    if user_current_state == "asking":
        problem_id = get_unsolved_problems_id(user_tg_id)
        text =  message.text

        if problem_id is None:
            create_problem(user_tg_id, chat_history="Пользователь: " + message.text)
            llm_answer = ask_llm(text)
        else:
            history = get_chat_history_from_problem(problem_id)
            llm_answer = ask_llm(text)
            change_problem_chat_history(problem_id, history + "\nПользователь: " + text + "\nLLM: " + llm_answer)

        await message.answer(llm_answer, reply_markup=user_reply_menu_kb)
        

    elif user_current_state == "chating":
        user_tg_id = message.from_user.id
        problem_id = get_unsolved_problems_id(user_tg_id)
        chat_history = get_chat_history_from_problem(problem_id)
        change_problem_chat_history(problem_id, chat_history +'\nПользователь: ' + message.text)

        admin_tg_id = get_admin_id_in_problems(problem_id)
        print("Отправляю админу с id ", admin_tg_id)
        if admin_tg_id is not None:
            await bot.send_message(chat_id=admin_tg_id, text=message.text)



#----------HANDLERS FOR BUTTONS----------

#Задать вопрос
@dp.callback_query(F.data == "ask_a_question")
async def change_state(callback: CallbackQuery):
    await callback.answer()
    user_tg_id = callback.from_user.id
    problem_id = get_unsolved_problems_id(user_tg_id)
    if problem_id is not None:
        change_problem_status(problem_id, new_status="Solved")

    change_user_current_state(callback.from_user.id, "asking")
    await callback.message.answer("Напиши свой вопрос")

#Позвать оператора
@dp.callback_query(F.data == "call_the_operator")
async def change_state(callback: CallbackQuery):
    await callback.answer()
    print("Вопрос задан")
    change_user_current_state(callback.from_user.id, "chating")
    await callback.message.answer("Предал ваш вопрос оператору. Скоро он поможет вам!")

#Завершить диалог
@dp.callback_query(F.data == "end_dialog")
async def change_state(callback: CallbackQuery):
    await callback.answer()
    change_user_current_state(callback.from_user.id, "asking")
    await callback.message.answer("Есть еще вопросы? Задавайте!")

#Начать работу
@dp.callback_query(F.data == "go_to_admin_main_menu")
async def change_state(callback: CallbackQuery):
    await callback.answer()
    change_user_current_state(callback.from_user.id, "main menu")
    await callback.message.answer(text="Главное меню", reply_markup=admin_main_menu_kb)

#Открыть заявки
@dp.callback_query(F.data == "see_the_problems")
async def change_state(callback: CallbackQuery):
    await callback.answer()
    change_user_current_state(callback.from_user.id, "looking at problems")
    text = 'Вот все заявки.\nДля выбора заявки отправьте id пользователя сообщением\n\n'
    problems = get_unsolved_problems_id()

    for problem_id in problems:
        text += "user: " + str(get_user_id_in_problems(problem_id)) + "\n" + get_chat_history_from_problem(problem_id)[:100] + "\n\n"
    
    await callback.message.answer(text=text, reply_markup=admin_back_to_main_menu_kb)

#Возврат в главное меню
@dp.callback_query(F.data == "back_to_main_menu")
async def change_state(callback: CallbackQuery):
    await callback.answer()
    change_user_current_state(callback.from_user.id, "main menu")
    await callback.message.answer(text="Главное меню", reply_markup=admin_main_menu_kb)

#Закрыть обращение
@dp.callback_query(F.data == "close_the_problem")
async def change_state(callback: CallbackQuery):
    await callback.answer()
    admin_tg_id = callback.from_user.id
    change_user_current_state(callback.from_user.id, "main menu")
    problem_id = get_unsolved_problems_id(admin_tg_id=admin_tg_id)
    change_problem_status(problem_id, new_status="Solved")
    await callback.message.answer(text="Главное меню", reply_markup=admin_main_menu_kb)

#Добавиить прецедент
@dp.callback_query(F.data == "create_precedent")
async def change_state(callback: CallbackQuery):
    await callback.answer()
    admin_tg_id = callback.from_user.id
    change_user_current_state(callback.from_user.id, "main menu")

    problem_id = get_unsolved_problems_id(admin_tg_id=admin_tg_id)
    add_precedent(get_chat_history_from_problem(problem_id))
    change_problem_status(problem_id, new_status="Solved")

    await callback.message.answer(text="Главное меню", reply_markup=admin_main_menu_kb)
    



#----------MAIN----------
async def main():
    print("Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: 
        open("info.db")
    except:
        print("создаю таблицу)")
        create_and_fill_db()

    asyncio.run(main())