# Odin + Sokol + Hot Reload template

WIP Hot reload with Odin and Sokol.

build.py can download and compile sokol for you, including the shader compiler

build.py also builds the game for you. Use `-hot-reload` to build in hot reload mode and `-release` to make a native release exe and `-web` to create a web build.

TODO:
- Make it work on linux and mac (some things in the build.py isn't platform independent)
- README
- Documentation
- Make the .vscode stuff work
- the file reading stuff in utils_web.odin is duiplicated in web folder
