import asyncio
import logging
import sys
import json

from config import BOT_TOKEN
from aiogram import Bot, Dispatcher, types, filters
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from faststream.rabbit import RabbitBroker
from schemas.schema import PriceRequest, PriceResponse


dp = Dispatcher()
broker = RabbitBroker("amqp://guest:guest@rabbitmq/")
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def load_items_from_json(filename: str) -> list[str]:
    with open(filename, 'r') as file:
        data = json.load(file)
    return data

ITEMS = load_items_from_json("items.json")


@dp.message(filters.Command("start"))
async def start_handler(msg: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=item)] for item in ITEMS],
        resize_keyboard=True
    )

    await msg.answer("Select or type an item to check the discount:", reply_markup=keyboard)

@dp.message()
async def text_handler(msg: types.Message):
    item = msg.text.strip()
    temp_msg = await msg.answer(f"Check discount on: {item}")

    request_data = PriceRequest(
        chat_id=msg.from_user.id,
        item_name=item
    )
    await broker.publish(request_data, "price_request")

    await asyncio.sleep(1.5)

    await temp_msg.delete()


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
            logging.info("RabbitMQ is available!!!")
            return
        except Exception as e:
            logging.info(f"[{i}/{max_attempts}] Waiting for RabbitMQ...")
            await asyncio.sleep(1)
    raise RuntimeError("Failed to connect to RabbitMQ :(")


async def main() -> None:
    await wait_for_rabbitmq_connection()

    while True:
        try:
            async with broker:
                await broker.start()
                await dp.start_polling(bot)
            return
        except Exception as e:
            logging.warning(f"RabbitMQ connection error: {e}")
            await asyncio.sleep(3)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())