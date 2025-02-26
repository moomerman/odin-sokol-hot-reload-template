#!/usr/bin/env python3

import argparse

args_parser = argparse.ArgumentParser(
	prog = "build.py",
	description = "Odin + Sokol Hot Reload Template build script.",
	epilog = "Made by Karl Zylinski.")

args_parser.add_argument("-hot-reload",        action="store_true",   help="Build hot reload game DLL. Also builds executable if game not already running. This is the default when not specifying anything.")
args_parser.add_argument("-release",           action="store_true",   help="Build release game executable. Note: Deletes everything in the 'build/release' directory.")
args_parser.add_argument("-debug",             action="store_true",   help="Build release-style game executable, but with debugging enabled. Note: Don't use this to debug the hot reload exe. The hot reload exe always has debugging enabled.")
args_parser.add_argument("-web",               action="store_true",   help="Build web release. Either make sure emscripten is in your PATH or use -emsdk-path flag to specify where it lives.")
args_parser.add_argument("-emsdk-path",                               help="Path to where you have emscripten installed. Should be the root directory of your emscripten installation. Not necessary if emscripten is in your PATH.")
args_parser.add_argument("-run",               action="store_true",   help="Run the executable after compiling it.")
args_parser.add_argument("-no-shader-compile", action="store_true",   help="Don't compile shaders.")
args_parser.add_argument("-update-sokol",      action="store_true",   help="Download Sokol bindings and Sokol shader compiler. Compiles the libraries for the current platform. Happens automatically when either the `sokol-shdc' or 'source/sokol' directories are missing. Note: Deletes everything in 'sokol-shdc' and 'source/sokol' directories.")

import urllib.request
import os
import zipfile
import shutil
import platform
import subprocess
from enum import Enum

args = args_parser.parse_args()

num_build_modes = 0
if args.hot_reload:
	num_build_modes += 1
if args.release:
	num_build_modes += 1
if args.debug:
	num_build_modes += 1
if args.web:
	num_build_modes += 1

if num_build_modes > 1:
	print("Can only use one of: -hot-reload, -release, -debug and -web.")
	exit(1)

SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_OSX = SYSTEM == "Darwin"
IS_LINUX = SYSTEM == "Linux"

assert IS_WINDOWS or IS_OSX or IS_LINUX, "Unsupported platform."

def main():
	update_sokol()

	if not args.no_shader_compile:
		build_shaders()

	exe_path = ""
	
	if args.release:
		exe_path = build_release()
	elif args.debug:
		exe_path = build_debug()
	elif args.web:
		exe_path = build_web()
	elif args.hot_reload:
		exe_path = build_hot_reload()
	else:
		exe_path = build_hot_reload()

	if exe_path != "" and args.run:
		print("Starting " + exe_path)
		subprocess.Popen(exe_path)

def build_shaders():
	print("Building shaders...")
	shdc = get_shader_compiler()

	shaders = []

	for root, dirs, files in os.walk("source"):
		for file in files:
			if file.endswith(".glsl"):
				shaders.append(os.path.join(root, file))

	for s in shaders:
		out_dir = os.path.dirname(s)
		out_filename = os.path.basename(s)
		out = out_dir + "/gen__" + (out_filename.removesuffix("glsl") + "odin")
		execute(shdc + " -i %s -o %s -l glsl300es:hlsl4:glsl430 -f sokol_odin" % (s, out))

def get_shader_compiler():
	path = ""

	if IS_WINDOWS:
		path = "sokol-shdc/win32/sokol-shdc.exe"
	elif IS_LINUX:
		path = "sokol-shdc/linux/sokol-shdc"

	assert os.path.exists(path), "Could not find shader compiler. Try running this script with update-sokol parameter"
	return path

path_join = os.path.join

def build_hot_reload():
	out_dir = "build/hot_reload"

	if not os.path.exists(out_dir):
		os.mkdir(out_dir)

	exe = "game_hot_reload" + executable_extension()
	dll_final_name = out_dir + "/game" + dll_extension()
	dll = dll_final_name

	if IS_LINUX or IS_OSX:
		dll = out_dir + "/game_tmp" + dll_extension()

	# Only used on windows
	pdb_dir = out_dir + "/game_pdbs"
	pdb_number = 0
	
	dll_extra_args = ""
	game_running = process_exists(exe)

	if IS_WINDOWS:
		if not game_running:
			out_dir_files = os.listdir(out_dir)

			for f in out_dir_files:
				if f.endswith(".dll"):
					os.remove(os.path.join(out_dir, f))

			if os.path.exists(pdb_dir):
				shutil.rmtree(pdb_dir)

		if not os.path.exists(pdb_dir):
			os.mkdir(pdb_dir)
		else:
			pdb_files = os.listdir(pdb_dir)

			for f in pdb_files:
				if f.endswith(".pdb"):
					n = int(f.removesuffix(".pdb").removeprefix("game_"))

					if n > pdb_number:
						pdb_number = n

		# On windows we make sure the PDB name for the DLL is unique on each
		# build. This makes debugging work properly.
		dll_extra_args = " -pdb-name:%s/game_%i.pdb" % (pdb_dir, pdb_number + 1)

	print("Building " + dll_final_name + "...")
	execute("odin build source -debug -define:SOKOL_DLL=true -build-mode:dll -out:%s %s" % (dll, dll_extra_args))

	if IS_LINUX or IS_OSX:
		os.rename(dll, dll_final_name)

	if game_running:
		print("Hot reloading...")

		# Hot reloading means the running executable will see the new dll.
		# So we can just return empty string here. This makes sure that the main
		# function does not try to run the executable, even if `run` is specified.
		return ""

	exe_extra_args = ""

	if IS_WINDOWS:
		exe_extra_args = " -pdb-name:%s/main_hot_reload.pdb" % out_dir

	print("Building " + exe + "...")
	execute("odin build source/main_hot_reload -strict-style -define:SOKOL_DLL=true -vet -debug -out:%s %s" % (exe, exe_extra_args))

	if IS_WINDOWS:
		dll_name = "sokol_dll_windows_x64_d3d11_debug.dll"

		if not os.path.exists(dll_name):
			print("Copying %s" % dll_name)
			shutil.copyfile(sokol_path + "/" + dll_name, dll_name)

	return exe

def build_release():
	out_dir = "build/release"

	if os.path.exists(out_dir):
		shutil.rmtree(out_dir)

	os.mkdir(out_dir)

	exe = out_dir + "/game_release" + executable_extension()

	print("Building " + exe + "...")

	extra_args = ""

	if IS_WINDOWS:
		extra_args += " -subsystem:windows"

	execute("odin build source/main_release -out:%s -strict-style -vet -no-bounds-check -o:speed %s" % (exe, extra_args))
	shutil.copytree("assets", out_dir + "/assets")

	return exe

def build_debug():
	out_dir = "build/debug"

	if not os.path.exists(out_dir):
		os.mkdir(out_dir)

	exe = out_dir + "/game_debug" + executable_extension()
	print("Building " + exe + "...")
	execute("odin build source/main_release -out:%s -strict-style -vet -debug" % exe)
	shutil.copytree("assets", out_dir + "/assets", dirs_exist_ok = True)
	return exe

def build_web():
	out_dir = "build/web"

	if not os.path.exists(out_dir):
		os.mkdir(out_dir)

	print("Building js_wasm32 game object...")
	execute("odin build source/main_web -target:js_wasm32 -build-mode:obj -vet -strict-style -out:%s/game -debug" % out_dir)
	odin_path = subprocess.run(["odin", "root"], capture_output=True, text=True).stdout

	shutil.copyfile(os.path.join(odin_path, "core/sys/wasm/js/odin.js"), os.path.join(out_dir, "odin.js"))
	os.environ["EMSDK_QUIET"] = "1"

	emcc_files = [
		"%s/game.wasm.o" % out_dir,
		"source/sokol/app/sokol_app_wasm_gl_release.a",
		"source/sokol/glue/sokol_glue_wasm_gl_release.a",
		"source/sokol/gfx/sokol_gfx_wasm_gl_release.a",
		"source/sokol/shape/sokol_shape_wasm_gl_release.a",
		"source/sokol/log/sokol_log_wasm_gl_release.a",
		"source/sokol/gl/sokol_gl_wasm_gl_release.a",
	]

	emcc_files_str = " ".join(emcc_files)

	# Note --preload-file assets, this bakes in the whole assets directory into
	# the web build.
	emcc_flags = "--shell-file source/web/index_template.html --preload-file assets -sWASM_BIGINT -sWARN_ON_UNDEFINED_SYMBOLS=0 -sMAX_WEBGL_VERSION=2 -sASSERTIONS"
	emcc_command = "emcc -g -o %s/index.html %s %s" % (out_dir, emcc_files_str, emcc_flags)

	emsdk_env = get_emscripten_env_command()

	if emsdk_env is not None:
		if IS_WINDOWS:
			emcc_command = emsdk_env + " && " + emcc_command
		else:
			emcc_command = "bash -c \"" + emsdk_env + " && " + emcc_command + "\""
	else:
		emcc_exists = shutil.which("emcc") is not None

		if not emcc_exists:
			print("Could not find emcc. Try providing emscripten SDK path using '-emsdk-path PATH' or run the emsdk_env script inside the emscripten folder before running this script.")
			exit(1)

	print("Building web application using emscripten to %s..." % out_dir)
	execute(emcc_command)

	# Not needed
	os.remove(os.path.join(out_dir, "game.wasm.o"))

def execute(cmd):
	res = os.system(cmd)
	assert res == 0, "Failed running: " + cmd

def dll_extension():
	if IS_WINDOWS:
		return ".dll"

	if IS_OSX:
		return ".dylib"

	return ".so"

def executable_extension():
	if IS_WINDOWS:
		return ".exe"

	return ".bin"

sokol_path = "source/sokol"

def update_sokol():
	force_update = args.update_sokol

	tools_zip = "https://github.com/floooh/sokol-tools-bin/archive/refs/heads/master.zip"
	sokol_zip = "https://github.com/floooh/sokol-odin/archive/refs/heads/main.zip"
	shdc_path = "sokol-shdc"

	if force_update:
		if os.path.exists(shdc_path):
			shutil.rmtree(shdc_path)

		if os.path.exists(sokol_path):
			shutil.rmtree(sokol_path)

	if (not os.path.exists(sokol_path)) or force_update:
		temp_zip = "sokol-temp.zip"
		temp_folder = "sokol-temp"
		print("Downloading Sokol Odin bindings to directory source/sokol...")
		urllib.request.urlretrieve(sokol_zip, temp_zip)

		with zipfile.ZipFile(temp_zip) as zip_file:
			zip_file.extractall(temp_folder)
			shutil.copytree(temp_folder + "/sokol-odin-main/sokol", sokol_path)

		os.remove(temp_zip)
		shutil.rmtree(temp_folder)

		print("Building Sokol C libraries...")
		owd = os.getcwd()
		os.chdir(sokol_path)

		emsdk_env = get_emscripten_env_command()


		if IS_WINDOWS:
			cl_exists = shutil.which("cl.exe") is not None

			if cl_exists:
				execute("build_clibs_windows.cmd")
			else:
				print("cl.exe not in PATH. Try running this from a Visual Studio command prompt.")

			emcc_exists = shutil.which("emcc.bat") is not None

			if emcc_exists:
				execute("build_clibs_wasm.bat")
			else:
				print("emcc.exe not in PATH, skipping building of WASM libs.")
		elif IS_LINUX:
			execute("bash build_clibs_linux.sh")

			build_wasm_prefix = ""
			if emsdk_env is not None:
				os.environ["EMSDK_QUIET"] = "1"
				build_wasm_prefix += emsdk_env + " && "

			execute("bash -c \"" + build_wasm_prefix + " bash build_clibs_wasm.sh\"")
		elif IS_OSX:
			execute("bash build_clibs_macos.sh")
			execute("bash build_clibs_wasm.sh")

		os.chdir(owd)

	if (not os.path.exists(shdc_path)) or force_update:
		temp_zip = "sokol-tools-temp.zip"
		temp_folder = "sokol-tools-temp"

		print("Downloading Sokol Shader Compiler to directory sokol-shdc...")
		urllib.request.urlretrieve(tools_zip, temp_zip)

		with zipfile.ZipFile(temp_zip) as zip_file:
			zip_file.extractall(temp_folder)
			shutil.copytree(temp_folder + "/sokol-tools-bin-master/bin", shdc_path)

		if IS_LINUX:
			execute("chmod +x sokol-shdc/linux/sokol-shdc")

		os.remove(temp_zip)
		shutil.rmtree(temp_folder)

def get_emscripten_env_command():
	if args.emsdk_path is None:
		return None

	if IS_WINDOWS:
		return os.path.join(args.emsdk_path, "emsdk_env.bat")
	elif IS_LINUX or IS_OSX:
		return "source " + os.path.join(args.emsdk_path, "emsdk_env.sh")

	return None

def process_exists(process_name):
	if IS_WINDOWS:
		call = 'TASKLIST', '/NH', '/FI', 'imagename eq %s' % process_name
		return process_name in str(subprocess.check_output(call))
	else:
		out = subprocess.run(["pidof", process_name], capture_output=True, text=True).stdout
		return out != ""


	return False

main()