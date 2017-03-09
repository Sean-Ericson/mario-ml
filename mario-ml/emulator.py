import subprocess
import socket
import os
import struct
import warnings
from threading import Thread
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from pywinauto.application import Application

bizhawk_dir = os.getcwd() + r'\bizhawk\\'

lua_script = 'pythonInterface.Lua'
bizhawk_exe = bizhawk_dir + 'EmuHawk.exe'
savestate = bizhawk_dir + r'DP1.State'
rom_path = r'C:\Users\Alex\Documents\Emulation\Zsnes\Super Mario World.smc'
savestate_arg = '--load-state=' + savestate

MSGLEN = 13 * 13


class EmulatorExecutor:
    def __init__(self, num_workers=1):
        self.num_workers = num_workers
        self.workers = []
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.fn_num = 0

        for i in range(0, num_workers):
            self.workers.append(EmulatorWorker(self.input_queue, self.output_queue))
            self.workers[-1].run()

    def submit(self, fn):
        self.input_queue.put((self.fn_num, fn))
        self.fn_num += 1

    def get_results(self):
        self.input_queue.join()
        res = {}
        while not self.output_queue.empty():
            fn_num, fitness = self.output_queue.get()
            res[fn_num] = fitness
        self.fn_num = 0
        return res

    def shutdown(self):
        for i in range(1, self.num_workers + 1):
            self.submit(None)
        for w in self.workers:
            w.join()


class EmulatorWorker:
    def __init__(self, input_queue, output_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue

        self.server_socket, self.port = self._get_socket()
        self.script_name = self._make_lua_script()

        self.emulator_process, self.connection = self._launch_emulator()
        self.thread = None

    def run(self):
        self.thread = Thread(target=self._run)
        self.thread.start()

    def join(self):
        self.thread.join()

    def _run(self):
        while True:
            task_num, fn = self.input_queue.get()
            if fn is None:
                break
            fitness = self._measure_fitness(fn)
            self.output_queue.put((task_num, fitness))
            self.input_queue.task_done()

        self.emulator_process.kill()
        script_full_path = bizhawk_dir + 'Lua\\' + self.script_name
        os.remove(script_full_path)

    def _measure_fitness(self, fn):
        # Reset and get initial screen
        self._send_message('reset')
        msg_type, buf = self._receive_message()
        position = struct.unpack(">169B", buf)
        net_input = [int(x == -1) for x in position]
        net_input += [int(x == 1) for x in position]
        while True:
            controller = fn(net_input)
            controller = [int(max(min(i, 1), 0)) for i in controller]
            self._send_message('controller_input', controller)
            msg_type, buf = self._receive_message()
            if msg_type == 1:
                fitness = struct.unpack('>i', buf)[0]
                return fitness
            position = struct.unpack(">169b", buf)
            # Separate sprites and level into different 0,1 inputs
            net_input = [int(x == -1) for x in position]
            net_input += [int(x == 1) for x in position]
            #position = np.array(position).reshape((13, 13))

    def _receive_message(self):
        msg_type = self.connection.recv(1)
        msg_type = struct.unpack('>B', msg_type)[0]

        if msg_type == 0:
            msg_len = 169
        if msg_type == 1:
            msg_len = 4
        else:
            ConnectionError('Unrecognized message type: {}'.format(msg_type))

        bytes_recd = 0
        buf = []
        while bytes_recd < msg_len:
            chunk = self.connection.recv(min(msg_len - bytes_recd, 2048))
            if chunk == '':
                raise RuntimeError('Socket connection broken')
            buf.append(chunk)
            bytes_recd += len(chunk)
        buf = b''.join(buf)
        return msg_type, buf

    def _send_message(self, msg_type, contents=None):
        if msg_type == 'controller_input':
            # Guard against up/down and left/right being pushed at same time
            # if contents[4] == 1 and contents[5] == 1:
            #     contents[4] = 0
            #     contents[5] = 1
            # if contents[6] == 1 and contents[7] == 1:
            #     contents[6] = 0
            #     contents[7] = 0
            message = bytes([0]) + struct.pack('>8B', *contents)
        elif msg_type == 'reset':
            message = bytes([1])
        self.connection.sendall(message)

    @staticmethod
    def _get_socket():
        server_socket = socket.socket()
        server_socket.bind(('', 0))
        server_socket.listen(1)
        port = server_socket.getsockname()[1]
        return server_socket, port

    def _make_lua_script(self):
        new_script_name = lua_script.split('.')
        new_script_name[0] += str(self.port)
        new_script_name = '.'.join(new_script_name)
        with open(bizhawk_dir + 'Lua\\' + lua_script, 'r+') as f:
            old = f.read()
        with open(bizhawk_dir + 'Lua\\' + new_script_name, 'w') as f:
            f.write('kPortNum = ' + str(self.port) + '\n' + old)
        return new_script_name

    def _launch_emulator(self):
        # Start EmuHawk and run Lua script. There is technically a race condition here - accept() must be run on the
        # socket before the Lua script kicked off by run_lua_script tries to connect to it, but it should never be a
        # problem in practice (ha!).
        emulator_process = subprocess.Popen(args=[bizhawk_exe, savestate_arg, rom_path])
        executor = ThreadPoolExecutor()
        executor.submit(self._run_lua_script, emulator_process, self.script_name)

        connection, address = self.server_socket.accept()
        return emulator_process, connection

    @staticmethod
    def _run_lua_script(emulator_process, script_name):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            app = Application().connect(process=emulator_process.pid)
        lua_window = app[u'Lua Console']
        lua_window.Wait('ready')
        lua_window.SetFocus()
        lua_window.TypeKeys('^o')

        app['Open'].Wait('ready')
        app['Open'].SetFocus()
        app['Open'].TypeKeys(script_name + '{ENTER}')

        lua_window.Minimize()


