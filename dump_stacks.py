import asyncio
import traceback
import sys


def dump():
    print("DUMPING ALL TASKS")
    for task in asyncio.all_tasks():
        print(f"Task: {task}")
        task.print_stack(file=sys.stdout)
    print("DONE DUMPING")
