# Kept for backward compatibility: color-setter.py and color-resetter.py were identical copies,
# so the implementation now lives in color-resetter.py and this script just runs it.
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'color-resetter.py'), run_name='__main__')
