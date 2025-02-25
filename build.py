def print_usage():
	print("Odin + Sokol Hot Reload Template build script. Possible flags:\n")
	print("hot-reload      Build hot reload game DLL. Also builds executable if game not already running. This is the default when not specifying anything.")
	print("release         Build release game executable. Note: Deletes everything in the 'build/release' directory")
	print("debug           Build release-style game executable, but with debugging enabled. Note: Don't use this to debug the hot reload exe. The hot reload exe always has debugging enabled.")
	print("run             Run the executable after compiling it.")
	print("skip-shaders    Don't compile shaders.")
	print("update-sokol    Download Sokol bindings and Sokol shader compiler. Compiles the libraries for the current platform. Note: Deletes everything in 'sokol-shdc' and 'source/sokol' directories.")	

import urllib.request
import os
import zipfile
import shutil
import sys
import platform
import subprocess
from enum import Enum

SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_OSX = SYSTEM == "Darwin"
IS_LINUX = SYSTEM == "Linux"

def main():
	if "help" in sys.argv or "--help" in sys.argv or "-help" in sys.argv:
		print_usage()
		return

	update_sokol("update-sokol" in sys.argv)

	if not "skip-shaders" in sys.argv:
		build_shaders()

	build_type = "hot-reload"

	if "release" in sys.argv:
		build_type = "release"

	if "debug" in sys.argv:
		build_type = "debug"

	if "hot-reload" in sys.argv:
		build_type = "hot-reload"

	exe_path = ""
	
	if build_type == "release":
		exe_path = build_release()
	if build_type == "debug":
		exe_path = build_debug()
	elif build_type == "hot-reload":
		exe_path = build_hot_reload()

	if exe_path != "" and "run" in sys.argv:
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
		path = "sokol-shdc\\win32\\sokol-shdc.exe"

	assert os.path.exists(path), "Could not find shader compiler. Try running this script with update-sokol parameter"
	return path

path_join = os.path.join

def build_hot_reload():
	out_dir = "build/hot_reload"

	if not os.path.exists(out_dir):
		os.mkdir(out_dir)

	exe = "game_hot_reload" + executable_extension()
	dll = out_dir + "/game" + dll_extension()

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

	print("Building " + dll + "...")
	execute("odin build source -debug -define:SOKOL_DLL=true -build-mode:dll -out:%s %s" % (dll, dll_extra_args))

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

def update_sokol(force_update):
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
			
		os.chdir(owd)

	if (not os.path.exists(shdc_path)) or force_update:
		temp_zip = "sokol-tools-temp.zip"
		temp_folder = "sokol-tools-temp"

		print("Downloading Sokol Shader Compiler to directory sokol-shdc...")
		urllib.request.urlretrieve(tools_zip, temp_zip)

		with zipfile.ZipFile(temp_zip) as zip_file:
			zip_file.extractall(temp_folder)
			shutil.copytree(temp_folder + "/sokol-tools-bin-master/bin", shdc_path)

		os.remove(temp_zip)
		shutil.rmtree(temp_folder)

def process_exists(process_name):
	if IS_WINDOWS:
		call = 'TASKLIST', '/NH', '/FI', 'imagename eq %s' % process_name
		return process_name in str(subprocess.check_output(call))

	return False

main()