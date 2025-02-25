import urllib.request
import os
import zipfile
import shutil
import sys
import platform
import subprocess

system = platform.system()
out_dir = "build/hot_reload"

def main():
	if not os.path.exists(out_dir):
		os.make_directory(out_dir)

	update_sokol("update-sokol" in sys.argv)
	print("Building shaders...")
	shdc = get_shader_compiler()
	os.system(shdc + " -i source/shader.glsl -o source/shader.odin -l glsl300es:hlsl4:glsl430 -f sokol_odin")
	build_hot_reload()

def get_shader_compiler():
	path = ""

	if system == "Windows":
		path = "sokol-shdc\\win32\\sokol-shdc.exe"

	assert os.path.exists(path), "Could not find shader compiler. Try running this script with update-sokol parameter"
	return path

def build_hot_reload():
	exe = output_executable()
	game_running = process_exists(exe)
	dll = output_dll()

	print("Building " + dll)
	os.system("odin build source -debug -define:SOKOL_DLL=true -build-mode:dll -out:" + dll)

	if game_running:
		print("Hot reloading...")

		# Hot reloading means the running executable will see the new dll.
		# So we can just return here.
		return

	print("Building " + exe)
	os.system("odin build source/main_hot_reload -strict-style -define:SOKOL_DLL=true -vet -debug -out:%s" % exe)

	if system == "Windows":
		dll_name = "sokol_dll_windows_x64_d3d11_debug.dll"

		if not os.path.exists(dll_name):
			print("Copying %s" % dll_name)
			shutil.copyfile(sokol_path + "/" + dll_name, dll_name)

	if "run" in sys.argv:
		print("Starting " + exe)
		subprocess.Popen(exe)

def output_executable():
	if system == "Windows":
		return "game_hot_reload.exe"

	return "game_hot_reload.bin"

def output_dll():
	if system == "Windows":
		return out_dir + "/game.dll"
	
	if system == "Darwin":
		return out_dir + "/game.dylib"

	return out_dir + "/game.so"

sokol_path = "source/sokol"

def update_sokol(force_update_sokol):
	tools_zip = "https://github.com/floooh/sokol-tools-bin/archive/refs/heads/master.zip"
	sokol_zip = "https://github.com/floooh/sokol-odin/archive/refs/heads/main.zip"
	shdc_path = "sokol-shdc"

	if force_update_sokol:
		if os.path.exists(shdc_path):
			shutil.rmtree(shdc_path)

		if os.path.exists(sokol_path):
			shutil.rmtree(sokol_path)

	if (not os.path.exists(sokol_path)) or force_update_sokol:
		temp_zip = "sokol-temp.zip"
		temp_folder = "sokol-temp"
		print("Downloading Sokol Odin bindings to directory source/sokol...")
		urllib.request.urlretrieve(sokol_zip, temp_zip)

		with zipfile.ZipFile(temp_zip) as zip_file:
			zip_file.extractall(temp_folder)
			shutil.copytree(temp_folder + "/sokol-odin-main/sokol", sokol_path)

		os.remove(temp_zip)
		shutil.rmtree(temp_folder)

		print("Building Sokol C libraries")
		owd = os.getcwd()
		os.chdir(sokol_path)

		if system == "Windows":
			cl_exists = shutil.which("cl.exe") is not None

			if cl_exists:
				os.system("build_clibs_windows.cmd")
			else:
				print("cl.exe not in PATH. Try running this from a Visual Studio command prompt.")

			emcc_exists = shutil.which("emcc.bat") is not None

			if emcc_exists:
				os.system("build_clibs_wasm.bat")
			else:
				print("emcc.exe not in PATH, skipping building of WASM libs.")
			
		os.chdir(owd)

	if (not os.path.exists(shdc_path)) or force_update_sokol:
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
	if system == "Windows":
		call = 'TASKLIST', '/NH', '/FI', 'imagename eq %s' % process_name
		return process_name in str(subprocess.check_output(call))

	return False

main()