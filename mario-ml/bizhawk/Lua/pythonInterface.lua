--kPortNum should be defined on first line by python code
socket = require("socket")
vstruct = require("vstruct")

ButtonNames = {
    "A",
    "B",
    "X",
    "Y",
    "Up",
    "Down",
    "Left",
    "Right",
}

file = assert(io.open("log.txt","w"), "Failed to open log file")

kTimeout = 40
kBoxRadius = 6
kInputSize = (kBoxRadius*2+1)*(kBoxRadius*2+1)

function isOverworld()
    return memory.readbyte(0x0100) == 0x0e
end

function getPosition()
    local marioX = memory.read_s16_le(0x94)
    local marioY = memory.read_s16_le(0x96)
    return marioX, marioY
end

function getTile(dx, dy, marioX, marioY)
    local x = math.floor((marioX+dx+8)/16)
    local y = math.floor((marioY+dy)/16)
    return memory.readbyte(0x1C800 + math.floor(x/0x10)*0x1B0 + y*0x10 + x%0x10)
end

function getSprites()
    local sprites = {}
    for slot=0,11 do
        local status = memory.readbyte(0x14C8+slot)
        if status ~= 0 then
            local spritex = memory.readbyte(0xE4+slot) + memory.readbyte(0x14E0+slot)*256
            local spritey = memory.readbyte(0xD8+slot) + memory.readbyte(0x14D4+slot)*256
            sprites[#sprites+1] = {["x"]=spritex, ["y"]=spritey}
        end
    end

    return sprites
end

function getExtendedSprites()
    local extended = {}
    for slot=0,11 do
        local number = memory.readbyte(0x170B+slot)
        if number ~= 0 then
            local spritex = memory.readbyte(0x171F+slot) + memory.readbyte(0x1733+slot)*256
            local spritey = memory.readbyte(0x1715+slot) + memory.readbyte(0x1729+slot)*256
            extended[#extended+1] = {["x"]=spritex, ["y"]=spritey}
        end
    end

    return extended
end

function getScreen()
    local marioX, marioY = getPosition()

    local sprites = getSprites()
    local extended = getExtendedSprites()

    local inputs = {}

    for dy=-kBoxRadius*16,kBoxRadius*16,16 do
        for dx=-kBoxRadius*16,kBoxRadius*16,16 do
            inputs[#inputs+1] = 0

            local tile = getTile(dx, dy, marioX, marioY)
            if tile == 1 and marioY+dy < 0x1B0 then
                inputs[#inputs] = 1
            end

            for i = 1,#sprites do
                local distx = math.abs(sprites[i]["x"] - (marioX+dx))
                local disty = math.abs(sprites[i]["y"] - (marioY+dy))
                if distx <= 8 and disty <= 8 then
                    inputs[#inputs] = -1
                end
            end

            for i = 1,#extended do
                local distx = math.abs(extended[i]["x"] - (marioX+dx))
                local disty = math.abs(extended[i]["y"] - (marioY+dy))
                if distx < 8 and disty < 8 then
                    inputs[#inputs] = -1
                end
            end
        end
    end

    return inputs
end

function clearJoypad()
    for b = 1,#ButtonNames do
        controller["P1 " .. ButtonNames[b]] = false
    end
    joypad.set(controller)
end

function setJoypad(input)
    for b = 1,#ButtonNames do
        local val = false
        if input[b] == 1 then
            val = true
        end
        controller["P1 " .. ButtonNames[b]] = val
    end
end

function receiveMessage(client)
    local msgType = client:receive(1)
    msgType = vstruct.read("u1>", msgType)
    msgType = msgType[1]
    file:write(msgType .. "\n")
    file:flush()
    if msgType == 0 then
        local data = client:receive(8)
        local input = vstruct.read("> 8*u1", data)
        file:write("Received input")
        file:flush()
        setJoypad(input)
    elseif msgType == 1 then
        file:write("Received reset\n")
        file:flush()
        initializeRun()
    end
end

function sendMessage(client, msgType)
    local message = 0
    if msgType == 0 then
        local screen = getScreen()
        table.insert(screen, 1, 0) -- Add 0 msg type
        message = vstruct.write("> 170*u1", screen)
    elseif msgType == 1 then
        local msg_arr  = {}
        msg_arr[1] = 1
        msg_arr[2] = fitness
        print(fitness)
        message = vstruct.write(">u1 i4", msg_arr)
    end
    client:send(message)
end

function initializeRun()
    savestate.load("DP1.state")
    currentFrame = 0
    timeout = kTimeout
    rightmost = 0
    controller = {}
    clearJoypad()
end

--------------
--Begin script
--------------

local client = socket.try(socket.connect("localhost",kPortNum))
local ip, port = client:getsockname()
print(ip)
print(port)
ip, port = client:getpeername()
print(ip)
print(port)

receiveMessage(client) --Initialize run here on first message receipt
while true do
    if currentFrame % 5 == 0 then
        sendMessage(client, 0)
        receiveMessage(client)
    end
    joypad.set(controller)

    local marioX, marioY = getPosition()
    if marioX > rightmost then
        rightmost = marioX
        timeout = kTimeout
    end

    timeout = timeout - 1
    local timeoutBoosted = timeout + currentFrame / 4
    if isOverworld() or (timeoutBoosted <= 0) then

        --fitness = math.floor(rightmost - currentFrame / 2)
        fitness = rightmost
        if rightmost > 4816 then
            fitness = fitness + 1000
        end
        sendMessage(client, 1)
        receiveMessage(client)
    end

	emu.frameadvance()
    currentFrame = currentFrame + 1
end