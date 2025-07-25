# Steam Price Checker Bot

This project is a Telegram bot that allows users to check item prices: increases and discounts from the Steam Market (but only for CS2). It uses RabbitMQ for communication between services and fetches real-time price data from the Steam Community Market API.

### Features

    Telegram bot interface with keyboard and manual input support

    Asynchronous messaging with RabbitMQ using faststream

    Fetches data from Steam Market using aiohttp

    Calculates discount based on current and median prices

    Resilient connection handling to RabbitMQ with retries

    Dynamic item list via items.json


### Tech Stack

    Python 3.11+

    Aiogram – Telegram bot framework

    FastAPI – Background service with broker subscriber

    FastStream + RabbitMQ – For async message communication

    Aiohttp – To fetch data from Steam Market

    Pydantic – Data validation with models