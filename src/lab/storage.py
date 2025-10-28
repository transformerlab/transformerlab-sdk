import os
import posixpath

import fsspec


_TFL_URI = os.getenv("TFL_STORAGE_URI")
_AWS_PROFILE = os.getenv("AWS_PROFILE")


def _get_fs_and_root():
    """
    Initialize filesystem and root path from TFL_STORAGE_URI.
    Falls back to local ~/.transformerlab or TFL_HOME_DIR when not set.
    """
    if not _TFL_URI or _TFL_URI.strip() == "":
        root = os.getenv(
            "TFL_HOME_DIR",
            os.path.join(os.path.expanduser("~"), ".transformerlab"),
        )
        fs = fsspec.filesystem("file")
        return fs, root

    # Let fsspec parse the URI
    fs, _token, paths = fsspec.get_fs_token_paths(
        _TFL_URI, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
    )
    # For S3 and other remote filesystems, we need to maintain the full URI format
    if _TFL_URI.startswith(("s3://", "gs://", "abfs://", "gcs://")):
        root = _TFL_URI.rstrip("/")
    else:
        root = paths[0] if paths else ""
    return fs, root


_fs, _root = _get_fs_and_root()


def root_uri() -> str:
    return _root


def filesystem():
    return _fs


def debug_info() -> dict:
    """Debug information about the current storage configuration."""
    return {
        "TFL_STORAGE_URI": _TFL_URI,
        "AWS_PROFILE": _AWS_PROFILE,
        "root_uri": _root,
        "filesystem_type": type(_fs).__name__,
    }


def join(*parts: str) -> str:
    return posixpath.join(*parts)


def root_join(*parts: str) -> str:
    return join(_root, *parts)


def exists(path: str) -> bool:
    return _fs.exists(path)


def isdir(path: str) -> bool:
    try:
        return _fs.isdir(path)
    except Exception:
        return False


def isfile(path: str) -> bool:
    try:
        return _fs.isfile(path)
    except Exception:
        return False


def makedirs(path: str, exist_ok: bool = True) -> None:
    try:
        _fs.makedirs(path, exist_ok=exist_ok)
    except TypeError:
        # Some filesystems don't support exist_ok parameter
        if not exist_ok or not _fs.exists(path):
            _fs.makedirs(path)


def ls(path: str, detail: bool = False):
    return _fs.ls(path, detail=detail)


def find(path: str) -> list[str]:
    return _fs.find(path)


def rm(path: str) -> None:
    if exists(path):
        _fs.rm(path)


def rm_tree(path: str) -> None:
    if exists(path):
        try:
            _fs.rm(path, recursive=True)
        except TypeError:
            # Some filesystems don't support recursive parameter
            # Use find() to get all files and remove them individually
            files = _fs.find(path)
            for file_path in reversed(files):  # Remove files before directories
                _fs.rm(file_path)


def open(path: str, mode: str = "r", **kwargs):
    return _fs.open(path, mode=mode, **kwargs)


def copy_file(src: str, dest: str) -> None:
    """Copy a single file from src to dest across arbitrary filesystems."""
    # Use streaming copy to be robust across different filesystems
    with fsspec.open(src, "rb") as r, fsspec.open(dest, "wb") as w:
        for chunk in iter_chunks(r):
            w.write(chunk)


def iter_chunks(file_obj, chunk_size: int = 8 * 1024 * 1024):
    """Helper to read file in chunks."""
    while True:
        data = file_obj.read(chunk_size)
        if not data:
            break
        yield data


def copy_dir(src_dir: str, dest_dir: str) -> None:
    """Recursively copy a directory tree across arbitrary filesystems."""
    makedirs(dest_dir, exist_ok=True)
    # Determine the source filesystem independently of destination
    src_fs, _ = fsspec.core.url_to_fs(src_dir)
    try:
        src_files = src_fs.find(src_dir)
    except Exception:
        # If find is not available, fall back to listing via walk
        src_files = []
        for _, _, files in src_fs.walk(src_dir):
            for f in files:
                src_files.append(f)

    for src_file in src_files:
        # Compute relative path with respect to the source dir
        rel_path = src_file[len(src_dir):].lstrip("/")
        dest_file = join(dest_dir, rel_path)
        # Ensure destination directory exists
        dest_parent = posixpath.dirname(dest_file)
        if dest_parent:
            makedirs(dest_parent, exist_ok=True)
        # Copy the file using streaming (robust across FSes)
        copy_file(src_file, dest_file)