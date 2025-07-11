import os


def env_bool(env_var: str, default: str = "false") -> bool:
    """Parse boolean environment variable.

    Args:
        env_var: Environment variable name.
        default: Default value if environment variable is not set.

    Returns:
        Boolean value.

    Raises:
        ValueError: If the environment variable value is invalid.
    """
    value = os.environ.get(env_var, default).lower()

    if value in ("true", "t", "1", "yes", "y", "on"):
        return True
    if value in ("false", "f", "0", "no", "n", "off"):
        return False
    msg = f"Invalid boolean value for {env_var}: '{value}'. Use true/false, 1/0, yes/no, on/off"
    raise ValueError(msg)
