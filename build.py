import urllib.request
import os
import zipfile
import shutil
import sys
import platform
import subprocess

system = platform.system()

def main():
	update_sokol()
	build_shaders()

	if "release" in sys.argv:
		build_release()
	else:
		build_hot_reload()

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
		os.system(shdc + " -i %s -o %s -l glsl300es:hlsl4:glsl430 -f sokol_odin" % (s, out))

def get_shader_compiler():
	path = ""

	if system == "Windows":
		path = "sokol-shdc\\win32\\sokol-shdc.exe"

	assert os.path.exists(path), "Could not find shader compiler. Try running this script with update-sokol parameter"
	return path

def build_hot_reload():
	out_dir = "build/hot_reload"

	if not os.path.exists(out_dir):
		os.mkdir(out_dir)

	exe = "game_hot_reload" + executable_extension()
	dll = out_dir + "/game" + dll_extension()

	game_running = process_exists(exe)

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


def build_release():
	out_dir = "build/release"

	if os.path.exists(out_dir):
		shutil.rmtree(out_dir)

	os.mkdir(out_dir)

	exe = out_dir + "/game_release" + executable_extension()

	print("Building " + exe)

	extra_args = ""

	if system == "Windows":
		extra_args += " -subsystem:windows"

	os.system("odin build source/main_release -out:%s -strict-style -vet -no-bounds-check -o:speed %s" % (exe, extra_args))
	shutil.copytree("assets", out_dir + "/assets")

	if "run" in sys.argv:
		print("Starting " + exe)
		subprocess.Popen(exe)

def dll_extension():
	if system == "Windows":
		return ".dll"

	if system == "Darwin":
		return ".dylib"

	return ".so"

def executable_extension():
	if system == "Windows":
		return ".exe"

	return ".bin"

sokol_path = "source/sokol"

def update_sokol():
	force_update_sokol = "update-sokol" in sys.argv

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