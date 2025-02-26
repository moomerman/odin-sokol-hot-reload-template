# THIS IS WORK IN PROGRESS AND NOT READY

# Odin + Sokol + Hot Reload template

Hot reload gameplay code when making games using Odin + Sokol. Also comes with web build support (no hot reload, just for web builds).

## Requirements

- Odin compiler (must be in PATH)
- Python
- Emscripten if you want web build support

## Getting started with Hot Reload

1. Run `build.py -hot-reload -run` (you need Python) -- It should download and build the Sokol bindings for you
2. If the building of the Sokol bindings failed in step 2) then you can re-run it using `build.py -hot-reload -compile-sokol -run`
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