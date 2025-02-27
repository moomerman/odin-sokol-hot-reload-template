# THIS IS WORK IN PROGRESS AND NOT READY

# Odin + Sokol + Hot Reload template

Hot reload gameplay code when making games using Odin + Sokol. Also comes with web build support (no hot reload, just for web builds).

## Requirements

- Odin compiler (must be in PATH)
- Python
- Emscripten if you want web build support

## Getting started with Hot Reload

1. Run `build.py -hot-reload -run` (you need Python) -- It should download the Sokol bindings and try to build the Sokol C libraries.
2. If the building of the Sokol C libraries failed in step 2) then you can re-run it by adding `-compile-sokol`: `build.py -hot-reload -compile-sokol -run` -- Common reasons for failing to compile the C libaries is that it can't find a C compiler.
3. A game with just a spinning cube should start
4. Leave the game running, change a some line in `game.odin`. Modify the line `g.rx += 60 * dt` to use the value `500` instead of `60`.
5. Re-run `build.py -hot-reload`. The game DLL will re-compile and get reloaded. The cube will spin faster.

## Getting started with web build

- Run `build.py -web`
- If it fails due not being able to find emscripten, then do `build.py -web -emsdk-path PATH_TO_EMSCRIPTEN`
- If it fails due to missing WASM libraries, then try `build.py -web -compile-sokol -emsdk-path PATH_TO_EMSCRITPEN`

## Making release builds

Make a native release build of your game (no hot reloading) using `build.py -release`

You can do `build.py -debug` to create a release-style executable without hot-reloading, but with debugging enabled.

## Updating Sokol

Add `-update-sokol` when runing `build.py` to download the lastest Odin Sokol bindings and latest Sokol shader compiler. Note that this will completely replace everything in the `sokol-shdc` and `source/sokol` directories.

The update process also tries to compile the Sokol C libraries.

## TODO

- VS Code settings is from raylib template, it's currently broken!
- More Linux testing
- OSX testing