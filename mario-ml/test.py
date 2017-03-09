import subprocess
import socket
import os
import atexit
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from pywinauto.application import Application
import matplotlib.pyplot as plt

bizhawk_dir = r'C:\Users\Alex\Desktop\BizHawk-1.11.6\\'

lua_script = 'pythonInterface.Lua'
bizhawk_exe = bizhawk_dir + 'EmuHawk.exe'
savestate = bizhawk_dir + r'DP1.State'
rom_path = r'C:\Users\Alex\Documents\Emulation\Zsnes\Super Mario World.smc'

savestate_arg = '--load-state=' + savestate


def make_lua_script(portNum):
    new_script_name = lua_script.split('.')
    new_script_name[0] = new_script_name[0] + str(portNum)
    new_script_name = '.'.join(new_script_name)
    with open(bizhawk_dir + 'Lua\\' + lua_script, 'r+') as f:
        old = f.read()
    with open(bizhawk_dir + 'Lua\\' + new_script_name, 'w') as f:
        f.write('kPortNum = ' + str(portNum) + '\n' + old)
    return new_script_name


def run_lua_script(p, script_name):
    app = Application().connect(process=p.pid)
    lua_window = app[u'Lua Console']
    lua_window.Wait('ready')
    lua_window.SetFocus()
    lua_window.TypeKeys('^o')

    app['Open'].Wait('ready')
    app['Open'].SetFocus()
    app['Open'].TypeKeys(script_name + '{ENTER}')

    lua_window.Minimize()


def main():
    # Make server socket and set it up. Generate custom Lua script for the port number we are assigned.
    server_socket = socket.socket()
    server_socket.bind(('', 0))
    port_num = server_socket.getsockname()[1]
    server_socket.listen(5)
    print(server_socket.getsockname())
    script_name = make_lua_script(port_num)
    atexit.register(os.remove, bizhawk_dir + 'Lua\\' + script_name)

    # Start EmuHawk and run Lua script
    p = subprocess.Popen(args=[bizhawk_exe, savestate_arg, rom_path])
    executor = ThreadPoolExecutor()
    executor.submit(run_lua_script, p, script_name)

    connection, address = server_socket.accept()
    print(address)

    #obj = plt.imshow(np.zeros((13, 13)))
    while True:
        MSGLEN = 13*13
        bytes_recd = 0
        buf = []
        while bytes_recd < MSGLEN:
            chunk = connection.recv(min(MSGLEN - bytes_recd, 2048))
            if chunk == '':
                raise RuntimeError('Socket connection broken')
            buf.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        buf = b''.join(buf)
        position = [int(chr(x)) for x in list(buf)]
        position = np.array(position).reshape((13, 13))
        #obj.set_array(position)
        #plt.draw()
        if buf == 0:
            break
        # print(buf)
        connection.sendall(b'OK')


if __name__ == "__main__":
    main()


