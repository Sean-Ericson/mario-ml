import emulator
from queue import Queue
import pygame

input_queue = Queue()
output_queue = Queue()

pygame.init()
def input_fn(position):
    key = pygame.key.get_pressed()
    emulator_input = [key[pygame.K_s], key[pygame.K_x], key[pygame.K_a], key[pygame.K_z],
                      key[pygame.K_UP], key[pygame.K_DOWN], key[pygame.K_LEFT], key[pygame.K_RIGHT]]
    return [int(x) for x in emulator_input]


def fn1(position):
    return [0, 0, 0, 0, 0, 0, 0, 1]

def fn2(position):
    return [0, 1, 0, 0, 0, 0, 0, 0]


executor = emulator.EmulatorExecutor(1)
executor.submit(input_fn)
executor.submit(input_fn)
executor.submit(input_fn)
executor.submit(fn2)
executor.submit(fn2)
executor.submit(fn2)

res = executor.get_results()

print(res)

