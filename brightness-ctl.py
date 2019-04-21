#!/usr/bin/env python3
from pathlib import Path
from sys import exit
from argparse import ArgumentParser
import re
import math

UDEV_HELP = """\
You don't seem to have permission to write to the selected backlight brightness sysfs entry.
Add the below section to your udev rules,
for example in /etc/udev/rules.d/backlight.rules

```
ACTION=="add", SUBSYSTEM=="backlight", KERNEL=="acpi_video0", RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness"
ACTION=="add", SUBSYSTEM=="backlight", KERNEL=="acpi_video0", RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"
```

This allows everyone that is part of the `video` group to write to the brightness entry of the acpi_video0 backlight device.
So after you apply the new rule add yourself to the `video` group and relogin.\
"""


class FsObj:
    def __init__(self, path: Path, cls=int):
        self.path = path
        self.cls = cls

    def get(self):
        return self.cls(self.path.read_text())

    def set(self, v):
        assert type(v) == self.cls
        self.path.write_text(str(v))


def calc_new_brightness(current: int, maxx: int, pct: str) -> int:
    m = re.match(r"^(\+|-)?([1-9][0-9]+|[0-9])%$", pct)
    if not m:
        exit("Invalid change_percentage")
    n = float(m[2])
    if not (n >= 0 and n <= 100):
        exit("Percentage must be between 100 and 0, got {}".format(n))

    diff = int(n / 100 * maxx)
    if m[1] == "+":
        current = min(current + diff, maxx)
    elif m[1] == "-":
        current = max(0, current - diff)
    else:
        current = diff

    assert current >= 0 and current <= maxx

    return current


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "change_percentage",
        help="Percentage in the format of 10%%(set brightness to 10%%), -10%%(10%% less brighter) or +10%%(10%% brighter)",
    )
    parser.add_argument(
        "--dev",
        "-d",
        action="store",
        default="acpi_video0",
        help="sysfs backlight device in /sys/class/backlight you want to control, defaults to acpi_video0",
    )
    args = parser.parse_args()

    dev_path = Path(args.dev)
    if dev_path.is_absolute() or len(dev_path.parts) != 1:
        exit("Invalid device name: {}".format(args.dev))
    backlight = Path("/sys/class/backlight").joinpath(dev_path)

    if not backlight.is_dir():
        exit("Backlight {} not found".format(args.dev))

    max_brightness = FsObj(backlight / "max_brightness").get()
    if max_brightness == 1:
        exit(
            "The backlight in {} doesn't support proper brightness controls", backlight
        )

    brightness = FsObj(backlight / "brightness")

    new = calc_new_brightness(brightness.get(), max_brightness, args.change_percentage)

    try:
        brightness.set(new)
    except PermissionError:
        exit(UDEV_HELP)


if __name__ == "__main__":
    main()
