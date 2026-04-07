"""Parsers for human-readable values such as file sizes."""

__version__ = "0.1.0"


class FromHumanized:
    """Convert human-readable strings into their machine-readable values."""

    @staticmethod
    def from_humanized_size(size_str: str) -> int:
        """Parse a string like ``"1.5MB"`` into a byte count.

        :raises ValueError: if the unit is unknown or the number is malformed.
        """
        size_str = size_str.strip().upper()
        units = {
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4,
            'PB': 1024**5,
            'B': 1,
        }

        for unit, multiplier in units.items():
            nstr = size_str.replace(' ', '').lower()
            nunit = unit.lower()

            if nstr.endswith(nunit):
                try:
                    number = float(nstr[:-len(nunit)].strip())
                    return int(number * multiplier)
                except ValueError:
                    raise ValueError(f"Invalid size format: {size_str}")
        raise ValueError(f"Unknown size unit in: {size_str}")

if __name__ == "__main__":
    assert (FromHumanized.from_humanized_size("10B") == 10)
    assert (FromHumanized.from_humanized_size("1KB") == 1024)
    assert (FromHumanized.from_humanized_size("1.5MB") == int(1.5 * 1024**2))
    assert (FromHumanized.from_humanized_size("2GB") == 2 * 1024**3)
    assert (FromHumanized.from_humanized_size("0.5TB") == int(0.5 * 1024**4))
    assert (FromHumanized.from_humanized_size("1PB") == 1024**5)
    assert (FromHumanized.from_humanized_size("  2 mb ") == 2 * 1024**2)
    assert (FromHumanized.from_humanized_size("3.5 gb") == int(3.5 * 1024**3))

    invalid_test_cases = [
        ("100", None),  # No unit
        ("5XB", None),  # Unknown unit
        ("abc", None),  # Not a number
    ]

    for test_str, expected in invalid_test_cases:
        try:
            result = FromHumanized.from_humanized_size(test_str)
            assert False, f"Expected ValueError for input: {test_str}"
        except ValueError:
            pass  # Expected exception