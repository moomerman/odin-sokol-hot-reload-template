/*
For making a release exe that does not use hot reload.
*/

package main_release

import "core:log"
import "core:os"
import "base:runtime"

import game ".."
import sapp "../sokol/app"

import "../web"

_ :: os
_ :: log

USE_TRACKING_ALLOCATOR :: #config(USE_TRACKING_ALLOCATOR, false)

IS_WEB :: ODIN_ARCH == .wasm32 || ODIN_ARCH == .wasm64p32

main :: proc() {
	when IS_WEB {
		// The WASM allocator doesn't seem to work properly in combination with
		// emscripten. There is some kind of conflict with how they manage
		// memory. So this sets up an allocator that uses emscripten's malloc.
		context.allocator = web.emscripten_allocator()

		// Make temp allocator use new `context.allocator` by re-initing it.
		runtime.init_global_temporary_allocator(1*runtime.Megabyte)
	}

	when USE_TRACKING_ALLOCATOR {
		default_allocator := context.allocator
		tracking_allocator: Tracking_Allocator
		tracking_allocator_init(&tracking_allocator, default_allocator)
		context.allocator = allocator_from_tracking_allocator(&tracking_allocator)
	}

	when !IS_WEB {
		mode: int = 0
		when ODIN_OS == .Linux || ODIN_OS == .Darwin {
			mode = os.S_IRUSR | os.S_IWUSR | os.S_IRGRP | os.S_IROTH
		}

		logh, logh_err := os.open("log.txt", (os.O_CREATE | os.O_TRUNC | os.O_RDWR), mode)

		if logh_err == os.ERROR_NONE {
			os.stdout = logh
			os.stderr = logh
		}

		logger := logh_err == os.ERROR_NONE ? log.create_file_logger(logh) : log.create_console_logger()
		context.logger = logger
	}
	custom_context = context

	app_desc := game.game_app_default_desc()

	app_desc.init_cb = init
	app_desc.frame_cb = frame
	app_desc.cleanup_cb = cleanup
	app_desc.event_cb = event

	sapp.run(app_desc)

	free_all(context.temp_allocator)

	when !IS_WEB {
		if logh_err == os.ERROR_NONE {
			log.destroy_file_logger(logger)
		}
	}

	when USE_TRACKING_ALLOCATOR {
		for key, value in tracking_allocator.allocation_map {
			log.error("%v: Leaked %v bytes\n", value.location, value.size)
		}

		tracking_allocator_destroy(&tracking_allocator)
	}
}

custom_context: runtime.Context

init :: proc "c" () {
	context = custom_context
	game.game_init()
}

frame :: proc "c" () {
	context = custom_context
	game.game_frame()
	free_all(context.temp_allocator)
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