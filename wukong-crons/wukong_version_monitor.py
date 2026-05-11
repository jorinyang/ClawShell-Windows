# Forward to actual script
import sys, os
real_path = r"C:\Users\Aorus\Documents\wukong-optimized-ClawShell-tmp\wukong-crons\wukong_version_monitor.py"
if os.path.exists(real_path):
    os.system('py "' + real_path + '"')
else:
    print("ERROR: Script not found")
    sys.exit(1)
