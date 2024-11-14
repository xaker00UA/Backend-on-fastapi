import asyncio
import aiohttp
import time
from motor import MotorClient

client = MotorClient("mongodb://localhost:27017")
collection = client.test.Session

url = "https://api.wotblitz.eu/wotb/tanks/stats/?application_id=4da1ac881324daee13ad9f3b9432b286&account_id=672696064"


async def connect():
    data = await collection.find(projection={"nickname": 1, "_id": 0}).to_list()
    return data


async def get():
    data = await connect()
    print(len(data))
    for d in data:
        yield d


async def task(session, queue):
    while True:
        try:
            # Берем элемент из очереди
            data = await queue.get()
            if data is None:  # Если получим None, значит нужно завершить
                break
            name = data["nickname"]
            # Вы можете делать запросы, например:
            async with session.get(f"/eu/player/get_session?name={name}") as response:
                data = await response.json()
            print(f"Processed {name}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            queue.task_done()


async def main():
    queue = asyncio.Queue()

    # Создаем воркеры
    async def producer():
        async for data in get():
            await queue.put(data)
        # Завершаем работу всех воркеров
        for _ in range(10):
            await queue.put(None)

    async with aiohttp.ClientSession("http://localhost:8000") as session:
        # Создаем задачи для воркеров
        tasks = [task(session, queue) for _ in range(10)]

        # Запускаем продюсера, который будет наполнять очередь
        await asyncio.gather(producer(), *tasks)
        await queue.join()  # Ожидаем, пока все задачи не завершатся


if __name__ == "__main__":
    asyncio.run(main())
