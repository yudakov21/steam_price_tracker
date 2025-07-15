import urllib
import aiohttp
import logging
import asyncio

from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from schemas.schema import PriceRequest, PriceResponse
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_rabbitmq_connection()

    try:
        await broker.start()
        logging.info("Starting broker...")
        yield
    finally:
        logging.info("Shutting down broker...")
        await broker.close()


app = FastAPI(lifespan=lifespan)
broker = RabbitBroker("amqp://guest:guest@rabbitmq/")


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


# Broker signs up for the line/queue price_request
@broker.subscriber("price_request")
async def handle_request(req: PriceRequest):
    # !!!
    encoded_name = urllib.parse.quote(req.item_name)
    url = f"https://steamcommunity.com/market/priceoverview/?appid=730&market_hash_name={encoded_name}&currency=1"

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url) as response:
            steam_data = await response.json()
    
    if steam_data.get("success") and steam_data.get("lowest_price"):
        current = float(steam_data["lowest_price"].replace("$", "").replace(",", "."))
        average = float(steam_data["median_price"].replace("$", "").replace(",", "."))

        discount = current < average * 0.95
    else:
        current = average = 0.0
        discount = None

    response_data = PriceResponse(
        chat_id=req.chat_id,
        item_name=req.item_name,
        current_price=current,
        average_price=average,
        discount=discount
    )

    # 'publish' send response_data to the specified queue
    # price_response is a queue / routing key
    await broker.publish(response_data, "price_response")   