import asyncio
import logging
import sys

from config import BOT_TOKEN
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from faststream.rabbit import RabbitBroker
from schemas.schema import PriceRequest, PriceResponse


dp = Dispatcher()
broker = RabbitBroker("amqp://guest:guest@rabbitmq/")
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


ITEMS = [
    "P250 | Verdigris (Battle-Scarred)",
    "Chroma 3 Case",
    "Gamma Case",
    "Operation Breakout Weapon Case"
]


@dp.message()
async def start_handler(msg: types.Message):
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text=item, callback_data=item)] for item in ITEMS]
    )
    await msg.answer("Select an item to check the discount:", reply_markup=keyboard)


@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    item = callback.data
    await callback.answer(f"Check discount on: {item}")

    request_data = PriceRequest(
        chat_id=callback.from_user.id, 
        item_name=item
    )

    await broker.publish(request_data, "price_request")


@broker.subscriber("price_response")
async def handle_response(response: PriceResponse):
    message = (
        f"<b>{response.item_name}</b>\n\n"
        f"💵 Current price: <b>${response.current_price:.2f}</b>\n"
        f"📊 Average price: <b>${response.average_price:.2f}</b>\n\n"
        f"{'🎯 <b>There is a discount!</b>' if response.discount else '💤 No discount.'}"
    )
    await bot.send_message(response.chat_id, message, parse_mode="HTML")


async def wait_for_rabbitmq_connection(max_attempts=30):
    for i in range(1, max_attempts):
        try:
            reader, writer = await asyncio.open_connection("rabbitmq", 5672)
            writer.close()
            await writer.wait_closed()
            print("RabbitMQ is available!!!")
            return
        except Exception as e:
            print(f"[{i}/{max_attempts}] Waiting for RabbitMQ...")
            await asyncio.sleep(1)
    raise RuntimeError("Failed to connect to RabbitMQ :(")


async def main() -> None:
    await wait_for_rabbitmq_connection()

    while True:
        try:
            async with broker:
                await broker.start()
                await dp.start_polling(bot)
            break
        except Exception as e:
            logging.warning(f"RabbitMQ connection error: {e}")
            await asyncio.sleep(3)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())