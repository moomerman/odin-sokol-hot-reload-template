/*
Web build entry point
*/

package main_web

import "core:log"
import "base:runtime"

import game ".."
import sapp "../sokol/app"

main :: proc() {
	// The WASM allocator doesn't work properly in combination with emscripten.
	// This sets up an allocator that uses emscripten's malloc.
	context.allocator = emscripten_allocator()

	// Make temp allocator use new `context.allocator` by re-initing it.
	runtime.init_global_temporary_allocator(1*runtime.Megabyte)

	context.logger = log.create_console_logger(lowest = .Info, opt = {.Level, .Short_File_Path, .Line, .Procedure})
	custom_context = context

	app_desc := game.game_app_default_desc()
	app_desc.init_cb = init
	app_desc.frame_cb = frame
	app_desc.cleanup_cb = cleanup
	app_desc.event_cb = event

	sapp.run(app_desc)
	free_all(context.temp_allocator)

	log.destroy_console_logger(context.logger)
}

custom_context: runtime.Context

init :: proc "c" () {
	context = custom_context
	game.game_init()
}

frame :: proc "c" () {
	context = custom_context
	game.game_frame()
}

event :: proc "c" (e: ^sapp.Event) {
	context = custom_context
	game.game_event(e)
}

cleanup :: proc "c" () {
	context = custom_context
	game.game_cleanup()
}

// make game use good GPU on laptops etc

@(export)
NvOptimusEnablement: u32 = 1

@(export)
AmdPowerXpressRequestHighPerformance: i32 = 1