import subprocess
import platform

def clear():

    command = "cls" if platform.system() == "Windows" else "clear"
    subprocess.run(command, shell=True)
