# mario-ml - Playing Mario with Machine Learning

This project was inspired from [Sethbling's excellent video](https://www.youtube.com/watch?v=qv6UVOQ0F44) on applying the 
[NEAT (Neuroevolution of augmenting topologies)](https://en.wikipedia.org/wiki/Neuroevolution_of_augmenting_topologies) algorithm to play
Super Mario World.

Sethbling implemented his entire algorithm in Lua, which can be run from within the Bizhawk emulator. My first goal was to separate the learning algorithm from the game interface and move it into Python where all of the existing ML libraries might be utilized. To accomplish that, I grafted LuaSocket onto the BizHawk Lua interpreter and created some simple message types to pass back and forth between the Lua script running in BizHawk and a separately running Python script. 

It's a bit cumbersome to run a Lua script in BizHawk, so I used Python to automate launching the emulator, loading the script, and opening communications on a new socket. This is all abstracted away in an EmulatorExecutor object, which provides an interface similar to ThreadpoolExecutor. This simple interface can be used to play around with different ML ideas.
