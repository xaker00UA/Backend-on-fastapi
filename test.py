import asyncio


async def one_task():
    await asyncio.sleep(5)
    print("one_task")


async def two_task():
    await asyncio.sleep(3)
    print("two_task")


async def three_task():
    await asyncio.sleep(5)
    print("three_task")


async def main():
    tasks = [
        # asyncio.create_task(one_task(), name="1"),
        asyncio.create_task(two_task(), name="2"),
        # asyncio.create_task(three_task(), name="3"),
        # asyncio.create_task(three_task(), name="4"),
    ]
    done, pending = await asyncio.wait(tasks, timeout=3)

    for task in done:
        print(task.result())  # Получаем результат выполнения
        print(task.get_name())
    print("---Pending tasks---")
    for task in pending:
        print(task.get_name())


asyncio.run(main())
