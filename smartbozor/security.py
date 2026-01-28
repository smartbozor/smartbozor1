import os

from django.core.signing import TimestampSigner

camera_signer = TimestampSigner(salt="camera-websocket-token", sep=":@:")

try:
    import pwd  # Unix-only module
except ImportError:
    pwd = None


def switch_to_www_data():
    """
    On Unix, try to switch process user/group to www-data.
    On Windows (no pwd module), this becomes a no-op with a debug message.
    """
    if pwd is None:
        # Running on a non-Unix platform; just log and return.
        print("switch_to_www_data: pwd module not available on this platform; skipping user switch.")
        return

    try:
        user = pwd.getpwnam("www-data")
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)
        print(f"Switched to {user.pw_name}:{user.pw_name}")
    except Exception as e:
        print(f"Cannot switch user: {e}")
