import urllib
import aiohttp
import logging
import asyncio

from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from schemas.schema import PriceRequest, PriceResponse
from contextlib import asynccontextmanager
from typing import Protocol


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


class PriceClient(Protocol):
    async def get_steam_prices(self, item_name: str) -> tuple[float, float]:
        ...

class SteamMarketClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def get_steam_prices(self, item_name: str) -> tuple[float, float]:
        encoded_name = urllib.parse.quote(item_name)
        url = f"https://steamcommunity.com/market/priceoverview/?appid=730&market_hash_name={encoded_name}&currency=1"

        async with self.session.get(url=url) as response:
            steam_data = await response.json()
        
        if steam_data.get("success") and steam_data.get("lowest_price"):
            current = float(steam_data["lowest_price"].replace("$", "").replace(",", "."))
            average = float(steam_data["median_price"].replace("$", "").replace(",", "."))
        else:
            current = average = 0.0

        return current, average


async def handle_request(req: PriceRequest, client: PriceClient):
    current, average = await client.get_steam_prices(req.item_name)

    discount = current < average * 0.95 if req.check_type == "discount" else None      
    increase = current > average * 1.05 if req.check_type == "increase" else None
            

    response_data = PriceResponse(
        chat_id=req.chat_id,
        item_name=req.item_name,
        current_price=current,
        average_price=average,
        discount=discount,
        increase=increase
    )

    # 'publish' send response_data to the specified queue
    # price_response is a queue / routing key
    await broker.publish(response_data, "price_response")   


@broker.subscriber("price_request")
async def broker_handler(req: PriceRequest):
    async with aiohttp.ClientSession() as session:
        steam_client = SteamMarketClient(session)
        await handle_request(req, steam_client)
