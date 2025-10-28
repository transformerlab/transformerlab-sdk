import os
import posixpath
import contextvars

import fsspec


# Context variable for storage URI (set by host app/session)
_current_tfl_storage_uri: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_tfl_storage_uri", default=None
)

_AWS_PROFILE = os.getenv("AWS_PROFILE")


def _get_fs_and_root():
    """
    Initialize filesystem and root path from context variable or TFL_STORAGE_URI.
    Falls back to local ~/.transformerlab or TFL_HOME_DIR when not set.
    """
    # Check context variable first, then fall back to environment variable
    # tfl_uri = _current_tfl_storage_uri.get() or os.getenv("TFL_STORAGE_URI")
    tfl_uri = os.getenv("TFL_STORAGE_URI")
    
    if not tfl_uri or tfl_uri.strip() == "":
        root = os.getenv(
            "TFL_HOME_DIR",
            os.path.join(os.path.expanduser("~"), ".transformerlab"),
        )
        fs = fsspec.filesystem("file")
        return fs, root

    # Let fsspec parse the URI
    fs, _token, paths = fsspec.get_fs_token_paths(
        tfl_uri, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
    )
    # For S3 and other remote filesystems, we need to maintain the full URI format
    if tfl_uri.startswith(("s3://", "gs://", "abfs://", "gcs://")):
        root = tfl_uri.rstrip("/")
    else:
        root = paths[0] if paths else ""
    return fs, root


def root_uri() -> str:
    _, root = _get_fs_and_root()
    return root


def filesystem():
    fs, _ = _get_fs_and_root()
    return fs


def debug_info() -> dict:
    """Debug information about the current storage configuration."""
    context_uri = _current_tfl_storage_uri.get()
    env_uri = os.getenv("TFL_STORAGE_URI")
    fs, root = _get_fs_and_root()
    return {
        "TFL_STORAGE_URI_context": context_uri,
        "TFL_STORAGE_URI_env": env_uri,
        "AWS_PROFILE": _AWS_PROFILE,
        "root_uri": root,
        "filesystem_type": type(fs).__name__,
    }


def join(*parts: str) -> str:
    return posixpath.join(*parts)


def root_join(*parts: str) -> str:
    return join(root_uri(), *parts)


def exists(path: str, filesystem_override: str | None = None) -> bool:
    if filesystem_override:
        fs, _token, paths = fsspec.get_fs_token_paths(
            filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
        )
        return fs.exists(path)
    else:
        return filesystem().exists(path)


def isdir(path: str, filesystem_override: str | None = None) -> bool:
    try:
        if filesystem_override:
            fs, _token, paths = fsspec.get_fs_token_paths(
                filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
            )
            return fs.isdir(path)
        else:
            return filesystem().isdir(path)
    except Exception:
        return False


def isfile(path: str, filesystem_override: str | None = None) -> bool:
    try:
        if filesystem_override:
            fs, _token, paths = fsspec.get_fs_token_paths(
                filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
            )
            return fs.isfile(path)
        else:
            return filesystem().isfile(path)
    except Exception:
        return False


def makedirs(path: str, exist_ok: bool = True, filesystem_override: str | None = None) -> None:
    try:
        if filesystem_override:
            fs, _token, paths = fsspec.get_fs_token_paths(
                filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
            )
            fs.makedirs(path, exist_ok=exist_ok)
        else:
            filesystem().makedirs(path, exist_ok=exist_ok)
    except TypeError:
        # Some filesystems don't support exist_ok parameter
        if not exist_ok or not exists(path):
            filesystem().makedirs(path)


def ls(path: str, detail: bool = False, filesystem_override: str | None = None):
    if filesystem_override:
        # Let fsspec parse the URI
        fs, _token, paths = fsspec.get_fs_token_paths(
            filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
        )
        paths = fs.ls(path, detail=detail)
        # Dont include the current path in the list
        # Ensure paths are full URIs for remote filesystems
        if path.startswith(("s3://", "gs://", "abfs://", "gcs://")):
            # For remote filesystems, ensure returned paths are full URIs
            full_paths = []
            for p in paths:
                if not p.startswith(("s3://", "gs://", "abfs://", "gcs://")):
                    # Convert relative path to full URI
                    protocol = path.split("://")[0] + "://"
                    full_path = protocol + p
                    full_paths.append(full_path)
                else:
                    full_paths.append(p)
            full_paths = [p for p in full_paths if p != path]
            return full_paths
        return paths
    else:
        return filesystem().ls(path, detail=detail)


def find(path: str, filesystem_override: str | None = None) -> list[str]:
    if filesystem_override:
        fs, _token, paths = fsspec.get_fs_token_paths(
            filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
        )
        return fs.find(path)
    else:
        return filesystem().find(path)


def rm(path: str, filesystem_override: str | None = None) -> None:
    if exists(path):
        if filesystem_override:
            fs, _token, paths = fsspec.get_fs_token_paths(
                filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
            )
            fs.rm(path)
        else:
            filesystem().rm(path)


def rm_tree(path: str, filesystem_override: str | None = None) -> None:
    if exists(path, filesystem_override=filesystem_override):
        try:
            if filesystem_override:
                fs, _token, paths = fsspec.get_fs_token_paths(
                    filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
                )
                fs.rm(path, recursive=True)
            else:
                filesystem().rm(path, recursive=True)
        except TypeError:
            # Some filesystems don't support recursive parameter
            # Use find() to get all files and remove them individually
            files = find(path, filesystem_override=filesystem_override)
            for file_path in reversed(files):  # Remove files before directories
                if filesystem_override:
                    fs, _token, paths = fsspec.get_fs_token_paths(
                        filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
                    )
                    fs.rm(file_path)
                else:
                    filesystem().rm(file_path)


def open(path: str, mode: str = "r", filesystem_override: str | None = None, **kwargs):
    if filesystem_override:
        fs, _token, paths = fsspec.get_fs_token_paths(
            filesystem_override, storage_options={"profile": _AWS_PROFILE} if _AWS_PROFILE else None
        )
        return fs.open(path, mode=mode, **kwargs)
    else:
        return filesystem().open(path, mode=mode, **kwargs)


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