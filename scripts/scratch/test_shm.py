from multiprocessing.shared_memory import SharedMemory

shm = SharedMemory(create=True, size=1024)
shm.close()
shm.unlink()
