import os

if not hasattr(os, "_walk_symlinks_as_files"):
    os._walk_symlinks_as_files = False
